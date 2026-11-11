"""FastAPI application factory and authenticated API endpoints."""

from __future__ import annotations

import secrets

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cogplat import __version__
from cogplat.config import Settings, ensure_data_dir, load_settings
from cogplat.db.connection import apply_migrations, connect_db
from cogplat.domain.conversation import (
    BranchFork,
    ConversationCreate,
    MessageCreate,
    ProjectCreate,
)
from cogplat.services import conversations as conversation_service


def create_app(settings: Settings | None = None) -> FastAPI:
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
                "chat": False,
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
        return {
            "items": conversation_service.list_conversations(connection, project_id)
        }

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
            return {
                "items": conversation_service.list_branches(connection, conversation_id)
            }
        except conversation_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc

    @app.post("/v1/branches", status_code=201, dependencies=[Depends(require_token)])
    def post_branch(
        payload: BranchFork, connection=Depends(open_database)
    ) -> dict[str, object]:
        try:
            return conversation_service.fork_branch(
                connection,
                payload.parent_branch_id,
                payload.fork_message_id,
                payload.name,
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
            return {
                "items": conversation_service.resolve_history(connection, branch_id)
            }
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
                connection,
                branch_id,
                payload.role,
                payload.participant,
                payload.content,
                payload.model_ref,
            )
        except conversation_service.ResourceNotFound as exc:
            raise not_found(str(exc)) from exc
        except Exception as exc:
            # Keep raw SQLite details out of the API response.
            import sqlite3

            if isinstance(exc, sqlite3.IntegrityError):
                raise HTTPException(
                    status_code=409,
                    detail={"code": "message_conflict", "message": "Message could not be appended."},
                ) from exc
            raise

    @app.get("/v1/openapi.json", dependencies=[Depends(require_token)])
    def openapi_schema() -> dict[str, object]:
        return get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )

    return app
