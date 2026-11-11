# Decisions

This is the project's living decision log. Add concise entries when an implementation choice resolves an ambiguity or departs from the build specification.

## Initial implementation decisions

- **Workflow:** Adopted Development State Machine Workflow 1.6.0 as recorded in Build-spec.md; follow the current canonical workflow (1.6.1 at implementation start) unless explicitly pinned. Use Testing and Verification and Context Continuity modules.
- **ASGI server:** Add Uvicorn as a runtime dependency because FastAPI is an ASGI application and needs an ASGI server to run outside tests.
- **Test client:** Use HTTPX2 as a development dependency because current Starlette TestClient uses it; plain HTTPX is deprecated by Starlette.
- **Package build backend:** Use Setuptools as the PEP 517 build backend so the src/ package can be installed by uv; it is a build-time dependency only.
- **Local API token:** Require COGPLAT_API_TOKEN; Electron will generate and pass a fresh token in M8.
- **Data directory:** Resolve COGPLAT_DATA_DIR first, otherwise use the platform's standard per-user application-data location and append CognitivePlatform.
- **Migrations:** Apply numbered SQL migrations transactionally and record each applied version.
- **API documentation:** Disable FastAPI's default unprotected documentation routes and expose OpenAPI only at authenticated /v1/openapi.json.
- **Existing design filename:** Preserve Build-spec.md; do not create a duplicate BUILD_SPEC.md.

## M1 decisions

- **UUIDv7:** Implement UUIDv7 generation using Python's standard-library uuid.UUID and secrets, because Python 3.12 does not provide uuid.uuid7(). This avoids adding a dependency and keeps ID generation in Python.
- **Branching from inherited history:** A branch may be forked from any message visible in the selected parent branch, including a message inherited from an ancestor. History resolution therefore follows the message's owning branch through the ancestry chain instead of assuming the fork message belongs to the immediate parent branch. This preserves the documented fork-at-any-message behavior and correctly handles fork-of-fork cases.
- **Message API:** Add POST /v1/branches/{branch_id}/messages as the M1 append-only message endpoint. The build spec requires message persistence and branch history but does not name a standalone message route; this endpoint is the smallest direct API for exercising that capability before chat streaming arrives in M2.
- **Database schema:** M1 uses the existing M0 tables and FTS triggers; no schema migration is needed.

## M2 decisions

- **Provider HTTP transport:** Use Python's standard-library `urllib` with `asyncio.to_thread` for streaming and model discovery. This avoids adding an unlisted runtime HTTP dependency while keeping the adapter interface asynchronous.
- **Provider endpoints:** Configure default Ollama and OpenAI-compatible base URLs through `COGPLAT_OLLAMA_BASE_URL` and `COGPLAT_OPENAI_COMPAT_BASE_URL`; keep provider API keys out of settings and SQLite.
- **Remote API key transport:** Accept a remote provider key only through the per-request `X-Provider-API-Key` header. Do not store it in run records, provider configuration, or logs.
- **M2 remote opt-in boundary:** Reject remote chat requests unless `allow_remote=true`. The complete deterministic remote gate, memory-scope filtering, and transmission audit are intentionally M3 work.
- **Run persistence:** Reuse the existing `runs` and `run_steps` tables from migration 0001; M2 requires no schema migration.
- **Provider configuration scope:** M2 exposes provider listing and model discovery for environment-configured providers. Persistent provider creation via `POST /v1/providers` is deferred rather than adding a partial configuration store.


## M3 decisions

- **Audit byte count:** UTF-8 byte length of compact JSON role/content messages at the provider-adapter boundary; excludes HTTP headers and provider/model envelope fields.
- **Audit ordering:** Commit the transmission ledger row before invoking the provider stream. Failed provider calls remain auditable because a request may already have reached the provider.
- **Append-only enforcement:** SQLite triggers reject updates and deletes from `remote_transmissions`; M3 adds migration 0002 rather than recreating the M0 table.
- **Memory scope timing:** Global/user filtering is a deterministic helper with opt-in settings defaulting false. M5 must call it when the context compiler begins adding memory to chat packets; M3 has no memory context compiler to wire yet.
- **Audit API:** Add authenticated `GET /v1/transmissions`; pagination and UI presentation are deferred.
