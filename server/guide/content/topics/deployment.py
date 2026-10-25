"""Topic 37 — Deployment: shipping this app, from image to blue/green flip.

The topic teaches deployment as the discipline of making the artifact you
tested be the artifact that serves — and knowing every door between the
two. Everything quoted here is this repository's REAL deploy surface: the
multi-stage uv Dockerfiles (.docker/server/), the compose trio (platform
/ prod / ci), the nginx app server and the shared-caddy TLS edge, the
health-gated CI workflow, the blue/green deploy over the caddy flip file,
the env template + fail-fast secrets story, and the Linux survival kit
the deploy script itself runs on failure. The demo is deploy:stack,
INLINE in the compose section: a live inspection of that surface —
runtime facts this server always has, real file checks when the repo is
mounted, honest manual rows when it is not.

Two honesty anchors, stated up front and kept throughout: Kubernetes
ships NO manifests in this repo (deploy/k8s/ does not exist — the section
teaches the concepts and the deliberate decision), and the tools this
repo does not run (gunicorn multi-worker, kubectl, terraform) appear only
as clearly-marked recipes, never as pretend integrations.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="deployment",
    title="Deployment",
    subtitle=(
        "Ship vs run: the image as the artifact, multi-stage Docker with "
        "uv, the compose trio (platform, per-release app stack, CI "
        "override), the caddy/nginx edge with TLS, worker processes and "
        "graceful shutdown, the CI/CD pipeline that publishes what it "
        "tested, parity and secrets, Kubernetes taught honestly (this "
        "repo ships none), blue/green rollouts over the caddy flip file, "
        "infrastructure as code, and the Linux survival kit — all quoted "
        "from this repository's real deploy surface."
    ),
    group="ship",
    order=37,
    sections=[
        # ── 1. ship vs run ────────────────────────────────────────────────
        Section(
            id="ship-vs-run",
            title="Ship vs run",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dpl-ship-pitch",
                    text=(
                        "Development runs a process; deployment ships an "
                        "artifact. The distinction sounds like a slogan "
                        "until the first 3am incident makes it concrete: "
                        "the process you run locally is yours — you "
                        "started it, you can restart it, its interpreter "
                        "is your interpreter, its dependencies are "
                        "whatever your machine had — while the thing that "
                        "serves customers is an artifact someone else "
                        "built, at a commit you may not have checked out, "
                        "on a machine you cannot log into casually. "
                        "Deployment is everything that stands between "
                        "those two: building a self-contained artifact, "
                        "placing it on a server, starting it under "
                        "supervision, wiring it to its dependencies, "
                        "letting traffic in, and taking it out again "
                        "without anyone noticing."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-ship-artifact",
                    text=(
                        "For a Python web app the artifact is a container "
                        "image: a tarball filesystem carrying the "
                        "interpreter, the locked dependencies, and the "
                        "application code, addressable by an immutable "
                        "digest or tag. This repository's image is built "
                        "by CI from an exact commit, tagged "
                        "sha-<first-7>, published to a registry (GHCR), "
                        "and the deployment boots exactly that tag — the "
                        "same bytes CI smoke-tested, never a fresh 'pull "
                        "and hope' build on the server. The whole journey "
                        "has a small fixed set of stages, and each one "
                        "exists to make a later failure impossible:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="dpl-ship-stages",
                    ordered=True,
                    items=[
                        "Build — the multi-stage Dockerfile turns the "
                        "commit into two images (server, client), "
                        "dependency layers cached by the lockfile.",
                        "Verify — the same suites that run locally "
                        "(pytest, ruff, mypy, the client build) run "
                        "hosted, against real datastores on the runner.",
                        "Smoke — CI boots BOTH production images with "
                        "the prod compose files and drives the real UI "
                        "with a browser before anything is published.",
                        "Publish — attested images (provenance + SBOM) "
                        "land in GHCR under a sha tag, for the VM's "
                        "actual architecture.",
                        "Release — the deploy boots a parallel stack, "
                        "probes it privately, then flips the shared edge "
                        "to it — with instant rollback on a failed gate.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="dpl-ship-gate-pitch",
                    text=(
                        "Every gate in that pipeline asks the application "
                        "one question — are you alive — and the answer is "
                        "a route this repo has carried since its first "
                        "commit. The health endpoint is deliberately "
                        "dependency-free: it reports the process and the "
                        "environment it booted in, nothing else, because "
                        "a liveness probe that fails when PostgreSQL "
                        "hiccups gets a healthy container killed. It is "
                        "the contract the compose healthchecks, the CI "
                        "probe, and the deploy's public gate all poll:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-ship-health-quote",
                    language="py",
                    caption="The liveness contract every gate polls — dependency-free by design.",
                    source="server/guide/presentation/routers/health.py",
                    snippet=(
                        '@router.get("/health", response_model=HealthResponse)\n'
                        "def read_health(config: Annotated[AppConfig, Depends(get_config)]) -> HealthResponse:\n"
                        '    """Report process liveness plus the environment it booted in."""\n'
                        '    return HealthResponse(status="ok", env=config.env)'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-ship-coda",
                    text=(
                        "Liveness is not readiness — 'is the process up' "
                        "versus 'can it serve this request well' — and "
                        "the observability topic built that split. "
                        "Deployment leans on the narrow one on purpose: "
                        "gates should fail only when restarting could "
                        "help. With the contract fixed, the rest of this "
                        "topic walks the pipeline in order: the image, "
                        "the stacks that run it, the edge that fronts it, "
                        "the process model inside the container, the "
                        "pipeline that ships it, and the rollout that "
                        "swaps it — each section quoting this repo's "
                        "real files, because deployment taught from "
                        "invented examples teaches the inventions."
                    ),
                ),
            ],
        ),
        # ── 2. Docker multi-stage (uv) ────────────────────────────────────
        Section(
            id="docker-multi-stage",
            title="Docker multi-stage (uv)",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dpl-image-pitch",
                    text=(
                        "A Docker image is built in layers, and the build "
                        "rule that matters most is boring: later layers "
                        "cache only while every earlier layer is "
                        "byte-identical. So the ordering discipline of a "
                        "good Dockerfile is 'stable things first' — and "
                        "in a Python project the stablest thing is the "
                        "lockfile. The dependency-management topic "
                        "established the two-step uv sync pattern; here "
                        "is where it pays rent, in the production server "
                        "image's builder stage:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-image-build-quote",
                    language="dockerfile",
                    caption="The uv builder stage: manifests first, source second — the dependency layer survives source edits.",
                    source=".docker/server/Dockerfile.prod",
                    snippet=(
                        "FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS build\n"
                        "\n"
                        "# copy (not hardlink) so the cross-stage COPY stays plain; bytecode-compile\n"
                        "# for faster cold starts.\n"
                        "ENV UV_COMPILE_BYTECODE=1 \\\n"
                        "    UV_LINK_MODE=copy\n"
                        "\n"
                        "WORKDIR /app\n"
                        "\n"
                        "# Manifests first: the dependency layer caches while only source churns.\n"
                        "# --no-install-project skips building the guide package itself here.\n"
                        "COPY server/pyproject.toml server/uv.lock ./\n"
                        "RUN uv sync --locked --no-dev --no-install-project\n"
                        "\n"
                        "COPY server/ ./\n"
                        "# …\n"
                        "RUN uv sync --locked --no-dev --no-editable"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-image-caching",
                    text=(
                        "Read the cache arithmetic: change a source file "
                        "and Docker replays from COPY server/ — the "
                        "expensive uv sync layer (resolving, downloading, "
                        "compiling nothing because wheels) is a cache "
                        "hit. Change a dependency and only then does the "
                        "manifests layer rebuild — with --locked "
                        "guaranteeing the resolution is exactly the "
                        "committed one, never a fresh solve. The first "
                        "sync deliberately skips the project (--no-"
                        "install-project, there is nothing to build "
                        "yet); the second installs the guide package as "
                        "--no-editable — a static, built copy — so the "
                        "final image runs the package from the venv "
                        "alone. The one source the image still carries "
                        "is the migration tree: the lifespan migrates "
                        "at boot, its paths resolve from the module, "
                        "and inside the image that module is a wheel in "
                        "site-packages — no checkout beside it — so the "
                        "runtime stage COPYies alembic.ini + alembic/ to "
                        "the WORKDIR and lifecycle.py falls back to that "
                        "copy (without it, prod boots would skip the "
                        "migration and serve a database with no tables)."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-image-final-quote",
                    language="dockerfile",
                    caption="The runtime stage: slim CPython, the venv, a non-root user, a drain-aware CMD.",
                    source=".docker/server/Dockerfile.prod",
                    snippet=(
                        "FROM python:3.13-slim-bookworm\n"
                        "\n"
                        "# Non-root runtime user (least privilege).\n"
                        "RUN groupadd --system guide && useradd --system --gid guide --create-home guide\n"
                        "\n"
                        "WORKDIR /app\n"
                        "COPY --from=build --chown=guide:guide /app/.venv /app/.venv\n"
                        "# Migration assets: the startup migration resolves the repo checkout from\n"
                        "# the module — which, in this image, is the venv's site-packages with no\n"
                        "# alembic tree beside it — so the SAME single tree (server/alembic.ini +\n"
                        "# server/alembic/) ships here at the WORKDIR, root-owned and therefore\n"
                        "# read-only to the app user; guide/data/db/lifecycle.py falls back to it.\n"
                        "COPY server/alembic.ini ./alembic.ini\n"
                        "COPY server/alembic ./alembic\n"
                        "\n"
                        'ENV PATH="/app/.venv/bin:$PATH"\n'
                        "\n"
                        "USER guide\n"
                        "EXPOSE 8000\n"
                        "# Graceful shutdown: in-flight requests get 30s to drain before exit.\n"
                        'CMD ["uvicorn", "guide.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "30"]'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-image-final-reading",
                    text=(
                        "The second FROM starts over from a clean base — "
                        "that is what multi-stage buys: the builder stage "
                        "carries uv, compilers, and caches; the runtime "
                        "stage carries python:3.13-slim and exactly one "
                        "thing from the builder, the venv. The venv's "
                        "python symlinks point at /usr/local/bin/"
                        "python3.13, which exists at the same path in "
                        "the slim base — the documented uv Docker "
                        "pattern, and the reason the copy 'just works'. "
                        "The runtime user is a system account with no "
                        "shell privileges, so a compromised process "
                        "owns /app and nothing else. And note what the "
                        "CMD does NOT contain: no --reload, no dev "
                        "groups, no test tooling — the image cannot run "
                        "the development workflow even if asked."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-image-dev-quote",
                    language="dockerfile",
                    caption="The dev image: same two-step shape, different values — editable install, --reload, the venv's uvicorn directly.",
                    source=".docker/server/Dockerfile",
                    snippet=(
                        "# Manifests first to leverage Docker layer caching (deps change least).\n"
                        "# …\n"
                        "COPY server/pyproject.toml server/uv.lock ./\n"
                        "RUN uv sync --locked --no-install-project\n"
                        "\n"
                        "COPY server/ ./\n"
                        "# …\n"
                        "RUN uv sync --locked\n"
                        "# …\n"
                        'CMD [".venv/bin/uvicorn", "guide.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-image-dev-contrast",
                    text=(
                        "The dev image is the same caching shape with "
                        "different values: the second sync is a plain "
                        "editable install (dev groups included), and the "
                        "CMD runs the venv's uvicorn binary directly "
                        "under --reload — no implicit sync at boot, "
                        "because compose then bind-mounts live source "
                        "over /app and shadows .venv with an anonymous "
                        "volume seeded from this layer. That is the "
                        "parity thesis in miniature, and it recurs "
                        "through this whole topic: dev and prod differ "
                        "by VALUES — editable vs built, reload vs drain "
                        "budget, dev groups vs none — never by process "
                        "shape or by which code runs. Same Dockerfile "
                        "skeleton, same entrypoint, same app; the "
                        "differences are flags a diff can show."
                    ),
                ),
            ],
        ),
        # ── 3. Compose (trio) + demo ──────────────────────────────────────
        Section(
            id="compose-trio",
            title="Compose",
            lead="This section carries the topic's demo — the live deploy-stack inspection.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dpl-compose-pitch",
                    text=(
                        "One container is a process; a deployment is a "
                        "topology — processes, networks, volumes, "
                        "healthchecks, and the ordering between them. "
                        "Docker Compose declares a topology in one "
                        "diffable YAML file, and this repo's deploy "
                        "surface is exactly three of them, split by "
                        "LIFETIME rather than by environment. The split "
                        "is the interesting decision: what outlives a "
                        "release (the datastores), what IS a release (the "
                        "app containers), and what only CI needs (an "
                        "override that bends the app file to a "
                        "runner's realities) are three different files "
                        "with three different owners:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="dpl-compose-trio-roles",
                    ordered=False,
                    items=[
                        "Platform — docker-compose.platform.yml, project "
                        "fdg_platform: postgres, redis, mongo; booted "
                        "once, untouched by every release; external "
                        "fdg_prod_* volumes and the fdg_backend network.",
                        "App stack — docker-compose.prod.yml, project "
                        "fdg_<color>: the server + client images of ONE "
                        "pinned release, gated by required-variable "
                        "rails; booted per deploy under the inactive "
                        "color.",
                        "CI override — docker-compose.ci.yml, project "
                        "fastapi_developers_guide_ci: pins the :ci image "
                        "tags, fixes container names, publishes the "
                        "client on the loopback; merged OVER the app "
                        "file by CI only.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="dpl-compose-platform-pin",
                    text=(
                        "The platform file is where long-lived state "
                        "meets version discipline, and its mongo service "
                        "is the honest teacher — pinned to the exact "
                        "patch the production volume was written with, "
                        "because a floating tag drifted under a live "
                        "datastore once and the volume refused to open "
                        "under the wrong mongod:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-compose-platform-quote",
                    language="yaml",
                    caption="Platform state: a patch-pinned datastore, a healthcheck, a network alias — survives every release flip.",
                    source=".docker/docker-compose-platform.yml",
                    snippet=(
                        "  mongo:\n"
                        "    # …\n"
                        "    image: mongo:8.0.34\n"
                        "    container_name: fdg_mongo\n"
                        "    restart: unless-stopped\n"
                        "    volumes:\n"
                        "      - mongo_data:/data/db\n"
                        "    healthcheck:\n"
                        '      test: ["CMD", "mongosh", "--quiet", "--eval", "db.runCommand({ ping: 1 }).ok"]\n'
                        "      # …\n"
                        "      interval: 10s\n"
                        "      timeout: 10s\n"
                        "      retries: 18\n"
                        "      start_period: 60s\n"
                        "    networks:\n"
                        "      fdg_backend:\n"
                        "        aliases:\n"
                        "          - mongo"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-compose-platform-reading",
                    text=(
                        "Three details worth internalizing. The image is "
                        "a full patch pin, with a comment recording WHY "
                        "(kernel-detection patches refused to start on "
                        "the runner kernels of late 2026) — a pin "
                        "without its reason rots into dogma. The "
                        "healthcheck is generous on purpose (start_period "
                        "60s, 18 retries): healthchecks are for humans "
                        "and pipelines, and a flapping one is worse than "
                        "none. And the network alias is the seam: the "
                        "app stacks join fdg_backend and reach this "
                        "postgres by the plain name postgres — the "
                        "alias keeps the app's URL shape stable no "
                        "matter which compose project owns the "
                        "datastore. The volumes at the bottom of the "
                        "file are external on purpose — created by the "
                        "deploy, looked up by compose, and never owned "
                        "by any one release, which is exactly why a "
                        "blue/green flip never touches data."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-compose-prod-pitch",
                    text=(
                        "The app-stack file is the release itself, and "
                        "its strongest feature is what it refuses to "
                        "do: it refuses to render without a pinned "
                        "image tag, and it refuses to render without "
                        "the three secrets. Compose's required-variable "
                        "syntax — ${VAR:?message} — turns an unset "
                        "variable into a deploy-time ERROR at config "
                        "time, before any container exists:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-compose-prod-quote",
                    language="yaml",
                    caption="The release stack: image rail, secrets rails, and a healthcheck the slim image can actually run.",
                    source=".docker/docker-compose.prod.yml",
                    snippet=(
                        "services:\n"
                        "  server:\n"
                        '    image: "ghcr.io/mayank-uk/fastapi-guide-server:${IMAGE_TAG:?IMAGE_TAG is required}"\n'
                        "    container_name: fdg_server_${COLOR:-blue}\n"
                        "    restart: unless-stopped\n"
                        "    # …\n"
                        "    environment:\n"
                        "      - FDG_ENV=prod\n"
                        "      # …\n"
                        "      - FDG_DATABASE_URL=postgresql+asyncpg://postgres:${FDG_DB_PASSWORD:?FDG_DB_PASSWORD must be set to a real database password}@postgres:5432/guide\n"
                        "      # …\n"
                        "      - FDG_JWT_SECRET=${FDG_JWT_SECRET:?FDG_JWT_SECRET must be set to a real high-entropy signing secret}\n"
                        "      - FDG_SESSION_SECRET=${FDG_SESSION_SECRET:?FDG_SESSION_SECRET must be set to a real high-entropy signing secret, distinct from FDG_JWT_SECRET}\n"
                        "    healthcheck:\n"
                        "      # …\n"
                        '      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen(\'http://127.0.0.1:8000/api/health\', timeout=5)"]\n'
                        "      interval: 30s\n"
                        "      timeout: 5s\n"
                        "      retries: 3\n"
                        "      start_period: 30s"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-compose-prod-reading",
                    text=(
                        "Note the healthcheck probe binary: the runtime "
                        "image is python:3.13-slim — no wget, no curl — "
                        "so the probe is the venv's own python issuing "
                        "one urllib GET against the liveness route from "
                        "the previous section. A healthcheck you cannot "
                        "run is a healthcheck you do not have; 'what "
                        "binaries exist in the image' is a deployment "
                        "question, not a trivia one. The environment "
                        "block also encodes precedence: environment: "
                        "beats env_file:, so FDG_ENV=prod and the "
                        "database URL win over anything the materialized "
                        "env file might carry — the file supplies "
                        "secrets, compose supplies topology."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-compose-demo-pitch",
                    text=(
                        "The rest of this topic keeps referring to that "
                        "deploy surface, so the demo makes it "
                        "inspectable: one GET that walks the surface and "
                        "reports, per claim, whether it CHECKED OUT — "
                        "reading the real compose files, Dockerfiles, "
                        "workflows, and env template from disk, plus the "
                        "runtime facts this very process always knows."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="deploy:stack",
                    title="The deploy stack, inspected",
                    description=(
                        "GET /api/demo/deploy/stack inspects the repo's "
                        "REAL deploy surface at request time. Runtime "
                        "rows are always live: the env this process "
                        "booted in, interpreter and pid, the server "
                        "command line (graceful-shutdown budget, "
                        "workers, --reload presence), and a REAL "
                        "internal GET /api/health driven through the "
                        "serving app. File rows read the actual "
                        "artifacts — the compose trio's services and "
                        "rails, the Dockerfiles' stages, the CI/deploy "
                        "workflows' gates, the env template — and quote "
                        "what they found; they run for real where the "
                        "repo is mounted (tests, the dev container) and "
                        "report honest manual verdicts on the live "
                        "server container, whose bind mount is server/ "
                        "only. The AppConfig row reads the server tree "
                        "and verifies everywhere; the Kubernetes row "
                        "checks a verifiable absence — deploy/k8s/ does "
                        "not exist in this repo."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-compose-demo-reading",
                    text=(
                        "Read the panel the way you would audit a "
                        "colleague's deployment: the runtime block first "
                        "(what is THIS process), then each area's "
                        "verdicts — every 'pass' carries the evidence "
                        "line that produced it, and the manual rows say "
                        "exactly why they cannot run from where you are "
                        "standing. The endpoint behind it is the usual "
                        "thin router: one GET, the builder does the "
                        "work, a declared response model:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-compose-router-quote",
                    language="py",
                    caption="One GET, the payload builder, the honest roots — repo root only when its marker is visible.",
                    source="server/guide/presentation/routers/demo/deploy.py",
                    snippet=(
                        '@router.get(STACK_PATH, response_model=DeployStackPanel)\n'
                        "async def read_deploy_stack_panel(\n"
                        "    request: Request,\n"
                        "    config: Annotated[AppConfig, Depends(get_config)],\n"
                        ") -> DeployStackPanel:\n"
                        '    """Serve the live deploy panel: runtime facts, file checks, honest manuals."""\n'
                        "    server_root, repo_root = default_roots()\n"
                        "    return await build_deploy_stack_payload(\n"
                        "        app=request.app,\n"
                        "        config=config,\n"
                        "        server_root=server_root,\n"
                        "        repo_root=repo_root,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-compose-demo-honesty",
                    text=(
                        "The honesty mechanism is the best-checklist "
                        "pattern: repo-root checks consult a visibility "
                        "marker and degrade to manual rows that NAME the "
                        "reason (the server container's bind mount is "
                        "server/ only), while a check whose file is "
                        "missing under a VISIBLE root is a fail, never "
                        "a silent skip. The judging core is small "
                        "enough to read in one glance, and both "
                        "directions are pinned by the endpoint's tests "
                        "— the real direction where the repo is "
                        "mounted, the degraded direction with the root "
                        "removed:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-compose-test-quote",
                    language="py",
                    caption="Both directions pinned: real file checks where mounted, honest manual rows where not.",
                    source="server/tests/demo/test_deploy_stack_endpoint.py",
                    snippet=(
                        "def test_repo_root_checks_follow_visibility_honestly(client: TestClient) -> None:\n"
                        "    _, repo_root = default_roots()\n"
                        "    rows = rows_by_area(client.get(STACK_PATH).json())\n"
                        "    if repo_root is not None:\n"
                        '        assert rows["platform-services"]["checkKind"] == "file"\n'
                        '        assert rows["platform-services"]["verdict"] == "pass"\n'
                        "    else:\n"
                        '        assert rows["platform-services"]["verdict"] == "manual"\n'
                        '        assert "not visible from this process" in rows["platform-services"]["whyManual"]'
                    ),
                ),
            ],
        ),
        # ── 4. Reverse proxy / TLS ────────────────────────────────────────
        Section(
            id="reverse-proxy-tls",
            title="Reverse proxy and TLS",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dpl-proxy-pitch",
                    text=(
                        "Traffic reaches this app through two proxies, "
                        "and knowing which one you are talking to is "
                        "half of debugging a production URL. The OUTER "
                        "proxy is one shared Caddy container on the VM "
                        "that publishes 80/443 for every app on the "
                        "box: it terminates TLS (automatic certificates, "
                        "HTTP→HTTPS redirects, domain-wide compression), "
                        "and forwards to this app's client container by "
                        "name over a shared Docker network. The INNER "
                        "proxy is nginx inside the client image — an "
                        "app server, really — which serves the built "
                        "SPA files and proxies the API to the FastAPI "
                        "server:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-proxy-nginx-quote",
                    language="nginx",
                    caption="The internal app server: /api to the compose service name; hashed assets immutable; the entry document never stale.",
                    source=".docker/client/nginx.conf",
                    snippet=(
                        "    # Proxy API calls to the FastAPI server (compose service name).\n"
                        "    location /api/ {\n"
                        "        proxy_pass http://server:8000;\n"
                        "        proxy_http_version 1.1;\n"
                        "        proxy_set_header Upgrade $http_upgrade;\n"
                        "        proxy_set_header Connection 'upgrade';\n"
                        "        proxy_set_header Host $host;\n"
                        "        proxy_cache_bypass $http_upgrade;\n"
                        "    }\n"
                        "\n"
                        "    # Hashed static assets (Vite emits content-hashed filenames under\n"
                        "    # /assets/) — the hash IS the cache key, so cache forever.\n"
                        "    location /assets/ {\n"
                        "        expires 1y;\n"
                        '        add_header Cache-Control "public, immutable";\n'
                        "    }\n"
                        "\n"
                        "    # SPA history fallback: unknown paths serve the app, which renders the 404 view.\n"
                        "    location / {\n"
                        "        try_files $uri $uri/ /index.html;\n"
                        "    }\n"
                        "\n"
                        "    location = /index.html {\n"
                        '        add_header Cache-Control "no-cache, no-store, must-revalidate";\n'
                        '        add_header Pragma "no-cache";\n'
                        "        expires 0;\n"
                        "    }"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-proxy-nginx-reading",
                    text=(
                        "Three moves in that file carry deployment "
                        "lessons. proxy_pass http://server:8000 uses the "
                        "compose SERVICE NAME — Docker's embedded DNS "
                        "resolves it, and because each release's app "
                        "stack runs as its own project on its own "
                        "app_internal network, 'server' can only ever "
                        "mean THIS release's API, never the other "
                        "color's (isolation by network namespace, not "
                        "by convention). The cache split is the "
                        "hashed-asset pattern from the caching topic "
                        "landed in config: content-hatched filenames "
                        "are immutable forever, while index.html — the "
                        "one document that names those files — always "
                        "revalidates, so a new deploy is picked up on "
                        "the very next visit. And the WebSocket upgrade "
                        "headers exist because the realtime topic's "
                        "sockets ride this same proxy."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-proxy-caddy",
                    text=(
                        "The outer edge is deliberately NOT per-app "
                        "infrastructure. One Caddy serves every domain "
                        "on the VM from its own compose project, and "
                        "this app's integration with it is a single "
                        "line in a file: platform/upstream.caddy reads "
                        "reverse_proxy fdg_client_<color>:80 — the "
                        "deploy rewrites that line to flip releases, "
                        "and the shared Caddy bind-mounts the file "
                        "read-only. Caddy reloads gracefully on that "
                        "flip (existing connections drain), and because "
                        "certificates live in exactly one place, a "
                        "release swap cannot fumble TLS. The rollouts "
                        "section shows the flip in the deploy workflow's "
                        "own words."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-proxy-tls-coda",
                    text=(
                        "Why terminate TLS at the edge and run plain "
                        "HTTP behind it? Because the hops behind the "
                        "edge — caddy to the client container, nginx to "
                        "the server container — travel private Docker "
                        "networks on one host, where the threat TLS "
                        "answers (on-path interception) is not the "
                        "threat that matters, while certificate "
                        "lifecycle in every container WOULD be an "
                        "operational cost multiplied by every release. "
                        "One place owns certs, renewal, and redirects; "
                        "everything inside is least-privilege by "
                        "network. If your hops leave the host, that "
                        "arithmetic changes — cross-machine traffic "
                        "belongs encrypted, and mTLS between services "
                        "is the scaled-up version of this same decision."
                    ),
                ),
            ],
        ),
        # ── 5. gunicorn + uvicorn workers / graceful shutdown ─────────────
        Section(
            id="workers-graceful-shutdown",
            title="gunicorn + uvicorn workers, graceful shutdown",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dpl-workers-pitch",
                    text=(
                        "The CMD runs one uvicorn process, and the "
                        "first deployment question everyone asks is "
                        "whether it should. A worker process is a "
                        "separate OS process running the same "
                        "application; N workers multiply throughput "
                        "when N cores would otherwise idle, and — more "
                        "importantly for a threaded-interpreter stack — "
                        "they give you process-level isolation: a wedged "
                        "or leaking worker dies alone while its siblings "
                        "serve. The classic recipe predates containers "
                        "and is still the safe default for bare-metal "
                        "or single-big-VM Python deployments:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-workers-recipe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# The classic multi-worker shape (NOT what this repo runs — honest recipe):\n"
                        "gunicorn guide.main:app \\\n"
                        "  --workers 4 \\\n"
                        "  --worker-class uvicorn.workers.UvicornWorker \\\n"
                        "  --bind 0.0.0.0:8000 \\\n"
                        "  --graceful-timeout 30 \\\n"
                        "  --timeout 120\n"
                        "# gunicorn is the process manager: it forks N UvicornWorker\n"
                        "# processes, restarts dead ones, and passes signals through.\n"
                        "# The performance topic's uvloop note applies inside each worker."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-workers-single",
                    text=(
                        "This repo deliberately runs a single uvicorn "
                        "per container, and the reasoning is the "
                        "container flip-side of the same coin: if a "
                        "process manager can fork workers for you, a "
                        "container orchestrator can fork CONTAINERS — "
                        "with better blast-radius properties, because "
                        "each copy gets its own network identity, "
                        "healthcheck, and lifecycle. The event loop is "
                        "this app's concurrency model (async handlers, "
                        "threadpool offloads for blocking work), and "
                        "the GIL means extra workers help CPU-bound "
                        "code more than async I/O code. Scaling here is "
                        "horizontal: more replicas of the same "
                        "single-process container behind the proxy — "
                        "the blue/green stacks are literally that "
                        "pattern, and the scaling topic picks it up."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-graceful-pitch",
                    text=(
                        "The other half of the process story is how it "
                        "ENDS — and it ends constantly: every deploy "
                        "retires a color, every restart sends SIGTERM, "
                        "and 'docker stop' kills anything that outlives "
                        "its grace window. An ungraceful server drops "
                        "in-flight requests on the floor mid-response. "
                        "The shutdown path has three stages: stop "
                        "accepting new connections, finish what is in "
                        "flight (bounded by a timeout), then run the "
                        "application's own shutdown so connections and "
                        "background loops close cleanly. The image's "
                        "CMD sets the drain budget, and the app's "
                        "lifespan does the closing:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-graceful-cmd-quote",
                    language="dockerfile",
                    caption="The drain budget lives in the image's CMD: 30 seconds for in-flight requests.",
                    source=".docker/server/Dockerfile.prod",
                    snippet=(
                        "# Graceful shutdown: in-flight requests get 30s to drain before exit.\n"
                        'CMD ["uvicorn", "guide.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "30"]'
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-graceful-lifespan-quote",
                    language="py",
                    caption="The app's side of shutdown: everything with a close/dispose gets one, in the lifespan's finally-half.",
                    source="server/guide/main.py",
                    snippet=(
                        "    config = get_config()\n"
                        "    await upgrade_database_on_startup(config.database_url)\n"
                        "    yield\n"
                        "    await app.state.db_engine.dispose()\n"
                        "    await app.state.grpc_runtime.stop()\n"
                        "    app.state.mongo_client.close()\n"
                        "    await app.state.redis_client.aclose()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-graceful-reading",
                    text=(
                        "On SIGTERM, uvicorn closes the listening "
                        "socket, waits up to 30 seconds for in-flight "
                        "responses, then runs the code after the "
                        "lifespan's yield — disposing the async engine's "
                        "pool, stopping the gRPC satellite, closing the "
                        "mongo and redis clients. One honest wrinkle "
                        "worth more than the happy path: docker stop "
                        "sends SIGTERM and then SIGKILLs after a grace "
                        "window whose default is TEN seconds — shorter "
                        "than the image's 30-second drain. The prod "
                        "compose file does not (yet) raise "
                        "stop_grace_period, so in practice the drain is "
                        "capped at the container's grace, not the "
                        "CMD's budget. Knowing your stop path end to "
                        "end — signal, drain budget, container grace — "
                        "is exactly the kind of arithmetic that turns a "
                        "'randomly dropped requests on deploy' bug into "
                        "a one-line fix."
                    ),
                ),
            ],
        ),
        # ── 6. CI/CD ──────────────────────────────────────────────────────
        Section(
            id="ci-cd",
            title="CI/CD",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dpl-ci-pitch",
                    text=(
                        "The CI workflow's server job is this repo's "
                        "verification protocol, replayed on a hosted "
                        "runner — same locked sync, same suite, same "
                        "lint and types. That identity is the point: "
                        "there is no second, weaker 'CI suite' to drift "
                        "from the local one, so green locally means "
                        "green hosted, and the steps read like the "
                        "dev-container commands they mirror:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-ci-server-quote",
                    language="yaml",
                    caption="The CI contract IS the local contract: locked sync, suite, lint, types.",
                    source=".github/workflows/ci.yml",
                    snippet=(
                        "            - run: uv sync --locked\n"
                        "            # …\n"
                        "            - name: Migrate and seed the fresh PostgreSQL\n"
                        "              run: |\n"
                        "                  uv run python -c '\n"
                        "                  # …\n"
                        "                  '\n"
                        "\n"
                        "            - run: uv run pytest -q\n"
                        "            - run: uv run ruff check .\n"
                        "            - run: uv run mypy guide"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-ci-reading",
                    text=(
                        "The interesting engineering is around those "
                        "four lines: the integration tests dial the "
                        "dev-stack datastore HOSTNAMES (postgres, "
                        "redis, mongo), so the job boots the same image "
                        "versions on the runner's loopback and aliases "
                        "the names to 127.0.0.1 — the suite cannot tell "
                        "it is not inside the dev network. And because "
                        "the data adapter tests assume the SEEDED dev "
                        "posture, the job migrates and seeds the fresh "
                        "PostgreSQL through the app's own entry points "
                        "(the same lifecycle function the server runs "
                        "at boot) rather than duplicating schema logic "
                        "in YAML — one source of truth, exercised "
                        "twice."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-ci-e2e-quote",
                    language="yaml",
                    caption="The image smoke: boot the platform, then the prod images beside it — the deploy's own seam.",
                    source=".github/workflows/ci.yml",
                    snippet=(
                        "                  docker compose -f .docker/docker-compose-platform.yml \\\n"
                        "                    -f .docker/docker-compose.platform-ci.yml up -d --wait --wait-timeout 300\n"
                        "                  docker compose -f .docker/docker-compose.prod.yml \\\n"
                        "                    -f .docker/docker-compose.ci.yml up -d --wait"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-ci-publish",
                    text=(
                        "Only after the browser gate passes does CI "
                        "publish. Publishing is deliberately paranoid: "
                        "an SSH recon reads the deployment VM's "
                        "architecture first, so images are built for "
                        "the platform the VM actually runs (QEMU "
                        "cross-building when runner and VM differ); "
                        "each image carries provenance and SBOM "
                        "attestations pushed alongside it as OCI "
                        "artifacts — verifiable answers to 'how was "
                        "this built' and 'what is inside it'; and the "
                        "tags are the commit — sha-<7> plus a moving "
                        "master — so a deployment always names an "
                        "immutable artifact. A prune job keeps the ten "
                        "newest sha tags and never deletes untagged "
                        "versions, a rule written in the aftermath of "
                        "an incident where an untagged sweep deleted "
                        "the per-arch children of a LIVE image and "
                        "took the deploy down — hygiene must never "
                        "outsmart the graph."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-ci-publish-quote",
                    language="yaml",
                    caption="Attested publishing: provenance + SBOM ride the image; the tag is the commit.",
                    source=".github/workflows/ci.yml",
                    snippet=(
                        "                    platforms: linux/${{ needs.vm-arch.outputs.arch }}\n"
                        "                    push: true\n"
                        "                    # …\n"
                        "                    provenance: true\n"
                        "                    sbom: true\n"
                        "                    tags: |\n"
                        "                      ${{ matrix.image }}:${{ steps.image_tag.outputs.tag }}\n"
                        "                      ${{ matrix.image }}:master"
                    ),
                ),
            ],
        ),
        # ── 7. parity / secrets ───────────────────────────────────────────
        Section(
            id="parity-secrets",
            title="Parity and secrets",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dpl-parity-pitch",
                    text=(
                        "Parity means the environments differ by values, "
                        "never by code or shape — and the values that "
                        "differ most dangerously are secrets. This "
                        "repo's secrets story has three doors, and "
                        "understanding why there are three (not one) is "
                        "the lesson. The committed artifact is a "
                        "TEMPLATE whose placeholders are chosen to "
                        "actually boot:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-parity-env-quote",
                    language="bash",
                    caption="The committed template: placeholders long and distinct enough to pass the validator, clearly not secrets.",
                    source="server/.env.production.example",
                    snippet=(
                        "FDG_DB_PASSWORD=placeholder-db-password-not-a-secret-ci-and-docs-only\n"
                        "FDG_JWT_SECRET=placeholder-jwt-signing-secret-32-chars-not-a-secret\n"
                        "FDG_SESSION_SECRET=placeholder-session-signing-secret-32-chars-not-a-secret\n"
                        "\n"
                        "# FDG_ENV / FDG_DATABASE_URL / FDG_REDIS_URL / FDG_MONGO_URL stay unset in\n"
                        "# this FILE on purpose — docker-compose.prod.yml supplies them via its\n"
                        "# environment: block, which beats env_file, pointing at the platform\n"
                        "# datastores by network alias."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-parity-materialize",
                    text=(
                        "The real file never touches git. It lives as "
                        "ONE GitHub environment secret — the base64 of "
                        "the whole file — and the deploy materializes "
                        "it on the runner at deploy time, mode 600, "
                        "after first validating the committed template "
                        "against the compose rails:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-parity-materialize-quote",
                    language="yaml",
                    caption="Secrets materialize at deploy time from the environment secret — never stored in the repo.",
                    source=".github/workflows/deploy-production.yml",
                    snippet=(
                        "            - name: Materialize the production env file from the environment secret\n"
                        "              env:\n"
                        "                  PROD_ENV_B64: ${{ secrets.PROD_ENV_B64 }}\n"
                        "              run: |\n"
                        "                  set -euo pipefail\n"
                        '                  printf \'%s\' "${PROD_ENV_B64:?PROD_ENV_B64 secret missing}" |\n'
                        "                    base64 -d > server/.env.production\n"
                        "                  chmod 600 server/.env.production"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-parity-rails",
                    text=(
                        "Now the three doors, in the order a forgotten "
                        "secret meets them. Door one: the compose "
                        "required-variable rails from the app-stack "
                        "section — an unset FDG_DB_PASSWORD or signing "
                        "secret fails `docker compose config` before "
                        "any container exists. Door two: the "
                        "application itself — AppConfig's validator "
                        "refuses to construct a non-dev config that "
                        "still carries a dev-default secret, naming "
                        "every offending variable. Door three: CI runs "
                        "a secrets scanner over the full history, so "
                        "the class of mistake that would commit the "
                        "real file is caught before it lands. Defense "
                        "in depth is not three times the work of one "
                        "check; each door catches failures the others "
                        "cannot — unset values, wrong values, and "
                        "leaked values are three different bugs. Here "
                        "is door two, the one that travels inside the "
                        "image:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-parity-config-quote",
                    language="py",
                    caption="The in-process door: a dev-default secret outside dev is a boot failure naming the variables.",
                    source="server/guide/core/config.py",
                    snippet=(
                        "    @model_validator(mode=\"after\")\n"
                        "    def _refuse_dev_secrets_outside_dev(self) -> Self:\n"
                        "        # …\n"
                        "        if self.env == _DEV_ENV:\n"
                        "            return self\n"
                        "        defaults = type(self).model_fields\n"
                        "        unset = [\n"
                        '            f"FDG_{name.upper()}"\n'
                        "            for name, field in defaults.items()\n"
                        '            if name.endswith("_secret") and getattr(self, name) == field.get_default()\n'
                        "        ]\n"
                        "        if unset:\n"
                        "            raise ValueError(\n"
                        '                f"env={self.env!r} refuses dev-default signing secrets: "\n'
                        '                f"{\', \'.join(unset)} must be set to real high-entropy values "\n'
                        '                f"(distinct from each other) before the app may start"\n'
                        "            )\n"
                        "        return self"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-parity-coda",
                    text=(
                        "Note the validator is generic on purpose — it "
                        "walks model fields ending in _secret rather "
                        "than hardcoding two names, so the NEXT secret "
                        "the app grows is protected the day it lands. "
                        "That is the parity discipline generalized: "
                        "write the rule once, at the layer that owns "
                        "the concept, and let every environment inherit "
                        "it — dev boots with safe defaults, CI boots "
                        "with placeholders, prod boots with real "
                        "values, and the code cannot tell, or care, "
                        "which one it is."
                    ),
                ),
            ],
        ),
        # ── 8. Kubernetes ─────────────────────────────────────────────────
        Section(
            id="kubernetes",
            title="Kubernetes",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dpl-k8s-pitch",
                    text=(
                        "Kubernetes is a container orchestrator: a "
                        "control plane that takes a DECLARATIVE "
                        "description of your workload — 'run three "
                        "replicas of this image, healthy by this probe, "
                        "receiving traffic on this port' — and continuously "
                        "reconciles reality toward it, restarting dead "
                        "pods, rescheduling around node failures, and "
                        "rolling out new versions by replacing pods "
                        "gradually. Everything this topic has built by "
                        "hand — the healthchecks, the replicas, the "
                        "zero-downtime swap — kubernetes generalizes "
                        "into platform primitives, at the cost of "
                        "running and understanding the platform itself. "
                        "The vocabulary is small:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="dpl-k8s-vocab",
                    ordered=False,
                    items=[
                        "Pod — the smallest schedulable unit: one or "
                        "more containers sharing network and storage on "
                        "one node; your image runs inside one.",
                        "Deployment — the declarative workload: desired "
                        "replica count + pod template; owns rollouts "
                        "and rollbacks by creating/removing ReplicaSets.",
                        "Service — a stable virtual IP and DNS name "
                        "fronting a changing set of pods (this app's "
                        "'the compose service name' problem, solved "
                        "permanently).",
                        "Ingress / Gateway — HTTP routing and TLS at "
                        "the cluster edge; the kubernetes answer to the "
                        "shared caddy (cert-manager usually feeds it "
                        "certs).",
                        "Probes — liveness (restart me) and readiness "
                        "(route around me) checks; the same distinction "
                        "the observability topic built, as platform "
                        "verbs.",
                        "ConfigMap / Secret — configuration and secret "
                        "material mounted or injected into pods; the "
                        "env-file rails' cluster-native counterparts.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="dpl-k8s-mapping",
                    text=(
                        "The mapping from this repo's compose world is "
                        "almost one-to-one, which is the honest way to "
                        "learn it: a compose file is a manifest; the "
                        "service+healthcheck pair becomes a Deployment "
                        "with probes; docker DNS names become Services; "
                        "the shared caddy becomes an Ingress with "
                        "TLS termination; PROD_ENV_B64 becomes a "
                        "Secret; and the blue/green flip becomes a "
                        "Deployment rollout — 'change the image tag, "
                        "replace pods gradually, keep the old "
                        "ReplicaSet for instant rollback' is the "
                        "platform doing by hand what this repo's deploy "
                        "workflow scripts explicitly."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-k8s-honest",
                    text=(
                        "The honest position, recorded in the demo's "
                        "kubernetes row as a verifiable absence: this "
                        "repository ships NO kubernetes manifests — "
                        "there is no deploy/k8s/ directory — and that "
                        "is a decision, not an omission. One VM, three "
                        "long-lived datastores, one shared TLS edge, "
                        "and a blue/green swap whose blast radius is "
                        "one file write covers this workload's actual "
                        "requirements; an orchestrator would add a "
                        "control plane to operate, RBAC to design, and "
                        "a second mental model for networking, in "
                        "exchange for self-healing and elastic scaling "
                        "this single-node deployment has no use for "
                        "yet. The signals to graduate are concrete: a "
                        "second node for redundancy or capacity, "
                        "deployments wanting per-service scaling, or "
                        "team growth past what one VM's shell history "
                        "can explain. Until then the compose trio IS "
                        "the right amount of orchestration."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-k8s-recipe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# The recipe for the day this repo graduates (NOT deployed here — honest recipe):\n"
                        "kubectl apply -f deploy/k8s/            # manifests would live here; they don't yet\n"
                        "kubectl rollout status deployment/guide-server\n"
                        "kubectl rollout undo deployment/guide-server   # the flip, as a platform verb\n"
                        "kubectl get pods -o wide                  # the answer to 'is it actually running'\n"
                        "kubectl describe pod <name>               # events + probe failures, the k8s log line"
                    ),
                ),
            ],
        ),
        # ── 9. rollouts ───────────────────────────────────────────────────
        Section(
            id="rollouts",
            title="Rollouts",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dpl-rollout-pitch",
                    text=(
                        "A rollout is the act of replacing the running "
                        "release with a new one while traffic flows. "
                        "This repo's answer is blue/green: TWO complete "
                        "app stacks — blue and green, each its own "
                        "compose project — where only one receives "
                        "traffic at a time, and 'deploying' means "
                        "booting the inactive color, proving it "
                        "privately, then moving one pointer. The "
                        "pointer is the flip file the shared caddy "
                        "bind-mounts, and moving it is deliberately "
                        "the smallest possible operation:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-rollout-flip-quote",
                    language="yaml",
                    caption="The flip: one line in one file, then a graceful reload — no TLS blip, no restart.",
                    source=".github/workflows/deploy-production.yml",
                    snippet=(
                        "                      # ── 7. Flip: upstream file + reload the shared caddy ────────\n"
                        "                      printf 'reverse_proxy fdg_client_%s:80\\n' \"$COLOR\" \\\n"
                        "                        > \"$ROOT/platform/upstream.caddy\"\n"
                        "                      docker exec caddy caddy reload --config /etc/caddy/Caddyfile"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-rollout-reading",
                    text=(
                        "Everything around the flip exists to make it "
                        "safe to do quickly. BEFORE it: the new color "
                        "booted under its own project with its own "
                        "network, `up --wait` proved its healthchecks, "
                        "and a private probe — a throwaway busybox "
                        "container joined to the new color's network, "
                        "curling the server and client by service name "
                        "— proved the stack answers from inside, all "
                        "while the live color kept serving. AFTER it: "
                        "a public health gate polls the real URL "
                        "through the real edge, and only then does the "
                        "workflow persist state — the last-successful "
                        "sha and the active color, each written to a "
                        "temp file and moved into place atomically — "
                        "and retire the old color. A failure at ANY "
                        "pre-flip step cleans up the candidate and "
                        "changes nothing a user could see."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-rollout-rollback-quote",
                    language="yaml",
                    caption="The rollback: flip the file back to the still-running color and reload.",
                    source=".github/workflows/deploy-production.yml",
                    snippet=(
                        "                      # ── 10. Post-flip failure: instant rollback ─────────────────\n"
                        '                      echo "Public health check failed after the flip: $DEPLOY_SHA" >&2\n'
                        "\n"
                        '                      if [ "$HAD_ACTIVE_COLOR" -eq 1 ]; then\n'
                        '                        echo "Flipping back to the still-running color $ACTIVE_COLOR." >&2\n'
                        "                        printf 'reverse_proxy fdg_client_%s:80\\n' \"$ACTIVE_COLOR\" \\\n"
                        "                          > \"$ROOT/platform/upstream.caddy\"\n"
                        "                        docker exec caddy caddy reload --config /etc/caddy/Caddyfile\n"
                        "                        # …"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-rollout-coda",
                    text=(
                        "The rollback is the same one-line flip, pointed "
                        "at the old color that never stopped running — "
                        "which is the entire argument for blue/green "
                        "over rolling updates: rollback latency is one "
                        "file write, not a re-roll of N pods through a "
                        "bad version. The costs are honest too: double "
                        "the app-tier resources during a deploy, a "
                        "database that must tolerate two schema "
                        "generations (this repo's migrations are "
                        "additive for exactly that reason), and release "
                        "directories to prune — the deploy keeps the "
                        "newest five, never the active or previous sha. "
                        "Choose blue/green when the app is stateless "
                        "enough to double and the rollback SLA is "
                        "seconds; choose rolling when resources are "
                        "tight and a slower, partial rollback is "
                        "acceptable. This repo chose the first, and "
                        "the flip file is the whole mechanism — no "
                        "load-balancer API, no DNS change, one line of "
                        "Caddyfile."
                    ),
                ),
            ],
        ),
        # ── 10. IaC ───────────────────────────────────────────────────────
        Section(
            id="iac",
            title="Infrastructure as code",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dpl-iac-pitch",
                    text=(
                        "Infrastructure as code means the servers, "
                        "networks, and volumes your app needs are "
                        "described in versioned, diffable files that a "
                        "machine can apply idempotently — running the "
                        "description twice changes nothing the second "
                        "time. You already speak it: this repo's "
                        "deploy surface IS code, in the plainest sense. "
                        "The compose trio describes the topology; the "
                        "workflows describe the process; the deploy "
                        "script creates the networks and external "
                        "volumes idempotently (`docker volume inspect "
                        "|| docker volume create` — the pattern in its "
                        "two-line essence). What the industry adds on "
                        "top is scale: templates that describe cloud "
                        "resources the same way, with a state file "
                        "tracking what the description created."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-iac-ladder",
                    text=(
                        "Think of it as a ladder, and notice you are "
                        "already on it. Rung one: shell scripts — "
                        "imperative, drift-prone, but honest. Rung two, "
                        "where this repo stands: container topology as "
                        "declarative files (compose), applied by a "
                        "versioned pipeline — the VM's docker daemon is "
                        "the only pet left. Rung three: the cloud "
                        "itself as files — Terraform, Pulumi, "
                        "OpenTofu — where the VM, its disks, its "
                        "firewall, and its DNS records are resources "
                        "with a plan/apply lifecycle. Rung four: the "
                        "cluster as the platform, IaC feeding it — "
                        "crossplane and friends making the kubernetes "
                        "API itself the infrastructure registry. Each "
                        "rung buys coverage and costs a control system; "
                        "standing a rung too high for your actual "
                        "complexity is the classic over-engineering "
                        "story with extra YAML."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-iac-recipe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# The rung-three recipe (NOT used by this repo — honest recipe):\n"
                        "terraform plan -out=tfplan    # diff: what WOULD change, before anything does\n"
                        "terraform apply tfplan        # converge reality onto the description\n"
                        "terraform state list          # what the description currently owns\n"
                        "# The property that matters is plan: preview, then apply —\n"
                        "# the same discipline as `docker compose config` before `up`."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-iac-tradeoffs",
                    text=(
                        "What full IaC adds beyond compose: STATE — a "
                        "record of which real resources belong to which "
                        "described ones, so deletion is as declarative "
                        "as creation; DRIFT DETECTION — noticing when "
                        "the console-clicking human changed something "
                        "the file does not know about; and PLAN — a "
                        "dry-run diff before convergence, the same "
                        "instinct as `compose config -q`. What it "
                        "costs: a state file that is itself a secret-"
                        "bearing critical artifact (back it up, lock "
                        "it, or use a remote backend), and a second "
                        "thing that can out-age the team that "
                        "understands it. The decision rule mirrors the "
                        "kubernetes one: when the infrastructure is "
                        "one VM created once by hand, a paragraph of "
                        "prose in the repo documents it better than "
                        "four hundred lines of HCL; when the second "
                        "environment or the second cloud account "
                        "appears, the template pays for itself "
                        "immediately."
                    ),
                ),
            ],
        ),
        # ── 11. Linux survival ────────────────────────────────────────────
        Section(
            id="linux-survival",
            title="Linux survival",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dpl-linux-pitch",
                    text=(
                        "Deployment servers run Linux, and the day "
                        "something breaks there is no container shell "
                        "nicety between you and the box. The survival "
                        "kit is small — a dozen commands — but it is "
                        "real enough that this repo's own deploy script "
                        "carries a version of it: when the platform "
                        "fails to boot, the workflow dumps diagnostics "
                        "into the Actions log before failing, because "
                        "a bare 'container unhealthy' one-liner wastes "
                        "the next hour. The function is worth reading "
                        "as a checklist of what matters on a sick box:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-linux-diag-quote",
                    language="yaml",
                    caption="The deploy's own diagnostics: container state, logs, kernel, disk, memory — the incident kit, verbatim.",
                    source=".github/workflows/deploy-production.yml",
                    snippet=(
                        "                      dump_platform_diagnostics() {\n"
                        '                        echo "PLATFORM BOOT FAILED - diagnostics follow" >&2\n'
                        "                        for c in fdg_postgres fdg_redis fdg_mongo; do\n"
                        '                          echo "=== $c: $(docker inspect -f \'state={{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}} image={{.Config.Image}}\' "$c" 2>/dev/null || echo not-present)" >&2\n'
                        '                          docker logs --tail 60 "$c" 2>&1 | sed "s/^/[$c] /" >&2 || true\n'
                        "                        done\n"
                        '                        echo "=== kernel: $(uname -r)" >&2\n'
                        "                        df -h / 2>&1 | sed 's/^/[df] /' >&2 || true\n"
                        "                        free -h 2>&1 | sed 's/^/[mem] /' >&2 || true\n"
                        "                      }"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-linux-diag-reading",
                    text=(
                        "Every line answers a question an incident "
                        "actually asks. State and exit code: did it "
                        "die, and how (OOMKilled is a memory story, "
                        "exit 1 a configuration one)? The last 60 log "
                        "lines, prefixed per container: what did it SAY "
                        "before dying? Kernel version: the mongo pin "
                        "story earlier in this topic turned on exactly "
                        "this — specific datastore builds refuse "
                        "specific kernel ranges. Disk and memory: the "
                        "two resources that fail slowly then suddenly, "
                        "and the two a full log volume or a leaking "
                        "process exhaust first. The kernel lesson "
                        "generalizes: on Linux, uname -r is a "
                        "deployment input, not trivia."
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="dpl-linux-kit",
                    ordered=False,
                    items=[
                        "ps aux | grep … — what is running, by whom, "
                        "eating how much CPU/memory; add pgrep -f for "
                        "script-free pid lookup.",
                        "ss -ltnp — which process listens on which "
                        "port; the first command when 'connection "
                        "refused' and 'it should be up' collide.",
                        "docker logs / docker inspect — the container "
                        "twins of tail and ps; -f follows, --tail N "
                        "bounds the past.",
                        "df -h / du -sh — disk headroom, then the "
                        "directory eating it; a full disk breaks "
                        "databases in confusing ways.",
                        "free -h — memory posture; Linux caching makes "
                        "'available' the column that matters, not "
                        "'free'.",
                        "kill -TERM <pid> — the polite stop (default "
                        "signal 15): exactly what docker stop and "
                        "compose down send first.",
                        "uname -r / uname -m — kernel and architecture; "
                        "version-gated software and image platforms "
                        "hang off these two strings.",
                        "chmod 600 / chown — permissions as deployment: "
                        "the env file materialized by the deploy gets "
                        "600 for the same reason it never touches git.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="dpl-linux-coda",
                    text=(
                        "The meta-skill is reading output like the "
                        "diagnostics function does: prefix every line "
                        "with its source, dump state before opinion, "
                        "and fail LOUD with the evidence attached — "
                        "the observability topic's correlation "
                        "discipline, applied to a shell. And the "
                        "survival instinct to internalize first: "
                        "prefer the commands that change NOTHING (ps, "
                        "ss, logs, inspect) over the ones that do, and "
                        "when a command WOULD change something on a "
                        "production box, make it the same idempotent, "
                        "logged shape the deploy script uses — that is "
                        "how a survival kit stays a toolkit instead of "
                        "becoming an incident report."
                    ),
                ),
            ],
        ),
        # ── 12. Terminal companion ────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="Deployment from a shell: the live stack inspection, the curriculum shape, an honest compose dry-run, this topic's own detail.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dpl-terminal-intro",
                    text=(
                        "Five stops on the running stack: the deploy "
                        "panel with every verdict, the content index as "
                        "the pipeline's own product (the ship group "
                        "this topic registered), an honest local "
                        "dry-run of the prod compose file — the same "
                        "validate step the deploy workflow runs — and "
                        "this topic's detail through both ports."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-terminal-panel",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the deploy stack, inspected: runtime facts + every area's verdicts\n"
                        "curl -s localhost:8000/api/demo/deploy/stack | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for r in panel[\"runtime\"]:\n"
                        "    print(\"%-18s %s\" % (r[\"label\"], r[\"value\"]))\n"
                        "for area in panel[\"areas\"]:\n"
                        "    verdicts = \", \".join(i[\"verdict\"] for i in area[\"items\"])\n"
                        "    print(\"%-12s %-22s %s\" % (area[\"id\"], area[\"title\"], verdicts))\n"
                        "# every pass row carries its evidence; manual rows say exactly why'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-terminal-index",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the pipeline's product: the served curriculum, ship group included\n"
                        "curl -s localhost:8000/api/content | python3 -c '\n"
                        "import json, sys\n"
                        "index = json.load(sys.stdin)\n"
                        "print(len(index[\"topics\"]), \"topics /\", len(index[\"groups\"]), \"groups\")\n"
                        "print([g[\"id\"] for g in index[\"groups\"]])\n"
                        "t = next(t for t in index[\"topics\"] if t[\"id\"] == \"deployment\")\n"
                        "print(\"deployment:\", t[\"group\"], t[\"order\"], t[\"sectionCount\"], \"sections\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-terminal-config",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — an honest dry-run of the prod stack (the deploy's own validate step):\n"
                        "# the rails demand IMAGE_TAG + the three secrets, and env_file must resolve —\n"
                        "# the committed placeholder template satisfies all of it, exactly as CI does.\n"
                        "cd <repo-root>\n"
                        "cp server/.env.production.example server/.env.production\n"
                        "set -a; . server/.env.production; set +a\n"
                        "docker compose -f .docker/docker-compose.platform.yml config -q && echo platform-ok\n"
                        "IMAGE_TAG=ci docker compose -f .docker/docker-compose.prod.yml config -q && echo prod-ok\n"
                        "rm server/.env.production   # the placeholder's job is done; never commit it"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dpl-terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — this topic's own detail: demo inline in compose, companion last\n"
                        "curl -s localhost:8000/api/content/deployment | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'\n"
                        "# stop 5 — the same page through the client proxy\n"
                        "curl -s localhost:5174/api/content/deployment \\\n"
                        "  | python3 -c 'import json,sys; print(\"proxy sections:\", len(json.load(sys.stdin)[\"sections\"]))'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dpl-terminal-coda",
                    text=(
                        "Stops 1–2 are the topic in one glance: the "
                        "panel's verdicts are the deploy surface "
                        "audited live, and the index proves the "
                        "pipeline serves what this curriculum ships. "
                        "Stop 3 is the habit to keep — every compose "
                        "edit earns a `config -q` before an `up`, the "
                        "same dry-run instinct the deploy workflow "
                        "formalizes. Stops 4–5 close the guide's "
                        "standing loop: the topic that taught "
                        "deployment is deployed by the pipeline it "
                        "teaches, its demo the audit and its companion "
                        "the transcript."
                    ),
                ),
            ],
        ),
    ],
)
