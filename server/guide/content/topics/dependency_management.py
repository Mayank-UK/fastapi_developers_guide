"""Topic 31 — Dependency management: the dependency surface as product.

The repo already IS the lesson: a PEP 621 manifest whose ranges are for
humans to read, a committed uv.lock whose exact pins and hashes are for
machines to install, a PEP 735 dev group that keeps tooling out of the
runtime image, and a Docker build that copies the two manifests alone into
their own layer so dependency installation caches while source churns. This
topic teaches all of it in place — what a dependency even is (nothing is
assumed), how manifest and lock divide the work, how to read the resolved
graph with uv tree and audit it, the upgrade loop this repo actually runs,
and how each dependency in the list was CHOSEN (strawberry, grpcio,
argon2-cffi, arq — every one a real decision with a reason). The demo is a
live manifest panel: the real pyproject.toml and uv.lock parsed at request
time — groups, every direct range beside its locked pin, a manifest/lock
agreement cross-check, and a fastapi-rooted direct-vs-transitive slice.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="dependency-management",
    title="Dependency management",
    subtitle=(
        "The dependency surface as product: what a manifest and a lock each "
        "own, dependency groups that keep tooling out of the runtime, "
        "reading and auditing the resolved graph with uv tree, the upgrade "
        "loop this repo really runs, Docker layer caching built on the "
        "two-step uv sync, and how to choose a dependency at all — taught "
        "from the real pyproject.toml and uv.lock, with a live panel that "
        "parses both at request time."
    ),
    group="platform",
    order=31,
    sections=[
        # ── 1. Product surface ────────────────────────────────────────────
        Section(
            id="product-surface",
            title="Product surface",
            blocks=[
                TextBlock(
                    kind="text",
                    id="deps-surface-pitch",
                    text=(
                        "Every import statement in a server process reaches "
                        "code somebody else wrote, tested, and shipped. A "
                        "dependency is the named, versioned package your "
                        "project installs to make that import work — FastAPI "
                        "for the framework, sqlalchemy for the ORM, structlog "
                        "for logging — and dependency management is the "
                        "discipline of deciding which packages those are, "
                        "which versions run, and how that answer travels "
                        "from a laptop to a production container without "
                        "changing along the way. The Python ecosystem's "
                        "shared package registry is PyPI, and this repo "
                        "manages the whole lifecycle with uv: one tool that "
                        "owns the manifest, the lockfile, the virtual "
                        "environment, and the install step."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-surface-product",
                    text=(
                        "It is worth convincing yourself that this surface "
                        "IS product, not chore. The dependency list decides "
                        "what ships inside the production image and how big "
                        "it is; it decides whether a security audit takes an "
                        "afternoon or a week; it decides whether the build "
                        "reproduces on a new machine or decays into a "
                        "mystery; and when a vulnerability lands in a "
                        "package you use, the time-to-answer is exactly how "
                        "long it takes to ask 'which locked version do we "
                        "run'. A service with a sloppy dependency surface "
                        "feels fine right up until the day it is the "
                        "incident. This repo treats the surface as a "
                        "first-class artifact: server/pyproject.toml and "
                        "server/uv.lock sit beside the code, committed, "
                        "reviewed, and quoted by this guide like any other "
                        "source of truth."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-surface-jobs-framing",
                    text=(
                        "The discipline decomposes into four jobs, and every "
                        "section of this topic is one of them applied to "
                        "this repository:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="deps-surface-jobs",
                    ordered=False,
                    items=[
                        "Declare — the manifest (pyproject.toml) names every "
                        "direct dependency with a range a human can reason "
                        "about.",
                        "Resolve and pin — the lockfile (uv.lock) records "
                        "the exact version set the ranges resolved to, with "
                        "hashes, committed as the contract.",
                        "Install — uv sync materializes the lock into a "
                        "virtual environment, byte-identical everywhere, "
                        "never re-resolving on its own.",
                        "Maintain — upgrades, audits, and the choosing "
                        "judgment that keeps the list short enough to own.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="deps-surface-two-halves",
                    text=(
                        "The same discipline runs in the other half of "
                        "this repository, and seeing it twice in one "
                        "codebase is worth a pause. The client is a "
                        "Node project: its manifest is package.json and "
                        "its lock is package-lock.json, its installer is "
                        "npm instead of uv, and yet the division of "
                        "labor is identical — ranges that humans accept "
                        "in the manifest, an exact hashed resolution "
                        "committed as the lock, and installs that go "
                        "through the lock rather than improvising from "
                        "ranges (npm ci, the npm twin of uv sync "
                        "--locked). Dependency management is not a "
                        "Python idiom being memorized; it is a shape "
                        "every ecosystem converged on — Rust's Cargo, "
                        "Go's go.sum, JavaScript's package-lock — "
                        "because the underlying problem is ecosystem-"
                        "independent: make 'what runs' a reviewed, "
                        "reproducible artifact. Learn it once here and "
                        "you can read it everywhere."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-surface-coda",
                    text=(
                        "One vocabulary note before going further, because "
                        "the rest of the topic leans on it hard. A DIRECT "
                        "dependency is a name your manifest writes down — "
                        "you chose it. A TRANSITIVE dependency is a name "
                        "that appears only because a direct dependency "
                        "needs it — you never wrote it, but you run it, own "
                        "its vulnerabilities, and carry its weight. The "
                        "repo's manifest declares 26 direct names (19 "
                        "runtime, 7 dev), and the lock resolves those into "
                        "75 installed packages — roughly two thirds of the "
                        "running code arrived through edges of somebody "
                        "else's graph. Keeping that ratio legible is most "
                        "of the job, and the demo later in this topic makes "
                        "it visible."
                    ),
                ),
            ],
        ),
        # ── 2. pyproject.toml + uv lock/groups ────────────────────────────
        Section(
            id="pyproject-lock-groups",
            title="pyproject.toml + uv lock/groups",
            blocks=[
                TextBlock(
                    kind="text",
                    id="deps-manifest-pitch",
                    text=(
                        "Two files divide the work, and the split is the "
                        "whole design. The MANIFEST — server/pyproject.toml "
                        "— is for humans: it declares each dependency with "
                        "a RANGE like >=0.115 that says what you accept, "
                        "and nothing more precise. The LOCKFILE — "
                        "server/uv.lock — is for machines: it records the "
                        "exact version every range resolved to, for every "
                        "platform, with cryptographic hashes of every "
                        "artifact. The manifest says what you MEAN; the "
                        "lock says what you GET. The repo states the "
                        "contract in the manifest's own header, and it is "
                        "worth reading as a policy document:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-manifest-header-quote",
                    language="toml",
                    caption="The manifest's opening contract: ranges here, exact pins in the lock.",
                    source="server/pyproject.toml",
                    snippet=(
                        "# Server manifest for the FastAPI Developers Guide (`guide` package).\n"
                        "# Ranges live here; the committed uv.lock pins exact versions — the lock is\n"
                        "# THE dependency contract, `uv sync --locked` never re-resolves.\n"
                        "[project]\n"
                        "name = \"guide\"\n"
                        "version = \"0.1.0\"\n"
                        "description = \"FastAPI Developers Guide server: the typed content API that is the guide\"\n"
                        "requires-python = \">=3.13\"\n"
                        "dependencies = [\n"
                        "    \"alembic>=1.20.0\",\n"
                        "    \"argon2-cffi>=25.1.0\",\n"
                        "    \"arq>=0.25.0\",\n"
                        "    \"asyncpg>=0.32.0\",\n"
                        "    \"babel>=2.18.0\",\n"
                        "    \"fastapi>=0.115\",\n"
                        "    # …\n"
                        "    \"sqlalchemy[asyncio]>=2.1.4\",\n"
                        "    \"strawberry-graphql[fastapi]>=0.335.0\",\n"
                        "    \"structlog>=24.4\",\n"
                        "    \"uvicorn[standard]>=0.30\",\n"
                        "]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-manifest-reading",
                    text=(
                        "Read the entries as three decisions stacked in one "
                        "line. The name is the PyPI distribution you chose "
                        "to depend on. The specifier is the floor you are "
                        "willing to run — >=0.115 means 'any FastAPI from "
                        "0.115 on', a range wide enough to move under you "
                        "during resolution yet narrow enough to exclude "
                        "what you know broke. The bracketed suffix on "
                        "sqlalchemy[asyncio] and uvicorn[standard] selects "
                        "EXTRAS — optional feature bundles a package ships "
                        "behind additional requirements, here the asyncio "
                        "driver extras and uvicorn's production server "
                        "goodies (uvloop, watchfiles, websockets). "
                        "requires-python is the same idea aimed at the "
                        "interpreter itself: this project accepts Python "
                        "3.13 or newer, and uv refuses to resolve for "
                        "anything older."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-groups-pitch",
                    text=(
                        "The manifest's second act separates what RUNS from "
                        "what DEVELOPS. PEP 735 dependency groups hold "
                        "tooling that should never ship: pytest, ruff, "
                        "mypy, the gRPC code generator, testcontainers. uv "
                        "installs the dev group by default for humans, and "
                        "the production image explicitly skips it — the "
                        "Docker layer section shows the flag. A build "
                        "backend is declared too, because the production "
                        "image installs this very package as a wheel:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-groups-quote",
                    language="toml",
                    caption="Tooling in the PEP 735 dev group; a real build backend for wheel installs.",
                    source="server/pyproject.toml",
                    snippet=(
                        "# Dev tooling rides in the PEP 735 dev group (the uv convention): `uv sync`\n"
                        "# installs it by default; production image builds pass --no-dev.\n"
                        "[dependency-groups]\n"
                        "dev = [\n"
                        "    \"grpcio-tools>=1.84.0\",\n"
                        "    \"httpx>=0.27\",\n"
                        "    \"mypy>=1.13\",\n"
                        "    # …\n"
                        "    \"testcontainers[postgresql]>=4.15.0\",\n"
                        "]\n"
                        "\n"
                        "# Flat layout (`guide/` at server/ root): hatchling auto-detects the package\n"
                        "# directory from the project name. A real build backend is required because\n"
                        "# the prod image installs the guide package as a static wheel\n"
                        "# (`uv sync --no-editable`).\n"
                        "[build-system]\n"
                        "requires = [\"hatchling\"]\n"
                        "build-backend = \"hatchling.build\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-lock-pitch",
                    text=(
                        "The lockfile is the other half, and its shape "
                        "teaches its guarantees. uv.lock is TOML — one "
                        "[[package]] entry per resolved package, whatever "
                        "pulled it — and this project's own entry is a "
                        "good first read: the guide package itself is "
                        "recorded as an editable local source whose "
                        "dependency list mirrors the manifest, extras "
                        "included:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-lock-guide-quote",
                    language="toml",
                    caption="The lock's record of this project: editable source, every direct name, extras carried.",
                    source="server/uv.lock",
                    snippet=(
                        "[[package]]\n"
                        "name = \"guide\"\n"
                        "version = \"0.1.0\"\n"
                        "source = { editable = \".\" }\n"
                        "dependencies = [\n"
                        "    { name = \"alembic\" },\n"
                        "    { name = \"argon2-cffi\" },\n"
                        "    { name = \"arq\" },\n"
                        "    { name = \"asyncpg\" },\n"
                        "    { name = \"babel\" },\n"
                        "    { name = \"fastapi\" },\n"
                        "    # …\n"
                        "    { name = \"sqlalchemy\", extra = [\"asyncio\"] },\n"
                        "    { name = \"strawberry-graphql\", extra = [\"fastapi\"] },\n"
                        "]\n"
                        "\n"
                        "[package.dev-dependencies]\n"
                        "dev = [\n"
                        "    { name = \"grpcio-tools\" },\n"
                        "    { name = \"httpx\" },\n"
                        "    { name = \"mypy\" },\n"
                        "    # …\n"
                        "    { name = \"testcontainers\" },\n"
                        "]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-lock-why",
                    text=(
                        "What the lock buys is reproducibility with teeth. "
                        "Every other [[package]] entry carries an exact "
                        "version plus sha256-hashed download URLs, so an "
                        "install can verify the artifact it fetches is the "
                        "artifact that was resolved — a supply-chain "
                        "guarantee a bare manifest cannot make. And because "
                        "the resolved set is recorded rather than "
                        "recomputed, 'uv sync --locked' installs precisely "
                        "this set or fails: it never quietly re-resolves "
                        "ranges behind your back, which is what makes "
                        "'which version do we run' a lookup instead of an "
                        "experiment. The trade is honest too — the lock is "
                        "a generated file you commit, reviewable as diffs "
                        "when dependencies move, and every consumer of the "
                        "repo (devcontainer, CI job, image build, the arq "
                        "worker's boot command) syncs from it rather than "
                        "improvising."
                    ),
                ),
            ],
        ),
        # ── 3. uv tree/audit ──────────────────────────────────────────────
        Section(
            id="uv-tree-audit",
            title="uv tree/audit",
            lead="This section carries the topic's demo — the deps manifest.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="deps-tree-pitch",
                    text=(
                        "The resolved dependency set is a GRAPH, not a "
                        "list, and reading it is a skill. 'uv tree' prints "
                        "the manifest's names as roots and indents beneath "
                        "each one the packages it pulled in, recursively — "
                        "the same view 'npm ls' or 'cargo tree' give their "
                        "ecosystems. The single most useful habit it builds "
                        "is checking what a heavyweight direct dependency "
                        "actually drags along. Take the one dependency no "
                        "FastAPI project avoids; the lock's entry for it "
                        "reads:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-tree-fastapi-quote",
                    language="toml",
                    caption="fastapi's locked entry: one pin, six transitive edges nobody declared.",
                    source="server/uv.lock",
                    snippet=(
                        "[[package]]\n"
                        "name = \"fastapi\"\n"
                        "version = \"0.143.1\"\n"
                        "source = { registry = \"https://pypi.org/simple\" }\n"
                        "dependencies = [\n"
                        "    { name = \"annotated-doc\" },\n"
                        "    { name = \"opentelemetry-api\" },\n"
                        "    { name = \"pydantic\" },\n"
                        "    { name = \"starlette\" },\n"
                        "    { name = \"typing-extensions\" },\n"
                        "    { name = \"typing-inspection\" },\n"
                        "]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-tree-reading",
                    text=(
                        "The manifest says only 'fastapi>=0.115'; the lock "
                        "says that resolved to 0.143.1 AND that this one "
                        "edge attaches six more packages — starlette (the "
                        "ASGI toolkit FastAPI is built on), pydantic, "
                        "typing-extensions, and three smaller ones. None of "
                        "those names appear in pyproject.toml, yet every "
                        "one runs in production and appears in audits. "
                        "That asymmetry is why the audit story starts from "
                        "the lock, never the manifest: 'uv tree' walks it, "
                        "'uv lock --check' proves it still matches the "
                        "manifest, and the metadata the lock keeps is "
                        "enough to cross-check every pin against its "
                        "declared range — the lock even remembers the "
                        "specifiers that produced it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-tree-metadata-quote",
                    language="toml",
                    caption="The lock remembers the manifest's ranges — pins and constraints in one file.",
                    source="server/uv.lock",
                    snippet=(
                        "[package.metadata]\n"
                        "requires-dist = [\n"
                        "    { name = \"alembic\", specifier = \">=1.20.0\" },\n"
                        "    { name = \"argon2-cffi\", specifier = \">=25.1.0\" },\n"
                        "    # …\n"
                        "    { name = \"fastapi\", specifier = \">=0.115\" },\n"
                        "    { name = \"grpcio\", specifier = \">=1.84.0\" },\n"
                        "    # …\n"
                        "    { name = \"sqlalchemy\", extras = [\"asyncio\"], specifier = \">=2.1.4\" },\n"
                        "    { name = \"strawberry-graphql\", extras = [\"fastapi\"], specifier = \">=0.335.0\" },\n"
                        "    # …\n"
                        "]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-demo-pitch",
                    text=(
                        "This topic's demo makes that reading permanent: a "
                        "live panel over the REAL manifest and lock, parsed "
                        "at request time. Both files live inside server/, "
                        "so the running server container carries them and "
                        "the demo simply reads them — the same "
                        "introspect-the-real-thing posture as the "
                        "environments topic's config inspector. The range "
                        "check inside the builder states its own honesty "
                        "rule: it judges only the single-clause operators "
                        "it understands, and says 'not judged' for "
                        "everything else rather than guessing:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-demo-satisfies-quote",
                    language="py",
                    caption="The panel's range check: >= and == judged, compound clauses honestly not.",
                    source="server/guide/domain/demos/dep_manifest.py",
                    snippet=(
                        "def _satisfies(locked_version: str, constraint: str) -> bool | None:\n"
                        "    \"\"\"Honest single-clause range check; None when the operator is not judged.\n"
                        "\n"
                        "    Only ``>=`` and ``==``/``===`` are judged, and only over plain dotted\n"
                        "    numeric versions — a pre-release suffix or a compound clause returns\n"
                        "    ``None`` so the row can say \"not judged\" instead of guessing.\n"
                        "    \"\"\"\n"
                        "    spec = constraint.strip()\n"
                        "    if \",\" in spec or not spec:\n"
                        "        return None\n"
                        "    for operator in (\">=\", \"==\", \"===\"):\n"
                        "        if spec.startswith(operator):\n"
                        "            locked = _version_tuple(locked_version)\n"
                        "            wanted = _version_tuple(spec[len(operator) :])\n"
                        "            if locked is None or wanted is None:\n"
                        "                return None\n"
                        "            return locked >= wanted if operator == \">=\" else locked == wanted\n"
                        "    return None"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="deps:manifest",
                    title="The deps manifest",
                    description=(
                        "GET /api/demo/deps serves a live panel over the "
                        "REAL server/pyproject.toml + server/uv.lock, "
                        "parsed at request time — relock the project and "
                        "the panel changes with it. The groups block shows "
                        "runtime (main) versus dev with their declared "
                        "counts; the direct table carries every one of the "
                        "26 declared names with its manifest range beside "
                        "the lock's exact pin, an honest "
                        "satisfied/not-judged verdict, and any extras; the "
                        "agreement row cross-checks manifest names against "
                        "the lock's record of what this project depends on "
                        "— the uv lock --check spirit, computed; and the "
                        "tree slice roots at fastapi to show its locked "
                        "pin and the six packages it pulls in that nobody "
                        "wrote down. Whole-lock counts close the picture: "
                        "total, direct, transitive. Anything unreadable "
                        "degrades to an honest unavailable panel with the "
                        "reason — never a failure."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-demo-reading",
                    text=(
                        "Reading the panel against the running stack is "
                        "the point: the fastapi row answers '>=0.115 "
                        "resolved to 0.143.1, satisfied', the "
                        "sqlalchemy row shows the asyncio extra riding "
                        "along, and the counts row makes the "
                        "direct-versus-transitive ratio concrete — 26 "
                        "names written down, 75 packages installed. The "
                        "endpoint behind it is as thin as every other "
                        "router in the stack: one GET, a pure payload "
                        "builder, a declared response model:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-demo-router-quote",
                    language="py",
                    caption="The whole demo endpoint: one GET, pure payload, declared response model.",
                    source="server/guide/presentation/routers/demo/deps.py",
                    snippet=(
                        "@router.get(PANEL_PATH, response_model=DepsManifestPanel)\n"
                        "async def read_dep_manifest() -> DepsManifestPanel:\n"
                        "    \"\"\"Serve the live manifest panel: groups, pins vs ranges, drift, tree.\"\"\"\n"
                        "    return build_dep_manifest_payload()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-audit-coda",
                    text=(
                        "The audit habit the panel seeds generalizes. When "
                        "an advisory names a package, the questions are "
                        "'is it in the lock' (direct or transitive), "
                        "'which exact version', and 'who pulled it' — and "
                        "the lock answers all three without a network. "
                        "The endpoint test pins exactly those answers "
                        "against the real files, so the panel cannot drift "
                        "from the lock it claims to read:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-audit-test-quote",
                    language="py",
                    caption="The endpoint test pins the real lock facts the panel serves.",
                    source="server/tests/demo/test_deps_manifest_endpoint.py",
                    snippet=(
                        "    fastapi_row = row_by_name(body, \"fastapi\")\n"
                        "    assert fastapi_row[\"constraint\"] == \">=0.115\"\n"
                        "    assert fastapi_row[\"group\"] == \"main\"\n"
                        "    assert fastapi_row[\"satisfies\"] is True\n"
                        "    assert fastapi_row[\"lockedVersion\"] == \"0.143.1\""
                    ),
                ),
            ],
        ),
        # ── 4. Upgrades ───────────────────────────────────────────────────
        Section(
            id="upgrades",
            title="Upgrades",
            blocks=[
                TextBlock(
                    kind="text",
                    id="deps-upgrades-pitch",
                    text=(
                        "Ranges move; that is what they are for. The "
                        "upgrade loop this repo runs is deliberately boring "
                        "and always the same shape, because the lock makes "
                        "'what changed' reviewable. Adding a dependency is "
                        "'uv add <name>': it writes the manifest entry with "
                        "a floor, resolves, and updates the lock in one "
                        "step — that is how every one of the six "
                        "dependency bundles this guide landed (strawberry "
                        "for GraphQL, grpcio and protobuf for the gRPC "
                        "topic, the alembic/sqlalchemy/asyncpg trio, "
                        "motor, redis) entered the project. Bumping inside "
                        "a range is 'uv lock --upgrade-package <name>' "
                        "(or bare --upgrade to move everything resolvable); "
                        "narrowing a range is a manifest edit followed by "
                        "'uv lock'. In every case the OUTPUT is a lockfile "
                        "diff — version lines that moved — reviewed like "
                        "code, because they are."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-upgrades-loop-framing",
                    text=(
                        "The loop, as an ordered sequence — each step "
                        "exists because skipping it has a named failure:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="deps-upgrades-loop",
                    ordered=True,
                    items=[
                        "Change the intent — uv add for a new name, uv lock "
                        "--upgrade-package for a bump, a manifest edit for "
                        "a new range.",
                        "Re-resolve — uv lock rewrites uv.lock; review the "
                        "diff, including the transitive edges that moved.",
                        "Install exactly — uv sync --locked materializes "
                        "the new lock or fails loudly; it never re-resolves.",
                        "Prove — run the suite in the container; a bump "
                        "that changes behavior shows up here or not at all.",
                        "Commit both files — manifest and lock land in the "
                        "same commit, so no checkout ever holds half a "
                        "dependency world.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="deps-upgrades-running-containers",
                    text=(
                        "One lesson this repo learned live and now carries "
                        "as a rule: the lock governs INSTALLS, and a "
                        "long-running container does not reinstall itself. "
                        "After 'uv add' lands a new dependency, the dev "
                        "server that has been up for days still has the "
                        "old venv — uvicorn --reload will re-import your "
                        "code but cannot import a package that was never "
                        "installed, and the process dies on the missing "
                        "import. The fix is a one-time 'uv sync --locked' "
                        "inside the running container's own venv, after "
                        "which --reload works again. The arq worker "
                        "service never had this problem, and the reason is "
                        "in its command — it syncs from the lock on every "
                        "boot, cheap precisely because an in-sync install "
                        "is a no-op:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-upgrades-worker-quote",
                    language="yaml",
                    caption="Boot-time sync from the lock: an in-sync --locked is a no-op, an out-of-sync one heals.",
                    source=".docker/docker-compose.yml",
                    snippet=(
                        "  arq-worker:\n"
                        "    image: fdg_server_dev\n"
                        "    container_name: fastapi_developers_guide_arq_worker_dev\n"
                        "    restart: unless-stopped\n"
                        "    working_dir: /app\n"
                        "    command: sh -c \"uv sync --locked && .venv/bin/arq guide.worker.WorkerSettings\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-upgrades-cadence",
                    text=(
                        "Cadence matters as much as mechanics. Upgrades "
                        "land best in small, boring, frequent commits — "
                        "one package or one cluster at a time, each "
                        "behind the suite — because a dependency set "
                        "that goes a year without moving turns every "
                        "future upgrade into a migration, and "
                        "migrations get deferred until a security "
                        "advisory makes them urgent at the worst "
                        "possible time. The advisory-driven bump is the "
                        "loop's special case: the lock answers 'which "
                        "version and who pulled it' in seconds, 'uv lock "
                        "--upgrade-package <name>' moves exactly the "
                        "affected edge set, and the suite either proves "
                        "the bump safe or names what broke. This "
                        "repository's verify one-liner exists so that "
                        "proof costs one command — dependency changes "
                        "and their evidence belong to the same commit, "
                        "which is the whole reason the surface stays "
                        "trustworthy."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-upgrades-drift",
                    text=(
                        "Drift is the failure mode the loop exists to "
                        "prevent: a manifest edited without relocking, or "
                        "a lock patched by hand, leaves the two files "
                        "disagreeing about the world. 'uv lock --check' "
                        "answers the question in CI terms — exit zero "
                        "when the lock is exactly what the manifest "
                        "resolves to, non-zero when it is stale — and "
                        "this repo's CI jobs sync with --locked, which "
                        "fails on drift by construction. The demo panel "
                        "computes the same cross-check live (its "
                        "agreement row), because a drift you can SEE on a "
                        "panel is a drift you fix before it becomes a "
                        "reproduces-on-my-machine afternoon."
                    ),
                ),
            ],
        ),
        # ── 5. Docker layer caching (uv sync) ─────────────────────────────
        Section(
            id="docker-layer-caching",
            title="Docker layer caching (uv sync)",
            blocks=[
                TextBlock(
                    kind="text",
                    id="deps-docker-pitch",
                    text=(
                        "Docker images build as a stack of layers, and a "
                        "layer is reused verbatim unless its inputs "
                        "changed — including every layer above it. That "
                        "rule turns COPY order into build performance: "
                        "copy the files that change LEAST first, do the "
                        "expensive work against them, and copy the "
                        "churning source afterwards. In a Python project "
                        "the slow step is dependency installation and the "
                        "stable inputs are exactly the two manifests — so "
                        "both server Dockerfiles copy pyproject.toml and "
                        "uv.lock alone, run a first uv sync, and only then "
                        "copy the source. The dev server image reads:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-docker-dev-quote",
                    language="dockerfile",
                    caption="The two-step sync: a dependency layer that survives source edits.",
                    source=".docker/server/Dockerfile",
                    snippet=(
                        "# Manifests first to leverage Docker layer caching (deps change least).\n"
                        "# --no-install-project: the guide source is not here yet; installing the\n"
                        "# project in this layer would fail (nothing to build from).\n"
                        "COPY server/pyproject.toml server/uv.lock ./\n"
                        "RUN uv sync --locked --no-install-project\n"
                        "\n"
                        "COPY server/ ./\n"
                        "# Second sync adds the guide package itself — editable, so the venv points at\n"
                        "# /app and compose's bind-mounted live source is what runs under --reload.\n"
                        "RUN uv sync --locked"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-docker-two-steps",
                    text=(
                        "The two steps exist because installing this "
                        "project's own package requires the project's "
                        "source, which the caching order deliberately "
                        "withholds from the expensive layer. The FIRST "
                        "sync installs only the locked third-party set "
                        "(--no-install-project: there is nothing to build "
                        "yet) — that layer rebuilds only when the lock "
                        "changes, which is the point. The SECOND sync, "
                        "after the source copy, adds the guide package "
                        "itself as an editable install, a cheap operation "
                        "over an already-populated venv. Day to day you "
                        "edit source, the image rebuilds the copy layer "
                        "and the second sync, and the dependency layer "
                        "below is served from cache in milliseconds; "
                        "add one dependency and only then does the "
                        "expensive layer rebuild, once, correctly."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-docker-prod-pitch",
                    text=(
                        "The production image runs the same trick with "
                        "production's stricter flags — the dev group "
                        "stays out entirely, and the project installs as "
                        "a built wheel rather than editable source, so "
                        "the package runs from the venv with no source "
                        "tree on disk:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-docker-prod-quote",
                    language="dockerfile",
                    caption="Same caching shape, prod discipline: --no-dev excludes tooling, --no-editable installs the wheel.",
                    source=".docker/server/Dockerfile.prod",
                    snippet=(
                        "# Manifests first: the dependency layer caches while only source churns.\n"
                        "# --no-install-project skips building the guide package itself here.\n"
                        "COPY server/pyproject.toml server/uv.lock ./\n"
                        "RUN uv sync --locked --no-dev --no-install-project\n"
                        "\n"
                        "COPY server/ ./\n"
                        "# Second sync installs the guide package into the venv as a static (built)\n"
                        "# copy — the final image runs the package from the venv alone (the one\n"
                        "# source it still carries is the migration tree; see the runtime stage).\n"
                        "RUN uv sync --locked --no-dev --no-editable"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-docker-coda",
                    text=(
                        "Note what the flags compose into: --locked keeps "
                        "the image honest to the committed lock (a "
                        "half-committed dependency change fails the "
                        "BUILD, not production), --no-dev keeps pytest "
                        "and its friends out of the runtime surface that "
                        "audits scan, and --no-editable gives the "
                        "multi-stage copy a self-contained venv. The "
                        "dependency-groups discipline from the second "
                        "section and the caching discipline of this one "
                        "are the same decision seen from two sides — what "
                        "you declare separately, you can install "
                        "separately, and what installs separately, caches "
                        "separately."
                    ),
                ),
            ],
        ),
        # ── 6. Choosing ───────────────────────────────────────────────────
        Section(
            id="choosing",
            title="Choosing",
            blocks=[
                TextBlock(
                    kind="text",
                    id="deps-choosing-pitch",
                    text=(
                        "Every entry in the manifest was a choice, and the "
                        "choosing is the part no tool does for you. This "
                        "repo's own history is the best textbook, because "
                        "each dependency arrived with a topic that needed "
                        "REAL machinery, not a mock: strawberry-graphql "
                        "because the GraphQL topic teaches schema-first "
                        "resolvers against a live endpoint; grpcio plus "
                        "protobuf because streaming RPC cannot be faked "
                        "honestly (and grpcio-tools stayed in the DEV "
                        "group — the code generator is not needed at "
                        "runtime); argon2-cffi, pyjwt, and itsdangerous "
                        "as the authentication trio; arq because the jobs "
                        "topic needed a real worker queue and it reuses "
                        "the Redis the stack already runs; alembic, "
                        "sqlalchemy, and asyncpg as the migration/ORM/"
                        "driver chain; motor and redis as async clients "
                        "for the optional stores; pillow and babel for "
                        "image processing and message formatting; "
                        "testcontainers in dev only, for real-database "
                        "tests."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-choosing-checklist-framing",
                    text=(
                        "The judgment behind those choices compresses into "
                        "a checklist you can actually apply to the next "
                        "candidate package:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="deps-choosing-checklist",
                    ordered=False,
                    items=[
                        "Maintenance signal — recent releases, issues that "
                        "get answers, a changelog; abandoned dependencies "
                        "become your code eventually.",
                        "Transitive weight — run uv tree mentally: one "
                        "name became six packages for fastapi; the ratio "
                        "must be worth the feature.",
                        "Typing — py.typed packages keep mypy strict "
                        "working for you; untyped ones poke holes in the "
                        "very discipline this repo runs on.",
                        "Fit before reach — prefer the small library that "
                        "does the one thing (itsdangerous for signed "
                        "sessions) over the platform that does everything.",
                        "Escape hatch — how hard is removal later; a "
                        "dependency wrapped behind one of your ports "
                        "(the repo's Protocols) is far cheaper to swap.",
                        "Runtime surface — does it belong in main or dev; "
                        "tooling that never ships must not ship.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="deps-choosing-build-vs-integrate",
                    text=(
                        "The deepest question is build-versus-integrate: "
                        "the third-party topics of this guide return to "
                        "it, and the rule of thumb is honest about both "
                        "directions. Integrating buys someone else's "
                        "accumulated bug fixes and costs a dependency's "
                        "worth of trust, upgrade attention, and audit "
                        "surface; building buys exact fit and costs the "
                        "entire maintenance tail, forever. This repo "
                        "integrated where the problem is commoditized and "
                        "the failure modes are well trodden — HTTP "
                        "frameworks, ORMs, drivers, password hashing — "
                        "and built where the code IS the lesson or the "
                        "shape is tiny (the HMAC signer, the UUIDv7 "
                        "generator, the scenario store). A dependency "
                        "list curated that way stays short enough to "
                        "hold in your head, which is the real ceiling on "
                        "surface size: 26 names you can name beat 60 you "
                        "scroll past."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-choosing-coda",
                    text=(
                        "Choosing is also where the discipline pays you "
                        "back. Because every dependency is locked, "
                        "hashed, grouped, and cached behind the flags "
                        "this topic walked through, the cost of a WRONG "
                        "choice is bounded: the lock tells you exactly "
                        "what it dragged in, the diff shows what moving "
                        "it moves, the dev-group split tells you whether "
                        "it even ships, and a port-wrapped integration "
                        "gives the swap a seam. Dependency management "
                        "cannot make choices good — it makes them "
                        "reversible, visible, and cheap to review, which "
                        "is everything engineering can ask of a decision "
                        "made under uncertainty."
                    ),
                ),
            ],
        ),
        # ── 7. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The dependency surface from a shell: the panel, the tree, the drift check.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="deps-terminal-intro",
                    text=(
                        "Five stops: the live panel parsed from the real "
                        "files, the direct-versus-transitive slice it "
                        "computes, the same graph through uv tree itself, "
                        "the lock-freshness check CI relies on, and this "
                        "topic's own content detail through both ports. "
                        "The stack is up; every command reads the real "
                        "machinery."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-terminal-panel",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the live panel: groups, agreement, counts, parsed at request time\n"
                        "curl -s localhost:8000/api/demo/deps \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"available:\", b[\"available\"], \"| requires-python:\", b[\"requiresPython\"]); \\\n"
                        "[print(\" \", g[\"group\"], \"-\", g[\"directCount\"], \"direct:\", g[\"note\"]) for g in b[\"groups\"]]; \\\n"
                        "print(\"agreement:\", b[\"agreement\"][\"agree\"], \"| counts:\", b[\"counts\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-terminal-slice",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the direct-vs-transitive slice: fastapi's pin and the six edges\n"
                        "curl -s localhost:8000/api/demo/deps \\\n"
                        "  | python3 -c 'import json,sys; s=json.load(sys.stdin)[\"slice\"]; \\\n"
                        "print(s[\"root\"], s[\"rootConstraint\"], \"->\", s[\"rootLockedVersion\"]); \\\n"
                        "[print(\"  \", c[\"name\"], c[\"lockedVersion\"]) for c in s[\"children\"]]; \\\n"
                        "print(s[\"note\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-terminal-tree",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the same graph, from the tool that owns it (one level deep)\n"
                        "docker exec fastapi_developers_guide_dev bash -lc \\\n"
                        "  'cd /workspaces/fastapi_developers_guide/server && uv tree --depth 1 | head -30'\n"
                        "# every indented name under a root is a package you run but never declared"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-terminal-check",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — lock freshness, the CI question: exit 0 means the lock IS the manifest\n"
                        "docker exec fastapi_developers_guide_dev bash -lc \\\n"
                        "  'cd /workspaces/fastapi_developers_guide/server && uv lock --check && echo LOCK-CURRENT'\n"
                        "# and the install side of the same honesty: --locked refuses a stale lock\n"
                        "docker exec fastapi_developers_guide_dev bash -lc \\\n"
                        "  'cd /workspaces/fastapi_developers_guide/server && uv sync --locked'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deps-terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — this topic's own detail: demo inline in uv-tree-audit, companion last\n"
                        "curl -s localhost:8000/api/content/dependency-management | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "print(\"sections:\", len(t[\"sections\"]))\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'\n"
                        "# and through the client's dev proxy, the way the browser reaches it:\n"
                        "curl -s localhost:5174/api/content/dependency-management | python3 -c 'import json,sys; print(\"proxy sections:\", len(json.load(sys.stdin)[\"sections\"]))'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deps-terminal-coda",
                    text=(
                        "Stops 1–2 read the surface through this topic's "
                        "own panel; stop 3 reads the same graph through "
                        "uv itself, which is the habit that outlives the "
                        "guide; stop 4 runs the freshness gate that keeps "
                        "manifest and lock honest in CI; stop 5 closes "
                        "the loop the guide always closes — the topic "
                        "that taught the dependency surface is itself "
                        "served from an image whose layers, groups, and "
                        "pins are that surface, put to work."
                    ),
                ),
            ],
        ),
    ],
)
