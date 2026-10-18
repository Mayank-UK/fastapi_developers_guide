# FastAPI Developers Guide

A runnable full-stack reference app that IS the guide: a Python 3.13 + FastAPI + uv server that carries 100% of the teaching as a typed content API (topics → sections → text/code/demo blocks), and a React 19 + Vite presentation-only shell that renders it. Third sibling of the guide family after `express_developers_guide` (backend canon + content model) and `spring_boot_developers_guide` (newest family patterns).

**Status: under construction — Phase 1.** The infrastructure (`.docker/`, `.devcontainer/`), the server skeleton (Phase 0.B: uv project with FastAPI app factory, `/api/health`), and the client skeleton (Phase 0.C: React 19 + Vite + TS shell) are in place; the server's content engine is now live (Phase 1: typed topic registry + `GET /api/content`, error taxonomy + one envelope, request-id middleware, ScenarioStore + `PATCH /api/demo/scenario`, snippet-source ratchet). Topic authoring starts with Phase 3.

## Development — devcontainer

The standard dev path is the VS Code devcontainer: open the repo in VS Code → "Reopen in Container". It starts the whole stack from `.docker/docker-compose.yml` — `dev` (Python 3.13 + uv + Node 22 toolchain), `server` (uvicorn `--reload` on http://localhost:8000), `client` (Vite on http://localhost:5174), plus postgres/redis/mongo. Integrated terminals are for tests, git, and builds; the app containers run their own dev servers.

## Verification (canonical one-liners)

The host has no project venv and host `node_modules` stay empty by design — builds and tests run in Docker, from the repo root:

Server (from the repo root):

```bash
docker run --rm -v "$PWD":/repo -w /repo/server -v fdg-uv:/root/.cache/uv ghcr.io/astral-sh/uv:python3.13-bookworm bash -lc 'flock /repo/server/.verify.lock bash -c "uv sync --locked && uv run pytest -q"'
```

Client:

```bash
docker run --rm -v "$PWD/client":/app -w /app -v fdg-npm:/root/.npm node:22-bookworm bash -lc 'flock /app/.verify.lock bash -c "npm ci && npm test"'
```

When Docker files change: `docker compose -f .docker/docker-compose.yml config -q && docker compose -f .docker/docker-compose.prod.yml config -q`.
