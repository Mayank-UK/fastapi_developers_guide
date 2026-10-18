"""Topic 34 — Testing: the suite this repo IS, taught in place.

The codebase carries one thousand-plus real tests, the Testcontainers
wiring with its honest in-container skips, the arq live-worker honest
skips, a client vitest suite with its own fetch-stub infrastructure, and
a CI contract that is deliberately LOCAL (docker verify one-liners, no
hosted CI). This topic teaches all of it by quoting it: the pyramid as
the suite actually shapes it, pytest fixtures from the real conftest,
TestClient and the repo's first async-httpx test, Testcontainers as the
clean-database proof, the awkward bits (event loops, DB isolation,
live-dependency honesty), the client's mirror suite, what coverage
would and would not buy, the local-first CI contract, and the deferred
browser E2E. The demo is a RUNNER: it executes curated slices of the
repo's own test files in a real subprocess and returns parsed results —
the suite guarding the app becomes a live exhibit of itself.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="testing",
    title="Testing",
    subtitle=(
        "The pyramid honestly, pytest fixtures, TestClient and async "
        "httpx, Testcontainers against a real throwaway PostgreSQL, the "
        "awkward bits (event loops, DB isolation, live dependencies), the "
        "client's vitest mirror, what coverage buys, the local-first CI "
        "contract, and the browser E2E that is honestly deferred — with a "
        "runner that executes curated slices of this repo's own 1200-test "
        "suite and returns the genuine results."
    ),
    group="platform",
    order=34,
    sections=[
        # ── 1. The pyramid, honestly ───────────────────────────────────────
        Section(
            id="the-pyramid-honestly",
            title="The pyramid, honestly",
            blocks=[
                TextBlock(
                    kind="text",
                    id="pyramid-pitch",
                    text=(
                        "The testing pyramid is usually drawn as a triangle "
                        "with a sermon attached — many unit tests, fewer "
                        "integration tests, a thin cap of end-to-end tests — "
                        "and then real codebases ignore it. This guide's "
                        "position is simpler: the pyramid is a BUDGET "
                        "statement, not a law. Every layer up the pyramid "
                        "costs more to run, more to debug when it fails, and "
                        "more to keep deterministic; every layer down "
                        "narrows what a failure can mean. The honest way to "
                        "teach it is to count what this repo actually "
                        "contains — over twelve hundred server tests whose "
                        "fast bulk is pure unit and in-process integration "
                        "work, a handful of Testcontainers tests that spin "
                        "real databases when Docker is reachable, two tests "
                        "that walk a live worker queue when the stack is "
                        "up, and zero browser E2E (deferred, on purpose, "
                        "to the hardening phase). That distribution IS the "
                        "pyramid, arrived at by cost, not by doctrine."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pyramid-layers-framing",
                    text=(
                        "Read the pyramid as a question you ask of every "
                        "new test — where is the cheapest place this "
                        "confidence can live? The layers, with what each "
                        "buys and what it costs in this repo's own terms:"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pyramid-behavior-pitch",
                    text=(
                        "One principle governs every layer equally, and "
                        "it is the difference between a suite that "
                        "protects refactoring and a suite that prevents "
                        "it: test BEHAVIOR, not implementation. A test "
                        "that asserts on the wire shape — status, "
                        "envelope code, the fields a client reads — "
                        "survives a rewrite of everything beneath; a "
                        "test that asserts on how a result was computed, "
                        "which helper was called, or the identity of a "
                        "mock breaks on every honest improvement and "
                        "teaches the team to distrust it. This repo's "
                        "own suite is audited against that bar: domain "
                        "tests pin outcomes (tamper refused, replay "
                        "out-of-window, retry trail visible), endpoint "
                        "tests pin wire contracts, and nothing anywhere "
                        "asserts a private method was invoked. When a "
                        "test wants to know 'did the cache get "
                        "consulted', the answer is an observable fact "
                        "on the response (the x-cache header), not a "
                        "spy — the assertion reads like the behavior it "
                        "guards."
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="pyramid-layers-list",
                    ordered=False,
                    items=[
                        "Unit tests — pure functions and domain engines "
                        "(the HMAC signer, the retry policy, the negotiation "
                        "engine): microseconds each, run in the thousands, "
                        "pin exact behavior including hostile inputs.",
                        "In-process integration — TestClient or an async "
                        "httpx client over the REAL app: full middleware, "
                        "routing, dependencies, and handlers, no socket; "
                        "this repo's workhorse layer and the bulk of its "
                        "1200.",
                        "Real-dependency integration — Testcontainers "
                        "throwaway PostgreSQL, live Redis, the real Mongo "
                        "client: proof against engines, not mocks of them; "
                        "seconds each, kept few on purpose.",
                        "Live-stack walks — tests that need the compose "
                        "stack's worker process: honest skips when it is "
                        "absent, the full walk when it is up (the arq pair "
                        "is the example).",
                        "Browser E2E — a real browser driving the real "
                        "client against the real server: the most "
                        "expensive confidence per assertion; deferred here "
                        "to Phase 12 rather than faked.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="pyramid-honesty",
                    text=(
                        "The honesty clause matters more than the shape. A "
                        "suite that PRETENDS to have run something it "
                        "skipped is worse than no suite: green lies. This "
                        "repo practices that as a discipline you will meet "
                        "throughout the topic — the Testcontainers tests "
                        "skip with the reason on the wire when no Docker "
                        "socket exists, the live-worker tests skip when no "
                        "worker heartbeat is reachable, and the runner demo "
                        "in the next sections shows those skips LIVE rather "
                        "than smoothing them over. A skip is a fact about "
                        "the environment; a pass is a fact about the code; "
                        "the suite's job is to never confuse the two, and "
                        "yours is to read the skip counts, not just the "
                        "exit code."
                    ),
                ),
            ],
        ),
        # ── 2. pytest fixtures ─────────────────────────────────────────────
        Section(
            id="pytest-fixtures",
            title="pytest fixtures",
            blocks=[
                TextBlock(
                    kind="text",
                    id="fixtures-pitch",
                    text=(
                        "pytest's fixture system is dependency injection "
                        "for tests, and it deserves the same design "
                        "attention the app's composition root gets — the "
                        "same resource, setup once, named, overridable. "
                        "This repo's whole suite rides TWO fixtures "
                        "declared in tests/conftest.py: a fresh application "
                        "per test, and a client bound to it. The app "
                        "fixture is worth reading closely because every "
                        "clause is a lesson: it neutralizes every FDG_* "
                        "environment variable so no test ever depends on "
                        "the host's ambient configuration, it clears the "
                        "config cache around the build so the app under "
                        "test really sees the neutralized world, and it "
                        "yields — setup before, teardown after, the same "
                        "yield-dependency shape topic 6 taught for "
                        "production code:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="fixtures-app-quote",
                    language="py",
                    caption="The suite's root fixture: a fresh app per test, environment-neutral by construction.",
                    source="server/tests/conftest.py",
                    snippet=(
                        "@pytest.fixture\n"
                        "def app(monkeypatch: pytest.MonkeyPatch) -> Iterator[FastAPI]:\n"
                        "    \"\"\"Fresh application per test.\n"
                        "\n"
                        "    Neutralizes every FDG_* env var (tests never depend on the host\n"
                        "    environment) and clears the config cache around each app build.\n"
                        "    \"\"\"\n"
                        "\n"
                        "    for name in [key for key in os.environ if key.startswith(\"FDG_\")]:\n"
                        "        monkeypatch.delenv(name)\n"
                        "    get_config.cache_clear()\n"
                        "    yield create_app()\n"
                        "    get_config.cache_clear()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="fixtures-client-pitch",
                    text=(
                        "The client fixture is the pair — one line of "
                        "meaning, and the reason twelve hundred tests can "
                        "afford a whole application each: TestClient "
                        "drives the app in-process, so a fresh app per "
                        "test costs milliseconds, not a server boot. Note "
                        "what the fixture signature does: it ASKS for the "
                        "app fixture by name, so pytest builds the "
                        "dependency the same way the app itself resolves "
                        "Depends — fixtures compose, and a test that needs "
                        "only the domain layer can ask for nothing heavier:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="fixtures-client-quote",
                    language="py",
                    caption="The suite's second root fixture: TestClient over the per-test app.",
                    source="server/tests/conftest.py",
                    snippet=(
                        "@pytest.fixture\n"
                        "def client(app: FastAPI) -> TestClient:\n"
                        "    \"\"\"Sync HTTP client bound to the per-test app.\"\"\"\n"
                        "    return TestClient(app)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="fixtures-discipline",
                    text=(
                        "Past these two, fixtures in this repo stay "
                        "LOCAL and purpose-shaped: the testcontainers "
                        "module owns its container fixture (next section), "
                        "the jobs tests own a redis-backed client that "
                        "resets the queue in teardown, the auth tests mint "
                        "credentials through the domain's own services. "
                        "The discipline worth copying: a fixture may build "
                        "or borrow state, but it never hides MEANING — a "
                        "test that reads ``client.get(...)`` should need "
                        "no ceremony to understand, because the fixture "
                        "gave it exactly one thing (a real app) and "
                        "nothing implicit. When you find yourself "
                        "threading a fixture through four levels of "
                        "indirection, that is usually the sign the test "
                        "wants a narrower subject, not a wider fixture."
                    ),
                ),
            ],
        ),
        # ── 3. TestClient and async httpx ──────────────────────────────────
        Section(
            id="httpx-testclient",
            title="TestClient and async httpx",
            lead="This section carries the topic's demo — the testing runner.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="testclient-pitch",
                    text=(
                        "TestClient is not a mock of HTTP — it IS "
                        "httpx.Client mounted on Starlette's ASGI transport, "
                        "calling your app's ``__call__`` directly with no "
                        "socket anywhere. Everything real stays real: the "
                        "middleware stack runs in order, routing matches "
                        "templates, dependencies resolve, exception handlers "
                        "answer, and the response you assert on is the "
                        "response the app would serialize. The security "
                        "middleware tests are the canonical example of the "
                        "style — asserting on the REAL wire shape of a "
                        "failure path, because the 404 envelope is exactly "
                        "what an attacker probes:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="testclient-quote",
                    language="py",
                    caption="Integration at the HTTP edge, in-process: the real envelope, the real headers.",
                    source="server/tests/test_security_middleware.py",
                    snippet=(
                        "def test_security_headers_are_on_the_404_envelope(client: TestClient) -> None:\n"
                        "    response = client.get(\"/api/nope\")\n"
                        "    assert response.status_code == 404\n"
                        "    assert response.json()[\"error\"][\"code\"] == \"not_found\"\n"
                        "    _assert_static_headers(response.headers)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="async-httpx-pitch",
                    text=(
                        "The async half of the story matters as soon as "
                        "the subject is concurrency. TestClient is sync "
                        "(it runs the app on a portal thread); when a test "
                        "itself must be async — awaiting app internals, "
                        "interleaving requests on ONE event loop — the "
                        "repo's answer is httpx.AsyncClient over an "
                        "ASGITransport, exactly what a live server's "
                        "transport does minus the socket. The testing "
                        "runner's own off-loop proof is the exemplar: it "
                        "fires the demo's subprocess-backed run endpoint "
                        "and a health probe CONCURRENTLY, then fails if "
                        "the probe could not land mid-run — a blocking "
                        "subprocess on the event loop would serialize the "
                        "two requests and collapse the ratio:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="async-httpx-quote",
                    language="py",
                    caption="The repo's first ASGI-transport async client test: concurrency as the assertion.",
                    source="server/tests/demo/test_testing_runner_endpoint.py",
                    snippet=(
                        "    transport = httpx.ASGITransport(app=app)\n"
                        "    async with httpx.AsyncClient(transport=transport, base_url=\"http://testserver\") as async_client:\n"
                        "        run_started = time.perf_counter()\n"
                        "        run_task = asyncio.create_task(async_client.post(UNIT_PURE_RUN))\n"
                        "        await asyncio.sleep(0.10)  # let the subprocess spawn\n"
                        "        probe_started = time.perf_counter()\n"
                        "        probe = await async_client.get(\"/api/health\")\n"
                        "        probe_ms = (time.perf_counter() - probe_started) * 1000\n"
                        "        run = await run_task\n"
                        "        run_ms = (time.perf_counter() - run_started) * 1000\n"
                        "\n"
                        "    assert probe.status_code == 200\n"
                        "    assert run.json()[\"outcome\"] == \"passed\"\n"
                        "    assert probe_ms < run_ms / 2, (\n"
                        "        f\"the health probe took {probe_ms:.0f}ms of a {run_ms:.0f}ms run — \"\n"
                        "        \"the subprocess is blocking the event loop\"\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="runner-engine-pitch",
                    text=(
                        "The demo below puts the whole section to work. "
                        "Its run endpoint executes a curated slice of THIS "
                        "repository's test files — the roster is frozen: "
                        "pure unit, conftest fixtures with TestClient, "
                        "async-native, and the testcontainers file — in a "
                        "real subprocess whose argv the engine builds and "
                        "you can read, whose environment carries the "
                        "recursion-guard marker, and whose output is "
                        "parsed, never composed:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="runner-engine-quote",
                    language="py",
                    caption="The runner's engine: real argv, guard env, off the loop (the router awaits to_thread).",
                    source="server/guide/domain/demos/testing_runner.py",
                    snippet=(
                        "    argv = [\n"
                        "        sys.executable,\n"
                        "        \"-m\",\n"
                        "        \"pytest\",\n"
                        "        *_PYTEST_FLAGS,\n"
                        "        *(_server_relative(path) for path in slice_.paths),\n"
                        "    ]\n"
                        "    command_line = \" \".join(argv)\n"
                        "    env = {**os.environ, RUNNER_CHILD_ENV: \"1\"}"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="testing:runner",
                    title="The testing runner",
                    description=(
                        "GET /api/demo/testing serves the roster; POST "
                        "/api/demo/testing/run/{sliceId} executes one "
                        "curated slice of the repo's own suite for real — "
                        "a subprocess pytest over the server venv (cwd "
                        "server/, hard 90s timeout, off the event loop "
                        "via asyncio.to_thread) with the summary and "
                        "per-test lines parsed into typed results. Fire "
                        "the testcontainers slice inside this container "
                        "and watch every test SKIP with the reason — the "
                        "honest shape, since there is no docker.sock here; "
                        "the host-run fallback runs them for real. The "
                        "client's vitest suite rides as a recipe row (its "
                        "docker exec command), never a faked run. The "
                        "recursion guard is proven in both directions: "
                        "the wire accepts only roster ids, and a "
                        "runner-started pytest carries "
                        "FDG_TEST_RUNNER_CHILD, on which the runner's own "
                        "tests skip themselves."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="runner-guard-pitch",
                    text=(
                        "A runner that is itself tested has a known trap: "
                        "recursion. If the endpoint's own tests could be "
                        "reached by a run they triggered, pytest would "
                        "spawn pytest would spawn pytest. This repo guards "
                        "it twice, and the tests prove both walls: the "
                        "wire accepts a slice ID validated against a "
                        "frozen roster — no request can steer a path at "
                        "the runner's own files — and every runner-started "
                        "pytest carries an env marker on which the "
                        "runner's test modules skip themselves:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="runner-guard-quote",
                    language="py",
                    caption="Guard wall two: a process already marked as a runner child refuses to nest.",
                    source="server/guide/presentation/routers/demo/testing.py",
                    snippet=(
                        "    if os.environ.get(RUNNER_CHILD_ENV):\n"
                        "        raise AppError(\n"
                        "            FailureKind.CONFLICT,\n"
                        "            \"This process is already a runner-started child — refusing to nest pytest runs.\",\n"
                        "            details={\"guardEnv\": RUNNER_CHILD_ENV},\n"
                        "        )"
                    ),
                ),
            ],
        ),
        # ── 4. Testcontainers ─────────────────────────────────────────────
        Section(
            id="testcontainers",
            title="Testcontainers",
            blocks=[
                TextBlock(
                    kind="text",
                    id="testcontainers-pitch",
                    text=(
                        "Mocks cannot lie to you about SQL — only a real "
                        "database can tell you your migration forgets a "
                        "constraint, your ORM emits a second SELECT, or "
                        "your optimistic lock never fires. Testcontainers "
                        "is the pattern that makes real-database testing "
                        "affordable: the test itself starts a throwaway "
                        "container (here PostgreSQL 17, the same major "
                        "version the stacks run), points the code at it, "
                        "and the container dies with the test. This "
                        "repo's wiring is the reference: topic 18's "
                        "clean-database round-trip spins a fresh "
                        "PostgreSQL, applies the FULL Alembic chain from "
                        "zero, and proves create, eager load, version "
                        "bump, and stale-write refusal on a database "
                        "nobody seeded by hand."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="testcontainers-honest-skip-pitch",
                    text=(
                        "The honest part is the gate. These tests need a "
                        "REACHABLE Docker daemon; the dev and verify "
                        "containers mount no docker.sock, so a module-level "
                        "probe runs first and every test in the file skips "
                        "with the reason when the probe fails — the "
                        "in-container suite stays green without pretending. "
                        "The host-run fallback command (docker.sock + "
                        "TESTCONTAINERS_HOST_OVERRIDE mounted, ``pytest -m "
                        "testcontainers``) is where the probe passes and "
                        "the same tests run for real. The gate is two "
                        "lines of pytest, and the marker beside it is "
                        "registered in pyproject so the fallback can "
                        "select exactly these tests:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="testcontainers-gate-quote",
                    language="py",
                    caption="The honest gate: probe, then module-wide skipif with the reason on the wire.",
                    source="server/tests/data/test_orm_testcontainers.py",
                    snippet=(
                        "DOCKER_OK, DOCKER_SKIP_REASON = _docker_reachable()\n"
                        "\n"
                        "pytestmark = [\n"
                        "    pytest.mark.testcontainers,\n"
                        "    pytest.mark.skipif(not DOCKER_OK, reason=DOCKER_SKIP_REASON),\n"
                        "]\n"
                        "\n"
                        "\n"
                        "@pytest.fixture\n"
                        "def container_url() -> Iterator[str]:\n"
                        "    \"\"\"One throwaway PostgreSQL; its asyncpg URL is the whole fixture.\"\"\"\n"
                        "    with PostgresContainer(POSTGRES_IMAGE) as postgres:\n"
                        "        # testcontainers hands out a psycopg2 URL; the guide speaks asyncpg.\n"
                        "        yield postgres.get_connection_url().replace(\"+psycopg2\", \"+asyncpg\")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="testcontainers-async-fixture-pitch",
                    text=(
                        "The next fixture up the chain shows the async "
                        "pattern these tests ride: pytest-asyncio runs "
                        "async fixtures natively, and the one genuinely "
                        "blocking step — applying migrations — is pushed "
                        "to a worker thread with the same "
                        "``asyncio.to_thread`` the runner demo uses. "
                        "Setup, yield, dispose in a finally: the "
                        "container's lifetime is the fixture's lifetime, "
                        "and teardown is guaranteed even when a test "
                        "fails:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="testcontainers-engine-quote",
                    language="py",
                    caption="Async fixture, blocking step off the loop, disposal in finally.",
                    source="server/tests/data/test_orm_testcontainers.py",
                    snippet=(
                        "@pytest.fixture\n"
                        "async def engine(container_url: str) -> AsyncEngine:\n"
                        "    \"\"\"Engine over the throwaway container, migrations applied to head.\"\"\"\n"
                        "    await asyncio.to_thread(upgrade_database_to_head, container_url)\n"
                        "    engine = create_async_engine(container_url, pool_pre_ping=True)\n"
                        "    try:\n"
                        "        yield engine\n"
                        "    finally:\n"
                        "        await engine.dispose()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="testcontainers-fallback-pitch",
                    text=(
                        "The fallback run deserves its own sentence, "
                        "because it is the pattern for running "
                        "Docker-needing tests from inside a Docker "
                        "workflow: mount the host's docker.sock so the "
                        "test process can start siblings, set "
                        "TESTCONTAINERS_HOST_OVERRIDE so the container's "
                        "advertised localhost resolves to the HOST's "
                        "loopback where the published ports actually "
                        "live, carry the named uv cache volume so the "
                        "environment is warm, and flock the bind mount "
                        "so two verification runs cannot interleave. "
                        "The result is one command that runs the real "
                        "PostgreSQL tests for real — no second suite to "
                        "maintain, no 'works in CI only' class of "
                        "mystery, and the same marker the pyproject "
                        "registered selecting exactly the tests the "
                        "socket enables. Run it before trusting a "
                        "migration; skip it on a plane."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="testcontainers-when",
                    text=(
                        "When to reach for this layer: when the thing under "
                        "test is the SHAPE of data access — migrations, "
                        "dialect quirks, transaction and locking behavior, "
                        "query plans — and a mock would merely replay your "
                        "assumptions back at you. This repo keeps exactly "
                        "one module in the class, because the migrations "
                        "and the ORM's loading/locking behavior are the "
                        "only subjects where only PostgreSQL will do; "
                        "everything data-shaped but engine-agnostic rides "
                        "the cheaper in-process layers. That restraint is "
                        "the pyramid budget again: a Testcontainers test "
                        "that only proves your own mock discipline is a "
                        "slow unit test wearing a container."
                    ),
                ),
            ],
        ),
        # ── 5. The awkward bits ────────────────────────────────────────────
        Section(
            id="awkward-bits",
            title="The awkward bits: async, loops, isolation",
            blocks=[
                TextBlock(
                    kind="text",
                    id="awkward-pitch",
                    text=(
                        "Async testing has a small set of traps that eat "
                        "an afternoon each the first time, and this repo "
                        "has already paid them — each with the fix wired "
                        "and quotable. The first is mechanical: async "
                        "tests need an event loop, and decorating every "
                        "test is noise the suite removes once, globally, "
                        "in pyproject — ``asyncio_mode = \"auto\"`` makes "
                        "every ``async def test`` just work, and the "
                        "testcontainers marker registered beside it is "
                        "how the host-run fallback selects its slice:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="awkward-pytest-config-quote",
                    language="toml",
                    caption="The suite's own config: auto mode for async tests, the marker the fallback selects.",
                    source="server/pyproject.toml",
                    snippet=(
                        "[tool.pytest.ini_options]\n"
                        "asyncio_mode = \"auto\"\n"
                        "testpaths = [\"tests\"]\n"
                        "markers = [\n"
                        "    # …\n"
                        "    \"testcontainers: needs a reachable Docker daemon (host-run fallback run)\",\n"
                        "]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="awkward-loop-pitch",
                    text=(
                        "The second trap is the loop-LIFETIME mismatch: "
                        "resources that bind to the loop they were created "
                        "on (redis pools, motor clients — topic 19 "
                        "measured this) break when a fixture-built client "
                        "meets a different test's loop. The suite's rule: "
                        "per-test apps already isolate the loop, and any "
                        "helper that must survive re-entry is built "
                        "loop-independent — the live-worker tests reuse "
                        "the dev stack's redis through a factory for "
                        "exactly this reason. The third trap is the "
                        "live-dependency lie: a test needing the real "
                        "arq worker could mock the walk and prove "
                        "nothing. Instead it probes the worker's OWN "
                        "heartbeat key and says what it found:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="awkward-live-worker-quote",
                    language="py",
                    caption="The live-worker honesty: probe, skip with the reason, or walk the real queue.",
                    source="server/tests/demo/test_jobs_live_worker.py",
                    snippet=(
                        "async def test_fail_once_retries_to_completion_with_a_live_worker() -> None:\n"
                        "    live = await _live_worker()\n"
                        "    if live is None:\n"
                        "        pytest.skip(\"no reachable redis with an arq worker heartbeat (compose arq-worker service)\")\n"
                        "    await live.aclose()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="awkward-isolation-framing",
                    text=(
                        "The remaining awkward bits are isolation "
                        "problems, and the suite's answers to each are "
                        "small enough to list — the trap, then the wired "
                        "fix you can go read:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="awkward-isolation-list",
                    ordered=False,
                    items=[
                        "Ambient state across tests — the request-id "
                        "contextvar survives a test's unwinding; the "
                        "conftest clears it before and after every test "
                        "(an autouse fixture, one purpose).",
                        "Environment bleed — an FDG_* var exported in "
                        "one shell changes every app build after it; "
                        "the app fixture neutralizes all of them per "
                        "test.",
                        "Shared mutable stores — demos that write the "
                        "live PG (the outbox) ride per-test cleanup "
                        "janitors, and pins self-heal to seeded state "
                        "instead of assuming emptiness.",
                        "Clock-dependent logic — fixed test clocks "
                        "derive from the wall clock, never future "
                        "instants (the auth topic's lesson, wired into "
                        "its fixtures).",
                        "TestClient re-raising — the sync client "
                        "re-raises unhandled exceptions by default; "
                        "injected-500 tests pass "
                        "raise_server_exceptions=False and assert the "
                        "envelope instead.",
                    ],
                ),
            ],
        ),
        # ── 6. Client testing ─────────────────────────────────────────────
        Section(
            id="client-testing",
            title="Client testing",
            blocks=[
                TextBlock(
                    kind="text",
                    id="client-pitch",
                    text=(
                        "The client is a presentation shell, but it has "
                        "real failure modes of its own — wire drift, "
                        "malformed payloads, status codes that never "
                        "ride the JSON pipeline — and its vitest suite "
                        "(437 tests at this writing) guards them with "
                        "the same Result discipline the server uses. "
                        "The heart is a piece of shared test "
                        "infrastructure: a URL-dispatching fetch stub "
                        "that answers JSON per route, fails LOUDLY on "
                        "an unstubbed URL (a missing mock is a 404 "
                        "envelope, never a hang), and can break json() "
                        "on demand for the non-JSON path:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="client-stub-quote",
                    language="ts",
                    caption="The client suite's fetch stub: routes answer, unstubbed URLs fail loudly.",
                    source="client/src/test/fetch_stub.ts",
                    snippet=(
                        "export function stubApiFetch(routes: readonly StubRoute[]): void {\n"
                        "  vi.stubGlobal(\n"
                        "    'fetch',\n"
                        "    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {\n"
                        "      const url = typeof input === 'string' ? input : input.toString();\n"
                        "      const method = init?.method ?? 'GET';\n"
                        "      const route = routes.find(\n"
                        "        (candidate) =>\n"
                        "          candidate.url === url &&\n"
                        "          (candidate.method === undefined || candidate.method === method),\n"
                        "      );\n"
                        "      if (route === undefined) {\n"
                        "        return jsonResponse(\n"
                        "          {\n"
                        "            error: {\n"
                        "              code: 'not_found',\n"
                        "              message: `no fetch stub for ${method} ${url}`,\n"
                        "              requestId: 'stub',\n"
                        "            },\n"
                        "          },\n"
                        "          404,\n"
                        "        );\n"
                        "      }"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="client-spec-pitch",
                    text=(
                        "On top of the stub, the repository specs read "
                        "exactly like the server's integration tests "
                        "read — stub the wire, run the real adapter "
                        "stack, assert on the parsed domain shape and "
                        "the Failed Results — and the demo component "
                        "specs swap container tokens instead of "
                        "stubbing fetch, which is the client-side "
                        "equivalent of dependency_overrides. The "
                        "pattern in one honest slice:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="client-spec-quote",
                    language="ts",
                    caption="A repository spec: stub the wire, run the real adapter, assert the parsed shape.",
                    source="client/src/data/demo/db-search-repository-impl.spec.ts",
                    snippet=(
                        "function makeRepository(): DbSearchRepositoryImpl {\n"
                        "  return new DbSearchRepositoryImpl(new DbSearchApi(createAppConfig()));\n"
                        "}\n"
                        "\n"
                        "describe('DbSearchRepositoryImpl', () => {\n"
                        "  it('fetches and parses the ranked payload with both plans', async () => {\n"
                        "    stubApiFetch([{ url: SEARCH_URL, method: 'GET', body: payload }]);"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="client-coverage-map",
                    text=(
                        "What the client suite actually covers is worth "
                        "a map, because it is the mirror of the "
                        "server's: the DTO validators are tested "
                        "adversarially (every fromJson throws on "
                        "wrong-typed, missing, and unknown shapes), "
                        "the repository impls prove that transport "
                        "failures resolve as Failed Results rather "
                        "than rejections, the guards pin the envelope "
                        "paths (non-2xx, non-JSON, network-down) with "
                        "the stub's broken-json mode, and every demo "
                        "component has a spec that swaps its container "
                        "token for a fake — the happy render, the "
                        "per-click call count, and the error-panel "
                        "recovery round trip. Nothing in the client "
                        "tests React itself; everything tests what "
                        "THIS client can get wrong about its server, "
                        "which is the whole job of a presentation "
                        "shell's suite."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="client-drift-lesson",
                    text=(
                        "One lesson from this repo's history belongs in "
                        "every memory: fixture-driven client specs pass "
                        "while the real wire drifts — the Phase 1 wire-"
                        "drift bug shipped exactly that way (a missing "
                        "version field every fixture innocently "
                        "omitted). The standing cures are the ones this "
                        "suite now practices: server-side tests pin "
                        "FULL payload shapes, DTO fromJson validators "
                        "throw on unknown shapes rather than coercing, "
                        "and every phase close runs one real topic page "
                        "through the actual stack. The browser-level "
                        "version of that cure is the deferred E2E "
                        "suite at the end of this topic."
                    ),
                ),
            ],
        ),
        # ── 7. Coverage ───────────────────────────────────────────────────
        Section(
            id="coverage",
            title="Coverage",
            blocks=[
                TextBlock(
                    kind="text",
                    id="coverage-pitch",
                    text=(
                        "Coverage tools count which lines your tests "
                        "executed, and the honest starting point is what "
                        "that number CANNOT tell you: not whether the "
                        "assertions are strong, not whether the edge "
                        "cases exist, not whether the behavior is right — "
                        "only whether execution passed through. A suite "
                        "can tour every line asserting nothing and report "
                        "100 percent. This repo deliberately runs without "
                        "a coverage gate today (the hardening phase lists "
                        "one), and the interim discipline is stronger "
                        "than a percentage: every new endpoint ships with "
                        "pytest cases by standing rule, every teaching "
                        "claim is quoted from real code a ratchet test "
                        "verifies, and failure paths are asserted as "
                        "wire shapes, not exceptions."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="coverage-uses-framing",
                    text=(
                        "Where coverage genuinely earns its keep, it is "
                        "as a DIFFERENCE instrument rather than a score — "
                        "the uses worth keeping when a gate eventually "
                        "lands:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="coverage-uses-list",
                    ordered=False,
                    items=[
                        "Diff review — the lines a change added but no "
                        "test touched: the cheapest possible 'did you "
                        "forget a case' checklist, per pull request.",
                        "Dead-code detection — modules nothing executes "
                        "are suspects for deletion long before they are "
                        "suspects for testing.",
                        "Regression triage — a bug's repro test should "
                        "light up exactly the lines that failed; if the "
                        "diff of executed lines is surprising, the repro "
                        "is testing something else.",
                        "Branch (not line) reads — line coverage hides "
                        "untaken else-paths; branch coverage is the "
                        "only flavor worth gating on.",
                        "Thresholds as ratchets — a gate that only "
                        "forbids going DOWN, never demands a number: "
                        "monotone improvement without Goodhart pressure.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="coverage-coda",
                    text=(
                        "The failure mode to remember is metric capture: "
                        "the moment a coverage percentage becomes a "
                        "target, tests degenerate into line-touching "
                        "ceremony, and the suite's real job — pinning "
                        "behavior, especially failure behavior — is "
                        "quietly abandoned. This repo's pyramid is held "
                        "by review and by the per-feature testing rules, "
                        "and any future coverage gate will be shaped as "
                        "a ratchet on branch coverage, not a floor on "
                        "line coverage, precisely to keep the incentive "
                        "pointed at assertions rather than execution."
                    ),
                ),
            ],
        ),
        # ── 8. The CI contract ────────────────────────────────────────────
        Section(
            id="ci-contract",
            title="The CI contract",
            blocks=[
                TextBlock(
                    kind="text",
                    id="ci-pitch",
                    text=(
                        "This repo's continuous-integration posture is a "
                        "deliberate family decision, not an omission: NO "
                        "hosted CI by default. The spring-boot sibling "
                        "removed theirs by developer choice, and this "
                        "guide starts in that posture — the verify "
                        "one-liners below are the ONLY gate, and they "
                        "run the same suites, linters, and type checks a "
                        "hosted runner would, inside the same containers "
                        "the dev stack already keeps alive. The trade is "
                        "honest: you lose the unreachable-runner "
                        "guarantee and the PR-status badge, and you gain "
                        "a gate that is always local, always warm, and "
                        "never a queue — for a single-developer "
                        "reference repo, that is the right side of the "
                        "trade. Adding hosted CI later is an explicit "
                        "request away, not a migration."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ci-commands-pitch",
                    text=(
                        "The contract, verbatim — server side first "
                        "(full suite, lint, strict types), then the "
                        "client (tests plus a production build):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="ci-server-commands",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the server gate: suite + lint + strict mypy, in the long-lived dev container\n"
                        "docker exec fastapi_developers_guide_dev bash -lc \\\n"
                        "  'cd /workspaces/fastapi_developers_guide/server && uv run pytest -q && uv run ruff check . && uv run mypy guide'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="ci-client-commands",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the client gate: vitest suite + production build\n"
                        "docker exec fastapi_developers_guide_client_dev bash -lc \\\n"
                        "  'cd /app && npm test && npm run build'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ci-discipline",
                    text=(
                        "Two disciplines make the local gate real "
                        "rather than aspirational. Parallel verifications "
                        "flock the bind mount so concurrent runs cannot "
                        "corrupt each other's caches — a lesson the "
                        "spring guide paid in container churn — and "
                        "verification rides the LONG-LIVED containers "
                        "instead of minting ephemeral ones per check, "
                        "which is why the one-liners above finish in "
                        "seconds warm. The Testcontainers fallback "
                        "carries the same shape with the docker socket "
                        "mounted, so even the 'clean database' layer of "
                        "the pyramid has a one-command local gate. When "
                        "a hosted CI does arrive, these commands ARE "
                        "the pipeline — the contract was designed so "
                        "there is nothing to translate."
                    ),
                ),
            ],
        ),
        # ── 9. Browser E2E ────────────────────────────────────────────────
        Section(
            id="browser-e2e",
            title="Browser E2E",
            blocks=[
                TextBlock(
                    kind="text",
                    id="e2e-pitch",
                    text=(
                        "The pyramid's top layer here is honestly empty: "
                        "no Playwright suite runs today, and the "
                        "repository says so instead of pretending — the "
                        "planned host-run e2e/ directory is a hardening-"
                        "phase item, taken only on explicit request. "
                        "Why deferred: the client is a presentation "
                        "shell over a typed content API it validates "
                        "strictly, the server pins the full wire shapes "
                        "it serves, and scripted curls against the "
                        "running stack already cover the seams a "
                        "browser would walk — so the expensive layer "
                        "buys the least marginal confidence per minute "
                        "of THIS repo's time. The cost being deferred "
                        "is real too: flake management, wait discipline, "
                        "and a second runtime to keep green."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="e2e-interim",
                    text=(
                        "What the repo does INSTEAD is the scripted-smoke "
                        "discipline you have seen cited in every phase: "
                        "at each close, curl the real stack through both "
                        "the server port and the client's dev proxy, "
                        "assert the payload shapes (topic counts, demo "
                        "placement, envelopes with request ids), and — "
                        "when a fix is user-facing — drive the real "
                        "browser by hand with one learned technique "
                        "worth recording: wait for content before "
                        "judging, because rapid navigation can snapshot "
                        "an empty page and manufacture a bug that does "
                        "not exist. That lesson, plus the wire-drift "
                        "story from the client-testing section, is the "
                        "seed from which the future e2e suite will grow: "
                        "one topic page, through the real client, "
                        "asserting rendered sections — a thin cap, "
                        "added the day the budget says so."
                    ),
                ),
            ],
        ),
        # ── 10. Terminal companion ────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The suite from a shell: run slices, read skips, gate the repo.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Six stops: the roster, a real run of the pure "
                        "unit slice, the testcontainers slice showing "
                        "its honest skips, the client's vitest recipe "
                        "row, the two verify one-liners that ARE the CI "
                        "contract, and this topic's own content detail. "
                        "The stack is up; every command answers from "
                        "the machinery this topic taught."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-roster",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the roster: four curated slices, the recipe, the guard facts\n"
                        "curl -s localhost:8000/api/demo/testing \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print([s[\"sliceId\"] for s in b[\"slices\"]]); \\\n"
                        "print(\"guard:\", b[\"facts\"][\"guardEnv\"], \"| timeout:\", b[\"facts\"][\"timeoutSeconds\"]); \\\n"
                        "print(\"recipe:\", b[\"clientRecipe\"][\"command\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-run",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — a REAL run: genuine pytest output for the pure unit slice\n"
                        "curl -s -X POST localhost:8000/api/demo/testing/run/unit-pure \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(b[\"outcome\"], \"| passed:\", b[\"passed\"], \"| wall:\", b[\"durationMs\"], \"ms\"); \\\n"
                        "print(\"pytest says:\", b[\"summaryLine\"]); \\\n"
                        "print(\"first test:\", b[\"testLines\"][0][\"nodeid\"], b[\"testLines\"][0][\"outcome\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-skips",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the honesty exhibit: no docker.sock here, so every test skips\n"
                        "curl -s -X POST localhost:8000/api/demo/testing/run/testcontainers-skips \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"outcome:\", b[\"outcome\"], \"| passed:\", b[\"passed\"], \"| skipped:\", b[\"skipped\"]); \\\n"
                        "print(b[\"summaryLine\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-guard",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the boundary: unknown slice is the 404 envelope, roster named\n"
                        "curl -s -X POST localhost:8000/api/demo/testing/run/nope \\\n"
                        "  | python3 -c 'import json,sys; e=json.load(sys.stdin)[\"error\"]; print(e[\"code\"], \"|\", e[\"message\"][:60])'\n"
                        "# the client suite, honestly a recipe (run it in the client container):\n"
                        "docker exec fastapi_developers_guide_client_dev bash -lc 'cd /app && npm test' | tail -4"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-gates",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the CI contract itself: the only gates this repo keeps\n"
                        "docker exec fastapi_developers_guide_dev bash -lc \\\n"
                        "  'cd /workspaces/fastapi_developers_guide/server && uv run pytest -q && uv run ruff check . && uv run mypy guide'\n"
                        "docker exec fastapi_developers_guide_client_dev bash -lc 'cd /app && npm test && npm run build'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — this topic's own detail, demo inline in the httpx-testclient section\n"
                        "curl -s localhost:8000/api/content/testing | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "print(\"sections:\", len(t[\"sections\"]))\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'\n"
                        "# and through the client's dev proxy, the way the browser reaches it:\n"
                        "curl -s localhost:5174/api/content/testing | python3 -c 'import json,sys; print(\"proxy sections:\", len(json.load(sys.stdin)[\"sections\"]))'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stops 1–3 are the demo doing its one job: real "
                        "subprocess rounds with genuine counts, and a "
                        "skip row that says out loud what this container "
                        "cannot do. Stop 4 reads the boundary the "
                        "recursion guard keeps and runs the client's "
                        "suite where it actually lives. Stop 5 is the "
                        "whole CI contract in two lines — everything a "
                        "hosted runner would run, run where you already "
                        "are. Stop 6 closes the loop the guide always "
                        "closes: the topic that taught the suite is "
                        "itself served, tested, and pinned by it."
                    ),
                ),
            ],
        ),
    ],
)
