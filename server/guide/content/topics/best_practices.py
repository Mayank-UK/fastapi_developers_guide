"""Topic 41 — Best practices: the whole guide, audited in one place.

The capstone. Forty topics built a runnable reference app — typed content,
thin routers, one error envelope, real stores, honest tests — and this
topic synthesizes the DISCIPLINES that produced it, area by area, each
taught at checklist level and grounded in the repo's own implementation:
the ruff/mypy-strict manifest for setup, the thin router and the family
envelope for API discipline, the headers/argon2/limiter trio for
security, migrations and bound parameters for data, timeouts and
best-effort boot for reliability, JSON logs and the request id for
observability, off-loop blocking and the shared pool for performance,
diffable compose files for operations. The demo is an interactive
SELF-AUDIT: every verdict computed live against the running app and the
repo it lives in — real probes, real file reads, and honest manual rows
where no automation can judge. The anti-checklist closes the teaching:
this repo's deliberate NOT-does, presented as decisions with reasons, and
the terminal companion gives the whole thing a curl tour.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="best-practices",
    title="Best practices",
    subtitle=(
        "The capstone synthesis: every discipline this guide taught, "
        "audited against the repo that taught it — setup and toolchain, "
        "API discipline, security, data, reliability, observability, "
        "performance, and operations as checklists grounded in real code, "
        "the git and human practices machines cannot check for you, an "
        "anti-checklist of deliberate not-does with their reasons, and a "
        "live self-audit that grades the running app honestly — every "
        "verdict computed at request time, manual where it must be."
    ),
    group="capstones",
    order=41,
    sections=[
        # ── 1. Setup ───────────────────────────────────────────────────────
        Section(
            id="setup",
            title="Setup",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bp-setup-pitch",
                    text=(
                        "Every practice in this topic stands on a floor "
                        "laid in the first hour of the project: a manifest "
                        "that IS the toolchain, a lockfile that IS the "
                        "dependency contract, and static analysis that runs "
                        "from the first commit rather than being retro-"
                        "fitted after the first incident. The repo says "
                        "this out loud in the manifest's own header — three "
                        "comment lines that state the whole policy, ranges "
                        "in the manifest for humans to read, exact pins in "
                        "the lock for machines to install:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-setup-manifest-quote",
                    language="toml",
                    caption="The manifest's opening contract: ranges here, exact pins in the lock.",
                    source="server/pyproject.toml",
                    snippet=(
                        "# Server manifest for the FastAPI Developers Guide (`guide` package).\n"
                        "# Ranges live here; the committed uv.lock pins exact versions — the lock is\n"
                        "# THE dependency contract, `uv sync --locked` never re-resolves.\n"
                        "[project]\n"
                        "name = \"guide\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-setup-analyzers",
                    text=(
                        "The two analyzers are configured, not merely "
                        "installed. Ruff runs with an explicit rule-family "
                        "list — style, pyflakes, pyupgrade, imports sorted, "
                        "bugbear — so 'clean' means a chosen bar, not a "
                        "default nobody remembers selecting. mypy runs "
                        "STRICT, with the pydantic plugin so validated "
                        "models and type inference agree, and the python "
                        "version pinned to the one actually deployed. Both "
                        "live beside the code in the same manifest, both "
                        "run in the same container as the tests, and the "
                        "verify one-liner in the terminal companion runs "
                        "all three in one breath — a setup you cannot "
                        "forget to use because it is the only way you "
                        "build:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-setup-strict-quote",
                    language="toml",
                    caption="The analyzers, configured: rule families named, strict on, versions pinned.",
                    source="server/pyproject.toml",
                    snippet=(
                        "[tool.ruff]\n"
                        "line-length = 100\n"
                        "target-version = \"py313\"\n"
                        "\n"
                        "[tool.ruff.lint]\n"
                        "select = [\"E\", \"F\", \"W\", \"I\", \"UP\", \"B\"]\n"
                        "# …\n"
                        "[tool.mypy]\n"
                        "strict = true\n"
                        "plugins = [\"pydantic.mypy\"]\n"
                        "python_version = \"3.13\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-setup-list-framing",
                    text=(
                        "Read as a checklist — the setup practices this "
                        "repo keeps, each one checkable by opening a file:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="bp-setup-list",
                    ordered=False,
                    items=[
                        "One manifest, one lock — pyproject.toml declares ranges, uv.lock pins "
                        "exact versions, uv sync --locked never re-resolves.",
                        "Strict types from day one — mypy strict plus the pydantic plugin; no "
                        "file is ever exempt except generated code, and each exemption is a "
                        "documented override.",
                        "Named lint bar — ruff's select list is explicit (E, F, W, I, UP, B), "
                        "so the standard survives personnel changes.",
                        "Dev tooling in the dev group — pytest, mypy, ruff, httpx ride PEP 735 "
                        "dependency-groups, absent from production images by construction.",
                        "Python version pinned twice — requires-python in the manifest, "
                        "target-version and python_version in the analyzers, one truth.",
                        "Everything containerized — no host venv, no host node_modules; the "
                        "dev containers are the only place builds happen.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="bp-setup-containers",
                    text=(
                        "The last setup practice is where the work "
                        "happens: nowhere but containers. The host stays "
                        "clean by design — no project venv, no node_modules "
                        "— because anonymous volumes keep the container-"
                        "only build outputs off the bind mount, and named "
                        "cache volumes mean the first dependency download "
                        "is also the last. That is a setup decision with "
                        "daily payoff: 'it works on my machine' stops "
                        "being a complaint category when nobody's machine "
                        "is special, the verify one-liner works identically "
                        "on a laptop and a fresh CI runner, and a new "
                        "contributor's first command is the same as the "
                        "maintainer's ten-thousandth. Cheap tooling that "
                        "everyone actually runs beats perfect tooling "
                        "that some people skip."
                    ),
                ),
            ],
        ),
        # ── 2. API discipline ──────────────────────────────────────────────
        Section(
            id="api-discipline",
            title="API discipline",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bp-api-pitch",
                    text=(
                        "API discipline is what makes a codebase of dozens "
                        "of routers readable in an afternoon: every "
                        "endpoint does the same four things in the same "
                        "order. Parse and validate the input through "
                        "pydantic at the boundary; call a use case that "
                        "returns a Result; raise the failure if there is "
                        "one so the ONE exception pipeline renders the "
                        "family envelope; set headers with the router's "
                        "own url_path_for instead of string-pasting. The "
                        "posts resource is the canonical shape — two of "
                        "its handlers fit on one screen and demonstrate "
                        "all of it, including the 201-plus-Location "
                        "convention and the two-line Err flip:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-api-router-quote",
                    language="py",
                    caption="The house router shape: validate, use case, raise-or-return, no logic.",
                    source="server/guide/presentation/routers/posts.py",
                    snippet=(
                        "@router.get(\"/api/posts/{post_id}\", response_model=Post)\n"
                        "def read_post(post_id: str, use_cases: PostUseCasesDep) -> Post:\n"
                        "    \"\"\"Serve one post; unknown ids are the shared 404 envelope.\"\"\"\n"
                        "    result = use_cases.get_post.execute(post_id)\n"
                        "    if isinstance(result, Err):\n"
                        "        raise result.failure\n"
                        "    return result.value\n"
                        "\n"
                        "# …\n"
                        "@router.post(\"/api/posts\", response_model=Post, status_code=201)\n"
                        "def create_post(draft: PostCreate, response: Response, use_cases: PostUseCasesDep) -> Post:\n"
                        "    \"\"\"Create from the validated body: 201 + Location names the resource.\"\"\"\n"
                        "    result = use_cases.create_post.execute(draft)\n"
                        "    if isinstance(result, Err):\n"
                        "        raise result.failure\n"
                        "    post = result.value\n"
                        "    response.headers[\"location\"] = router.url_path_for(\"read_post\", post_id=post.id)\n"
                        "    return post"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-api-envelope",
                    text=(
                        "The envelope is the other half of the discipline. "
                        "Every failure in the whole app — validation, "
                        "auth, missing, conflict, throttled, degraded, "
                        "internal — renders as one JSON shape with a code, "
                        "a message, the request id, and optional details, "
                        "and every error response carries the x-request-id "
                        "header so a curl and a log line agree. Status "
                        "codes are decided in exactly one place, the "
                        "kind-to-status map in the error taxonomy, so no "
                        "handler ever invents a 418. The self-audit "
                        "probes this live: a request for a post that does "
                        "not exist must answer 404 with the not_found "
                        "envelope, and the id in the body must equal the "
                        "id in the header — the demo judges that contract "
                        "against the running app, not against a fixture."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-api-list-framing",
                    text=(
                        "The API checklist this repo actually keeps, in "
                        "the order a request meets them:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="bp-api-list",
                    ordered=False,
                    items=[
                        "Models at the boundary — request bodies and responses are pydantic "
                        "models with declared response_model, so the contract generates itself.",
                        "Thin routers — parse, call a use case, map the Result; business logic "
                        "never lives in a handler.",
                        "One error envelope — every failure is the same JSON shape with code, "
                        "message, requestId, and the x-request-id header to match.",
                        "Statuses decided once — the taxonomy's kind-to-status map is the only "
                        "place an HTTP status is chosen.",
                        "Locations resolved, never pasted — 201s name the new resource with "
                        "url_path_for, which cannot drift from the route table.",
                        "Pagination in headers — totals, page counts, and an RFC 8288 Link so "
                        "clients page without guessing conventions.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="bp-api-coda",
                    text=(
                        "A closing note on the contract's lifecycle, "
                        "because discipline at creation is only half the "
                        "practice. The OpenAPI document generates from the "
                        "running app, so it cannot disagree with the "
                        "routes; the client validates every payload "
                        "against its own typed shapes, so wire drift "
                        "surfaces loudly rather than half-rendering; and "
                        "shape pins in the suite freeze the envelopes "
                        "this guide teaches, so an accidental field "
                        "rename fails a test before it puzzles a "
                        "consumer. Versioning stays boring on purpose — "
                        "the content API is version one and says so in "
                        "every payload, and the family's lesson applies: "
                        "earn a version two by shipping a breaking change "
                        "you can no longer avoid, not by anticipating "
                        "ones you might."
                    ),
                ),
            ],
        ),
        # ── 3. Security ────────────────────────────────────────────────────
        Section(
            id="security",
            title="Security",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bp-security-pitch",
                    text=(
                        "Security practices fail when they are features "
                        "somebody has to remember to enable, so this repo "
                        "wires its defaults globally and lets nothing opt "
                        "out. The defensive headers are stamped by "
                        "middleware on EVERY response — including error "
                        "envelopes, because the error paths are the ones "
                        "attackers actually probe — with a path-aware "
                        "content-security policy that refuses everything "
                        "on JSON routes and permits exactly the docs "
                        "pages' CDN assets:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-security-headers-quote",
                    language="py",
                    caption="Headers that are not opt-in: the static set every response starts from.",
                    source="server/guide/presentation/middleware/security_headers.py",
                    snippet=(
                        "_STATIC_HEADERS: Final[dict[str, str]] = {\n"
                        "    \"X-Content-Type-Options\": \"nosniff\",\n"
                        "    \"X-Frame-Options\": \"DENY\",\n"
                        "    \"Referrer-Policy\": \"no-referrer\",\n"
                        "    \"Content-Security-Policy\": API_CSP,\n"
                        "}\n"
                        "\"\"\"The headers every response starts from; CSP is overridden on docs paths.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-security-argon2",
                    text=(
                        "Password storage is the second non-negotiable, "
                        "and the repo's implementation carries a subtler "
                        "practice inside it: uniform cost. Verification "
                        "burns one full argon2 run whether the answer is "
                        "a match, a mismatch, or a user who does not "
                        "exist — the decoy hash makes 'no such user' "
                        "cost the same as 'wrong password', so response "
                        "times cannot enumerate usernames:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-security-argon2-quote",
                    language="py",
                    caption="Timing-uniform verification: the decoy hash makes absence cost the same as error.",
                    source="server/guide/domain/auth/password_service.py",
                    snippet=(
                        "    def verify_uniform(self, stored_hash: str | None, password: str) -> bool:\n"
                        "        \"\"\"The timing-uniform credential check every login uses.\n"
                        "\n"
                        "        ``stored_hash`` None (unknown username) burns a decoy verification\n"
                        "        so the answer takes the same time as a real wrong password; the\n"
                        "        result is False either way, and callers learn nothing about WHICH\n"
                        "        half failed.\n"
                        "        \"\"\"\n"
                        "        verdict = self.verify_password(\n"
                        "            VerifyPasswordRequest(password=password, hash=stored_hash or DECOY_HASH)\n"
                        "        )\n"
                        "        return verdict.ok"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-security-list-framing",
                    text=(
                        "The rest of the security checklist as this repo "
                        "keeps it — each row verified by the audit where a "
                        "machine honestly can:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="bp-security-list",
                    ordered=False,
                    items=[
                        "Headers on every response — nosniff, DENY, no-referrer, and a strict "
                        "CSP stamped by middleware, error envelopes included.",
                        "Argon2id with rehash-on-login — modern cost parameters, and "
                        "check_needs_rehash upgrades old hashes at the next successful verify.",
                        "Uniform verification cost — unknown users burn a decoy hash so "
                        "timing cannot enumerate accounts.",
                        "Rate limiting at the edge — a sliding-window limiter behind a "
                        "dependency, keyed by client and route template, 429s carrying "
                        "Retry-After.",
                        "CORS as an allow-list — exact origins with credentials, never the "
                        "wildcard pairing that leaks cookies cross-origin.",
                        "Secrets as environment values — dev defaults documented in code, "
                        "prod forced through required-variable rails, display surfaces "
                        "redacting server-side.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="bp-security-coda",
                    text=(
                        "Ordering is the quiet practice that makes the "
                        "rest hold together: the middleware stack is "
                        "built with the request-id layer innermost, the "
                        "security headers wrapping every response "
                        "including envelopes, and CORS outermost — so "
                        "even a throttled or failing answer carries the "
                        "CORS verdict a browser needs to READ the error. "
                        "Each layer was added for a stated reason and "
                        "the composition is observable: the middleware "
                        "topic's pipeline demo walks the built stack "
                        "live, and this topic's audit checks the "
                        "outermost results — headers on a 200, headers "
                        "on a 404, an id that round-trips. When you can "
                        "prove your security defaults from a curl, you "
                        "stop having to argue them in code review."
                    ),
                ),
            ],
        ),
        # ── 4. Data ────────────────────────────────────────────────────────
        Section(
            id="data",
            title="Data",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bp-data-pitch",
                    text=(
                        "Data practices come down to two commitments: the "
                        "schema has a history, and input never becomes "
                        "code. The first is Alembic's chain — four "
                        "revisions at time of writing, each linked to its "
                        "parent, every constraint NAMED at creation so a "
                        "future migration can address it without "
                        "archaeology. The initial revision demonstrates "
                        "the house style — check domains, deliberate ON "
                        "DELETE behaviors, one b-tree per foreign key, "
                        "and a partial index that covers only published "
                        "posts so drafts never bloat the tree the "
                        "newest-first query reads:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-data-migration-quote",
                    language="py",
                    caption="Named constraints and a partial index: schema decisions, reviewable as code.",
                    source="server/alembic/versions/0001_guide_schema.py",
                    snippet=(
                        "    op.create_index(\"ix_posts_author_id\", \"posts\", [\"author_id\"], unique=False)\n"
                        "    op.create_index(\"ix_comments_post_id\", \"comments\", [\"post_id\"], unique=False)\n"
                        "    # A PARTIAL index: only published posts are covered, so drafts never\n"
                        "    # bloat the tree the \"newest published first\" query reads.\n"
                        "    op.create_index(\n"
                        "        \"ix_posts_published_created_at\",\n"
                        "        \"posts\",\n"
                        "        [\"created_at\"],\n"
                        "        unique=False,\n"
                        "        postgresql_where=sa.text(\"status = 'published'\"),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-data-parameterized",
                    text=(
                        "The second commitment is parameterized SQL. "
                        "Every query the data layer runs sends user input "
                        "as a bind parameter — the colon names in the "
                        "query text are data slots, and the driver "
                        "packages the values separately so a quote in a "
                        "search box can only ever match text, never "
                        "become syntax. The safety demo's filter is the "
                        "teaching example, and its docstring states the "
                        "rule the whole layer follows:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-data-bind-quote",
                    language="py",
                    caption="Binds are data: the filter query and the execute that feeds it.",
                    source="server/guide/data/db/repository.py",
                    snippet=(
                        "TITLE_FILTER_SQL = \"\"\"\n"
                        "SELECT p.id, p.slug, p.title, p.status\n"
                        "FROM posts AS p\n"
                        "WHERE p.title ILIKE :pattern\n"
                        "ORDER BY p.id\n"
                        "\"\"\"\n"
                        "\"\"\"The safety demo's filter query — :pattern is a BIND PARAMETER, so the\n"
                        "caller's text can only ever be data.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-data-list-framing",
                    text=(
                        "The data checklist, as the repo's files and its "
                        "audit rows keep it:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="bp-data-list",
                    ordered=False,
                    items=[
                        "Migrations own the schema — no hand-edited tables; the chain from the "
                        "first revision to head is complete, linked, and applied at startup.",
                        "Named constraints — every check, key, and index is named at creation, "
                        "so later migrations address them precisely.",
                        "Parameterized SQL everywhere — user input rides bind parameters; "
                        "rendered SQL strings are for DISPLAY, never for execution.",
                        "One dialect, tested for real — PostgreSQL only, and persistence tests "
                        "run against a real throwaway instance rather than a lying twin.",
                        "Optimistic concurrency where rows contend — a version column turns "
                        "lost updates into clean StaleDataError rejections.",
                        "Writes that belong together in one transaction — the outbox pattern "
                        "commits the row and the event atomically, never half."
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="bp-data-coda",
                    text=(
                        "Two smaller data practices round it out because "
                        "they keep paying quietly. Identifiers are chosen "
                        "for the database's sake: UUIDv7 for the rows "
                        "that want global uniqueness, sequences for the "
                        "ones that want locality, and never a string "
                        "primary key because it scanned well in a "
                        "migration. And sensitive tables carry their own "
                        "memory — the audit_log table from the first "
                        "revision records who changed what inside the "
                        "same transaction as the change, so a rollback "
                        "erases the claim and a commit preserves it, "
                        "which the audit demo proves with counts. Data "
                        "practices compound like interest: none of these "
                        "rows is exciting alone, and together they are "
                        "the difference between a schema you operate and "
                        "a schema you survive."
                    ),
                ),
            ],
        ),
        # ── 5. Reliability ─────────────────────────────────────────────────
        Section(
            id="reliability",
            title="Reliability",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bp-reliability-pitch",
                    text=(
                        "Reliability practices are mostly decisions about "
                        "what happens when a dependency is gone, and this "
                        "repo's answer is consistent: degrade fast, "
                        "degrade loudly, boot anyway. Optional stores get "
                        "short timeouts on purpose — two seconds, not the "
                        "thirty a driver defaults to — so an unreachable "
                        "service costs one quick failure that maps to the "
                        "service_unavailable envelope, not a worker hung "
                        "half a minute per request. The constants say it "
                        "in their own docstrings:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-reliability-timeouts-quote",
                    language="py",
                    caption="Timeouts chosen for degradation: two seconds, then the 503 envelope.",
                    source="server/guide/data/mongo/client.py",
                    snippet=(
                        "SERVER_SELECTION_TIMEOUT_MS: Final = 2_000\n"
                        "\"\"\"How long an operation waits for a reachable mongod before failing.\n"
                        "\n"
                        "Short on purpose: when MongoDB is down, a demo request should degrade\n"
                        "to the 503 envelope in about two seconds, not hang a worker for the\n"
                        "30-second driver default.\n"
                        "\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-reliability-boot",
                    text=(
                        "The boot path applies the same discipline to "
                        "schema readiness: migrations run at startup, "
                        "best-effort, because an app that cannot reach "
                        "its database can still serve everything that "
                        "does not need it — and the first request that "
                        "does need it reports the outage through the "
                        "normal error taxonomy instead of a crash loop. "
                        "The lifespan function is four lines of try, "
                        "warn, continue:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-reliability-lifecycle-quote",
                    language="py",
                    caption="Best-effort boot: apply migrations, or log the skip and serve the rest.",
                    source="server/guide/data/db/lifecycle.py",
                    snippet=(
                        "async def upgrade_database_on_startup(database_url: str) -> None:\n"
                        "    \"\"\"Best-effort startup migration: apply, or log the skip and continue.\"\"\"\n"
                        "    try:\n"
                        "        await asyncio.to_thread(upgrade_database_to_head, database_url)\n"
                        "    except Exception as exc:\n"
                        "        logger.warning(\n"
                        "            \"db_migrations_skipped\",\n"
                        "            error=type(exc).__name__,\n"
                        "            detail=str(exc),\n"
                        "            hint=\"PostgreSQL may be down — the app stays up; DB-backed \"\n"
                        "            \"features will report service_unavailable until it returns.\",\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-reliability-list-framing",
                    text=(
                        "The reliability checklist this repo keeps — the "
                        "audit reads each item from the code that "
                        "implements it:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="bp-reliability-list",
                    ordered=False,
                    items=[
                        "Bounded waits — two-second timeouts on optional stores so absence is "
                        "a quick 503, never a hung worker.",
                        "Degradation, not collapse — one store down degrades only the "
                        "features that need it; the process serves the rest.",
                        "Best-effort boot — migrations apply at startup or log the skip; the "
                        "app never refuses to start because a store is absent.",
                        "A closed failure vocabulary — eight kinds, one status each, so "
                        "failures are countable and no handler invents codes.",
                        "Retries as policy, not instinct — background jobs route every retry "
                        "through one engine with backoff and a dead-letter end state.",
                        "Idempotent consumers — replayed deliveries are recognized and "
                        "skipped, because at-least-once means at-least-once."
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="bp-reliability-coda",
                    text=(
                        "What makes these reliability practices rather "
                        "than reliability hopes is that each one is "
                        "PROVEN, not asserted. The degradation tests wire "
                        "an unreachable URL and assert the 503 envelope "
                        "arrives fast; the boot test starts the app with "
                        "stores absent; the jobs suite counts retries "
                        "until a poison message dead-letters, then "
                        "replays it and watches the counter reset. That "
                        "is the transferable habit: for every failure "
                        "mode you claim to survive, own a test that "
                        "inflicts it — otherwise the claim is a comment "
                        "with ambitions. The audit panel's reliability "
                        "rows read the same discipline from the code's "
                        "own constants and log events, which is the "
                        "quiet standard across this whole synthesis: the "
                        "proof lives in the artifact, not the brochure."
                    ),
                ),
            ],
        ),
        # ── 6. Observability ───────────────────────────────────────────────
        Section(
            id="observability",
            title="Observability",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bp-obs-pitch",
                    text=(
                        "Observability practices answer three questions — "
                        "what happened, in what order, and where do I look "
                        "— and this repo answers them with the smallest "
                        "machinery that honestly can. Logs are structured "
                        "JSON from the first line: one object per event "
                        "with level, timestamp, and event name, greppable "
                        "by machines and readable by humans, no log files "
                        "anywhere. The whole pipeline is one configure "
                        "call:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-obs-logging-quote",
                    language="py",
                    caption="The entire logging setup: JSON from the first line of the process.",
                    source="server/guide/core/logging.py",
                    snippet=(
                        "    structlog.configure(\n"
                        "        processors=[\n"
                        "            structlog.processors.add_log_level,\n"
                        "            structlog.processors.TimeStamper(fmt=\"iso\"),\n"
                        "            structlog.processors.format_exc_info,\n"
                        "            structlog.processors.JSONRenderer(),\n"
                        "        ],\n"
                        "        wrapper_class=structlog.make_filtering_bound_logger(_numeric_level(level)),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-obs-request-id",
                    text=(
                        "The correlation id is the other half: every "
                        "request gets exactly one, echoed on the response "
                        "header and bound to a contextvar so any log line "
                        "anywhere in the call stack can carry it. The "
                        "assignment is defensive by design — an inbound "
                        "id is accepted but capped, so hostile headers "
                        "cannot bloat every line, and absence mints a "
                        "fresh uuid:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-obs-request-id-quote",
                    language="py",
                    caption="One id per request: accepted-and-capped or freshly minted, never trusted raw.",
                    source="server/guide/core/request_context.py",
                    snippet=(
                        "def _assign_request_id(inbound: str | None) -> str:\n"
                        "    \"\"\"Normalize the inbound header: strip, cap at 200, default to uuid4 hex.\"\"\"\n"
                        "    candidate = (inbound or \"\").strip()[:_MAX_INBOUND_ID_LENGTH]\n"
                        "    return candidate or uuid4().hex"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-obs-list-framing",
                    text=(
                        "The observability checklist as kept here — "
                        "deliberately modest, honestly labelled:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="bp-obs-list",
                    ordered=False,
                    items=[
                        "Structured logs from day one — JSON objects to stdout, no files, no "
                        "custom parsers, greppable by event name.",
                        "One correlation id — assigned per request, echoed on the response, "
                        "bound where any logger can read it.",
                        "Liveness that lies about nothing — /api/health reports the process, "
                        "not its dependencies, and says so in its docstring.",
                        "Failures logged with their id — every error path emits the request "
                        "id, so a user report maps to exact log lines.",
                        "Panels over sources of truth — demo surfaces read the middleware or "
                        "config that enforces a fact, so docs cannot drift from behavior.",
                        "Honest gaps named — metrics and tracing are planned depth, not "
                        "pretended presence; the repo says what it does not yet have."
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="bp-obs-coda",
                    text=(
                        "Level discipline is the part teams lose first, "
                        "so it is worth stating as a practice: INFO for "
                        "events an operator greps after the fact, WARNING "
                        "for handled failures the taxonomy already "
                        "classified, ERROR for the unhandled — and "
                        "nothing logged twice at two levels. The repo's "
                        "error paths demonstrate the policy: an "
                        "app_error event logs warning with its kind and "
                        "request id, an unhandled exception logs error "
                        "with the traceback, and neither repeats. Run "
                        "any request against the live stack and the "
                        "JSON lines read like a narration of the "
                        "taxonomy — which is the test: if a stranger "
                        "cannot follow one request through your logs in "
                        "one grep, the logs are decoration, not "
                        "observability."
                    ),
                ),
            ],
        ),
        # ── 7. Performance ─────────────────────────────────────────────────
        Section(
            id="performance",
            title="Performance",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bp-perf-pitch",
                    text=(
                        "Performance practices in this repo start with "
                        "restraint: measure before tuning, and keep the "
                        "event loop clean regardless. The single most "
                        "important async discipline is that BLOCKING WORK "
                        "LEAVES THE LOOP — synchronous migrations, "
                        "subprocesses, anything that would park the "
                        "serving thread, runs through asyncio.to_thread "
                        "so the loop keeps answering requests while it "
                        "happens. The lifecycle module you met in the "
                        "reliability section does it for migrations; the "
                        "testing runner does it for pytest subprocesses "
                        "and states the rule in its own catalog:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-perf-offloop-quote",
                    language="py",
                    caption="The off-loop rule, stated where it is practiced.",
                    source="server/guide/domain/demos/testing_runner.py",
                    snippet=(
                        "    command_template=\"<venv python> -m pytest -v --no-header <slice paths>\",\n"
                        "    cwd=\"server/\",\n"
                        "    timeout_seconds=RUN_TIMEOUT_SECONDS,\n"
                        "    off_loop=\"asyncio.to_thread (a blocking subprocess never sits on the event loop)\","
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-perf-pool",
                    text=(
                        "The pooling practice is the same shape: one "
                        "engine per process, built by one factory every "
                        "adapter shares, so pool policy lives in exactly "
                        "one place — and the factory's docstring carries "
                        "the restraint rule with it, pre-ping on, sizing "
                        "left at defaults until real load is measured "
                        "rather than guessed:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-perf-engine-quote",
                    language="py",
                    caption="One seam for pooling: pre-ping on, sizing untouched until measured.",
                    source="server/guide/data/db/engine.py",
                    snippet=(
                        "def create_db_engine(config: AppConfig) -> AsyncEngine:\n"
                        "    \"\"\"Build the process's async engine from the app config's URL rail.\n"
                        "\n"
                        "    ``pool_pre_ping`` so a PostgreSQL restart between requests surfaces as\n"
                        "    a clean reconnect instead of a stale-socket error; pool sizing stays\n"
                        "    at SQLAlchemy's defaults until topic 38 measures real load.\n"
                        "    \"\"\"\n"
                        "    return create_async_engine(config.database_url, pool_pre_ping=True)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-perf-list-framing",
                    text=(
                        "The performance checklist this repo keeps — "
                        "short, because the honest list is short:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="bp-perf-list",
                    ordered=False,
                    items=[
                        "Never block the loop — blocking calls run through asyncio.to_thread, "
                        "from migrations to subprocesses to Pillow work.",
                        "One pool per process — a single engine factory every adapter shares, "
                        "pre-ping healing sockets a restart stranded.",
                        "The fast ASGI path — uvicorn[standard] with uvloop and httptools as a "
                        "pinned dependency, not a folklore flag.",
                        "Measure before tuning — pool sizing, caching, and GC choices wait "
                        "for real numbers; defaults are documented as deliberate.",
                        "Stream what is big — uploads and downloads flow chunked with "
                        "backpressure instead of buffering bodies in memory.",
                        "Cache with a policy — versioned keys, TTLs, single-flight fills, and "
                        "explicit invalidation rather than hopeful memoization."
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="bp-perf-coda",
                    text=(
                        "The measurement honesty deserves its own line, "
                        "because it is the practice that keeps the other "
                        "five honest. Wherever this repo quotes a "
                        "number, the number was measured in that process: "
                        "password verification reports its real "
                        "milliseconds, the caching layer stamps hit, "
                        "miss, and age onto responses, the ORM probe "
                        "counts queries with a listener rather than "
                        "estimating them. Nowhere does it average "
                        "rounded marketing into a payload. That is a "
                        "habit worth copying wholesale — performance "
                        "claims that survive contact with a panel are "
                        "the only kind a teammate can build on, and the "
                        "alternative is a README benchmark nobody can "
                        "reproduce on a Tuesday."
                    ),
                ),
            ],
        ),
        # ── 8. Operations ──────────────────────────────────────────────────
        Section(
            id="operations",
            title="Operations",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bp-ops-pitch",
                    text=(
                        "Operational practices are what let somebody else "
                        "run what you built, and the repo's whole posture "
                        "is files-you-can-diff: the dev and prod stacks "
                        "are compose files whose entire difference is "
                        "values — environment pointers, published ports, "
                        "and the required-variable rail that refuses to "
                        "render prod without a real database password. "
                        "Backing services declare their own healthchecks "
                        "so a human asking 'is redis up' gets the same "
                        "answer the orchestrator would:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-ops-compose-quote",
                    language="yaml",
                    caption="Truth as config: a backing service's healthcheck, in the stack file.",
                    source=".docker/docker-compose.yml",
                    snippet=(
                        "    healthcheck:\n"
                        "      test: [\"CMD-SHELL\", \"pg_isready -U postgres -d guide\"]\n"
                        "      interval: 10s\n"
                        "      timeout: 5s\n"
                        "      retries: 5\n"
                        "      start_period: 10s"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-ops-cache-volumes",
                    text=(
                        "The same file carries the workflow economics: "
                        "the named cache volumes are declared EXTERNAL on "
                        "purpose, reused by the host-side verification "
                        "runs so a fresh machine pays its dependency "
                        "download exactly once — and the comment block "
                        "explains what happens if you forget, which is "
                        "the difference between a stack and a runbook:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-ops-volumes-quote",
                    language="yaml",
                    caption="External caches: declared, reused, and explained where they are declared.",
                    source=".docker/docker-compose.yml",
                    snippet=(
                        "  fdg-uv:\n"
                        "    name: fdg-uv\n"
                        "    external: true\n"
                        "  fdg-npm:\n"
                        "    name: fdg-npm\n"
                        "    external: true"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-ops-list-framing",
                    text=(
                        "The operations checklist as the repo's own files "
                        "keep it:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="bp-ops-list",
                    ordered=False,
                    items=[
                        "Environments as diffs — dev and prod are two compose files over the "
                        "same images; every difference is a value, never a branch.",
                        "Render before you run — docker compose config is the pre-flight; the "
                        "secrets rail fires there, before any container starts.",
                        "Healthchecks declared — each backing service states how its own "
                        "truth is probed, for humans and orchestrators alike.",
                        "Clean build contexts — .dockerignore keeps secrets, caches, and "
                        "version-control noise out of every image build.",
                        "One-command onboarding — the devcontainer names the whole world; a "
                        "new machine reaches a running stack without a runbook.",
                        "Verification as a one-liner — the suite, lint, and types run inside "
                        "the long-lived containers with one command, zero setup ceremony."
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="bp-ops-coda",
                    text=(
                        "The production half closes the loop with the "
                        "same files-diff principle: the prod stack runs "
                        "the SAME images as dev behind a different "
                        "compose file, the images are built multi-stage "
                        "so the shipped artifact carries no dev "
                        "toolchain, and the deployer's environment is "
                        "the only place a real secret can enter. "
                        "Operational practices earn their keep at 3am "
                        "with a pager going off — and the difference "
                        "between a stack you can reason about then and "
                        "one you cannot is almost always whether the "
                        "differences were declared in files you can "
                        "read, or smeared across consoles you cannot "
                        "revisit. This repo keeps everything on the "
                        "readable side of that line, on purpose."
                    ),
                ),
            ],
        ),
        # ── 9. Git and review ──────────────────────────────────────────────
        Section(
            id="git-and-review",
            title="Git and review",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bp-git-pitch",
                    text=(
                        "The version-control practices here are mostly "
                        "disciplines of smallness and honesty: small "
                        "diffs, atomic commits, and a review culture "
                        "where machines check what machines can check so "
                        "humans can spend their attention on design "
                        "intent. The repo's strongest git-adjacent "
                        "practice is the snippet ratchet — a test that "
                        "proves every quoted line in every topic is a "
                        "real line of a real file, so documentation "
                        "cannot rot silently. The belt is two lines, and "
                        "the contract is in the constant's docstring:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-git-ratchet-quote",
                    language="py",
                    caption="The review force-multiplier: a ratchet that only turns one way.",
                    source="server/tests/test_snippet_ratchet.py",
                    snippet=(
                        "RATCHET = 0\n"
                        "\"\"\"Maximum allowed violations. Never raise it; drive it to 0 and keep it there.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-git-review-culture",
                    text=(
                        "Around that machine belt sits the human one. "
                        "Every diff gets read by a person before it "
                        "lands — not to re-verify what the suite proves, "
                        "but to ask the questions automation cannot: is "
                        "this the simplest shape that solves it, does the "
                        "name say the thing, will the next reader have "
                        "the context this change assumes. The audit panel "
                        "below is honest about this boundary: it has a "
                        "row for review-your-diffs, and that row comes "
                        "back verdict MANUAL with a one-line why, because "
                        "a checklist that pretends to verify judgment is "
                        "lying with extra steps."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-git-list-framing",
                    text=(
                        "The git-and-review checklist this repo keeps:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="bp-git-list",
                    ordered=False,
                    items=[
                        "Small, atomic diffs — one purpose per change, so review reads like a "
                        "paragraph instead of a novel.",
                        "Machines first — the suite, the analyzers, and the ratchet answer "
                        "what they can, before any human time is spent.",
                        "The ratchet only tightens — quality gates are constants that never "
                        "rise; regressions are fixed, not re-baselined.",
                        "Humans read design intent — every diff lands reviewed; what cannot "
                        "be automated is admitted, not faked.",
                        "History that answers why — commits and the planning file carry the "
                        "reasoning, so archaeology starts at a decision, not a diff."
                    ],
                ),
            ],
        ),
        # ── 10. Human practices ────────────────────────────────────────────
        Section(
            id="human-practices",
            title="Human practices",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bp-human-pitch",
                    text=(
                        "The practices that matter most are the ones no "
                        "checklist can verify, and a practices synthesis "
                        "that omits them is a list of chores. This repo "
                        "was built with three habits that live entirely "
                        "in people, and the audit panel says so plainly: "
                        "these rows come back manual. First, the threat "
                        "model is revisited whenever the attack surface "
                        "changes — a new endpoint, a new dependency, a "
                        "new store — because a threat model that is "
                        "written once is a snapshot of a system that no "
                        "longer exists. Second, production secrets are "
                        "actually overridden: the compose rail enforces "
                        "presence, but only an operator knows whether the "
                        "value behind the variable is strong, rotated, "
                        "and owned. Third, onboarding stays honest — when "
                        "a new machine cannot reach a running stack in "
                        "one command, that is a bug in the repo, not a "
                        "rite of passage for the newcomer."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-human-communication",
                    text=(
                        "Communication is the other half. Failures get "
                        "reported with their request id, because 'it "
                        "broke' is an anecdote while 'request 4f2c broke' "
                        "is a diagnosis. Divergences get written down "
                        "where the next reader trips over them — this "
                        "topic's anti-checklist exists precisely so that "
                        "the repo's not-does read as decisions instead of "
                        "gaps. And estimates stay guesses in public: the "
                        "build plan in this family's planning file marks "
                        "work done only when its definition of done "
                        "names a command that passed, which is a "
                        "communication practice disguised as a "
                        "bookkeeping one — the whole team reads the same "
                        "definition of finished."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-human-list-framing",
                    text=(
                        "The human checklist — manual by nature, "
                        "deliberately so:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="bp-human-list",
                    ordered=False,
                    items=[
                        "Refresh the threat model on surface changes — when an endpoint, "
                        "dependency, or store lands, the conversation is scheduled, not "
                        "assumed.",
                        "Verify prod secrets for real — presence is railed; strength and "
                        "rotation are operator facts that deserve a look.",
                        "Report failures with ids — a request id turns an anecdote into a "
                        "greppable diagnosis.",
                        "Write divergences down — every deliberate not-do carries its reason "
                        "where the next reader finds it.",
                        "Keep onboarding one command — the day a fresh machine needs a "
                        "runbook, the repo owes a fix.",
                        "Share one definition of done — finished means the named command "
                        "passed, and everyone reads the same name."
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="bp-human-coda",
                    text=(
                        "Treat every checklist — this topic's included — "
                        "as a budget statement rather than a score. The "
                        "rows you pass are sunk discipline, the rows you "
                        "fail are scheduled work, and the rows that come "
                        "back manual are the agenda of your next "
                        "conversation with your team; none of them is a "
                        "feelings report. The audit panel was built to "
                        "make that posture concrete: verdicts computed "
                        "from evidence, manuals admitted with reasons, "
                        "not-does owned with artifacts. Practices guides "
                        "fail when they become rituals performed for "
                        "auditors — the entire point of grounding this "
                        "one in a repo that runs is that every claim "
                        "here is one curl away from being checked, "
                        "including the claims about honesty itself."
                    ),
                ),
            ],
        ),
        # ── 11. The anti-checklist ─────────────────────────────────────────
        Section(
            id="anti-checklist",
            title="The anti-checklist",
            lead="This section carries the topic's demo — the live self-audit.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bp-anti-pitch",
                    text=(
                        "An honest practices guide ends with what it "
                        "deliberately did NOT do, because a checklist "
                        "without its complement teaches cargo cult. This "
                        "repo's not-does are decisions with reasons: no "
                        "hosted CI by default (the local docker-flock "
                        "verify one-liners are the only gate, a hosted "
                        "pipeline arrives only on explicit request); "
                        "PostgreSQL only, no SQLite fallback (one dialect "
                        "learned deeply, persistence tested against the "
                        "real thing); browser end-to-end suites deferred "
                        "to a planned hardening phase (scripted checks "
                        "against the live stack bridge the gap and say "
                        "so); and zero teaching exhibits — no compilable "
                        "fakes parked in the tree, every quoted line is "
                        "production-shaped code the ratchet verifies. "
                        "The demo below presents all four as first-class "
                        "rows beside the checklist it audits."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-anti-honesty",
                    text=(
                        "The same honesty shapes what the audit itself "
                        "refuses to fake. Some practices have no honest "
                        "automated check — reviewing diffs, overriding "
                        "prod secrets — and for those the panel returns "
                        "verdict manual with a one-line why instead of a "
                        "theater of green checks. One not-do even leaks "
                        "into the checklist mechanics: the running server "
                        "container mounts only the server tree, so "
                        "repo-root files (compose, .dockerignore, the "
                        "devcontainer) cannot be read from there — and "
                        "rather than pretending, those rows report manual "
                        "with exactly that reason, flipping to real file "
                        "checks wherever the whole repo is visible. The "
                        "pytest manifest carries the same spirit in "
                        "miniature, declaring its own honest-skip "
                        "contract for tests that need a Docker daemon:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-anti-markers-quote",
                    language="toml",
                    caption="Honest skips as declared contract: probe, then skip loudly, never silently pass.",
                    source="server/pyproject.toml",
                    snippet=(
                        "[tool.pytest.ini_options]\n"
                        "asyncio_mode = \"auto\"\n"
                        "testpaths = [\"tests\"]\n"
                        "markers = [\n"
                        "    # Spins a REAL throwaway PostgreSQL via Docker (testcontainers). The\n"
                        "    # dev/verify container has no docker.sock, so these tests probe for a\n"
                        "    # reachable Docker daemon and SKIP (with the reason) when there is\n"
                        "    # none; the host-run fallback command (docker.sock + TESTCONTAINERS_\n"
                        "    # HOST_OVERRIDE mounted, `pytest -m testcontainers`) runs them for real.\n"
                        "    \"testcontainers: needs a reachable Docker daemon (host-run fallback run)\",\n"
                        "]"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="best:checklist",
                    title="The best-practices self-audit",
                    description=(
                        "GET /api/demo/best/checklist serves an "
                        "interactive self-audit of the running app and "
                        "the repo it lives in. Ten practice areas (setup, "
                        "API discipline, security, data, reliability, "
                        "observability, performance, operations, git and "
                        "review, human practices), each row a verdict "
                        "COMPUTED AT REQUEST TIME: 'live' rows drive real "
                        "self-requests through this very application — "
                        "security headers found on a 200 AND on a 404, "
                        "the envelope's requestId matching its header, a "
                        "422 from an invalid POST, OpenAPI generating, "
                        "health answering — with the evidence lines "
                        "carried verbatim; 'file' rows read the repo for "
                        "real (pyproject parsed for ruff families and "
                        "mypy strict, the alembic chain walked revision "
                        "by revision, uv.lock parsed, sources scanned); "
                        "'manual' rows are the practices no automation "
                        "can judge and claim nothing, each with a "
                        "one-line why. The anti-checklist rides along: "
                        "the repo's deliberate not-does with reasons and "
                        "real artifacts. A summary line counts pass, "
                        "fail, and manual — and the honesty note on the "
                        "panel explains exactly how every verdict was "
                        "earned."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-anti-panel-reading",
                    text=(
                        "Reading the panel against the live stack is the "
                        "point: the live rows pass because the running "
                        "app really does stamp headers on error "
                        "responses and echo request ids; the file rows "
                        "pass because the manifest really is strict and "
                        "the migration chain really is linked; and the "
                        "manual rows stay manual — on the server "
                        "container, where the repo root is not mounted, "
                        "the compose and dockerignore rows say so in as "
                        "many words. The router serving it is as thin as "
                        "every other demo router in the stack — the "
                        "audit's machinery lives in the domain, the "
                        "handler only hands it the app and the honest "
                        "roots:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-anti-router-quote",
                    language="py",
                    caption="The audit endpoint: pure payload, declared response model, honest roots.",
                    source="server/guide/presentation/routers/demo/best.py",
                    snippet=(
                        "@router.get(CHECKLIST_PATH, response_model=BestChecklistPanel)\n"
                        "async def read_best_checklist(request: Request) -> BestChecklistPanel:\n"
                        "    \"\"\"Serve the live self-audit: probes, file reads, honest manuals.\"\"\"\n"
                        "    server_root, repo_root = default_roots()\n"
                        "    return await build_best_checklist_payload(\n"
                        "        app=request.app,\n"
                        "        server_root=server_root,\n"
                        "        repo_root=repo_root,\n"
                        "    )"
                    ),
                ),
            ],
        ),
        # ── 12. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The practices from a shell: audit the live app, verify the repo, read the decisions.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bp-terminal-intro",
                    text=(
                        "Six stops: the curriculum this capstone closes, "
                        "the audit panel and its verdict counts, the "
                        "evidence and the honest manuals up close, the "
                        "verify one-liner that IS this repo's gate, the "
                        "compose dry-run and friends from the host where "
                        "the repo root lives, and this topic's own "
                        "detail through both ports. The stack is up; "
                        "every command reads the real machinery."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-terminal-curriculum",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the curriculum this capstone closes: the capstones group arrives\n"
                        "curl -s localhost:8000/api/content | python3 -c '\n"
                        "import json, sys\n"
                        "body = json.load(sys.stdin)\n"
                        "print(\"groups:\", [g[\"id\"] for g in body[\"groups\"]])\n"
                        "print(\"topics:\", len(body[\"topics\"]))\n"
                        "print(\"last:\", body[\"topics\"][-1][\"id\"], \"· sections:\", body[\"topics\"][-1][\"sectionCount\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-terminal-audit",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the self-audit: summary line, then verdicts per area\n"
                        "curl -s localhost:8000/api/demo/best/checklist | python3 -c '\n"
                        "import json, sys\n"
                        "body = json.load(sys.stdin)\n"
                        "print(\"summary:\", body[\"summary\"])\n"
                        "for area in body[\"areas\"]:\n"
                        "    counts = {}\n"
                        "    for row in area[\"items\"]:\n"
                        "        counts[row[\"verdict\"]] = counts.get(row[\"verdict\"], 0) + 1\n"
                        "    print(\" \", area[\"id\"].ljust(18), counts)'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-terminal-evidence",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — evidence up close: a live row's proof, and an honest manual's why\n"
                        "curl -s localhost:8000/api/demo/best/checklist | python3 -c '\n"
                        "import json, sys\n"
                        "rows = {r[\"id\"]: r for a in json.load(sys.stdin)[\"areas\"] for r in a[\"items\"]}\n"
                        "for line in rows[\"one-error-envelope\"][\"evidence\"]:\n"
                        "    print(\"live  |\", line)\n"
                        "print(\"manual |\", rows[\"review-your-diffs\"][\"practice\"])\n"
                        "print(\"manual | why:\", rows[\"review-your-diffs\"][\"whyManual\"])'\n"
                        "# the anti-checklist rides the same payload\n"
                        "curl -s localhost:8000/api/demo/best/checklist \\\n"
                        "  | python3 -c 'import json,sys; [print(\"not-do |\", n[\"notDone\"]) for n in json.load(sys.stdin)[\"notDones\"]]'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-terminal-verify",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the repo's actual gate: suite + lint + strict types, one breath\n"
                        "docker exec fastapi_developers_guide_dev bash -lc \\\n"
                        "  'cd /workspaces/fastapi_developers_guide/server && uv run pytest -q && uv run ruff check . && uv run mypy guide'\n"
                        "# client side, same discipline\n"
                        "docker exec fastapi_developers_guide_client_dev bash -lc 'cd /app && npm test && npm run build'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-terminal-host",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — from the HOST (the repo root the server container cannot see):\n"
                        "docker compose -f .docker/docker-compose.yml config > /dev/null && echo \"dev renders\"\n"
                        "docker compose -f .docker/docker-compose.prod.yml config > /dev/null 2>&1 \\\n"
                        "  || echo \"prod refuses without FDG_DB_PASSWORD (the rail, working)\"\n"
                        "grep -c \"env\" .dockerignore && echo \"dockerignore excludes env files\""
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bp-terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — this topic's own detail: demo inline in the anti-checklist, companion last\n"
                        "curl -s localhost:8000/api/content/best-practices | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "print(\"sections:\", len(t[\"sections\"]))\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'\n"
                        "# and through the client's dev proxy, the way the browser reaches it:\n"
                        "curl -s localhost:5174/api/content/best-practices \\\n"
                        "  | python3 -c 'import json,sys; print(\"proxy sections:\", len(json.load(sys.stdin)[\"sections\"]))'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bp-terminal-coda",
                    text=(
                        "Stops 1–3 close the loop this whole guide has "
                        "ridden: the content that teaches the practices, "
                        "served by the app that practices them, audited "
                        "by a panel that proves both — live, with "
                        "evidence, and honest about what it cannot know. "
                        "Stop 4 is the gate every change passes; stop 5 "
                        "is the dry-run the deploy path owes you; stop 6 "
                        "is the capstone reading itself. If the panel is "
                        "green where it claims, manual where it admits, "
                        "and the one-liners still hurt nowhere — the "
                        "practices hold, and the next feature inherits "
                        "them for free."
                    ),
                ),
            ],
        ),
    ],
)
