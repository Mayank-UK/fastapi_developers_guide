# FastAPI Developers Guide

A runnable full-stack reference app that **is** the guide. The server (Python 3.13 + FastAPI + uv) carries 100% of the teaching as a typed content API — 43 topics, 10 groups, 63 inline live demos — and the client (React 19 + Vite + TypeScript + Tailwind v4) is a presentation-only shell that renders it. Nothing is a screenshot or a promise: every endpoint, query, worker, and failure path the text teaches is real code in this repository, and every demo panel exercises it live.

Third sibling of the guide family, after `express_developers_guide` (the canon origin — content model, devcontainer workflow, snippet discipline) and `spring_boot_developers_guide` (the newest family patterns). All 43 topics are authored; the suites are green (server: 1,500+ tests + `ruff` + `mypy --strict`; client: 500 tests + production build — both run in CI on every push).

## The curriculum at a glance

Ten groups, 43 topics, in curriculum order (titles as the API serves them):

- **Foundations** — The Python language · The CPython runtime · HTTP, the web's contract
- **Framework** — FastAPI, the framework · Pydantic, the boundary · Dependencies: Depends
- **Request handling** — Routing · Middleware · The request and the response · Validation
- **APIs** — API design · API documentation · GraphQL · Webhooks · gRPC
- **Data** — SQL schema design · Databases and SQL · The SQLAlchemy ORM · MongoDB and document stores · Redis
- **State & auth** — Caching · Messaging · Authentication · Authorization · Security
- **Media & realtime** — Files and media · Internationalization · Realtime: SSE and WebSockets · Background jobs: BackgroundTasks and worker queues
- **Platform** — Exception handling · Dependency management · Architecture · Observability · Testing · Debugging · Environments
- **Ship** — Deployment · Performance · Reliability · Scaling
- **Capstones** — Best practices · Third-party services · Advanced architecture

Each topic is ~3,000 words of prose grounded in this repo's own code, ends with a curl-able terminal companion, and hosts its demos inline beside the sections that teach them.

## Architecture

**Server** (`server/guide/`), five layers with one dependency rule:

- `core/` — the cross-cutting machinery: pydantic-settings config, the eight-kind error taxonomy behind one error envelope, structured JSON logging with request-id correlation, the `Result` type, the runtime `ScenarioStore`
- `content/` — the teaching as data: a pydantic content model (topic → sections → blocks of `text | code | demo | list`) and a registry that validates every topic at import, so broken content fails the process at startup
- `domain/<area>/` — entities, ports (typing `Protocol`s), and use cases per teaching area; the domain imports neither FastAPI nor any adapter
- `data/<area>/` — the adapters: in-memory, PostgreSQL (asyncpg + Alembic + SQLAlchemy 2.1 async ORM), motor, redis-py, arq
- `presentation/` — thin routers (parse input → call one use case → return a typed response model), middleware, and `Depends` wiring

The dependency rule is `presentation → domain ← data`: adapters implement domain ports, the composition root (`create_app()` in `main.py`) wires each port to its adapter once, and nothing else knows which adapter answered. The same posts use cases serve REST, GraphQL, gRPC, and the caching lab precisely because no edge can reach past the port.

**Client** (`client/src/`) mirrors the layering — `core/` (fetch, guards, typed DTOs), `domain/` (view models, planned-content logic), `data/` (the content API adapter), `ui/` (the design system, views, lazy-loaded demo panels). It renders whatever the content API serves and holds no teaching of its own.

**Wire contract** (stable, drift-tested): `GET /api/content` → `{version: 1, groups, topics}`; `GET /api/content/{topicId}` → the full topic with sections and blocks; `GET/PATCH /api/demo/scenario`; every error — 404 and 405 included — answers the one envelope `{error: {code, message, requestId, details?}}` with an `x-request-id` header.

## Running it

The standard path is the VS Code devcontainer: open the repo → **Reopen in Container**. That starts the whole stack defined in [`.docker/docker-compose.yml`](.docker/docker-compose.yml): the `dev` tooling container, the server (uvicorn `--reload`), the client (Vite), an arq worker, and PostgreSQL 17 / Redis 7 / MongoDB 8. Without VS Code:

```bash
docker volume create fdg-uv && docker volume create fdg-npm   # once, on a fresh machine (shared caches)
docker compose -f .docker/docker-compose.yml up -d
```

Then: API and docs at http://localhost:8000 (`/docs` Swagger UI, `/redoc`, `/openapi.json`), the client at http://localhost:5174, PostgreSQL on 5432, Redis on 6379, MongoDB on 27017. Optional services stay optional — the server boots and serves with any datastore down; the demos that need one degrade to an honest `service_unavailable` envelope.

Smoke it:

```bash
curl -s http://localhost:8000/api/health        # {"status":"ok","env":"dev"}
curl -s http://localhost:8000/api/content | head -c 400
```

## Live demos and the scenario toggle

Every demo runs against the real substrate — the same posts use cases `/api/posts` serves, the same redis client, the same worker — never a canned fixture. Two endpoints make the stack teachable by hand:

```bash
# flip the data mode and inject failures on demand
curl -s -X PATCH http://localhost:8000/api/demo/scenario \
  -H 'content-type: application/json' -d '{"dataMode":"live"}'
curl -s -X PATCH http://localhost:8000/api/demo/scenario \
  -H 'content-type: application/json' -d '{"injectFailure":"error"}'

# return every demo state to its baseline (scenario, posts seed, cache keys,
# shared counter, jobs lists, PII records, log ring) — with an honest
# per-area report of what was reset and what was deliberately not
curl -s -X POST http://localhost:8000/api/demo/reset
```

`POST /api/demo/reset` never touches PostgreSQL tables, Alembic history, MongoDB collections, or the Redis Streams history — destructive database resets are out of scope, and the response says so rather than implying a clean slate.

## Snippets: the code is the source of truth

Every code block in a topic whose language demands sourcing (py, toml, yaml, sql, proto, ts, json, …) carries a `source:` path into this repository, and a ratchet test verifies each quoted snippet is an ordered, comment- and blank-normalized subsequence of the **current** file — so the guide cannot drift from the code it teaches without failing the suite. Hand-written teaching exhibits exist only where no real counterpart exists, and the ratchet is pinned at zero violations.

## Verification

The host has no project venv and host `node_modules` stay empty by design — builds and tests run in Docker. Against the long-lived dev containers:

```bash
docker exec fastapi_developers_guide_dev bash -lc \
  'cd /workspaces/fastapi_developers_guide/server && uv sync --locked && uv run pytest -q && uv run ruff check . && uv run mypy guide'
docker exec fastapi_developers_guide_client_dev bash -lc \
  'cd /app && npm test && npm run build'
```

Host-run fallback for running the suite without a devcontainer attached — it joins the dev stack's docker network so the integration tests reach the same PostgreSQL/Redis/MongoDB, and shares the same external caches (the stack from `up -d` must be running):

```bash
docker run --rm --network fastapi_developers_guide_default \
  -v "$PWD":/repo -w /repo/server -v fdg-uv:/root/.cache/uv \
  ghcr.io/astral-sh/uv:python3.13-bookworm \
  bash -lc 'flock /repo/server/.verify.lock bash -c "uv sync --locked && uv run pytest -q"'
docker run --rm -v "$PWD/client":/app -w /app -v fdg-npm:/root/.npm \
  node:22-bookworm \
  bash -lc 'flock /app/.verify.lock bash -c "npm ci && npm test"'
```

## CI/CD and deployment

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) gates every push and PR: the server job boots PostgreSQL/Redis/MongoDB on the runner, migrates and seeds through the app's own entry points, then runs `uv sync --locked → pytest → ruff → mypy`; the client job runs `npm ci → test → build`; gitleaks scans history; and the e2e job builds both production images locally, boots them behind nginx with the production compose trio, and drives the real UI with Playwright. On master, CI publishes attested images (provenance + SBOM) to `ghcr.io/mayank-uk/fastapi-guide-{server,client}` for the architecture the deployment VM actually runs.

[`.github/workflows/deploy-production.yml`](.github/workflows/deploy-production.yml) ships **blue/green**: each release boots as its own compose project (`fdg_blue` / `fdg_green`) beside the shared platform stack (caddy edge + datastores), health-gated, and a caddy flip file switches the live hostname — https://fastapidevelopersguide.mayankcodeworks.com — from one color to the other. The old color stays up for rollback.

## Analytics

The site reports to a self-hosted Umami instance — no third-party tracker, no cookie banner. The beacon is env-gated (`VITE_UMAMI_*` build args, public by design, baked by CI): with either variable empty — the default, and always in dev/test — analytics is a complete no-op. Custom events: `topic-open` (a topic screen finishes loading, property `topic` = the served topic id) and `copy-code` (a code block's copy button succeeds, property `topic` = the current route path). Tag share links with UTM parameters — `utm_source` = where the link lives, `utm_medium` = `readme` | `post` | `social` — e.g. `https://fastapidevelopersguide.mayankcodeworks.com/?utm_source=github&utm_medium=readme`.
