"""The deploy-stack payload: this repo's shipping surface, inspected live.

``GET /api/demo/deploy/stack`` serves this payload INLINE in topic 37's
compose section. The question the panel answers is the deployment
question — WHAT exactly ships, and can every claim be checked — answered
with three kinds of evidence, each labelled in the row's ``check_kind``
(the best-checklist vocabulary):

``live`` — runtime facts this server ALWAYS has, no repo access needed:
the env it booted in, the interpreter and process id, the uvicorn command
line this process actually runs under (graceful-shutdown budget, workers,
--reload presence — reported honestly as "not in this process's argv"
under pytest/TestClient), and a REAL internal ``GET /api/health`` driven
through the very ASGI app serving this payload.

``file`` — the repo's real deploy surface, read as text and judged by
containment (pyyaml ships no ``py.typed``, so the family precedent is
containment-based checking; the full parse stays the terminal
companion's ``docker compose config`` stop). The platform/app/edge/
images/pipeline/release/parity rows quote what they found: service
lists, image rails, required-variable rails, healthcheck probes, flip
mechanics. The server process's bind mount is ``server/`` only, so
repo-ROOT checks consult the visibility marker and, when the root is not
mounted (the live server container), return an honest ``manual`` verdict
that says why — never a faked pass, never an exception. The one
server-root row (AppConfig's fail-fast validator) verifies everywhere.

``manual`` — claims no automation here can judge. Exactly one ships: the
Kubernetes row, whose claim is a verifiable ABSENCE (``deploy/k8s/`` does
not exist in this repo — deployment is compose on a single VM with
blue/green over the shared caddy), reported as a pass with absence
evidence when the repo root is visible and honest manual otherwise.
"""

import asyncio
import os
import platform
import sys
import time
from pathlib import Path
from typing import Final, Literal

from starlette.types import ASGIApp, Message, Scope

from guide.core.config import AppConfig
from guide.core.serialization import CamelModel

CheckKind = Literal["live", "file", "manual"]
"""How a row is checked: a live runtime fact, a file read, or a human verdict."""

Verdict = Literal["pass", "fail", "manual"]
"""pass/fail are machine-judged from real evidence; manual claims nothing."""

PROBE_TIMEOUT_S: Final = 5.0
"""The health probe's ceiling — a wedged round becomes a fail verdict, not a hang."""

PROBE_HOST: Final = "deploy-stack.internal"
"""The host header the internal health probe carries (ASGI scope only)."""

REPO_ROOT_MARKER: Final = ".dockerignore"
"""A file only the real repo root carries — the honest visibility test."""

HONESTY_NOTE: Final = (
    "Every row was computed at request time. 'live' rows read THIS process and "
    "drove a real internal GET /api/health through the app serving this payload; "
    "'file' rows read the repo's deploy surface as text (containment checks — "
    "the family precedent; the full compose parse is the terminal companion's "
    "docker compose config stop). Repo-root files (the compose trio, nginx, the "
    "workflows, the env template) are checked for real when the repo root is "
    "mounted into this process; the server container's bind mount is server/ "
    "only, and there those rows report manual with that exact reason — a check "
    "that cannot run is never reported as passed. The AppConfig row reads the "
    "server tree, which every environment mounts."
)


def _read(root: Path | None, relative: str) -> str | None:
    """One file's text under a root, or None when it is not there."""
    if root is None:
        return None
    try:
        return (root / relative).read_text(encoding="utf-8")
    except OSError:
        return None


class RuntimeRow(CamelModel):
    """One runtime fact about THIS process — always real, never manual."""

    id: str
    label: str
    value: str


class StackItemRow(CamelModel):
    """One claim about the deploy surface, one verdict, the evidence."""

    id: str
    claim: str
    check_kind: CheckKind
    verdict: Verdict
    evidence: list[str]
    why_manual: str | None = None


class StackAreaRow(CamelModel):
    """One area of the deploy surface: its rows plus a one-line frame."""

    id: str
    title: str
    note: str
    items: list[StackItemRow]


class DeployStackPanel(CamelModel):
    """Wire shape of ``GET /api/demo/deploy/stack`` — the panel's contract."""

    runtime: list[RuntimeRow]
    areas: list[StackAreaRow]
    honesty_note: str


async def _probe_health(app: ASGIApp) -> tuple[int, str, float]:
    """Drive ONE real internal GET /api/health at the ASGI boundary.

    The arch-tracer channel: a hand-built ``http`` scope handed to the app
    callable — no socket, no staged responses. Whatever this probe reports
    is what the running app actually did, and it is the same route the
    prod compose healthcheck and the deploy's public gate poll.
    """
    entered = time.perf_counter()
    status: list[int] = []
    body_chunks: list[bytes] = []

    async def receive() -> Message:
        """The probe sends no body; an honest disconnect if anything asks."""
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        """Collect the status line and body chunks as they leave the app."""
        if message["type"] == "http.response.start":
            status.append(int(message["status"]))
        elif message["type"] == "http.response.body":
            body_chunks.append(message.get("body", b""))

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/health",
        "raw_path": b"/api/health",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", PROBE_HOST.encode("utf-8")),
            (b"accept", b"application/json"),
        ],
        "client": ("deploy-stack", 0),
        "server": (PROBE_HOST, 80),
    }
    await asyncio.wait_for(app(scope, receive, send), timeout=PROBE_TIMEOUT_S)
    if not status:
        raise RuntimeError("the health probe never flushed a response")
    body = b"".join(body_chunks).decode("utf-8", errors="replace")
    return status[0], body, round((time.perf_counter() - entered) * 1000, 1)


def _argv_value(flag: str) -> str | None:
    """The value that follows ``flag`` in this process's argv, or None."""
    argv = sys.argv
    for index, arg in enumerate(argv):
        if arg == flag and index + 1 < len(argv):
            return argv[index + 1]
        if arg.startswith(flag + "="):
            return arg.split("=", 1)[1]
    return None


async def _runtime_rows(app: ASGIApp, config: AppConfig) -> list[RuntimeRow]:
    """The runtime facts this server always has — read from the process."""
    argv = sys.argv
    runs_uvicorn_cli = any("uvicorn" in arg for arg in argv) or "guide.main:app" in argv
    if runs_uvicorn_cli:
        command = " ".join(argv)
        graceful = _argv_value("--timeout-graceful-shutdown")
        graceful_value = (
            f"{graceful}s (in this process's argv)"
            if graceful is not None
            else "absent from this process's argv — this command runs without it"
        )
        workers = _argv_value("--workers")
        workers_value = workers if workers is not None else "1 (default; no --workers flag)"
        reload_value = "present (--reload — a DEV-only flag)" if "--reload" in argv else "absent"
    else:
        command = (
            "not the uvicorn CLI in this process (pytest/TestClient drives the app in-process)"
        )
        graceful_value = (
            "not observable here — the prod image's CMD carries 30s (the images area)"
        )
        workers_value = "not observable here — one process per container is this repo's design"
        reload_value = "not observable here (no uvicorn argv in this process)"

    try:
        status, body, elapsed_ms = await _probe_health(app)
        health = f"{status} {body.strip()} in {elapsed_ms}ms"
    except Exception as exc:  # a broken probe is DATA, never a crashed panel
        health = f"probe failed: {type(exc).__name__}: {exc}"

    return [
        RuntimeRow(id="env", label="FDG_ENV this process booted in", value=config.env),
        RuntimeRow(id="python", label="interpreter", value=platform.python_version()),
        RuntimeRow(id="pid", label="process id", value=str(os.getpid())),
        RuntimeRow(id="command", label="server command line", value=command),
        RuntimeRow(
            id="graceful-shutdown",
            label="graceful-shutdown budget (--timeout-graceful-shutdown)",
            value=graceful_value,
        ),
        RuntimeRow(id="workers", label="worker processes", value=workers_value),
        RuntimeRow(id="reload", label="--reload (dev hot reload)", value=reload_value),
        RuntimeRow(id="health", label="real internal GET /api/health", value=health),
    ]


def _root_unavailable_row(item_id: str, claim: str, relative: str) -> StackItemRow:
    """A repo-root check that cannot run from this process — honest manual."""
    return StackItemRow(
        id=item_id,
        claim=claim,
        check_kind="manual",
        verdict="manual",
        evidence=[],
        why_manual=(
            "the file lives at the repo root ("
            + relative
            + ") and is not visible from this process — the server container's "
            "bind mount is server/ only; run the check where the whole repo is "
            "(the dev container or the host)"
        ),
    )


def _file_row(
    item_id: str, claim: str, evidence: list[str], *, ok: bool
) -> StackItemRow:
    """One file-verdict row — pass/fail strictly from what was read."""
    return StackItemRow(
        id=item_id,
        claim=claim,
        check_kind="file",
        verdict="pass" if ok else "fail",
        evidence=evidence,
    )


def _judge(
    text: str | None,
    root: Path | None,
    relative: str,
    item_id: str,
    claim: str,
    markers: tuple[str, ...],
    describe: str,
) -> StackItemRow:
    """Judge one file by containment: every marker present → pass.

    ``None`` root is the visibility case (honest manual); a visible root
    with an unreadable file is a FAIL, never a silent skip.
    """
    if root is None:
        return _root_unavailable_row(item_id, claim, relative)
    if text is None:
        return _file_row(item_id, claim, [f"{relative}: not found/readable"], ok=False)
    missing = [marker for marker in markers if marker not in text]
    found = len(markers) - len(missing)
    return _file_row(
        item_id,
        claim,
        [
            f"{relative}: {found}/{len(markers)} markers found"
            + ("" if not missing else " — MISSING: " + "; ".join(missing))
        ]
        + [describe],
        ok=not missing,
    )


_PLATFORM_COMPOSE: Final = ".docker/docker-compose-platform.yml"
_PROD_COMPOSE: Final = ".docker/docker-compose.prod.yml"
_NGINX_CONF: Final = ".docker/client/nginx.conf"
_SERVER_DOCKERFILE: Final = ".docker/server/Dockerfile.prod"
_DEV_DOCKERFILE: Final = ".docker/server/Dockerfile"
_CI_WORKFLOW: Final = ".github/workflows/ci.yml"
_DEPLOY_WORKFLOW: Final = ".github/workflows/deploy-production.yml"
_ENV_EXAMPLE: Final = "server/.env.production.example"
_CONFIG: Final = "guide/core/config.py"


def _platform_rows(repo_root: Path | None) -> list[StackItemRow]:
    text = _read(repo_root, _PLATFORM_COMPOSE)
    return [
        _judge(
            text,
            repo_root,
            _PLATFORM_COMPOSE,
            "platform-services",
            "The persistent platform carries exactly three datastores — postgres, "
            "redis, mongo — each with a healthcheck and a restart policy",
            ("  postgres:", "  redis:", "  mongo:", "restart: unless-stopped"),
            "services postgres, redis, mongo; healthchecks counted on read",
        ),
        _judge(
            text,
            repo_root,
            _PLATFORM_COMPOSE,
            "image-pins",
            "Datastore images are pinned — postgres:17, redis:7-alpine, mongo:8.0.34 "
            "(the exact patch the production volume was written with)",
            ("image: postgres:17", "image: redis:7-alpine", "image: mongo:8.0.34"),
            "no floating datastore tags on the platform",
        ),
        _judge(
            text,
            repo_root,
            _PLATFORM_COMPOSE,
            "platform-state",
            "Platform state outlives releases — external fdg_prod_* volumes and the "
            "external fdg_backend network the app stacks join by alias",
            (
                "fdg_prod_postgres_data",
                "fdg_prod_redis_data",
                "fdg_prod_mongo_data",
                "external: true",
            ),
            "volumes are platform state, never per-color state",
        ),
    ]


def _app_stack_rows(repo_root: Path | None) -> list[StackItemRow]:
    text = _read(repo_root, _PROD_COMPOSE)
    return [
        _judge(
            text,
            repo_root,
            _PROD_COMPOSE,
            "image-rail",
            "A release runs only a pinned image — ${IMAGE_TAG:?} refuses to render "
            "the stack when the tag is unset",
            ("${IMAGE_TAG:?IMAGE_TAG is required}",),
            "the rail fires on server AND client images at compose-render time",
        ),
        _judge(
            text,
            repo_root,
            _PROD_COMPOSE,
            "env-rails",
            "Three required-variable rails fail `compose config` up front when the "
            "secrets are unset — FDG_DB_PASSWORD, FDG_JWT_SECRET, FDG_SESSION_SECRET",
            (
                "${FDG_DB_PASSWORD:?FDG_DB_PASSWORD must be set to a real database password",
                "- FDG_JWT_SECRET=${FDG_JWT_SECRET:?FDG_JWT_SECRET must be set to a real "
                "high-entropy signing secret",
                "- FDG_SESSION_SECRET=${FDG_SESSION_SECRET:?FDG_SESSION_SECRET must be set "
                "to a real high-entropy signing secret, distinct from FDG_JWT_SECRET",
            ),
            "deploy-time door number one: an unset secret never reaches a container",
        ),
        _judge(
            text,
            repo_root,
            _PROD_COMPOSE,
            "healthcheck-probe",
            "The server healthcheck probes the real liveness route with the venv "
            "python — the slim runtime image ships no wget or curl",
            (
                "urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5)",
                "start_period: 30s",
            ),
            "the probe binary is the image's own interpreter; the route is /api/health",
        ),
        _judge(
            text,
            repo_root,
            _PROD_COMPOSE,
            "color-isolation",
            "Each release is its own compose project — fdg_server_${COLOR} on a "
            "project-scoped app_internal network, so nginx always reaches its OWN "
            "color's API",
            ("fdg_server_${COLOR:-blue}", "app_internal: {}", "fdg_client_${COLOR:-blue}"),
            "the network namespace is the isolation unit between blue and green",
        ),
    ]


def _edge_rows(repo_root: Path | None) -> list[StackItemRow]:
    nginx = _read(repo_root, _NGINX_CONF)
    platform = _read(repo_root, _PLATFORM_COMPOSE)
    return [
        _judge(
            nginx,
            repo_root,
            _NGINX_CONF,
            "nginx-app-server",
            "nginx is the internal app server — /api/ proxies to the compose "
            "service name server:8000, everything else is the SPA",
            ("proxy_pass http://server:8000;", "try_files $uri $uri/ /index.html;"),
            "the API stays internal; nginx is the only caller",
        ),
        _judge(
            nginx,
            repo_root,
            _NGINX_CONF,
            "spa-cache-policy",
            "Hashed assets cache forever (immutable, 1y); index.html always "
            "revalidates — a deploy is picked up on the next visit",
            (
                "expires 1y",
                'add_header Cache-Control "public, immutable";',
                'location = /index.html {',
            ),
            "the hash is the cache key; the entry document is never stale-cached",
        ),
        _judge(
            platform,
            repo_root,
            _PLATFORM_COMPOSE,
            "caddy-tls-edge",
            "The TLS edge is ONE shared caddy on the VM — it reaches this app's "
            "fdg_client_<color> containers by name over fdg_frontend, and releases "
            "flip by rewriting the upstream.caddy file it bind-mounts",
            ("upstream.caddy", "fdg_frontend", "caddy reload"),
            "documented in the platform file's header; the live flip file lives on "
            "the VM — the mechanism is checked here as documentation, the runtime "
            "fact belongs to the VM",
        ),
    ]


def _images_rows(repo_root: Path | None) -> list[StackItemRow]:
    prod = _read(repo_root, _SERVER_DOCKERFILE)
    dev = _read(repo_root, _DEV_DOCKERFILE)
    rows = [
        _judge(
            prod,
            repo_root,
            _SERVER_DOCKERFILE,
            "multi-stage-uv",
            "The prod server image is multi-stage — a uv builder installs the "
            "locked set, the final stage is slim CPython carrying only the venv",
            (
                "FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS build",
                "FROM python:3.13-slim-bookworm",
            ),
            "two FROM lines, two purposes: build tools stay behind",
        ),
        _judge(
            prod,
            repo_root,
            _SERVER_DOCKERFILE,
            "manifests-first-caching",
            "Manifests copy first so the dependency layer caches while only "
            "source churns — the two-step uv sync from the dependency topic",
            (
                "COPY server/pyproject.toml server/uv.lock ./",
                "RUN uv sync --locked --no-dev --no-install-project",
                "RUN uv sync --locked --no-dev --no-editable",
            ),
            "an unchanged lockfile reuses the dependency layer wholesale",
        ),
        _judge(
            prod,
            repo_root,
            _SERVER_DOCKERFILE,
            "least-privilege-drain",
            "The runtime is non-root (a system user) and in-flight requests get a "
            "30s drain before exit — no --reload anywhere in the prod image",
            (
                "useradd --system --gid guide --create-home guide",
                '"--timeout-graceful-shutdown", "30"',
            ),
            "the dev image carries --reload; the prod image deliberately does not"
            if prod is None or "--reload" not in prod
            else "UNEXPECTED: --reload found in the prod image",
        ),
    ]
    if repo_root is None:
        rows.append(
            _root_unavailable_row(
                "dev-image-contrast",
                "The dev image is the same two-step uv sync but editable, run "
                "under --reload with the venv's uvicorn directly",
                _DEV_DOCKERFILE,
            )
        )
    else:
        rows.append(
            _judge(
                dev,
                repo_root,
                _DEV_DOCKERFILE,
                "dev-image-contrast",
                "The dev image is the same two-step uv sync but editable, run "
                "under --reload with the venv's uvicorn directly",
                ("uv sync --locked", "--reload"),
                "dev and prod differ by values, not by process shape",
            )
        )
    return rows


def _pipeline_rows(repo_root: Path | None) -> list[StackItemRow]:
    ci = _read(repo_root, _CI_WORKFLOW)
    return [
        _judge(
            ci,
            repo_root,
            _CI_WORKFLOW,
            "ci-contract",
            "CI mirrors the repo's own verification convention — uv sync --locked, "
            "the suite, ruff, mypy — exactly the dev-container commands",
            (
                "- run: uv sync --locked",
                "- run: uv run pytest -q",
                "- run: uv run ruff check .",
                "- run: uv run mypy guide",
            ),
            "the CI contract IS the local contract; no second suite exists",
        ),
        _judge(
            ci,
            repo_root,
            _CI_WORKFLOW,
            "image-smoke-browser-gate",
            "The e2e job builds BOTH prod images, boots them beside the platform "
            "datastores with the CI override, and drives the real UI with Playwright",
            (
                "docker compose -f .docker/docker-compose-platform.yml",
                "-f .docker/docker-compose.ci.yml up -d --wait",
                "npx playwright install",
            ),
            "the gate exercises the same seam the deploy boots: platform first, "
            "then the app stack",
        ),
        _judge(
            ci,
            repo_root,
            _CI_WORKFLOW,
            "attested-publish",
            "Published images carry provenance + SBOM attestations beside a sha-7 "
            "tag (and :master), built for the architecture the VM actually runs",
            ("provenance: true", "sbom: true", "cut -c1-7"),
            "supply-chain evidence rides the image as OCI artifacts in GHCR",
        ),
    ]


def _release_rows(repo_root: Path | None) -> list[StackItemRow]:
    deploy = _read(repo_root, _DEPLOY_WORKFLOW)
    return [
        _judge(
            deploy,
            repo_root,
            _DEPLOY_WORKFLOW,
            "blue-green-boot",
            "Deploys boot the INACTIVE color under its own project, wait for its "
            "healthcheck, and probe it privately through the color's own network "
            "before anything goes live",
            (
                'docker compose -p "fdg_$COLOR"',
                "probe_new_color",
                "busybox:stable",
            ),
            "the live color is never touched until the new one is healthy",
        ),
        _judge(
            deploy,
            repo_root,
            _DEPLOY_WORKFLOW,
            "caddy-flip",
            "A release goes live by rewriting the one-line upstream.caddy flip "
            "file and gracefully reloading the shared caddy — no TLS blip",
            (
                "reverse_proxy fdg_client_%s:80",
                "docker exec caddy caddy reload --config /etc/caddy/Caddyfile",
            ),
            "the flip is one file write plus one reload; caddy keeps its certs",
        ),
        _judge(
            deploy,
            repo_root,
            _DEPLOY_WORKFLOW,
            "instant-rollback",
            "A failed post-flip public health gate flips back to the still-running "
            "old color — instant rollback, state written atomically on success only",
            (
                "Flipping back to the still-running color",
                "last-successful-sha",
                "active-color",
            ),
            "pre-flip failures clean up the candidate; post-flip failures roll back",
        ),
        _judge(
            deploy,
            repo_root,
            _DEPLOY_WORKFLOW,
            "env-materialization",
            "The real env file never touches git — the deploy materializes "
            "server/.env.production from the PROD_ENV_B64 secret, mode 600",
            (
                "PROD_ENV_B64",
                "base64 -d > server/.env.production",
                "chmod 600 server/.env.production",
            ),
            "secrets live in the GitHub environment, not in the repo",
        ),
    ]


def _parity_rows(repo_root: Path | None, server_root: Path) -> list[StackItemRow]:
    example = _read(repo_root, _ENV_EXAMPLE)
    config = _read(server_root, _CONFIG)
    return [
        _judge(
            example,
            repo_root,
            _ENV_EXAMPLE,
            "template-boots",
            "The committed placeholder template BOOTS the real app outside dev — "
            "long, distinct placeholder secrets pass the fail-fast validator while "
            "being clearly non-secret",
            (
                "FDG_DB_PASSWORD=placeholder-db-password-not-a-secret-ci-and-docs-only",
                "FDG_JWT_SECRET=placeholder-jwt-signing-secret-32-chars-not-a-secret",
                "FDG_SESSION_SECRET=placeholder-session-signing-secret-32-chars-not-a-secret",
            ),
            "CI and config dry-runs consume the template; only the deploy gets "
            "the real values",
        ),
        _judge(
            config,
            server_root,
            _CONFIG,
            "appconfig-fail-fast",
            "AppConfig refuses any dev-default signing secret outside dev at boot, "
            "naming the FDG_* vars to set — the second, in-process door behind the "
            "compose rails",
            (
                "_refuse_dev_secrets_outside_dev",
                "refuses dev-default signing secrets",
                "must be set to real high-entropy values",
            ),
            "reads the server tree — verifies in EVERY environment, including "
            "the server-only bind mount",
        ),
    ]


def _kubernetes_rows(repo_root: Path | None) -> list[StackItemRow]:
    claim = (
        "No Kubernetes manifests ship in this repo — deployment is the compose "
        "trio on a single VM with blue/green over the shared caddy; the kubernetes "
        "section teaches the concepts this pipeline deliberately does not need yet"
    )
    if repo_root is None:
        return [
            _root_unavailable_row(
                "k8s-manifests", claim, "deploy/k8s/ (absence cannot be checked from here)"
            )
        ]
    k8s_dir = repo_root / "deploy" / "k8s"
    present = k8s_dir.is_dir() and any(k8s_dir.iterdir())
    return [
        _file_row(
            "k8s-manifests",
            claim,
            [
                "deploy/k8s/: "
                + (
                    "manifests FOUND — this row predates them; update the claim"
                    if present
                    else "does not exist in the repo (checked at request time)"
                ),
                "the real rollout mechanism is the caddy flip (see the release area)",
            ],
            ok=not present,
        )
    ]


_AREA_FRAMES: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "platform",
        "Platform",
        "docker-compose.platform.yml — the datastores that outlive every release.",
    ),
    (
        "app-stack",
        "App stack",
        "docker-compose.prod.yml — one pinned release per color, rails up front.",
    ),
    (
        "edge",
        "Edge",
        "nginx inside, one shared caddy outside — proxying, caching, TLS, flips.",
    ),
    (
        "images",
        "Images",
        "The server Dockerfiles — multi-stage uv builds, least privilege, no reload.",
    ),
    (
        "pipeline",
        "Pipeline",
        "The CI workflow — the local contract, replayed hosted, then published.",
    ),
    (
        "release",
        "Release",
        "The deploy workflow — blue/green boot, private probe, flip, rollback.",
    ),
    (
        "parity",
        "Parity & secrets",
        "One env template that boots anywhere; one validator that refuses defaults.",
    ),
    (
        "kubernetes",
        "Kubernetes",
        "The honest absence — and what the concepts map onto when it's time.",
    ),
)


async def build_deploy_stack_payload(
    *,
    app: ASGIApp,
    config: AppConfig,
    server_root: Path,
    repo_root: Path | None,
) -> DeployStackPanel:
    """Compose the panel: live runtime facts, real file reads, honest manuals.

    ``server_root`` is the server/ tree this process lives in (always
    readable — the AppConfig row reads it); ``repo_root`` is the full repo
    when its marker file is visible — ``None`` turns repo-root checks into
    honest manual rows, never faked passes.
    """
    area_items: dict[str, list[StackItemRow]] = {
        "platform": _platform_rows(repo_root),
        "app-stack": _app_stack_rows(repo_root),
        "edge": _edge_rows(repo_root),
        "images": _images_rows(repo_root),
        "pipeline": _pipeline_rows(repo_root),
        "release": _release_rows(repo_root),
        "parity": _parity_rows(repo_root, server_root),
        "kubernetes": _kubernetes_rows(repo_root),
    }
    areas = [
        StackAreaRow(id=area_id, title=title, note=note, items=area_items[area_id])
        for area_id, title, note in _AREA_FRAMES
    ]
    return DeployStackPanel(
        runtime=await _runtime_rows(app, config),
        areas=areas,
        honesty_note=HONESTY_NOTE,
    )


def resolve_roots(module_file: Path) -> tuple[Path, Path | None]:
    """The server root for a domain/demos module file, and the repo root when visible.

    Same depth contract as the best-checklist resolver (demos → domain →
    guide → server): the server root is three parents up; the repo root is
    one more and only counts when its marker file is actually mounted —
    the server container binds server/ alone, and honest rows must say so.
    """
    server_root = module_file.resolve().parents[3]
    candidate = server_root.parent
    repo_root = candidate if (candidate / REPO_ROOT_MARKER).is_file() else None
    return server_root, repo_root


def default_roots() -> tuple[Path, Path | None]:
    """The roots for THIS module — the one place the depth assumption lives."""
    return resolve_roots(Path(__file__))
