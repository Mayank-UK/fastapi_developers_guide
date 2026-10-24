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

When Docker files change: `docker compose -f .docker/docker-compose.yml config -q`, plus — after copying `server/.env.production.example` to `server/.env.production` and sourcing it (`set -a; . server/.env.production; set +a`) so the required-variable rails resolve — `docker compose -f .docker/docker-compose-platform.yml config -q` and `docker compose -f .docker/docker-compose.prod.yml -f .docker/docker-compose.ci.yml config -q`.

## Analytics

The site reports to a **self-hosted Umami** instance at https://umami.mayankcodeworks.com — no third-party tracker, no cookies banner needed. The beacon is env-gated: CI bakes the `VITE_UMAMI_SRC` / `VITE_UMAMI_ID` **repository Variables** (not secrets — both values are public by design, visible in the served page source anyway) into the client image as Docker build-args (see `client/src/ui/analytics/analytics.ts`). With either variable empty — the default, and always in dev/test — analytics is a complete no-op: no script is injected and nothing is sent.

Custom events:

| Event | Property | Trigger |
| ----- | -------- | ------- |
| `topic-open` | `topic` — the served topic id (e.g. `pydantic`) | a topic screen finishes loading (home-card click, direct link, or refresh) |
| `copy-code` | `topic` — the current route path (e.g. `/topics/pydantic`) | a code block's copy button succeeds |

(No `demo-run` event: demos mount inline beside their teaching sections with no single user-triggered "run" action, so there is nothing to report.)

**UTM convention for share links** — tag any link you post with `utm_source` = where the link lives and `utm_medium` = `readme` \| `post` \| `social`; Umami parses the standard UTM parameters automatically:

```text
https://fastapidevelopersguide.mayankcodeworks.com/?utm_source=github&utm_medium=readme
https://fastapidevelopersguide.mayankcodeworks.com/?utm_source=reddit&utm_medium=post
https://fastapidevelopersguide.mayankcodeworks.com/?utm_source=dev.to&utm_medium=post
```
