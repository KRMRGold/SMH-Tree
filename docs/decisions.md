# Decisions

This is the project's living decision log. Add concise entries when an implementation choice resolves an ambiguity or departs from the build specification.

## Initial implementation decisions

- **Workflow:** Adopted Development State Machine Workflow 1.6.0 as recorded in `Build-spec.md`; follow the current canonical workflow (1.6.1 at implementation start) unless explicitly pinned. Use the current Testing and Verification and Context Continuity modules.
- **ASGI server:** Add Uvicorn as a runtime dependency because FastAPI is an ASGI application and needs an ASGI server to run outside tests. This does not change the locked FastAPI/Pydantic backend choice.
- **Test client:** Add HTTPX as a development dependency because FastAPI's `TestClient` uses it for in-process HTTP integration tests.
- **Package build backend:** Use Setuptools as the PEP 517 build backend so the `src/` package can be installed by `uv`; it is a build-time dependency only.
- **Local API token:** Require `COGPLAT_API_TOKEN` in the backend environment. Electron will generate and pass a fresh token in M8; M0 does not invent a fallback or hard-code a credential.
- **Data directory:** Resolve `COGPLAT_DATA_DIR` first, otherwise use the platform's standard per-user application-data location and append `CognitivePlatform`.
- **Migrations:** Apply numbered SQL migrations transactionally and record each applied version. The app factory ensures the database schema is current before serving requests.
- **API documentation:** Disable FastAPI's default unprotected documentation routes and expose the OpenAPI schema only at authenticated `/v1/openapi.json`, consistent with the spec's requirement that every request be authenticated.
- **Existing design filename:** Preserve the existing `Build-spec.md` path rather than create a duplicate `BUILD_SPEC.md` during M0. The repository's current source filename is retained; README links to it directly.
