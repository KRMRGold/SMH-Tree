# SMH-Tree

A local-first desktop platform for persistent, branching, memory-backed AI conversations with an epistemic record of claims, evidence, and contradictions.

## Project status

**Current milestone:** M1 — Conversations and branching (candidate backend 0.1.0).

The authoritative implementation plan is [Build-spec.md](Build-spec.md). The broader product vision is [Distributed-Cognitive-Architecture.md](Distributed-Cognitive-Architecture.md). Accepted behavior and test history are recorded in [docs/MAINTENANCE.md](docs/MAINTENANCE.md) and [docs/TEST_RECORD.md](docs/TEST_RECORD.md).

## Backend development

Requirements: Python 3.12+ and [uv](https://docs.astral.sh/uv/).

From the backend/ directory:

```powershell
uv sync --dev
$env:COGPLAT_API_TOKEN = (python -c "import secrets; print(secrets.token_urlsafe(32))")
uv run uvicorn cogplat.main:create_app --factory --host 127.0.0.1 --port 8000
```

The backend refuses to start without COGPLAT_API_TOKEN. Set COGPLAT_DATA_DIR to override the platform's default application-data directory.

Every API request, including health and OpenAPI, requires:

```text
Authorization: Bearer <COGPLAT_API_TOKEN>
```

The API binds to loopback only. Do not expose it to a network interface.

Run tests from backend/:

```powershell
uv run pytest
```

## API

All routes require bearer authentication.

- GET /v1/health — backend, package, and database status.
- GET /v1/openapi.json — authenticated OpenAPI schema.
- GET/POST /v1/projects — list and create projects.
- GET/POST /v1/conversations — list and create conversations; creation also creates the root branch.
- GET /v1/conversations/{id}/branches — list a conversation's branches.
- POST /v1/branches — fork a branch from a visible message.
- GET /v1/branches/{id}/messages — resolved inherited history.
- POST /v1/branches/{id}/messages — append a message to a branch.

Chat providers and streaming arrive in M2. Memory, epistemic workflows, and the desktop shell are later milestones.
