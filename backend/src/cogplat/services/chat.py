"""Chat run lifecycle and SSE event production."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import AsyncIterator

from cogplat.domain.chat import ChatMessage
from cogplat.domain.ids import new_id
from cogplat.domain.time import utc_now
from cogplat.providers.base import ModelProvider
from cogplat.repos import conversations as conversation_repo
from cogplat.repos import runs as run_repo
from cogplat.services import conversations as conversation_service
from cogplat.services import remote_gate

RemoteNotAllowed = remote_gate.RemoteNotAllowed


class ResourceNotFound(Exception):
    """The requested branch or run does not exist."""


def prepare_chat(
    connection: sqlite3.Connection,
    branch_id: str,
    content: str,
    provider_id: str,
    model: str,
    allow_remote: bool,
) -> tuple[dict[str, object], dict[str, object], list[ChatMessage]]:
    branch = conversation_repo.get_branch(connection, branch_id)
    if branch is None:
        raise ResourceNotFound("Branch not found.")

    with connection:
        user_message = conversation_repo.insert_message(
            connection, branch_id, "user", "user", content, None
        )
        history = conversation_service.resolve_history(connection, branch_id)
        run = run_repo.create_run(
            connection,
            "chat_turn",
            str(branch["conversation_id"]),
            branch_id,
            allow_remote,
            {
                "provider": provider_id,
                "model": model,
                "user_message_id": str(user_message["id"]),
                "message_refs": [str(item["id"]) for item in history],
            },
        )
        step = run_repo.create_step(connection, str(run["id"]), "provider_stream")

    messages = [ChatMessage(role=str(item["role"]), content=str(item["content"])) for item in history]
    return run, step, messages


async def stream_chat_events(
    connection: sqlite3.Connection,
    run: dict[str, object],
    step: dict[str, object],
    branch_id: str,
    provider_id: str,
    provider: ModelProvider,
    model: str,
    messages: list[ChatMessage],
    api_key: str | None = None,
) -> AsyncIterator[tuple[str, dict[str, object]]]:
    chunks: list[str] = []
    run_id = str(run["id"])
    try:
        options: dict[str, object] = {}
        if api_key:
            options["api_key"] = api_key
        run_input = run.get("input_json") or {}
        remote_gate.authorize_and_audit(connection, run, provider, messages, run_input.get("message_refs", []))
        async for token in provider.stream_chat(model, messages, **options):
            if not isinstance(token, str):
                raise TypeError("Provider yielded a non-text token.")
            if token:
                chunks.append(token)
                yield "token", {"run_id": run_id, "token": token}

        assistant_content = "".join(chunks)
        with connection:
            assistant_message = conversation_repo.insert_message(
                connection,
                branch_id,
                "assistant",
                provider.label,
                assistant_content,
                f"{provider_id}:{model}",
            )
            run_repo.finish_step(connection, str(step["id"]), "succeeded")
            run_repo.finish_run(
                connection,
                run_id,
                "succeeded",
                {"assistant_message_id": str(assistant_message["id"])},
            )
        yield "done", {"run_id": run_id, "message": assistant_message}
    except asyncio.CancelledError:
        with connection:
            run_repo.finish_step(connection, str(step["id"]), "cancelled", "Client disconnected.")
            run_repo.finish_run(connection, run_id, "cancelled", error="Client disconnected.")
        raise
    except Exception as exc:
        message = str(exc) if str(exc) else "Provider request failed."
        with connection:
            run_repo.finish_step(connection, str(step["id"]), "failed", message[:500])
            run_repo.finish_run(connection, run_id, "failed", error=message[:1000])
        yield "error", {"run_id": run_id, "code": "provider_error", "message": message[:500]}
