"""Topic 36 — Environments: one codebase, many worlds, real config.

The repo already IS the lesson: a pydantic-settings ``AppConfig`` that has
carried every real knob since Phase 1 (with the two signing secrets and
their dev-defaults comment from topic 23), dev+prod compose stacks that
differ by VALUES and rails rather than code, a devcontainer that boots the
whole world, and a ScenarioStore that is the repo's genuine runtime
feature-flag mechanism. This topic teaches all of it in place — twelve
factor graded honestly against the repo's actual compliance AND its named
divergences, secrets taught as a ladder (dev defaults, compose injection,
required-variable rails, server-side redaction), and flags distinguished
from config. The demo is a live inspector over the REAL AppConfig: every
setting with its type, effective value, and honestly-introspected source —
env or default, derived from the same EnvSettingsSource pydantic-settings
consults — with secret-bearing fields redacted SERVER-SIDE before the
payload exists, and the scenario store's live flag snapshot beside it.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="environments",
    title="Environments",
    subtitle=(
        "One codebase promoted through many environments: what varies and "
        "what must not, twelve factor graded against this repo's real "
        "compliance and its honest divergences, pydantic-settings as typed "
        "config with honest source attribution, environment-specific "
        "behavior as values rather than branches, secrets beyond the .env "
        "file (dev defaults, compose rails, server-side redaction), and "
        "feature flags as the runtime switch the ScenarioStore really is — "
        "with a live inspector over the process's actual configuration."
    ),
    group="platform",
    order=36,
    sections=[
        # ── 1. One codebase, many environments ────────────────────────────
        Section(
            id="one-codebase-many-environments",
            title="One codebase, many environments",
            blocks=[
                TextBlock(
                    kind="text",
                    id="env-codebase-pitch",
                    text=(
                        "An environment is the total surroundings a process "
                        "runs in: which databases it can reach, which "
                        "credentials it holds, how loudly it logs, which "
                        "features are switched on. A codebase that is "
                        "developed, demonstrated, and shipped has at least "
                        "three — the devcontainer world, the dev compose "
                        "stack, and the prod compose stack — and the only "
                        "sane way to keep them from forking is brutally "
                        "simple: ONE artifact, promoted unchanged, with "
                        "everything that differs living OUTSIDE the code "
                        "as values the process reads at boot. This repo "
                        "takes that rule literally: the same server image "
                        "runs in dev and prod, the same source runs under "
                        "uvicorn and as the arq worker, and the entire "
                        "difference between stacks is a handful of "
                        "environment variables you can diff in one screen."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="env-varies-framing",
                    text=(
                        "So the first question to ask of any environment "
                        "story is an inventory: what actually varies here? "
                        "This repo's complete list, each item small enough "
                        "to name precisely:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="env-varies-list",
                    ordered=False,
                    items=[
                        "Backing-service URLs — where PostgreSQL, Redis, "
                        "and MongoDB live: localhost for host runs, "
                        "service names inside compose, the FDG_*_URL trio.",
                        "Credentials and secrets — dev-grade defaults in "
                        "dev, deployer-supplied values in prod (the "
                        "required-variable rails).",
                        "Runtime flags — the scenario store's dataMode and "
                        "injectFailure, switched at runtime without a "
                        "restart (the feature-flags section).",
                        "Log verbosity — the log level the logging "
                        "configuration starts with, read from the config.",
                        "The environment label — FDG_ENV, a name for "
                        "humans and telemetry, deliberately not a branch "
                        "condition anywhere in the code.",
                        "Exposure — dev publishes the data-service ports "
                        "to the host for psql and friends; prod keeps "
                        "them internal to the compose network.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="env-compose-pitch",
                    text=(
                        "The dev stack's server service is the canonical "
                        "example, and it is worth reading as a whole: four "
                        "environment variables, and every one of them a "
                        "POINTER rather than a behavior. The comment says "
                        "the quiet part out loud — the config's defaults "
                        "point at localhost so a host-run server works "
                        "with zero setup, and inside compose the same "
                        "fields point at service names because that is "
                        "how the compose network addresses sibling "
                        "containers:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="env-dev-compose-quote",
                    language="yaml",
                    caption="The dev server's entire environment: four pointers, no behavior.",
                    source=".docker/docker-compose.yml",
                    snippet=(
                        "    environment:\n"
                        "      # FDG_ env rails (pydantic-settings reads these; defaults point at\n"
                        "      # localhost for host runs). Inside compose the data services are\n"
                        "      # reachable by service name, not localhost.\n"
                        "      - FDG_ENV=dev\n"
                        "      - FDG_DATABASE_URL=postgresql+asyncpg://postgres:guide@postgres:5432/guide\n"
                        "      - FDG_REDIS_URL=redis://redis:6379\n"
                        "      - FDG_MONGO_URL=mongodb://mongo:27017"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="env-codebase-promotion",
                    text=(
                        "Promotion between those environments is "
                        "correspondingly boring, which is the "
                        "compliment it deserves: nothing is rebuilt and "
                        "nothing is hand-edited on the way up — the "
                        "prod stack runs the same images with a "
                        "different compose file, and the pre-flight is "
                        "one command, 'docker compose -f "
                        ".docker/docker-compose.prod.yml config', which "
                        "renders the stack without starting it. That "
                        "dry-run is not ceremonial: it is exactly where "
                        "the required-variable rail from the "
                        "env-specific-behavior section fires, so a "
                        "stack that cannot render correctly never gets "
                        "the chance to half-boot. An environment story "
                        "you can verify with a config command is one "
                        "you can hand to somebody else without a "
                        "runbook."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="env-codebase-coda",
                    text=(
                        "The discipline this block embodies: differences "
                        "between environments live in FILES YOU CAN DIFF, "
                        "not in code you can branch on. A reviewer can "
                        "open the dev and prod compose files side by side "
                        "and see every environmental difference in one "
                        "read; nobody has to grep the source for "
                        "environment-conditional logic, because there is "
                        "none to find. When a new developer arrives, the "
                        "onboarding is one compose up — the code, the "
                        "defaults, and the rails already agree on the "
                        "shape of the world. That agreement is what the "
                        "rest of this topic unpacks, factor by factor."
                    ),
                ),
            ],
        ),
        # ── 2. Twelve factor ──────────────────────────────────────────────
        Section(
            id="twelve-factor",
            title="Twelve factor",
            blocks=[
                TextBlock(
                    kind="text",
                    id="twelve-factor-pitch",
                    text=(
                        "Twelve-factor app methodology (Heroku, 2011) is a "
                        "checklist for building software-as-a-service that "
                        "deploys cleanly: config in the environment, "
                        "backing services as swappable resources, "
                        "processes that boot and die on demand, logs to "
                        "stdout. It is old enough that half its advice now "
                        "reads as obvious, and it remains the best "
                        "framework for AUDITING an environment story — "
                        "not as a religion, but as a graded checklist. "
                        "The honest way to teach it here is to grade this "
                        "repository against the factors it actually "
                        "exercises, compliant where it complies and "
                        "explicit where it diverges, because a divergence "
                        "you can name is a decision, while one you cannot "
                        "is a bug."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="twelve-factor-scorecard-framing",
                    text=(
                        "The scorecard — six factors this repo genuinely "
                        "exercises, each with its honest verdict:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="twelve-factor-scorecard",
                    ordered=False,
                    items=[
                        "Config — store config in the environment: "
                        "compliant; every knob is an FDG_-prefixed "
                        "variable read by pydantic-settings, never a "
                        "code-conditional (one named divergence: dev "
                        "default secrets, taught in the secrets section).",
                        "Backing services — treat data stores as attached "
                        "resources addressed by URL: compliant; the "
                        "FDG_*_URL trio swaps localhost for service names "
                        "with zero code change.",
                        "Dev/prod parity — keep stages as similar as "
                        "possible: mostly compliant; the SAME images run "
                        "in both stacks, diverging only in env values, "
                        "published ports, and the secrets rails.",
                        "Processes — execute as stateless, share-nothing "
                        "processes: honestly partial; request handling is "
                        "stateless, but demo state (scenario store, "
                        "in-memory stores) is process-local BY DESIGN and "
                        "says so on its panels.",
                        "Logs — treat logs as event streams to stdout: "
                        "compliant; structured JSON via structlog, no log "
                        "files anywhere (the observability topic).",
                        "Admin processes — run one-off or auxiliary "
                        "processes in the same codebase: compliant; the "
                        "arq worker is the same image, the same config "
                        "rails, a different command.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="twelve-factor-worker-pitch",
                    text=(
                        "That last factor is the easiest to overlook and "
                        "the cheapest to show, because the repo's worker "
                        "service is five lines of compose that say the "
                        "whole thing: the SAME fdg_server_dev image the "
                        "API server runs, the same working directory, "
                        "only the command exchanged for the arq worker "
                        "loop — and it inherits the identical FDG_* "
                        "environment rails, so the worker and the API "
                        "literally cannot disagree about where Redis is:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="twelve-factor-worker-quote",
                    language="yaml",
                    caption="Admin processes, twelve-factor style: same image, same rails, different command.",
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
                    id="twelve-factor-worker-reading",
                    text=(
                        "Read the block as the pattern it is: because the "
                        "worker rides the same image, every dependency "
                        "pin, every migration, every ratchet-verified "
                        "quote applies to it automatically, and a new "
                        "task added to guide.worker is available to both "
                        "halves of the jobs story with no separate build "
                        "to forget. This is what the factor actually "
                        "buys — not purity, but the elimination of an "
                        "entire class of drift between the API process "
                        "and its auxiliary processes."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="twelve-factor-release-divergence",
                    text=(
                        "One more divergence belongs on the record: "
                        "the build/release/run separation. The repo "
                        "builds clean artifacts (the multi-stage images "
                        "the deployment topic teaches) and runs them "
                        "under compose, but it has no distinct RELEASE "
                        "stage — no tagged, promotion-tracked artifact "
                        "moving stage to stage, the way a hosted "
                        "pipeline would stamp one. For a local-first "
                        "reference repo that is the honest size; for a "
                        "team, that stage is where the environment "
                        "story gets auditable, because the release id "
                        "is what answers 'which exact artifact is prod "
                        "running'. Naming the gap now is cheaper than "
                        "discovering it during an incident."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="twelve-factor-divergences",
                    text=(
                        "The divergences deserve their own paragraph, "
                        "because a checklist applied dishonestly is worse "
                        "than none. This repo's statelessProcesses entry "
                        "is partial ON PURPOSE: the scenario store and "
                        "the in-memory demo stores are process-local so "
                        "every test and every app instance gets isolated "
                        "state, and the panels that depend on that say "
                        "so in plain words. The dev-default secrets "
                        "divergence is deliberate too, documented in the "
                        "config's own comment, and the prod rails close "
                        "it — the next section shows how. Twelve-factor "
                        "conformance, like the testing pyramid, is a "
                        "BUDGET statement: know the score, spend the "
                        "divergences consciously, and write each one "
                        "down where the next reader will trip over it."
                    ),
                ),
            ],
        ),
        # ── 3. pydantic-settings ─────────────────────────────────────────
        Section(
            id="pydantic-settings",
            title="pydantic-settings",
            lead="This section carries the topic's demo — the env inspector.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="pydantic-settings-pitch",
                    text=(
                        "Environment variables arrive as untyped strings, "
                        "and an app that reads them with os.environ.get "
                        "inherits every parsing mistake at the worst "
                        "possible moment — boot time in production. "
                        "pydantic-settings fixes the boundary the same "
                        "way pydantic fixes every other boundary in this "
                        "stack: declare a model, let the typed fields "
                        "validate and coerce, fail loudly at construction. "
                        "The repo's AppConfig has carried every real knob "
                        "since Phase 1, and it fits in one screen: a "
                        "prefix, a frozen flag, and eight fields whose "
                        "names double as their environment variable "
                        "names. Note the two signing secrets at the "
                        "bottom — their comment is an honesty contract "
                        "the secrets section keeps:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pydantic-settings-config-quote",
                    language="py",
                    caption="The whole configuration surface: typed, prefix-ruled, frozen, dev-bootable.",
                    source="server/guide/core/config.py",
                    snippet=(
                        "class AppConfig(BaseSettings):\n"
                        "    \"\"\"Process-wide settings; each field name doubles as its env var name.\"\"\"\n"
                        "\n"
                        "    model_config = SettingsConfigDict(env_prefix=\"FDG_\", frozen=True)\n"
                        "\n"
                        "    env: str = \"dev\"\n"
                        "    debug: bool = False\n"
                        "    database_url: str = \"postgresql+asyncpg://postgres:guide@localhost:5432/guide\"\n"
                        "    redis_url: str = \"redis://localhost:6379\"\n"
                        "    mongo_url: str = \"mongodb://localhost:27017\"\n"
                        "    log_level: str = \"info\"\n"
                        "    # The two signing secrets (topic 23): dev-only defaults let the stack boot\n"
                        "    # anywhere with zero setup, and NOTHING behind them is secret in dev — but\n"
                        "    # production MUST override both via FDG_JWT_SECRET / FDG_SESSION_SECRET\n"
                        "    # (distinct, high-entropy values); the validator below makes a default\n"
                        "    # secret in a non-dev env a startup failure instead of a quiet liability.\n"
                        "    jwt_secret: str = \"dev-only-jwt-secret-override-me-32+chars\"\n"
                        "    session_secret: str = \"dev-only-session-secret-override-me-32+chars\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pydantic-settings-reading",
                    text=(
                        "Read the model as four decisions. The prefix: "
                        "every variable becomes FDG_ plus the uppercased "
                        "field name, so the process's configuration "
                        "footprint is greppable and cannot collide with "
                        "some library's unprefixed expectation. The "
                        "types: FDG_DEBUG is parsed as a real boolean, "
                        "and a value that will not coerce fails at "
                        "construction — configuration errors surface at "
                        "boot, not mid-request. The defaults: every "
                        "field declares one, so the app boots ANYWHERE "
                        "with zero secrets, which is exactly what lets "
                        "the dev stack, the test suite, and a plane-ride "
                        "laptop all run the same code. The frozen flag: "
                        "settings are read-only after startup, so no "
                        "request handler can quietly mutate the world "
                        "the rest of the process sees."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pydantic-settings-cache-pitch",
                    text=(
                        "Construction happens exactly once per process, "
                        "and the caching is part of the design rather "
                        "than an optimization bolted on later — one "
                        "line of functools, one instance, one truth:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pydantic-settings-get-config-quote",
                    language="py",
                    caption="One config instance per process; tests clear the cache around app builds.",
                    source="server/guide/core/config.py",
                    snippet=(
                        "@lru_cache(maxsize=1)\n"
                        "def get_config() -> AppConfig:\n"
                        "    \"\"\"Return the process-wide config instance (one per process).\"\"\"\n"
                        "    return AppConfig()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pydantic-settings-precedence",
                    text=(
                        "When several sources could provide a field, "
                        "pydantic-settings resolves in a fixed order — "
                        "init kwargs, then environment variables, then "
                        ".env files, then a secrets directory, then the "
                        "declared default. This repo deliberately uses "
                        "only two of those: the environment (compose sets "
                        "FDG_* values per stack) and the defaults "
                        "(everything compose does not set). There is no "
                        ".env file anywhere in the repo — on purpose, as "
                        "the secrets section argues — which keeps the "
                        "question every operator asks, WHERE did this "
                        "value come from, answerable with real "
                        "introspection: ask the same EnvSettingsSource "
                        "pydantic-settings consults which fields the "
                        "environment provides, and everything else fell "
                        "back to default. That is precisely how the "
                        "demo below attributes every row — and how it "
                        "redacts every secret-bearing field before the "
                        "payload exists:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pydantic-settings-redaction-quote",
                    language="py",
                    caption="The inspector's two honesty rules in one branch: redact secrets, attribute sources for real.",
                    source="server/guide/domain/demos/env_inspector.py",
                    snippet=(
                        "        if secret:\n"
                        "            value = REDACTED_VALUE\n"
                        "            shape_hint = f\"{len(raw)} chars, hidden\"\n"
                        "        else:\n"
                        "            value = str(raw)\n"
                        "            shape_hint = None\n"
                        "        source: Literal[\"env\", \"default\"] = \"env\" if name in provided else \"default\""
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="env:inspector",
                    title="The env inspector",
                    description=(
                        "GET /api/demo/env serves a live inspector over "
                        "the process's REAL AppConfig — no fixture, no "
                        "copy: the environment name, the config's own "
                        "mechanics facts (prefix, frozen, per-process "
                        "cache), and one row per setting with its env-var "
                        "name, its type from the model's own metadata, "
                        "the frozen instance's effective value, and a "
                        "source attribution derived from the SAME "
                        "EnvSettingsSource pydantic-settings consults — "
                        "'env' when the process environment provides the "
                        "field, 'default' when it fell back. Secret-"
                        "bearing fields (any *_secret / *_key / "
                        "*_password) are redacted SERVER-SIDE before the "
                        "payload is built: the value shown is the word "
                        "'redacted' plus a bare length hint, and the "
                        "endpoint test asserts the live values appear "
                        "nowhere in the fully serialized panel. The flags "
                        "sub-panel reads the scenario store's live "
                        "snapshot — the repo's real feature flags, the "
                        "subject of the last teaching section — with the "
                        "real GET/PATCH endpoints beside it."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pydantic-settings-panel-reading",
                    text=(
                        "Reading the panel against the RUNNING stack is "
                        "the point: four rows answer 'env' — FDG_ENV, "
                        "FDG_DATABASE_URL, FDG_REDIS_URL, FDG_MONGO_URL, "
                        "exactly the variables the dev compose file sets "
                        "— while FDG_DEBUG, FDG_LOG_LEVEL, and the two "
                        "secrets answer 'default', because compose does "
                        "not set them and the declared defaults carry "
                        "the process. The secret rows show 'redacted' "
                        "with a length hint and nothing else, which is "
                        "not a UI nicety but the API discipline the "
                        "secrets section teaches: the value never "
                        "crossed the wire at all. And because the panel "
                        "is built from the cached config instance the "
                        "whole app reads, what you see is what the "
                        "process is actually running under — served by "
                        "a router that stays as thin as every other "
                        "router in the stack:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pydantic-settings-router-quote",
                    language="py",
                    caption="The whole demo endpoint: one GET, pure payload, declared response model.",
                    source="server/guide/presentation/routers/demo/env.py",
                    snippet=(
                        "@router.get(PANEL_PATH, response_model=EnvInspectorPanel)\n"
                        "async def read_env_inspector(store: ScenarioStoreDep) -> EnvInspectorPanel:\n"
                        "    \"\"\"Serve the live inspector: settings + sources, redacted secrets, flags.\"\"\"\n"
                        "    return build_env_inspector_payload(get_config(), store.get())"
                    ),
                ),
            ],
        ),
        # ── 4. Env-specific behavior ──────────────────────────────────────
        Section(
            id="env-specific-behavior",
            title="Env-specific behavior",
            blocks=[
                TextBlock(
                    kind="text",
                    id="env-behavior-rule",
                    text=(
                        "The rule this repo keeps absolutely: "
                        "environment-specific BEHAVIOR is expressed as "
                        "environment-specific VALUES, never as code "
                        "branches. Search the source for an 'if "
                        "environment is prod' conditional and you find "
                        "nothing, because FDG_ENV is a label for humans "
                        "and telemetry — the inspector shows it, the "
                        "compose files set it — while everything that "
                        "actually DIFFERS rides in the URL-shaped and "
                        "flag-shaped values the previous sections "
                        "covered. When dev and prod need different "
                        "behavior, the repo gives them different "
                        "RESOURCES (different URLs, different stores) or "
                        "different RAILS (validation that refuses to "
                        "start), which keeps the behavior space "
                        "testable: every code path runs identically in "
                        "every environment, so the suite proves "
                        "behavior once instead of once per stage. The "
                        "prod stack's server block is the rule made "
                        "visible:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="env-behavior-prod-quote",
                    language="yaml",
                    caption="The prod server's environment: same fields as dev, plus the fail-fast secrets rail.",
                    source=".docker/docker-compose.prod.yml",
                    snippet=(
                        "    environment:\n"
                        "      - FDG_ENV=prod\n"
                        "      # Compose-level fail-fast: the required-variable syntax makes an unset\n"
                        "      # FDG_DB_PASSWORD a deploy-time error — `docker compose ... up` refuses to\n"
                        "      # render the stack at all, before any container starts (the spring\n"
                        "      # guide's SDG_DB_PASSWORD pattern). The image stays clean; the secret\n"
                        "      # arrives from the deployer's environment.\n"
                        "      - FDG_DATABASE_URL=postgresql+asyncpg://postgres:${FDG_DB_PASSWORD:?FDG_DB_PASSWORD must be set to a real database password}@postgres:5432/guide\n"
                        "      # The signing secrets ride the SAME required-variable rail: unset\n"
                        "      # values refuse at `compose config` time, and the server's AppConfig\n"
                        "      # validator refuses any dev-default secret in this env a second time\n"
                        "      # at boot — two independent doors, both closed.\n"
                        "      - FDG_JWT_SECRET=${FDG_JWT_SECRET:?FDG_JWT_SECRET must be set to a real high-entropy signing secret}\n"
                        "      - FDG_SESSION_SECRET=${FDG_SESSION_SECRET:?FDG_SESSION_SECRET must be set to a real high-entropy signing secret, distinct from FDG_JWT_SECRET}\n"
                        "      # Data services by service name inside the compose network, mirroring\n"
                        "      # the dev stack's rails.\n"
                        "      - FDG_REDIS_URL=redis://redis:6379\n"
                        "      - FDG_MONGO_URL=mongodb://mongo:27017"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="env-behavior-rails",
                    text=(
                        "The ${FDG_DB_PASSWORD:?...} syntax is a compose "
                        "rail: the question-mark-colon form makes an "
                        "unset variable a RENDER-time error, so "
                        "'docker compose config' refuses to draw the "
                        "stack before a single container starts — the "
                        "failure happens at deploy time with the "
                        "variable's name in the message, not at 3am with "
                        "a database authentication error. And the rail "
                        "is doubled: the postgres service consumes the "
                        "SAME required variable as POSTGRES_PASSWORD, so "
                        "the app's connection string and the database's "
                        "actual password agree by construction — there "
                        "is no way to typo them apart. The dev-grade "
                        "'guide' password from the dev stack cannot "
                        "ride into prod because nothing in the prod "
                        "file contains it; the value arrives from the "
                        "deployer's environment or not at all. That is "
                        "environment-specific behavior with zero "
                        "environment-specific code."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="env-behavior-devcontainer-pitch",
                    text=(
                        "The third environment is the developer's "
                        "workspace itself, and the devcontainer declares "
                        "it as data too — one line naming the exact set "
                        "of services a full local world needs, so "
                        "'reopen in container' and the whole stack "
                        "arrives together, consistently, on every "
                        "machine:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="env-behavior-devcontainer-quote",
                    language="json",
                    caption="The developer environment as a declarative service list.",
                    source=".devcontainer/devcontainer.json",
                    snippet=(
                        "  \"runServices\": [\"dev\", \"server\", \"client\", \"postgres\", \"redis\", \"mongo\", \"arq-worker\"],"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="env-behavior-coda",
                    text=(
                        "Even the client obeys the values-not-branches "
                        "rule: its Vite dev proxy targets API_PROXY_TARGET "
                        "(http://server:8000 inside compose, localhost "
                        "for a host-run client), an environment variable "
                        "the compose file sets — the same pointer-swap "
                        "trick the server's URLs play, in the other "
                        "stack half. The result across all three "
                        "environments is a codebase where the answer to "
                        "'why does prod behave differently from dev' is "
                        "always a diff of small declarative files, never "
                        "an archaeology dig through conditional logic."
                    ),
                ),
            ],
        ),
        # ── 5. Secrets beyond the .env file ───────────────────────────────
        Section(
            id="secrets-beyond-the-env-file",
            title="Secrets beyond the .env file",
            blocks=[
                TextBlock(
                    kind="text",
                    id="secrets-pitch",
                    text=(
                        "The .env file is where configuration hygiene "
                        "goes to die: it starts as a local convenience, "
                        "gets committed 'just the dev one', accumulates "
                        "real credentials, and ends up shared across "
                        "environments that were supposed to differ. This "
                        "repo contains NO .env file at all, and that "
                        "absence is a designed position with three "
                        "legs. First, the dev defaults live IN CODE with "
                        "the comment you read in the pydantic-settings "
                        "section — visible, versioned, and honestly "
                        "labeled as dev-only values that guard nothing "
                        "secret. Second, real per-stack values arrive "
                        "through the environment, set explicitly by the "
                        "compose files — diffable, reviewable, never "
                        "mixed into the source tree. Third, the point "
                        "where a secret MUST exist (the prod database "
                        "password) is fenced by the required-variable "
                        "rail, so absence fails loudly at render time. "
                        "The ladder climbs from dev defaults to deployer "
                        "environment without ever needing a file that "
                        "blends them."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="secrets-ladder-framing",
                    text=(
                        "The full ladder this repo actually climbs, "
                        "rung by rung — each one already met in this "
                        "topic:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="secrets-ladder",
                    ordered=False,
                    items=[
                        "Dev defaults in code — bootable anywhere, "
                        "guarding nothing secret, with the honesty "
                        "comment attached to the two signing secrets.",
                        "Compose environment injection — per-stack "
                        "values, explicit and diffable, the dev stack's "
                        "four FDG_* pointers.",
                        "Required-variable rails — ${FDG_DB_PASSWORD:?} "
                        "fails compose render before any container "
                        "starts, and feeds the database the same value.",
                        "Server-side redaction — display surfaces never "
                        "echo secret values; the inspector's rule, this "
                        "section's centerpiece.",
                        "Fail-fast prod startup — the planned hardening "
                        "that makes a default secret in a prod "
                        "environment a boot failure instead of a quiet "
                        "liability.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="secrets-redaction-pitch",
                    text=(
                        "Redaction deserves its own rung because it is "
                        "the one that applies to CODE you write, not "
                        "just infrastructure you configure. Any surface "
                        "that shows configuration — a debug panel, a "
                        "settings endpoint, a support screen — is a "
                        "leak path the moment it stringifies a config "
                        "object, and the leak travels through logs and "
                        "browser caches long after the page closes. The "
                        "inspector's rule: any field whose name ends in "
                        "_secret, _key, or _password never crosses the "
                        "wire; the row carries the word 'redacted' and "
                        "a bare length hint, and the redaction happens "
                        "in the payload builder, BEFORE a wire model "
                        "exists, so no serialization path can carry the "
                        "live value. The test pins exactly that, by "
                        "serializing the ENTIRE panel and asserting the "
                        "live values appear nowhere in it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="secrets-test-quote",
                    language="py",
                    caption="The redaction proof: live secret values absent from the full serialized payload.",
                    source="server/tests/demo/test_env_inspector_endpoint.py",
                    snippet=(
                        "    serialized = json.dumps(body)\n"
                        "    assert LIVE_JWT_SECRET not in serialized\n"
                        "    assert LIVE_SESSION_SECRET not in serialized\n"
                        "\n"
                        "    jwt_row = row_by_name(body, \"jwt_secret\")\n"
                        "    assert jwt_row[\"value\"] == \"redacted\"\n"
                        "    assert jwt_row[\"shapeHint\"] == f\"{len(LIVE_JWT_SECRET)} chars, hidden\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="secrets-beyond",
                    text=(
                        "Beyond compose, the same interface scales up "
                        "without the app noticing: orchestrator secrets "
                        "(the Kubernetes deployment injects the same "
                        "FDG_* variables at pod start), "
                        "secret-manager services that inject at boot, "
                        "file-based sources pydantic-settings reads "
                        "natively. The application never learns where a "
                        "value came from — it sees a typed field filled "
                        "at construction — which is the whole point of "
                        "keeping the config model small, typed, and "
                        "frozen: the backing storage can improve "
                        "underneath a boundary that never changes."
                    ),
                ),
            ],
        ),
        # ── 6. Feature flags ──────────────────────────────────────────────
        Section(
            id="feature-flags",
            title="Feature flags",
            blocks=[
                TextBlock(
                    kind="text",
                    id="flags-pitch",
                    text=(
                        "Configuration answers 'what is this process "
                        "wired to' once, at boot. Feature flags answer a "
                        "different question — 'how should it behave "
                        "RIGHT NOW' — and the difference is the whole "
                        "discipline: flags change at runtime, without a "
                        "restart, and they are reversible, which is why "
                        "they are the standard tool for kill switches, "
                        "gradual rollouts, and demonstrating failure "
                        "paths on demand. This repo has a REAL flag "
                        "mechanism that has been live since Phase 1 — "
                        "the scenario store — and every demo in this "
                        "guide reads it. Its vocabulary is two closed "
                        "enums, and the honest way to present them is "
                        "the source:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="flags-state-quote",
                    language="py",
                    caption="The repo's real flag vocabulary: two Literal enums, one immutable snapshot.",
                    source="server/guide/core/scenario.py",
                    snippet=(
                        "DataMode = Literal[\"fake\", \"live\"]\n"
                        "FailureInjection = Literal[\"none\", \"error\", \"latency\"]\n"
                        "\n"
                        "DEFAULT_DATA_MODE: DataMode = \"fake\"\n"
                        "DEFAULT_FAILURE_INJECTION: FailureInjection = \"none\"\n"
                        "\n"
                        "\n"
                        "class ScenarioState(CamelModel):\n"
                        "    \"\"\"Immutable snapshot of the demo scenario; wire is camelCase.\"\"\"\n"
                        "\n"
                        "    data_mode: DataMode = DEFAULT_DATA_MODE\n"
                        "    inject_failure: FailureInjection = DEFAULT_FAILURE_INJECTION"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="flags-reading",
                    text=(
                        "dataMode is a data-source flag: 'fake' points "
                        "every demo at its in-memory world, 'live' at "
                        "the real stores — one switch, flipped at "
                        "runtime, changing which ADAPTER serves the "
                        "same domain logic, which is flags at their "
                        "most legitimate. injectFailure is a behavior "
                        "flag: 'error' and 'latency' are switchable "
                        "failure modes the errors topic's probe reads "
                        "live — the repo's demonstration that a flag "
                        "can gate not just features but faults. The "
                        "Literal types matter as much as the fields: "
                        "the flag vocabulary is CLOSED, so an illegal "
                        "value is a validation error, not a novel "
                        "runtime state somebody debugs for an "
                        "afternoon. The inspector panel's flags "
                        "sub-panel reads this exact snapshot, so the "
                        "flag state is always visible rather than "
                        "tribal knowledge."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="flags-write-pitch",
                    text=(
                        "The write path is PATCH /api/demo/scenario — "
                        "partial by design (missing keys mean "
                        "unchanged), and, unusually carefully, "
                        "REVALIDATED inside the store rather than "
                        "trusted from the wire: the merge re-runs "
                        "pydantic validation on the merged state, so "
                        "the store defends its own enum invariant even "
                        "against untyped callers:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="flags-update-quote",
                    language="py",
                    caption="Flag writes merge partial patches and revalidate — the store defends its own invariant.",
                    source="server/guide/core/scenario.py",
                    snippet=(
                        "        changes = patch.model_dump(exclude_unset=True)\n"
                        "        try:\n"
                        "            self._state = ScenarioState.model_validate(\n"
                        "                {**self._state.model_dump(), **changes}\n"
                        "            )\n"
                        "        except ValueError as exc:\n"
                        "            raise AppError(\n"
                        "                FailureKind.VALIDATION_FAILED, f\"Invalid scenario patch: {exc}\"\n"
                        "            ) from exc\n"
                        "        return self._state"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="flags-versus-config",
                    text=(
                        "The decision rule for flag-or-config is worth "
                        "stating crisply, because the two get muddled "
                        "the moment a codebase has both. If a value "
                        "describes the WORLD the process lives in — a "
                        "URL, a credential, a capacity — it is config: "
                        "set at boot, fixed for the process lifetime, "
                        "and owned by the deployer. If a value steers "
                        "BEHAVIOR you need to change while the process "
                        "is serving — which data source demos read, "
                        "whether a fault is injected, whether a half-"
                        "finished feature is exposed — it is a flag: "
                        "mutable at runtime, reversible, and owned by "
                        "the operator or the team shipping the change. "
                        "The muddle always starts innocently, usually "
                        "as a config value somebody got tired of "
                        "restarting to change, and it ends with "
                        "environment variables that mean different "
                        "things in different requests. Keeping the two "
                        "in separate mechanisms — the typed frozen "
                        "model versus the validated mutable store — is "
                        "not ceremony; it is what keeps each one "
                        "honest about its own lifecycle."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="flags-scope",
                    text=(
                        "Honesty about scope: this is a demo-scoped flag "
                        "store, not a flags platform. It is per-app and "
                        "in-memory (every test gets its own), it has no "
                        "persistence, no per-user targeting, no "
                        "percentage rollouts, and no audit trail — and "
                        "for a teaching guide that is the right size. "
                        "In the wild, those capabilities arrive with "
                        "real costs: flag platforms become the most "
                        "entangled dependency a codebase can grow, and "
                        "every flag is a loan against future "
                        "complexity that must eventually be paid off by "
                        "removing it. The discipline worth keeping at "
                        "any scale is visible right here: a small "
                        "closed vocabulary, typed and validated at the "
                        "boundary, visible on a panel, and reset by "
                        "design — flags you can see are flags you can "
                        "retire."
                    ),
                ),
            ],
        ),
        # ── 7. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The environment from a shell: read the panel, prove the redaction, flip a flag.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Five stops: the live panel with every setting "
                        "and its true source, the redaction proof run "
                        "against the live payload, the process "
                        "environment the attribution consulted, one "
                        "flag round trip through the scenario store, "
                        "and this topic's own content detail through "
                        "both ports. The stack is up; every command "
                        "reads the real machinery."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-panel",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the live inspector: every setting, its type, value, and true source\n"
                        "curl -s localhost:8000/api/demo/env \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"environment:\", b[\"environment\"], \"| prefix:\", b[\"facts\"][\"envPrefix\"], \"| frozen:\", b[\"facts\"][\"frozen\"]); \\\n"
                        "[print(\" \", s[\"envVar\"], \"=\", s[\"value\"], \"[\" + s[\"type\"] + \", \" + s[\"source\"] + \"]\") for s in b[\"settings\"]]'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-redaction",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the redaction proof: both dev-default secrets contain 'override-me',\n"
                        "# and neither may appear anywhere in the live payload (expect 0 twice)\n"
                        "curl -s localhost:8000/api/demo/env | grep -c \"override-me\"; echo \"matches (want 0)\"\n"
                        "# the shape hint is all that survives: length only, nothing reconstructable\n"
                        "curl -s localhost:8000/api/demo/env \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "row=[s for s in b[\"settings\"] if s[\"secret\"]][0]; \\\n"
                        "print(row[\"envVar\"], \"->\", row[\"value\"], \"|\", row[\"shapeHint\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-process-env",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the process environment the attribution consulted: compose set these\n"
                        "docker exec fastapi_developers_guide_server_dev env | grep \"^FDG_\"\n"
                        "# every row above appears with source \"env\" in stop 1; the rest fell back to default"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-flags",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — one flag round trip: read, flip dataMode, watch the panel follow, restore\n"
                        "curl -s localhost:8000/api/demo/scenario\n"
                        "curl -s -X PATCH localhost:8000/api/demo/scenario \\\n"
                        "  -H \"content-type: application/json\" -d \"{\\\"dataMode\\\": \\\"live\\\"}\"\n"
                        "curl -s localhost:8000/api/demo/env \\\n"
                        "  | python3 -c 'import json,sys; print(\"flags now:\", json.load(sys.stdin)[\"flags\"][\"dataMode\"])'\n"
                        "curl -s -X PATCH localhost:8000/api/demo/scenario \\\n"
                        "  -H \"content-type: application/json\" -d \"{\\\"dataMode\\\": \\\"fake\\\"}\""
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — this topic's own detail: demo inline in pydantic-settings, companion last\n"
                        "curl -s localhost:8000/api/content/environments | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "print(\"sections:\", len(t[\"sections\"]))\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'\n"
                        "# and through the client's dev proxy, the way the browser reaches it:\n"
                        "curl -s localhost:5174/api/content/environments | python3 -c 'import json,sys; print(\"proxy sections:\", len(json.load(sys.stdin)[\"sections\"]))'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stops 1–3 are the topic's core loop: read the "
                        "real config, see where each value came from, "
                        "and prove the secrets stayed home — the same "
                        "assertion the endpoint test makes, run against "
                        "the live wire. Stop 4 flips one real flag end "
                        "to end and restores it, leaving the stack as "
                        "it was found. Stop 5 closes the guide's "
                        "constant loop: the topic that taught the "
                        "environment story is itself served from the "
                        "environment the compose files describe, "
                        "attributed honestly, secrets and all."
                    ),
                ),
            ],
        ),
    ],
)
