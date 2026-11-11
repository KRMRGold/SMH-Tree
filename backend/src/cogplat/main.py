"""FastAPI application factory and authenticated M0 endpoints."""

from __future__ import annotations

import secrets
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cogplat import __version__
from cogplat.config import Settings, ensure_data_dir, load_settings
from cogplat.db.connection import apply_migrations, connect_db


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

    @app.get("/v1/health", dependencies=[Depends(require_token)])
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "version": __version__,
            "schema_version": schema_version,
            "capabilities": {
                "sqlite": True,
                "sqlite_fts5": True,
                "branching": False,
                "chat": False,
            },
        }

    @app.get("/v1/openapi.json", dependencies=[Depends(require_token)])
    def openapi_schema() -> dict[str, object]:
        return get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )

    return app
