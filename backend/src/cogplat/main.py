"""FastAPI application factory and authenticated API endpoints."""

from __future__ import annotations

import json
import secrets
from collections.abc import Mapping

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cogplat import __version__
from cogplat.config import Settings, ensure_data_dir, load_settings
from cogplat.db.connection import apply_migrations, connect_db
from cogplat.domain.chat import ChatRequest
from cogplat.domain.context import ContextCompileError
from cogplat.domain.memory import MemoryCreate, MemoryLifecycleUpdate
from cogplat.domain.epistemic import (
    ClaimAssessmentCreate, ClaimCreate, ClaimRelationCreate, ClaimStatusCreate,
    EvidenceCreate, OpenQuestionCreate, OpenQuestionUpdate, SourceCreate,
)
from cogplat.domain.conversation import (
    BranchFork,
    ConversationCreate,
    MessageCreate,
    ProjectCreate,
)
from cogplat.providers.base import ModelProvider, ProviderError
from cogplat.providers.registry import build_registry
from cogplat.repos import context_snapshots as snapshot_repo
from cogplat.repos import runs as run_repo
from cogplat.repos import transmissions as transmission_repo
from cogplat.services import chat as chat_service
from cogplat.services import conversations as conversation_service
from cogplat.services import memory as memory_service
from cogplat.services import epistemic as epistemic_service
from cogplat.services.permissions import InvalidAccessContext, build_access_context


def create_app(
    settings: Settings | None = None,
    providers: Mapping[str, ModelProvider] | None = None,
) -> FastAPI:
    """Create the API, prepare its local database, and require bearer auth."""

    runtime_settings = settings if settings is not None else load_settings()
    data_dir = ensure_data_dir(runtime_settings.data_dir)
    database_path = data_dir / "app.db"

    connection = connect_db(database_path)
    try:
        schema_version = apply_migrations(connection)
    finally:
        connection.close()

    app = FastAPI(
        title="SMH-Tree API",
        version=__version__,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    app.state.database_path = database_path
    app.state.providers = dict(providers) if providers is not None else build_registry(runtime_settings)
    bearer = HTTPBearer(auto_error=False)

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            error = {
                "code": detail.get("code", "http_error"),
                "message": detail.get("message", "Request failed."),
                "details": detail.get("details", {}),
            }
        else:
            error = {"code": "http_error", "message": str(detail), "details": {}}
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": error},
            headers=exc.headers,
        )

    def require_token(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> None:
        if credentials is None or not secrets.compare_digest(
            credentials.credentials, runtime_settings.api_token
        ):
            raise HTTPException(
                status_code=401,
                detail={"code": "unauthorized", "message": "A valid bearer token is required."},
                headers={"WWW-Authenticate": "Bearer"},
            )

    def open_database():
        connection = connect_db(app.state.database_path)
        try:
            yield connection
        finally:
            connection.close()

    def not_found(message: str = "Resource not found.") -> HTTPException:
        return HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": message},
        )

    @app.get("/v1/health", dependencies=[Depends(require_token)])
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "version": __version__,
            "schema_version": schema_version,
            "capabilities": {
                "sqlite": True,
                "sqlite_fts5": True,
                "branching": True,
                "chat": True,
                "streaming": True,
            "memory": True,
            "epistemic": True,
            },
        }

    @app.get("/v1/projects", dependencies=[Depends(require_token)])
    def get_projects(connection=Depends(open_database)) -> dict[str, object]:
        return {"items": conversation_service.list_projects(connection)}

    @app.post("/v1/projects", status_code=201, dependencies=[Depends(require_token)])
    def post_project(
        payload: ProjectCreate, connection=Depends(open_database)
    ) -> dict[str, object]:
        with connection:
            project = conversation_service.create_project(
                connection, payload.name, payload.description
            )
        return project

    @app.get("/v1/conversations", dependencies=[Depends(require_token)])
    def get_conversations(
        project_id: str | None = Query(default=None),
        connection=Depends(open_database),
    ) -> dict[str, object]:
        return {"items": conversation_service.list_conversations(connection, project_id)}

    @app.post("/v1/conversations", status_code=201, dependencies=[Depends(require_token)])
    def post_conversation(
        payload: ConversationCreate, connection=Depends(open_database)
    ) -> dict[str, object]:
        try:
            return conversation_service.create_conversation(
                connection, payload.title, payload.project_id
            )
        except conversation_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc

    @app.get(
        "/v1/conversations/{conversation_id}/branches",
        dependencies=[Depends(require_token)],
    )
    def get_branches(
        conversation_id: str, connection=Depends(open_database)
    ) -> dict[str, object]:
        try:
            return {"items": conversation_service.list_branches(connection, conversation_id)}
        except conversation_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc

    @app.post("/v1/branches", status_code=201, dependencies=[Depends(require_token)])
    def post_branch(
        payload: BranchFork, connection=Depends(open_database)
    ) -> dict[str, object]:
        try:
            return conversation_service.fork_branch(
                connection, payload.parent_branch_id, payload.fork_message_id, payload.name
            )
        except conversation_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc
        except conversation_service.InvalidFork as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "invalid_fork", "message": str(exc)},
            ) from exc

    @app.get(
        "/v1/branches/{branch_id}/messages",
        dependencies=[Depends(require_token)],
    )
    def get_messages(
        branch_id: str, connection=Depends(open_database)
    ) -> dict[str, object]:
        try:
            return {"items": conversation_service.resolve_history(connection, branch_id)}
        except conversation_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc

    @app.post(
        "/v1/branches/{branch_id}/messages",
        status_code=201,
        dependencies=[Depends(require_token)],
    )
    def post_message(
        branch_id: str,
        payload: MessageCreate,
        connection=Depends(open_database),
    ) -> dict[str, object]:
        try:
            return conversation_service.append_message(
                connection, branch_id, payload.role, payload.participant,
                payload.content, payload.model_ref,
            )
        except conversation_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc
        except Exception as exc:
            import sqlite3
            if isinstance(exc, sqlite3.IntegrityError):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "message_conflict", "message": "Message could not be appended."},
                ) from exc
            raise

    @app.get("/v1/providers", dependencies=[Depends(require_token)])
    def get_providers() -> dict[str, object]:
        return {
            "items": [
                {"id": key, "label": provider.label, "is_remote": provider.is_remote}
                for key, provider in app.state.providers.items()
            ]
        }

    @app.get("/v1/providers/{provider_id}/models", dependencies=[Depends(require_token)])
    async def get_provider_models(
        provider_id: str,
        x_provider_api_key: str | None = Header(default=None, alias="X-Provider-API-Key"),
    ) -> dict[str, object]:
        provider = app.state.providers.get(provider_id)
        if provider is None:
            raise not_found("Provider not found.")
        try:
            if provider.is_remote:
                models = await provider.list_models(api_key=x_provider_api_key)
            else:
                models = await provider.list_models()
            return {"items": models}
        except ProviderError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "provider_error", "message": str(exc)},
            ) from exc

    @app.post(
        "/v1/branches/{branch_id}/chat",
        dependencies=[Depends(require_token)],
    )
    async def post_chat(
        branch_id: str,
        payload: ChatRequest,
        request: Request,
        x_provider_api_key: str | None = Header(default=None, alias="X-Provider-API-Key"),
    ):
        provider = app.state.providers.get(payload.provider)
        if provider is None:
            raise not_found("Provider not found.")
        if provider.is_remote and not payload.allow_remote:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "remote_not_allowed",
                    "message": "Remote transmission is disabled for this chat turn.",
                },
            )

        connection = connect_db(app.state.database_path)
        try:
            run, step, messages = chat_service.prepare_chat(
                connection, branch_id, payload.content, payload.provider,
                payload.model, payload.allow_remote,
                runtime_settings.default_max_input_tokens,
                runtime_settings.default_reserve_output_tokens,
                provider.label,
                provider.is_remote,
            )
        except chat_service.ResourceNotFound as exc:
            connection.close()
            raise not_found(str(exc)) from exc
        except ContextCompileError as exc:
            connection.close()
            raise HTTPException(
                status_code=422,
                detail={"code": exc.code, "message": str(exc), "details": exc.details},
            ) from exc
        except Exception:
            connection.close()
            raise

        async def event_stream():
            try:
                async for event, data in chat_service.stream_chat_events(
                    connection, run, step, branch_id, payload.provider, provider,
                    payload.model, messages, api_key=x_provider_api_key,
                ):
                    yield f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"
            finally:
                connection.close()

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )



    @app.get("/v1/memory", dependencies=[Depends(require_token)])
    def get_memory_items(
        q: str | None = Query(default=None, max_length=500),
        scope: str | None = Query(default=None),
        state: str = Query(default="active"),
        project_id: str | None = Query(default=None),
        conversation_id: str | None = Query(default=None),
        branch_id: str | None = Query(default=None),
        agent_id: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        connection=Depends(open_database),
    ) -> dict[str, object]:
        try:
            context = build_access_context(
                connection, project_id=project_id, conversation_id=conversation_id,
                branch_id=branch_id, agent_id=agent_id,
            )
            items = memory_service.list_memory(
                connection, context, query=q, scope=scope, state=state,
                limit=limit, offset=offset,
            )
            return {"items": items}
        except InvalidAccessContext as exc:
            raise HTTPException(status_code=422, detail={
                "code": "invalid_memory_context", "message": str(exc)
            }) from exc
        except memory_service.InvalidMemoryScope as exc:
            raise HTTPException(status_code=422, detail={
                "code": "invalid_memory_filter", "message": str(exc)
            }) from exc

    @app.post("/v1/memory", status_code=201, dependencies=[Depends(require_token)])
    def post_memory_item(payload: MemoryCreate, connection=Depends(open_database)):
        try:
            return memory_service.create_memory(connection, payload)
        except memory_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc
        except memory_service.InvalidMemoryScope as exc:
            raise HTTPException(status_code=422, detail={
                "code": "invalid_memory_scope", "message": str(exc)
            }) from exc

    @app.get("/v1/memory/{memory_id}", dependencies=[Depends(require_token)])
    def get_memory_item(
        memory_id: str,
        project_id: str | None = Query(default=None),
        conversation_id: str | None = Query(default=None),
        branch_id: str | None = Query(default=None),
        agent_id: str | None = Query(default=None),
        connection=Depends(open_database),
    ):
        try:
            context = build_access_context(
                connection, project_id=project_id, conversation_id=conversation_id,
                branch_id=branch_id, agent_id=agent_id,
            )
            return memory_service.get_memory(connection, memory_id, context)
        except (memory_service.ResourceNotFound, InvalidAccessContext) as exc:
            raise not_found(str(exc)) from exc

    @app.patch("/v1/memory/{memory_id}", dependencies=[Depends(require_token)])
    def patch_memory_item(
        memory_id: str, payload: MemoryLifecycleUpdate,
        connection=Depends(open_database),
    ):
        try:
            return memory_service.update_memory_lifecycle(connection, memory_id, payload)
        except memory_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc
        except memory_service.InvalidMemoryTransition as exc:
            raise HTTPException(status_code=409, detail={
                "code": "invalid_memory_transition", "message": str(exc)
            }) from exc



    @app.get("/v1/sources", dependencies=[Depends(require_token)])
    def get_sources(
        project_id: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        connection=Depends(open_database),
    ):
        try:
            context = build_access_context(connection, project_id=project_id)
            return {"items": epistemic_service.list_sources(connection, context, limit, offset)}
        except InvalidAccessContext as exc:
            raise HTTPException(status_code=422, detail={
                "code": "invalid_epistemic_context", "message": str(exc)
            }) from exc

    @app.post("/v1/sources", status_code=201, dependencies=[Depends(require_token)])
    def post_source(payload: SourceCreate, connection=Depends(open_database)):
        try:
            return epistemic_service.create_source(connection, payload)
        except epistemic_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc
        except epistemic_service.InvalidEpistemicRecord as exc:
            raise HTTPException(status_code=422, detail={
                "code": "invalid_epistemic_record", "message": str(exc)
            }) from exc

    @app.get("/v1/claims", dependencies=[Depends(require_token)])
    def get_claims(
        q: str | None = Query(default=None, max_length=500),
        project_id: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        connection=Depends(open_database),
    ):
        try:
            context = build_access_context(connection, project_id=project_id)
            return {"items": epistemic_service.list_claims(
                connection, context, query=q, limit=limit, offset=offset
            )}
        except InvalidAccessContext as exc:
            raise HTTPException(status_code=422, detail={
                "code": "invalid_epistemic_context", "message": str(exc)
            }) from exc

    @app.post("/v1/claims", status_code=201, dependencies=[Depends(require_token)])
    def post_claim(payload: ClaimCreate, connection=Depends(open_database)):
        try:
            return epistemic_service.create_claim(connection, payload)
        except epistemic_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc

    @app.get("/v1/claims/{claim_id}", dependencies=[Depends(require_token)])
    def get_claim(
        claim_id: str,
        project_id: str | None = Query(default=None),
        connection=Depends(open_database),
    ):
        try:
            context = build_access_context(connection, project_id=project_id)
            return epistemic_service.get_claim(connection, claim_id, context)
        except (epistemic_service.ResourceNotFound, InvalidAccessContext) as exc:
            raise not_found(str(exc)) from exc

    @app.post("/v1/claims/{claim_id}/status", status_code=201, dependencies=[Depends(require_token)])
    def post_claim_status(
        claim_id: str,
        payload: ClaimStatusCreate,
        project_id: str | None = Query(default=None),
        connection=Depends(open_database),
    ):
        try:
            context = build_access_context(connection, project_id=project_id)
            return epistemic_service.append_claim_status(connection, claim_id, payload, context)
        except epistemic_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc
        except (epistemic_service.InvalidEpistemicRecord, InvalidAccessContext) as exc:
            raise HTTPException(status_code=422, detail={
                "code": "invalid_epistemic_record", "message": str(exc)
            }) from exc

    @app.post("/v1/claims/{claim_id}/assessments", status_code=201, dependencies=[Depends(require_token)])
    def post_claim_assessment(
        claim_id: str,
        payload: ClaimAssessmentCreate,
        project_id: str | None = Query(default=None),
        connection=Depends(open_database),
    ):
        try:
            context = build_access_context(connection, project_id=project_id)
            return epistemic_service.append_claim_assessment(connection, claim_id, payload, context)
        except epistemic_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc
        except InvalidAccessContext as exc:
            raise HTTPException(status_code=422, detail={
                "code": "invalid_epistemic_context", "message": str(exc)
            }) from exc

    @app.post("/v1/claims/{claim_id}/evidence", status_code=201, dependencies=[Depends(require_token)])
    def post_claim_evidence(
        claim_id: str,
        payload: EvidenceCreate,
        project_id: str | None = Query(default=None),
        connection=Depends(open_database),
    ):
        try:
            context = build_access_context(connection, project_id=project_id)
            return epistemic_service.add_evidence(connection, claim_id, payload, context)
        except epistemic_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc
        except InvalidAccessContext as exc:
            raise HTTPException(status_code=422, detail={
                "code": "invalid_epistemic_context", "message": str(exc)
            }) from exc

    @app.post("/v1/claims/{claim_id}/relations", status_code=201, dependencies=[Depends(require_token)])
    def post_claim_relation(
        claim_id: str,
        payload: ClaimRelationCreate,
        project_id: str | None = Query(default=None),
        connection=Depends(open_database),
    ):
        try:
            context = build_access_context(connection, project_id=project_id)
            return epistemic_service.add_relation(connection, claim_id, payload, context)
        except epistemic_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc
        except (epistemic_service.InvalidEpistemicRecord, InvalidAccessContext) as exc:
            raise HTTPException(status_code=422, detail={
                "code": "invalid_epistemic_record", "message": str(exc)
            }) from exc

    @app.get("/v1/open-questions", dependencies=[Depends(require_token)])
    def get_open_questions(
        project_id: str | None = Query(default=None),
        state: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        connection=Depends(open_database),
    ):
        try:
            context = build_access_context(connection, project_id=project_id)
            if state is not None and state not in {"open", "investigating", "answered", "dropped"}:
                raise HTTPException(status_code=422, detail={
                    "code": "invalid_question_state", "message": "Unknown open-question state."
                })
            return {"items": epistemic_service.list_open_questions(
                connection, context, state, limit, offset
            )}
        except InvalidAccessContext as exc:
            raise HTTPException(status_code=422, detail={
                "code": "invalid_epistemic_context", "message": str(exc)
            }) from exc

    @app.post("/v1/open-questions", status_code=201, dependencies=[Depends(require_token)])
    def post_open_question(payload: OpenQuestionCreate, connection=Depends(open_database)):
        try:
            return epistemic_service.create_open_question(connection, payload)
        except epistemic_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc

    @app.patch("/v1/open-questions/{question_id}", dependencies=[Depends(require_token)])
    def patch_open_question(
        question_id: str,
        payload: OpenQuestionUpdate,
        project_id: str | None = Query(default=None),
        connection=Depends(open_database),
    ):
        try:
            context = build_access_context(connection, project_id=project_id)
            return epistemic_service.update_open_question(
                connection, question_id, payload, context
            )
        except epistemic_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc
        except (epistemic_service.InvalidEpistemicRecord, InvalidAccessContext) as exc:
            raise HTTPException(status_code=409, detail={
                "code": "invalid_question_transition", "message": str(exc)
            }) from exc

    @app.get("/v1/transmissions", dependencies=[Depends(require_token)])
    def get_transmissions(connection=Depends(open_database)) -> dict[str, object]:
        return {"items": transmission_repo.list_transmissions(connection)}

    @app.get("/v1/runs/{run_id}", dependencies=[Depends(require_token)])
    def get_run(run_id: str, connection=Depends(open_database)) -> dict[str, object]:
        run = run_repo.get_run(connection, run_id)
        if run is None:
            raise not_found("Run not found.")
        return run

    @app.get("/v1/runs/{run_id}/context", dependencies=[Depends(require_token)])
    def get_run_context(run_id: str, connection=Depends(open_database)) -> dict[str, object]:
        run = run_repo.get_run(connection, run_id)
        if run is None:
            raise not_found("Run not found.")
        snapshot = snapshot_repo.get_snapshot(connection, run_id)
        if snapshot is None:
            raise not_found("Context snapshot not found for this run.")
        return snapshot

    @app.get("/v1/openapi.json", dependencies=[Depends(require_token)])
    def openapi_schema() -> dict[str, object]:
        return get_openapi(title=app.title, version=app.version, routes=app.routes)

    return app
