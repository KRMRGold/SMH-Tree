"""Checkpointed LangGraph workflows for chat turns and explicit claim extraction."""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from typing import TypedDict

# The graph state contains only JSON-compatible primitives. Keep msgpack's
# restrictive deserialization mode enabled before importing the checkpoint stack.
os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from cogplat.domain.chat import ChatMessage
from cogplat.domain.context import CompileRequest, ContextCompileError
from cogplat.domain.epistemic import ClaimType
from cogplat.domain.ids import new_id
from cogplat.domain.time import utc_now
from cogplat.providers.base import ModelProvider
from cogplat.repos import context_snapshots as snapshot_repo
from cogplat.repos import conversations as conversation_repo
from cogplat.repos import epistemic as epistemic_repo
from cogplat.repos import runs as run_repo
from cogplat.services import context_compiler, conversations as conversation_service
from cogplat.services import remote_gate
from cogplat.services.permissions import build_access_context


class ChatState(TypedDict, total=False):
    run_id: str
    branch_id: str
    user_message_id: str
    compile_step_id: str
    content: str
    provider_id: str
    model: str
    allow_remote: bool
    messages: list[dict[str, str]]
    context_source_refs: list[str]
    provider_step_id: str
    assistant_content: str
    assistant_message: dict[str, object]


class ExtractedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    claim_type: ClaimType
    text: str = Field(min_length=1, max_length=20_000)
    evidence_excerpt: str = Field(min_length=1, max_length=20_000)


class ExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    claims: list[ExtractedClaim] = Field(max_length=30)


class ExtractState(TypedDict, total=False):
    run_id: str
    message_id: str
    project_id: str | None
    content: str
    provider_id: str
    model: str
    allow_remote: bool
    raw_output: str
    claims: list[dict[str, str]]
    output: dict[str, object]


def start_chat(
    connection: sqlite3.Connection, branch_id: str, content: str,
    provider_id: str, model: str, allow_remote: bool,
) -> tuple[dict[str, object], dict[str, object]]:
    """Create durable user/run records; context compilation is the graph's first node."""
    branch = conversation_repo.get_branch(connection, branch_id)
    if branch is None:
        raise LookupError("Branch not found.")
    with connection:
        user_message = conversation_repo.insert_message(
            connection, branch_id, "user", "user", content, None
        )
        run = run_repo.create_run(
            connection, "chat_turn", str(branch["conversation_id"]), branch_id,
            allow_remote, {
                "provider": provider_id, "model": model,
                "user_message_id": str(user_message["id"]),
            },
        )
        compile_step = run_repo.create_step(
            connection, str(run["id"]), "context_compile"
        )
    return run, {
        "run_id": str(run["id"]), "branch_id": branch_id,
        "user_message_id": str(user_message["id"]), "content": content,
        "provider_id": provider_id, "model": model, "allow_remote": allow_remote,
        "compile_step_id": str(compile_step["id"]),
    }


def build_chat_graph(
    connection: sqlite3.Connection, provider: ModelProvider, *,
    provider_label: str, provider_is_remote: bool, api_key: str | None,
    max_input_tokens: int, reserve_output_tokens: int,
):
    async def compile_context_node(state: ChatState) -> dict[str, object]:
        branch = conversation_repo.get_branch(connection, state["branch_id"])
        if branch is None:
            raise LookupError("Branch not found.")
        history = conversation_service.resolve_history(connection, state["branch_id"])
        access = build_access_context(
            connection, branch_id=state["branch_id"],
            allow_remote=state["allow_remote"],
        )
        packet = context_compiler.compile_context(
            connection,
            CompileRequest(
                access_context=access, current_user_message=state["content"],
                current_user_message_id=state["user_message_id"], history=history,
                provider_id=state["provider_id"], provider_label=provider_label,
                provider_is_remote=provider_is_remote, model=state["model"],
                max_input_tokens=max_input_tokens,
                reserve_output_tokens=reserve_output_tokens,
            ),
        )
        packet_data = packet.to_dict()
        run_input = {
            "provider": state["provider_id"], "model": state["model"],
            "user_message_id": state["user_message_id"],
            "context_source_refs": packet.source_refs,
            "message_refs": packet.source_refs,
            "compiler_version": packet.compiler_version,
        }
        with connection:
            run_repo.update_run_input(connection, state["run_id"], run_input)
            snapshot_repo.create_snapshot(
                connection, state["run_id"], packet.provider_label,
                packet_data, packet.token_estimate,
            )
            run_repo.finish_step(connection, state["compile_step_id"], "succeeded")
            provider_step = run_repo.create_step(
                connection, state["run_id"], "provider_stream"
            )
        return {
            "messages": [item.model_dump() for item in packet.messages],
            "context_source_refs": packet.source_refs,
            "provider_step_id": str(provider_step["id"]),
        }

    async def authorize_node(state: ChatState) -> dict[str, object]:
        run = run_repo.get_run(connection, state["run_id"])
        remote_gate.authorize_and_audit(
            connection, run, provider,
            [ChatMessage(**item) for item in state["messages"]],
            state.get("context_source_refs", []),
        )
        return {}

    async def stream_node(state: ChatState) -> dict[str, object]:
        writer = get_stream_writer()
        chunks: list[str] = []
        options: dict[str, object] = {}
        if api_key:
            options["api_key"] = api_key
        async for token in provider.stream_chat(
            state["model"], [ChatMessage(**item) for item in state["messages"]],
            **options,
        ):
            if not isinstance(token, str):
                raise TypeError("Provider yielded a non-text token.")
            if token:
                chunks.append(token)
                writer({"kind": "token", "token": token})
        return {"assistant_content": "".join(chunks)}

    async def persist_node(state: ChatState) -> dict[str, object]:
        run = run_repo.get_run(connection, state["run_id"])
        existing = (run or {}).get("output_json") or {}
        message_id = existing.get("assistant_message_id")
        if message_id:
            message = conversation_repo.get_message(connection, str(message_id))
            if message is None:
                raise RuntimeError("Run output references a missing assistant message.")
        else:
            with connection:
                message = conversation_repo.insert_message(
                    connection, state["branch_id"], "assistant", provider.label,
                    state["assistant_content"],
                    f'{state["provider_id"]}:{state["model"]}',
                )
                run_repo.finish_step(
                    connection, state["provider_step_id"], "succeeded"
                )
                run_repo.finish_run(
                    connection, state["run_id"], "succeeded",
                    {"assistant_message_id": str(message["id"])},
                )
        return {"assistant_message": message}

    graph = StateGraph(ChatState)
    graph.add_node("compile_context", compile_context_node)
    graph.add_node("authorize_remote", authorize_node)
    graph.add_node("stream_provider", stream_node)
    graph.add_node("persist_assistant", persist_node)
    graph.add_edge(START, "compile_context")
    graph.add_edge("compile_context", "authorize_remote")
    graph.add_edge("authorize_remote", "stream_provider")
    graph.add_edge("stream_provider", "persist_assistant")
    graph.add_edge("persist_assistant", END)
    return graph


async def stream_chat_workflow(
    database_path: str, connection: sqlite3.Connection,
    provider: ModelProvider, initial_state: dict[str, object], *,
    provider_label: str, provider_is_remote: bool, api_key: str | None,
    max_input_tokens: int, reserve_output_tokens: int,
):
    """Yield the legacy token/done/error SSE events from a checkpointed graph."""
    run_id = str(initial_state["run_id"])
    config = {"configurable": {"thread_id": run_id}}
    async with AsyncSqliteSaver.from_conn_string(database_path) as saver:
        graph = build_chat_graph(
            connection, provider, provider_label=provider_label,
            provider_is_remote=provider_is_remote, api_key=api_key,
            max_input_tokens=max_input_tokens,
            reserve_output_tokens=reserve_output_tokens,
        ).compile(checkpointer=saver)
        try:
            async for item in graph.astream(
                initial_state, config=config, stream_mode="custom"
            ):
                if isinstance(item, dict) and item.get("kind") == "token":
                    yield "token", {"run_id": run_id, "token": item["token"]}
            snapshot = await graph.aget_state(config)
            message = snapshot.values.get("assistant_message")
            if message is None:
                raise RuntimeError("Chat workflow completed without an assistant message.")
            yield "done", {"run_id": run_id, "message": message}
        except BaseException as exc:
            state = await graph.aget_state(config)
            values = state.values
            step_id = values.get("provider_step_id") or values.get("compile_step_id")
            cancelled = isinstance(exc, asyncio.CancelledError)
            if step_id:
                with connection:
                    run_repo.finish_step(
                        connection, str(step_id),
                        "cancelled" if cancelled else "failed", str(exc)[:500],
                    )
            with connection:
                run_repo.finish_run(
                    connection, run_id,
                    "cancelled" if cancelled else "failed", error=str(exc)[:1000],
                )
            raise


def create_extraction_run(
    connection: sqlite3.Connection, message_id: str, provider_id: str,
    model: str, allow_remote: bool,
) -> tuple[dict[str, object], dict[str, object]]:
    message = conversation_repo.get_message(connection, message_id)
    if message is None:
        raise LookupError("Message not found.")
    branch = conversation_repo.get_branch(connection, str(message["branch_id"]))
    conversation = conversation_repo.get_conversation(connection, str(branch["conversation_id"]))
    with connection:
        run = run_repo.create_run(
            connection, "extract_claims", str(conversation["id"]),
            str(branch["id"]), allow_remote,
            {"message_id": message_id, "provider": provider_id, "model": model},
        )
    return run, {
        "run_id": str(run["id"]), "message_id": message_id,
        "project_id": conversation["project_id"], "content": str(message["content"]),
        "provider_id": provider_id, "model": model, "allow_remote": allow_remote,
    }


def build_extraction_graph(
    connection: sqlite3.Connection, provider: ModelProvider, *,
    provider_label: str, api_key: str | None,
):
    async def load_source(state: ExtractState) -> dict[str, object]:
        message = conversation_repo.get_message(connection, state["message_id"])
        if message is None or str(message["content"]) != state["content"]:
            raise LookupError("Source message changed or is unavailable.")
        return {}

    async def generate(state: ExtractState) -> dict[str, object]:
        prompt = (
            "Extract distinct, explicit claims from the supplied message. Return only JSON "
            'matching {"claims":[{"claim_type":"factual|causal|normative|predictive|definition|other",'
            '"text":"concise standalone claim","evidence_excerpt":"exact verbatim substring"}]}. '
            "Use evidence_excerpt copied exactly from the message. Do not infer unsupported "
            "claims, assess truth, assign confidence, or add commentary. Return an empty claims "
            "array when there are no extractable claims.\n\nMESSAGE:\n" + state["content"]
        )
        run = run_repo.get_run(connection, state["run_id"])
        remote_gate.authorize_and_audit(
            connection, run, provider, [ChatMessage(role="user", content=prompt)], [state["message_id"]]
        )
        options: dict[str, object] = {}
        if api_key:
            options["api_key"] = api_key
        chunks: list[str] = []
        async for token in provider.stream_chat(
            state["model"], [ChatMessage(role="user", content=prompt)], **options
        ):
            chunks.append(token)
        return {"raw_output": "".join(chunks)}

    def validate(state: ExtractState) -> dict[str, object]:
        try:
            parsed = ExtractionOutput.model_validate_json(state["raw_output"])
        except ValidationError as exc:
            raise ValueError("Provider output did not match the claim extraction contract.") from exc
        validated: list[dict[str, str]] = []
        for claim in parsed.claims:
            if claim.evidence_excerpt not in state["content"]:
                raise ValueError("Claim evidence must be an exact excerpt from the source message.")
            start = state["content"].find(claim.evidence_excerpt)
            validated.append({
                "claim_type": claim.claim_type, "text": claim.text.strip(),
                "evidence_excerpt": claim.evidence_excerpt,
                "locator": f"chars:{start}-{start + len(claim.evidence_excerpt)}",
            })
        return {"claims": validated}

    async def persist(state: ExtractState) -> dict[str, object]:
        run = run_repo.get_run(connection, state["run_id"])
        existing = (run or {}).get("output_json") or {}
        if existing.get("claim_ids") is not None:
            return {"output": existing}

        now = utc_now()
        claim_ids: list[str] = []
        with connection:
            source = epistemic_repo.create_source(
                connection, project_id=state.get("project_id"), kind="message",
                title=f'Message {state["message_id"]}', uri=None,
                content_hash=None, retrieved_at=None,
            )
            source_id = str(source["id"])
            for item in state["claims"]:
                claim_id = epistemic_repo.create_claim(
                    connection, project_id=state.get("project_id"),
                    claim_type=item["claim_type"], text=item["text"],
                    subject=None, predicate=None, object_value=None,
                    valid_from=None, valid_to=None, origin_kind="extraction",
                    origin_ref=state["message_id"],
                )
                epistemic_repo.create_origin_link(
                    connection, claim_id, target_type="message",
                    target_id=state["message_id"], actor_kind="agent",
                    actor_ref=state["run_id"],
                )
                epistemic_repo.append_evidence(
                    connection, claim_id, source_id=source_id, stance="context",
                    excerpt=item["evidence_excerpt"], locator=item["locator"],
                )
                epistemic_repo.append_status(
                    connection, claim_id, status="proposed", scope="default",
                    policy=None, rationale="Proposed by explicit model-assisted extraction; not verified.",
                    actor_kind="agent", actor_ref=state["run_id"],
                )
                link_id = new_id()
                connection.execute(
                    "INSERT INTO links(id, from_type, from_id, to_type, to_id, rel, "
                    "created_by_kind, created_by_ref, created_at) "
                    "VALUES (?, 'claim', ?, 'run', ?, 'produced_by', 'agent', ?, ?)",
                    (link_id, claim_id, state["run_id"], state["run_id"], now),
                )
                claim_ids.append(claim_id)
            output = {
                "run_id": state["run_id"], "message_id": state["message_id"],
                "source_id": source_id, "claim_ids": claim_ids,
                "claims": state["claims"],
            }
            run_repo.finish_run(connection, state["run_id"], "succeeded", output)
        return {"output": output}

    graph = StateGraph(ExtractState)
    graph.add_node("load_source", load_source)
    graph.add_node("generate_claims", generate)
    graph.add_node("validate_output", validate)
    graph.add_node("persist_claims", persist)
    graph.add_edge(START, "load_source")
    graph.add_edge("load_source", "generate_claims")
    graph.add_edge("generate_claims", "validate_output")
    graph.add_edge("validate_output", "persist_claims")
    graph.add_edge("persist_claims", END)
    return graph


async def run_extraction_workflow(
    database_path: str, connection: sqlite3.Connection,
    provider: ModelProvider, initial_state: dict[str, object], *,
    provider_label: str, api_key: str | None,
) -> dict[str, object]:
    run_id = str(initial_state["run_id"])
    config = {"configurable": {"thread_id": run_id}}
    async with AsyncSqliteSaver.from_conn_string(database_path) as saver:
        graph = build_extraction_graph(
            connection, provider, provider_label=provider_label, api_key=api_key
        ).compile(checkpointer=saver)
        try:
            await graph.ainvoke(initial_state, config=config)
            state = await graph.aget_state(config)
            output = state.values.get("output")
            if output is None:
                raise RuntimeError("Extraction completed without a persisted result.")
            return output
        except Exception as exc:
            with connection:
                run_repo.finish_run(connection, run_id, "failed", error=str(exc)[:1000])
            raise
