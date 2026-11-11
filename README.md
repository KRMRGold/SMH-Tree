# SMH-Tree

A local-first desktop platform for persistent, branching, memory-backed AI conversations with an epistemic record of claims, evidence, and contradictions.

## Project status

**Current milestone:** M0 — Skeleton (candidate implementation).

The authoritative implementation plan is [`Build-spec.md`](Build-spec.md). The broader product vision is [`Distributed-Cognitive-Architecture.md`](Distributed-Cognitive-Architecture.md).

## Backend development

Requirements: Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

From the `backend/` directory:

```powershell
uv sync --dev
$env:COGPLAT_API_TOKEN = (python -c "import secrets; print(secrets.token_urlsafe(32))")
uv run uvicorn cogplat.main:create_app --factory --host 127.0.0.1 --port 8000
```

The backend refuses to start without `COGPLAT_API_TOKEN`. Set `COGPLAT_DATA_DIR` to override the platform's default application-data directory.

Every API request, including health and OpenAPI, requires:

```text
Authorization: Bearer <COGPLAT_API_TOKEN>
```

The API binds to loopback only. Do not expose it to a network interface.

Run tests from `backend/`:

```powershell
uv run pytest
```

## Current API

- `GET /v1/health` — authenticated backend, package, and database status.
- `GET /v1/openapi.json` — authenticated OpenAPI schema.

The remaining API and application features are introduced by the milestones in the build specification.
