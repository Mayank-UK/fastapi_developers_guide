"""Topic 39 — Reliability: surviving the failure of everything you call.

Performance asked how fast the steady state is; this topic asks what
happens when the steady state ends — the dependency that hangs, the pool
that exhausts, the retry storm, the race that double-charges. Everything
quoted here is this repository's real reliability machinery: the bounded
optional-service timeouts in the data layer, the two pure retry engines
(jobs and webhooks) and the arq worker that executes their verdicts, the
circuit-breaker substrate this topic adds in ``domain/reliability``, the
optional-service 503 degradation, the rate-limit and realtime ceilings as
bulkheads and shedding, the scenario store's failure injection as the
chaos lever, and the row-lock and idempotence answers to the races
retries create. The demo is reliability:breaker, INLINE in the
circuit-breaker section, and every verdict it serves was returned by the
real substrate on the request that served it.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="reliability",
    title="Reliability",
    subtitle=(
        "Surviving distributed failure: why networks lie and calls hang, "
        "the timeouts that bound every optional-service call this repo "
        "makes, the two real retry engines and their poison classification, "
        "a real circuit breaker walked through one full cycle (closed → "
        "open → half-open → closed) with fail-fast latency evidence, the "
        "503 degradation that keeps the app serving when a store is down, "
        "bulkheads and load shedding from the rate limiter's 429 to the "
        "realtime ceilings, failure injection as chaos rehearsal, and the "
        "row-lock and idempotence answers to the races retries create."
    ),
    group="ship",
    order=39,
    sections=[
        # ── 1. distributed failure ────────────────────────────────────────
        Section(
            id="distributed-failure",
            title="Distributed failure",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rel-df-pitch",
                    text=(
                        "Every topic before this one could pretend the world "
                        "is one program, because within one process a "
                        "function call either returns or raises — there is "
                        "no third option. The moment a request leaves the "
                        "process — this server calling PostgreSQL, Redis, "
                        "MongoDB, or the gRPC satellite; the client calling "
                        "this server — a third option appears: the call "
                        "hangs. The peer accepted the connection and then "
                        "went silent; the packet is in flight forever; the "
                        "server is up but the one worker that would answer "
                        "you is parked on someone else's hung call. "
                        "Reliability engineering is the discipline of "
                        "designing for that third option, and this topic "
                        "walks the toolbox in the order you reach for it: "
                        "bound the call (timeouts), retry the transient "
                        "ones carefully, stop calling what keeps failing "
                        "(the circuit breaker), keep serving without the "
                        "failed piece (degradation), refuse work you cannot "
                        "do well (bulkheads and shedding), rehearse all of "
                        "it on purpose (chaos), and handle the races the "
                        "retries create."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-df-fallacies-pitch",
                    text=(
                        "The classic framing is the fallacies of "
                        "distributed computing — the assumptions every "
                        "engineer imports from single-process life that are "
                        "all false. They were cataloged at Sun Microsystems "
                        "in the nineties and have outlived every technology "
                        "they were written about, because they are not "
                        "about technology: they are about what a network "
                        "is. This repo lives all eight, concretely:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="rel-df-fallacies",
                    ordered=False,
                    items=[
                        "The network is reliable — the compose network "
                        "restarts, the VPN hiccups, and a perfectly written "
                        "query still raises ConnectionError.",
                        "Latency is zero — every hop costs milliseconds; "
                        "topic 38 measured them, and they multiply when a "
                        "retry repeats the whole hop.",
                        "Bandwidth is infinite — a response big enough "
                        "slowly becomes a response late enough to look "
                        "like a hang.",
                        "The network is secure — topic 25's threat model; "
                        "an unreachable dependency and a blocked one look "
                        "identical from the caller.",
                        "Topology never changes — a store moves to another "
                        "host and every cached connection is suddenly a "
                        "lie (the pool's pre_ping exists for exactly this).",
                        "There is one administrator — the Redis your demo "
                        "assumes may be someone else's maintenance window.",
                        "Transport cost is zero — serialization is real "
                        "CPU; a retry pays it twice.",
                        "The network is homogeneous — the same request "
                        "meets nginx, vite's proxy, and uvicorn on its "
                        "way in, and any of them can be the slow hop.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="rel-df-cascading",
                    text=(
                        "The reason hung calls are an emergency and not an "
                        "annoyance is cascading failure: one slow "
                        "dependency converts latency into resource "
                        "exhaustion, which converts exhaustion into "
                        "failure somewhere else. Trace the chain in this "
                        "stack. A request awaits a store call with no "
                        "timeout; the call hangs; the handler occupies its "
                        "spot on the event loop's schedule and, worse, "
                        "holds whatever it checked out — a pool connection, "
                        "a queue slot. Traffic keeps arriving, every new "
                        "request piles onto the same hung call, the pool "
                        "empties (topic 38's exhaustion pathology), and "
                        "now requests that never touched the sick "
                        "dependency fail too, because the shared resources "
                        "are spent. The failure cascaded upward from one "
                        "TCP connection to the whole process. This is why "
                        "the optional-service discipline in this repo is "
                        "not politeness but physics: an unbounded call is "
                        "a reservation with no cancellation."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-df-retry-storm",
                    text=(
                        "And the chain has a feedback loop: naive retries. "
                        "When a dependency slows down, clients time out and "
                        "retry — so the dependency now serves the same "
                        "load twice or three times, at exactly the moment "
                        "it has the least capacity to serve anything. More "
                        "retries mean more timeouts mean more retries: the "
                        "retry storm (also called a thundering herd when "
                        "many clients synchronize on the same recovery "
                        "instant). Retrying is a bet that attempt two "
                        "succeeds more often than attempt one because the "
                        "failure was transient — during an outage that bet "
                        "is exactly backwards, and every retry is extra "
                        "load on a dying system. The rest of this topic is "
                        "the careful version: bound first, retry with a "
                        "budget and backoff, then stop calling entirely "
                        "when the evidence says the dependency is down."
                    ),
                ),
            ],
        ),
        # ── 2. timeouts ───────────────────────────────────────────────────
        Section(
            id="timeouts",
            title="Timeouts: bound every call",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rel-to-pitch",
                    text=(
                        "The default timeout of most network libraries is "
                        "the operating system's patience, which is to say "
                        "minutes — a hung call is a parked worker, and "
                        "section 1 showed what parked workers become. The "
                        "first and cheapest reliability lever is therefore "
                        "not retrying, shedding, or breaking: it is "
                        "deciding, in advance, how long you are willing to "
                        "wait, and making that number smaller than the "
                        "damage the wait would do. A timeout converts the "
                        "third outcome (hang) into the first two (returns "
                        "or raises), which every other tool in this topic "
                        "requires — you cannot retry, shed, or circuit-"
                        "break a call that never answers."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-to-optional-pitch",
                    text=(
                        "This repo's rule is one sentence: every call to "
                        "an optional service is bounded to about two "
                        "seconds, at the one place each client is built. "
                        "MongoDB and Redis are optional services here — "
                        "the app boots and serves with either down — so "
                        "their client factories carry the timeout policy "
                        "every adapter shares, and the number is chosen "
                        "against the driver default it replaces:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-to-mongo-quote",
                    language="py",
                    caption="The motor client's two-second bounds — the constants and the one constructor that uses them.",
                    source="server/guide/data/mongo/client.py",
                    snippet=(
                        "SERVER_SELECTION_TIMEOUT_MS: Final = 2_000\n"
                        "\"\"\"How long an operation waits for a reachable mongod before failing.\n"
                        "\n"
                        "Short on purpose: when MongoDB is down, a demo request should degrade\n"
                        "to the 503 envelope in about two seconds, not hang a worker for the\n"
                        "30-second driver default.\n"
                        "\"\"\"\n"
                        "\n"
                        "CONNECT_TIMEOUT_MS: Final = 2_000\n"
                        "\"\"\"Per-connection handshake timeout — the other half of fast degradation.\"\"\"\n"
                        "\n"
                        "# …\n"
                        "    return AsyncIOMotorClient(\n"
                        "        config.mongo_url,\n"
                        "        serverSelectionTimeoutMS=SERVER_SELECTION_TIMEOUT_MS,\n"
                        "        connectTimeoutMS=CONNECT_TIMEOUT_MS,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-to-mongo-reading",
                    text=(
                        "Two different waits get two different constants, "
                        "because they bound different phases of the same "
                        "call. serverSelectionTimeoutMS is how long any "
                        "operation spends hunting for a usable server — "
                        "when the URL points at nothing reachable, this is "
                        "the clock that fires. connectTimeoutMS bounds "
                        "just the TCP-plus-auth handshake of one "
                        "connection. Both land at two seconds so the "
                        "worst case composes to a bounded answer either "
                        "way, and the comment names the alternative it "
                        "refuses: the driver default of thirty seconds, "
                        "which is one hung store times every concurrent "
                        "request — the cascading-failure arithmetic of "
                        "section 1 in one constant."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-to-redis-quote",
                    language="py",
                    caption="The redis client's matching bounds — connect handshake and per-command read/write, same two seconds.",
                    source="server/guide/data/redis/client.py",
                    snippet=(
                        "def create_redis_client(config: AppConfig) -> Redis:\n"
                        "    \"\"\"Build the process's redis.asyncio client from the config's URL rail.\n"
                        "\n"
                        "    Short socket timeouts keep the optional-service discipline FAST: when the\n"
                        "    URL points at nothing, the first command fails within the two-second\n"
                        "    bounds instead of the driver default, and the adapter maps that failure\n"
                        "    to the 503 envelope.\n"
                        "    \"\"\"\n"
                        "    return Redis.from_url(\n"
                        "        config.redis_url,\n"
                        "        decode_responses=True,\n"
                        "        socket_connect_timeout=SOCKET_CONNECT_TIMEOUT_S,\n"
                        "        socket_timeout=SOCKET_TIMEOUT_S,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-to-redis-reading",
                    text=(
                        "redis-py splits the same two ways: "
                        "socket_connect_timeout bounds the handshake, "
                        "socket_timeout bounds each command's reads and "
                        "writes — and because the playground's pub/sub "
                        "listener reads on the same connection discipline, "
                        "a store that stops answering fails inside the "
                        "same bound instead of parking the listener "
                        "forever. The two client factories are "
                        "deliberately near-identical: timeout policy is "
                        "boring, boring is reviewable, and one shape in "
                        "two places is how a team keeps the third store "
                        "from inventing a third policy."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-to-elsewhere",
                    text=(
                        "The same discipline appears wherever this repo "
                        "dials out. The SQL engine rides the pool's "
                        "30-second checkout timeout topic 38 measured (the "
                        "pool itself is the timeout for getting a "
                        "connection). The gRPC console turns the topic-15 "
                        "deadline into a per-call timeout handed straight "
                        "to the stub — the wire protocol's native version "
                        "of the same idea:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-to-grpc-quote",
                    language="py",
                    caption="gRPC deadlines: the request's deadline_ms becomes the stub call's timeout — the RPC-native timeout rail.",
                    source="server/guide/data/grpc/console.py",
                    snippet=(
                        "        timeout = request.deadline_ms / 1000 if request.deadline_ms is not None else None\n"
                        "        started = time.perf_counter()\n"
                        "# …\n"
                        "            if request.method == \"get-post\":\n"
                        "                reply = await stub.GetPost(\n"
                        "                    guide_pb2.GetPostRequest(slug=request.slug), timeout=timeout\n"
                        "                )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-to-budget",
                    text=(
                        "Choosing the number is budget arithmetic, not a "
                        "superstition: your caller has a patience budget, "
                        "and every nested call's timeout must fit inside "
                        "it with room for the work between calls. This API "
                        "gives a demo request roughly two seconds per "
                        "optional store because the degradation path (a "
                        "clean 503, next section) is a fine outcome for a "
                        "demo and five concurrent hung waits would not be. "
                        "The one rule that generalizes: the inner "
                        "timeout is always shorter than the outer one — a "
                        "database call inside a 3-second HTTP deadline "
                        "with a 30-second driver timeout is a hung user "
                        "with extra steps, because the outer budget "
                        "expires first and the inner wait was never "
                        "cancellable by it. Deadline propagation — the "
                        "caller telling the callee how much budget "
                        "remains, exactly as the gRPC deadline does — is "
                        "the systematic answer, and the reason its console "
                        "carries the milliseconds in the request itself."
                    ),
                ),
            ],
        ),
        # ── 3. retries ────────────────────────────────────────────────────
        Section(
            id="retries",
            title="Retries: ask again, carefully",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rel-rt-pitch",
                    text=(
                        "Once a call is bounded, a timeout becomes a "
                        "normal exception, and the obvious next move is to "
                        "try again. Whether that is wise depends on two "
                        "questions, and neither is about code. First: was "
                        "the failure transient — is there a reason attempt "
                        "two would succeed where attempt one failed (a "
                        "blip, a restart, a momentarily exhausted pool)? "
                        "Second: is the operation safe to repeat — a "
                        "read is, a charge is not, and section 8 shows why "
                        "at-least-once delivery makes 'we only send once' "
                        "a promise nobody can keep. A retry policy that "
                        "cannot answer both is a load multiplier wearing "
                        "a reliability costume."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-rt-engine-pitch",
                    text=(
                        "This repo answers with two real, pure retry "
                        "engines — the webhook sender's schedule (topic "
                        "14, exponential backoff over attempts the "
                        "receiver controls) and the jobs worker's policy "
                        "(topic 29), which additionally classifies "
                        "poison. The jobs engine is the fuller one: given "
                        "a policy it derives the exact attempt schedule, "
                        "deterministically, with no sleeping in the "
                        "policy itself:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-rt-policy-quote",
                    language="py",
                    caption="The pure retry schedule: fixed or exponential delay between attempts, accumulated into run offsets.",
                    source="server/guide/domain/jobs/policy.py",
                    snippet=(
                        "    def delay_before(self, attempt: int) -> float:\n"
                        "        \"\"\"Seconds to wait after failed ``attempt`` (1-based) before the next one.\"\"\"\n"
                        "        if attempt < 1:\n"
                        "            raise ValueError(f\"attempt is 1-based, got {attempt}\")\n"
                        "        if self.strategy == \"fixed\":\n"
                        "            return self.base_delay_seconds\n"
                        "        return self.base_delay_seconds * (2.0 ** (attempt - 1))\n"
                        "\n"
                        "    def attempt_offsets(self) -> list[float]:\n"
                        "        \"\"\"The whole schedule at a glance — the panel's timeline shows exactly this.\"\"\"\n"
                        "        offsets: list[float] = []\n"
                        "        offset = 0.0\n"
                        "        for attempt in range(1, self.max_attempts + 1):\n"
                        "            offsets.append(offset)\n"
                        "            offset += self.delay_before(attempt)\n"
                        "        return offsets"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-rt-reading",
                    text=(
                        "Two curves, one budget. The fixed curve waits the "
                        "same pause after every failure — right when "
                        "failures are cheap blips with a steady recovery "
                        "rate. The exponential curve doubles each pause, "
                        "so the demo policy's three attempts run at "
                        "offsets 0, 0.25, and 0.75 seconds: recovery ROOM, "
                        "not a hammer, which is why the webhook sender "
                        "ships exponential-only with offsets 0/1/3/7/15. "
                        "The pauses are deliberately jitter-free in this "
                        "repo so every schedule is exactly teachable and "
                        "testable; the module's docstring says the quiet "
                        "part — production adds random jitter to these "
                        "same offsets so a fleet of workers recovering "
                        "from the same incident does not synchronize into "
                        "the thundering herd of section 1. The budget caps "
                        "the whole walk: three attempts here, five for "
                        "webhooks, and the attempt that exhausts the "
                        "budget parks the job in the dead-letter queue "
                        "instead of retrying forever."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-rt-worker-pitch",
                    text=(
                        "The schedule is pure computation; the arq worker "
                        "is where it meets a real queue. arq's own retry "
                        "mechanism is the Retry exception — raising it "
                        "re-queues the job — and the worker raises it "
                        "with exactly the delay the policy computed, so "
                        "the queue and the policy never disagree:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-rt-worker-quote",
                    language="py",
                    caption="The worker's retry round: attempt 1 fails, the policy's delay becomes arq's Retry defer.",
                    source="server/guide/worker.py",
                    snippet=(
                        "async def fail_once(ctx: dict[str, Any]) -> str:\n"
                        "    \"\"\"A transient failure: attempt 1 fails, the policy schedules attempt 2.\"\"\"\n"
                        "    attempt = int(ctx[\"job_try\"])\n"
                        "    delay = DEMO_JOB_POLICY.delay_before(attempt)\n"
                        "    if attempt == 1:\n"
                        "        await _note(\n"
                        "            str(ctx[\"job_id\"]),\n"
                        "            attempt,\n"
                        "            \"retry_scheduled\",\n"
                        "            f\"attempt 1 failed (simulated transient) — policy schedules \"\n"
                        "            f\"attempt 2 in {delay:.2f}s\",\n"
                        "        )\n"
                        "        raise Retry(defer=timedelta(seconds=delay))"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-rt-poison-pitch",
                    text=(
                        "The other half of the policy is knowing when NOT "
                        "to retry. A malformed payload fails the same way "
                        "every time — retrying it is a budget burned for "
                        "nothing — so the engine classifies failures, and "
                        "poison ones go straight to the dead-letter queue:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-rt-poison-quote",
                    language="py",
                    caption="Poison classification: the input-is-wrong family never gets a second attempt.",
                    source="server/guide/domain/jobs/policy.py",
                    snippet=(
                        "def classify_failure(exc: BaseException) -> FailureClass:\n"
                        "    \"\"\"Decide whether one failure deserves another attempt.\n"
                        "\n"
                        "    POISON is the input-is-wrong family: ``ValueError`` and everything\n"
                        "    that derives from it (pydantic's ``ValidationError`` included) mean\n"
                        "    the payload itself is malformed — attempt two would re-ask the same\n"
                        "    broken question. Everything else defaults RETRYABLE, matching the\n"
                        "    posture arq and Celery ship with; tighten that default deliberately\n"
                        "    in your own shop if you would rather fail fast on the unfamiliar.\n"
                        "    \"\"\"\n"
                        "    if isinstance(exc, ValueError):\n"
                        "        return \"poison\"\n"
                        "    return \"retryable\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-rt-coda",
                    text=(
                        "Put together, the careful version of 'try again' "
                        "is: bound the call first (a retry of a hang is "
                        "two hangs), retry only the transient world-is-"
                        "wrong family, back off exponentially so the sick "
                        "dependency gets room, cap the budget and "
                        "dead-letter what exhausts it, add jitter in "
                        "production so recovery does not stampede, and "
                        "make the retried work idempotent (section 8). "
                        "What retries still cannot do is stop you from "
                        "calling a dependency that is hard down — every "
                        "attempt pays the full timeout, and the budget "
                        "multiplies load precisely when the system has "
                        "the least capacity. That is the job of the next "
                        "tool, and it is the one this topic builds for "
                        "real."
                    ),
                ),
            ],
        ),
        # ── 4. circuit breaker ────────────────────────────────────────────
        Section(
            id="circuit-breaker",
            title="The circuit breaker",
            lead="This section carries the topic's demo — the live breaker cycle.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rel-cb-pitch",
                    text=(
                        "A circuit breaker answers the question retries "
                        "cannot: this dependency has failed so "
                        "consistently that every further call is wasted "
                        "work — stop calling it entirely for a while. The "
                        "name is the electrical panel metaphor: rather "
                        "than letting every new request shove its hand "
                        "into the short circuit, the breaker trips and "
                        "the flow stops; someone checks whether the fault "
                        "is fixed before the panel resets. Where a retry "
                        "policy reasons about ONE call's outcome, the "
                        "breaker reasons about a WINDOW of them — it is "
                        "memory, and the memory is the state."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-cb-states-pitch",
                    text=(
                        "The pattern is three states with two controlled "
                        "transitions, and every implementation is a "
                        "variation on exactly these boxes:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="rel-cb-states",
                    ordered=True,
                    items=[
                        "Closed — the healthy default: calls flow through, "
                        "and the breaker only counts consecutive failures "
                        "(a success resets the count, because three "
                        "failures in a row is an outage while three in an "
                        "hour is Tuesday).",
                        "Open — the trip: once the count reaches the "
                        "threshold, calls are rejected immediately, "
                        "without touching the dependency, until the open "
                        "timeout elapses — the fail-fast that converts a "
                        "60ms wasted call into a 0ms refusal.",
                        "Half-open — the probe: after the timeout, exactly "
                        "one call goes through as a test; its success "
                        "closes the breaker, its failure re-opens it with "
                        "a fresh timeout — recovery is earned with "
                        "evidence, not assumed by a timer.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="rel-cb-substrate-pitch",
                    text=(
                        "This repo's breaker is a real, pure substrate in "
                        "the domain layer — the same design posture as "
                        "the sliding-window limiter and the retry "
                        "engines: no sleeping, no network, an injected "
                        "clock, every transition a unit test with integer "
                        "inputs. The knobs first, because every edge case "
                        "hangs off them:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-cb-policy-quote",
                    language="py",
                    caption="The breaker policy: trip threshold, open timeout, and what a probe must show to close again.",
                    source="server/guide/domain/reliability/breaker.py",
                    snippet=(
                        "@final\n"
                        "@dataclass(frozen=True, slots=True)\n"
                        "class BreakerPolicy:\n"
                        "    \"\"\"The knobs: when to trip, how long to stay open, what closes it again.\n"
                        "\n"
                        "    ``failure_threshold`` counts CONSECUTIVE failures (a success resets the\n"
                        "    count) — three in a row is evidence of an outage where three spread\n"
                        "    over an hour is evidence of nothing. ``open_timeout_s`` is how long the\n"
                        "    open state refuses calls before allowing one half-open probe; the demo\n"
                        "    policy keeps it at two seconds so the full cycle is watchable live.\n"
                        "    ``half_open_successes`` is how many consecutive half-open successes\n"
                        "    close the breaker (one: a single healthy probe is enough — the\n"
                        "    conservative production choice is a small odd number like three, at\n"
                        "    the cost of keeping the gate half-closed longer).\n"
                        "    \"\"\"\n"
                        "\n"
                        "    failure_threshold: int = 3\n"
                        "    open_timeout_s: float = 2.0\n"
                        "    half_open_successes: int = 1"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-cb-gate-pitch",
                    text=(
                        "The runtime shape is an acquire/record protocol — "
                        "the same two phases any guarded call has. "
                        "`acquire` is the gate every caller passes BEFORE "
                        "the call; `record_success` and `record_failure` "
                        "deliver the verdict AFTER it. The gate is where "
                        "the interesting edge cases live, quoted from the "
                        "substrate:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-cb-gate-quote",
                    language="py",
                    caption="The gate: closed admits everyone, open fast-fails with the probe countdown, half-open admits exactly one probe.",
                    source="server/guide/domain/reliability/breaker.py",
                    snippet=(
                        "    def acquire(self, now: float | None = None) -> Admission:\n"
                        "        \"\"\"The gate every caller passes BEFORE the call.\n"
                        "\n"
                        "        Closed admits everyone; open admits nobody (fast-fail, with the\n"
                        "        seconds until the probe); half-open admits exactly ONE probe — a\n"
                        "        concurrent second caller arriving while the probe is in flight is\n"
                        "        rejected with a reason that names it, so the recovering dependency\n"
                        "        is never stampeded by its own recovery window.\n"
                        "        \"\"\"\n"
                        "        moment = self._clock() if now is None else now\n"
                        "        self._refresh(moment)\n"
                        "        if self._state == \"closed\":\n"
                        "            return Admission(\n"
                        "                allowed=True,\n"
                        "                state=\"closed\",\n"
                        "                is_probe=False,\n"
                        "                retry_after_s=None,\n"
                        "                reason=\"closed — calls flow through to the dependency\",\n"
                        "            )\n"
                        "        if self._state == \"open\":\n"
                        "            wait_s = self.seconds_until_probe(moment)\n"
                        "            return Admission(\n"
                        "                allowed=False,\n"
                        "                state=\"open\",\n"
                        "                is_probe=False,\n"
                        "                retry_after_s=round(wait_s, 2),\n"
                        "                reason=(\n"
                        "                    f\"open — fast-fail without touching the dependency; \"\n"
                        "                    f\"half-open probe allowed in {wait_s:.2f}s\"\n"
                        "                ),\n"
                        "            )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-cb-edges",
                    text=(
                        "Three edge cases the substrate pins deliberately. "
                        "The threshold is inclusive on the exact count — "
                        "with a threshold of three, the second consecutive "
                        "failure leaves the breaker closed and only the "
                        "third trips it, because the count compares "
                        "greater-or-equal after the increment. The "
                        "half-open probe is single-flight: the first "
                        "acquire after the timeout becomes the probe, and "
                        "a concurrent second caller is rejected with a "
                        "reason that says a probe is in flight — the "
                        "recovering dependency sees exactly one trial "
                        "request, never a stampede at the moment it can "
                        "least afford one. And a failed probe re-opens "
                        "with a FRESH timeout measured from the probe, "
                        "not the original trip — otherwise a dependency "
                        "that is still down would have its probe window "
                        "expire immediately forever, and it would be "
                        "probed to death by its own breaker. Late verdicts "
                        "(a result recorded after other callers' failures "
                        "tripped the gate) change nothing while open: the "
                        "trip decision stands, and the probe — not a "
                        "straggler — decides recovery."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-cb-demo-pitch",
                    text=(
                        "The demo walks this substrate through one full "
                        "cycle on every request, with real per-call "
                        "latency evidence: a failing dependency costs a "
                        "bounded 60 milliseconds, a rejected call costs "
                        "approximately zero and never touches it, and the "
                        "two-second open timeout elapses on the breaker's "
                        "injected clock — deterministically, repeatably, "
                        "without the panel ever sleeping out the wait."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="reliability:breaker",
                    title="The circuit breaker, one full cycle",
                    description=(
                        "GET /api/demo/reliability/breaker walks the REAL "
                        "pure CircuitBreaker substrate (domain/reliability/"
                        "breaker.py) through one complete cycle on the very "
                        "request that serves it: two healthy calls while "
                        "closed · the dependency degrades and three "
                        "consecutive failures trip the breaker open · "
                        "calls are REJECTED fast (0ms, dependency never "
                        "touched, Retry-After-shaped countdown served) at "
                        "the trip and again at the timeout's midpoint · "
                        "the injected clock advances past the two-second "
                        "open timeout · one half-open probe goes through "
                        "and succeeds · the breaker closes and ordinary "
                        "calls flow again. Every row is the actual "
                        "verdict the substrate returned (state at acquire, "
                        "probe flag, measured latency, consecutive-failure "
                        "count, the reason string), the fail-fast vs "
                        "real-failure latency contrast is computed from "
                        "those measured rows, and the state line reads "
                        "closed → open → half-open → closed."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-cb-demo-reading",
                    text=(
                        "How to read the panel. Watch the "
                        "consecutive-failure column: it climbs 1, 2, 3 "
                        "across the degraded calls and the third row's "
                        "reason names the trip. Then compare latencies: "
                        "the three failing calls each paid the bounded "
                        "60ms, while both rejected rows measured ~0ms with "
                        "dependency_touched false — that difference, "
                        "times every call your real traffic would have "
                        "made, is the entire point of the pattern. The "
                        "advance-clock rows are the injected clock moving "
                        "without sleeping — the same determinism trick "
                        "the limiter's tests use — so the identical cycle "
                        "replays on every request from a fresh breaker, "
                        "and the panel is honest that only the 60ms "
                        "failure latency is real wall time. The measured "
                        "dependency itself is labeled simulated (the jobs "
                        "catalog's precedent); the bookkeeping around it "
                        "is the real, tested substrate. The walk's own "
                        "recording of a rejected round, from the payload "
                        "builder:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-cb-walk-quote",
                    language="py",
                    caption="The walk's rejected row: no dependency touch, zero elapsed, the gate's own reason verbatim.",
                    source="server/guide/domain/demos/reliability_breaker.py",
                    snippet=(
                        "    admission = breaker.acquire(logical_now[\"t\"])\n"
                        "    state_before = admission.state\n"
                        "    if not admission.allowed:\n"
                        "        return BreakerCallRow(\n"
                        "            step=step,\n"
                        "            label=_STEP_LABELS[label_key],\n"
                        "            action=\"call\",\n"
                        "            state_before=state_before,\n"
                        "            admitted=False,\n"
                        "            is_probe=False,\n"
                        "            dependency_touched=False,\n"
                        "            outcome=\"rejected\",\n"
                        "            elapsed_ms=0.0,\n"
                        "            consecutive_failures=breaker.consecutive_failures,\n"
                        "            retry_after_s=admission.retry_after_s,\n"
                        "            reason=admission.reason,\n"
                        "        )"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-cb-router-quote",
                    language="py",
                    caption="The demo's thin router: one GET, the payload builder, a declared response model.",
                    source="server/guide/presentation/routers/demo/reliability.py",
                    snippet=(
                        "@router.get(BREAKER_PATH, response_model=BreakerPanel)\n"
                        "async def read_breaker_panel() -> BreakerPanel:\n"
                        "    \"\"\"Serve the live breaker cycle: closed → open → half-open → closed.\"\"\"\n"
                        "    return await build_breaker_panel()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-cb-where",
                    text=(
                        "Where a breaker belongs: around one dependency, "
                        "at the client that calls it — one breaker per "
                        "remote service, keyed nothing else, so Redis "
                        "being down does not lock the PostgreSQL gate. "
                        "This repo keeps the substrate pure and teaches it "
                        "through the demo because its optional services "
                        "degrade by the coarser mechanism of the next "
                        "section (bounded timeouts plus the 503 envelope) "
                        "— the honest sizing decision for a teaching app "
                        "whose stores are one hop away. In a production "
                        "client you wrap the transport once (an httpx "
                        "wrapper, a DB accessor) so every caller gets the "
                        "gate for free; libraries like pybreaker exist "
                        "for exactly that, and this substrate is the "
                        "readable core of what they add — states, "
                        "thresholds, single-flight probes, fresh re-open "
                        "timers — in a hundred testable lines."
                    ),
                ),
            ],
        ),
        # ── 5. degradation ────────────────────────────────────────────────
        Section(
            id="degradation",
            title="Degrade, don't die",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rel-dg-pitch",
                    text=(
                        "Timeouts bound the wait, retries spend a small "
                        "budget, the breaker stops the bleeding — but none "
                        "of them answers the user-facing question: what "
                        "does THIS request do now? The optional-service "
                        "discipline this repo has practiced since topic 19 "
                        "is the answer: a dependency that cannot be "
                        "reached is degraded to an honest, typed failure "
                        "for exactly the features that need it, and the "
                        "rest of the app keeps serving. The app boots with "
                        "PostgreSQL, Redis, or MongoDB down — lazy clients "
                        "connect to nothing at construction, migrations "
                        "run best-effort at startup — and only the demos "
                        "that need the sick store answer differently."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-dg-envelope-pitch",
                    text=(
                        "The typed failure is the error taxonomy's "
                        "service_unavailable kind, which the shared map "
                        "renders as HTTP 503 — one consistent envelope, "
                        "the same shape as every other failure in the "
                        "app:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-dg-errors-quote",
                    language="py",
                    caption="The taxonomy's status map: service_unavailable is a first-class kind, not an ad-hoc 500.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "_HTTP_STATUS_BY_KIND: dict[FailureKind, int] = {\n"
                        "    FailureKind.VALIDATION_FAILED: 422,\n"
                        "    FailureKind.UNAUTHORIZED: 401,\n"
                        "    FailureKind.FORBIDDEN: 403,\n"
                        "    FailureKind.NOT_FOUND: 404,\n"
                        "    FailureKind.CONFLICT: 409,\n"
                        "    FailureKind.RATE_LIMITED: 429,\n"
                        "    FailureKind.SERVICE_UNAVAILABLE: 503,\n"
                        "    FailureKind.INTERNAL: 500,\n"
                        "}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-dg-adapter-pitch",
                    text=(
                        "The mapping happens once per adapter, at the "
                        "boundary where the driver's exceptions surface — "
                        "the mongo console's version is the template every "
                        "optional-service adapter follows:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-dg-mongo-quote",
                    language="py",
                    caption="Optional-service degradation: driver failures become one typed envelope, logged, never swallowed.",
                    source="server/guide/data/mongo/console.py",
                    snippet=(
                        "@contextmanager\n"
                        "def _map_mongo_failures(operation: str) -> Iterator[None]:\n"
                        "    \"\"\"Optional-service discipline: MongoDB trouble becomes service_unavailable.\"\"\"\n"
                        "    try:\n"
                        "        yield\n"
                        "    except AppError:\n"
                        "        raise\n"
                        "    except (PyMongoError, OSError) as exc:\n"
                        "        logger.warning(\n"
                        "            \"mongo_console_unavailable\",\n"
                        "            operation=operation,\n"
                        "            error=type(exc).__name__,\n"
                        "            detail=str(exc),\n"
                        "        )\n"
                        "        raise AppError(\n"
                        "            FailureKind.SERVICE_UNAVAILABLE,\n"
                        "            \"MongoDB is unreachable or unusable — this demo runs real operations \"\n"
                        "            \"against the live document store and refuses to serve stale facts.\",\n"
                        "        ) from exc"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-dg-reading",
                    text=(
                        "Read what that context manager refuses to do. It "
                        "does not swallow: the exception handler's first "
                        "act is re-raising AppError untouched, and the "
                        "driver failure is logged as a structured warning "
                        "with the operation and error type — topic 33's "
                        "rule that nothing disappears silently, applied to "
                        "the failure path. It does not serve stale facts: "
                        "a demo that runs real operations against the "
                        "live store would rather answer 503 than a "
                        "cached-looking lie, and the message says exactly "
                        "that. And it does not retry — the bounded timeout "
                        "already fired; the degradation IS the policy for "
                        "this request, and the user's next click is the "
                        "retry."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-dg-ladder",
                    text=(
                        "Degradation is a ladder, and 503 is only one rung. "
                        "Below it: serve a cached answer with a staleness "
                        "label (topic 21's cache-aside already holds the "
                        "seam — serve the stale value when the origin "
                        "times out, and say so); serve a reduced payload "
                        "(the home page without the live counts); queue "
                        "the work for later (topic 29's pattern — accept "
                        "the job, retry it in a worker, answer 202-shaped "
                        "honesty). What every rung shares is that the "
                        "answer is TRUE about what it is: a 503 that says "
                        "the store is unreachable, a cached row that says "
                        "it is five minutes old, a queued job that says "
                        "when it will run. The one move the taxonomy has "
                        "no kind for is the fake 200 — serving wrong data "
                        "with a success status — because it is the only "
                        "failure the caller cannot detect. This repo "
                        "climbs the ladder deliberately: the demos 503, "
                        "because for them stale facts are worse than no "
                        "facts; your features choose rung by rung."
                    ),
                ),
            ],
        ),
        # ── 6. bulkheads & shedding ───────────────────────────────────────
        Section(
            id="bulkheads-shedding",
            title="Bulkheads and load shedding",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rel-bh-pitch",
                    text=(
                        "A bulkhead is a ship's wall: one compartment "
                        "floods and the ship floats, because the water "
                        "cannot cross. In a service, a bulkhead is any "
                        "fixed budget that contains the blast radius of "
                        "overload — a pool of five connections that runs "
                        "out before the database does, a queue of thirty-"
                        "two messages that fills before memory does, a "
                        "thread pool that saturates before the process "
                        "does. Load shedding is the policy that rides the "
                        "wall: when a compartment is full, REJECT new "
                        "work early and visibly, instead of accepting it "
                        "and degrading everything. The two together "
                        "answer an overload question the earlier tools "
                        "cannot: what do we do when the problem is not a "
                        "sick dependency but too much honest demand?"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-bh-limiter-pitch",
                    text=(
                        "This repo's most visible shed is the rate "
                        "limiter topic 25 built. A throttled request is "
                        "not an error in disguise — it is the system "
                        "telling an honest client exactly when to come "
                        "back, which is why the envelope carries numbers "
                        "and the header carries the seconds:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-bh-limiter-quote",
                    language="py",
                    caption="The shed: a denial raises the 429 envelope with Retry-After and the numbers in details.",
                    source="server/guide/presentation/dependencies/rate_limit.py",
                    snippet=(
                        "    limiter = get_rate_limiter(request)\n"
                        "    verdict = limiter.hit(client_key(request))\n"
                        "    if verdict.allowed:\n"
                        "        return verdict\n"
                        "    retry_after_s = max(1, math.ceil(verdict.retry_after_s or 0))\n"
                        "    raise AppError(\n"
                        "        FailureKind.RATE_LIMITED,\n"
                        "        (\n"
                        "            f\"rate limit exceeded — {verdict.limit} requests per \"\n"
                        "            f\"{verdict.window_s:g}s per {limiter.policy.keying}; retry in \"\n"
                        "            f\"{retry_after_s}s\"\n"
                        "        ),\n"
                        "        details={\n"
                        "            \"limit\": verdict.limit,\n"
                        "            \"windowSeconds\": verdict.window_s,\n"
                        "            \"retryAfterSeconds\": retry_after_s,\n"
                        "            \"keying\": limiter.policy.keying,\n"
                        "        },\n"
                        "        headers={\"Retry-After\": str(retry_after_s)},\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-bh-limiter-reading",
                    text=(
                        "Three shedding decisions are packed in that "
                        "raise. The denial is computed from the sliding "
                        "window's honest arithmetic — and crucially the "
                        "limiter does NOT record denied hits, so a client "
                        "hammering past the limit does not extend its own "
                        "lockout (shedding is load control, not "
                        "punishment). The Retry-After seconds round UP — "
                        "a client told to try in 2.1 seconds must not try "
                        "in 2 — and never zero, because a denial always "
                        "owes at least one second of patience. And the "
                        "structured details ride beside the header so "
                        "programs that prefer fields to headers get the "
                        "same contract. This is a shed, not a breaker: it "
                        "keys on the CALLER's rate, not the DEPENDENCY's "
                        "health — the two tools compose, one protecting "
                        "us from the world, the other protecting the "
                        "dependency from us."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-bh-ceiling-pitch",
                    text=(
                        "The realtime manager is the same doctrine in "
                        "push form: two fixed ceilings (eight members per "
                        "room, thirty-two queued messages per connection), "
                        "and the slow-consumer one is enforced at fanout "
                        "with the queue's own boundedness — no sender ever "
                        "awaits a slow receiver:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-bh-manager-quote",
                    language="py",
                    caption="The slow-consumer bulkhead: a full queue retires its member instead of blocking the sender.",
                    source="server/guide/domain/realtime/manager.py",
                    snippet=(
                        "        retired: list[str] = []\n"
                        "        for member in tuple(self._rooms.get(room, {}).values()):\n"
                        "            if member.id == exclude_id:\n"
                        "                continue\n"
                        "            try:\n"
                        "                member.queue.put_nowait(message)\n"
                        "            except asyncio.QueueFull:\n"
                        "                self.leave(member)\n"
                        "                self._retire(member)\n"
                        "                retired.append(member.name)\n"
                        "        return retired"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-bh-ceiling-reading",
                    text=(
                        "The choice hidden in put_nowait is the whole "
                        "lesson: broadcast does not await, so one stalled "
                        "websocket can never back up the event loop that "
                        "serves every other connection — the queue is the "
                        "bulkhead, and the QueueFull exception is the "
                        "moment of shedding. What gets shed is the "
                        "consumer that fell a whole queue-depth behind: "
                        "it is removed from the roster and handed a "
                        "sentinel that closes its socket with 1013 (try "
                        "again later), which is harsher than a 429 and "
                        "correct — a push consumer that far behind is "
                        "receiving history, not news, and topic 28 taught "
                        "it to reconnect with Last-Event-ID for the "
                        "replay. The room ceiling is the same wall one "
                        "level up, checked under the join lock so two "
                        "concurrent joins cannot both claim the last "
                        "slot."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-bh-pools",
                    text=(
                        "The quieter bulkheads are the pools. Topic 38 "
                        "read them as performance; reliability reads the "
                        "same five-connection pool as a wall: a flood of "
                        "database demand queues at the pool (up to the "
                        "30-second checkout timeout) instead of "
                        "multiplying database connections until PostgreSQL "
                        "refuses everyone. to_thread's default executor "
                        "is the same wall for blocking work — a fixed "
                        "thread budget that saturates before the process "
                        "does. And the biggest bulkhead in this repo is a "
                        "process boundary: the arq worker is a separate "
                        "container, so a queue backlog of retrying jobs "
                        "consumes the worker's CPU and memory, not the "
                        "API's — one compartment, by deployment shape. "
                        "When you size any of these, you are not "
                        "optimizing; you are choosing which compartment "
                        "floods first, and the answer should always be "
                        "the one that fails loudest and recovers "
                        "cheapest."
                    ),
                ),
            ],
        ),
        # ── 7. chaos ──────────────────────────────────────────────────────
        Section(
            id="chaos",
            title="Chaos: rehearse the failure",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rel-ch-pitch",
                    text=(
                        "Every mechanism in this topic is a hypothesis "
                        "until it has failed for real: the timeout that "
                        "has never fired, the degradation that has never "
                        "served, the breaker that has never tripped are "
                        "correct-looking code. Chaos engineering is the "
                        "practice of injecting failure on purpose, "
                        "routinely, in conditions you control — so the "
                        "first execution of every failure path is a "
                        "rehearsal, not an incident. This repo has a "
                        "real, quotable chaos lever at its center "
                        "already: the scenario store, the runtime toggle "
                        "every demo reads."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-ch-scenario-pitch",
                    text=(
                        "PATCH /api/demo/scenario flips two flags — data "
                        "mode and, the one reliability cares about, "
                        "failure injection — and the store defends its "
                        "own invariants on every write:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-ch-scenario-quote",
                    language="py",
                    caption="The chaos lever's engine: partial update, full revalidation — bad patches cannot corrupt the flags.",
                    source="server/guide/core/scenario.py",
                    snippet=(
                        "    def update(self, patch: ScenarioPatch) -> ScenarioState:\n"
                        "        \"\"\"Merge only the fields the patch set, revalidating the enums.\n"
                        "\n"
                        "        Raises ``AppError(validation_failed)`` if the merged state is not a\n"
                        "        legal ScenarioState — the store defends its own invariant because\n"
                        "        patches can also arrive from untyped callers, not just HTTP bodies\n"
                        "        (which FastAPI pre-validates).\n"
                        "        \"\"\"\n"
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
                    id="rel-ch-probe-pitch",
                    text=(
                        "The injection's live reader is topic 30's probe "
                        "endpoint — the one route in the app whose "
                        "failure IS the feature, and the reason this "
                        "topic's terminal companion can stage a real "
                        "outage in four curl calls:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-ch-probe-quote",
                    language="py",
                    caption="The probe: injectFailure=error raises a genuine unhandled error — no try/except, by design.",
                    source="server/guide/presentation/routers/demo/errors.py",
                    snippet=(
                        "@router.get(PROBE_ROUTE, response_model=ProbeRow)\n"
                        "async def probe_scenario_injection(store: ScenarioStoreDep) -> ProbeRow:\n"
                        "    \"\"\"Answer per the scenario's failure injection — no try/except by design.\n"
                        "\n"
                        "    ``injectFailure=error`` raises an unhandled RuntimeError: the last-resort\n"
                        "    handler logs the traceback (with the request id) and answers the generic\n"
                        "    500 envelope, proving internals never leak while the log sees everything.\n"
                        "    ``latency`` sleeps first; ``none`` answers immediately.\n"
                        "    \"\"\"\n"
                        "    state = store.get()\n"
                        "    if state.inject_failure == \"error\":\n"
                        "        raise RuntimeError(\n"
                        "            \"scenario-injected failure (injectFailure=error) — the outermost \"\n"
                        "            \"handler turns this into the generic 500 envelope\"\n"
                        "        )\n"
                        "    if state.inject_failure == \"latency\":\n"
                        "        await asyncio.sleep(PROBE_LATENCY_SECONDS)\n"
                        "    return build_probe_row(state)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-ch-reading",
                    text=(
                        "Notice what the probe proves beyond the raise: "
                        "the full failure stack behaves. The injected "
                        "RuntimeError travels the middleware onion, the "
                        "outermost handler logs it WITH the request id, "
                        "and the client receives the generic 500 envelope "
                        "— internals never leak, and topic 33's viewer "
                        "shows the log row that proves it. The latency "
                        "injection is the subtler rehearsal: a 1.5-second "
                        "sleep that makes the degradation-shaped slowness "
                        "visible to a stopwatch without hurting anything. "
                        "That pair — cause a real failure, watch the "
                        "system's honest response — is chaos engineering "
                        "compressed into a teaching app."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-ch-discipline",
                    text=(
                        "The discipline this repo models scales up. Blast "
                        "radius first: the scenario flags flip demo "
                        "behavior, not data; a production chaos platform "
                        "(or a composed game day) starts just as bounded "
                        "— one dependency, one metric, one rollback "
                        "switch, never Friday. Label the simulation: the "
                        "jobs catalog's failures say simulated in their "
                        "own strings, because an unlabeled simulated "
                        "failure is indistinguishable from a real bug. "
                        "Verify the system did the right thing, not just "
                        "that it survived: the probe's envelope shape and "
                        "request id are asserted in tests, the breaker's "
                        "cycle is asserted per request, the errors "
                        "explorer's live triggers are pinned — chaos "
                        "without a hypothesis and a measurement is just "
                        "vandalism with a dashboard. And when you are "
                        "ready for the least simulated rehearsal of all, "
                        "the stack itself is the tool: stop one store "
                        "container and watch exactly which endpoints "
                        "degrade to 503 — the terminal companion of topic "
                        "19 already scripted that drill."
                    ),
                ),
            ],
        ),
        # ── 8. races & idempotence ────────────────────────────────────────
        Section(
            id="races",
            title="Races and idempotence",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rel-race-pitch",
                    text=(
                        "The last failure mode reliability owns is the one "
                        "its own medicine creates: retries and at-least-"
                        "once delivery mean the same work can run twice, "
                        "and concurrent requests mean two writers can "
                        "read the same state and both act on it. These "
                        "are races — not crashes, but correct-looking "
                        "wrong answers. This repo has real, taught "
                        "answers at both layers where races live: the "
                        "database, where two transactions contend, and "
                        "the stream, where delivery repeats."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-race-lock-pitch",
                    text=(
                        "The database answer is the row lock. Topic 17's "
                        "race demo runs the SAME two transactions twice — "
                        "unlocked (both read the same count, both insert, "
                        "a slot number is assigned twice) and locked "
                        "(both take SELECT FOR UPDATE first, the writes "
                        "serialize, every number is unique). The locked "
                        "half, quoted from the repository that runs it "
                        "against live PostgreSQL:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-race-lock-quote",
                    language="py",
                    caption="The locked race: A locks the row, B's lock request blocks until A commits — the writes serialize.",
                    source="server/guide/data/db/repository.py",
                    snippet=(
                        "    async def _race_locked(self, post_id: int, baseline: int) -> RaceRunRow:\n"
                        "        \"\"\"Same race, but both transactions take SELECT ... FOR UPDATE first.\n"
                        "\n"
                        "        A locks the post row; B's lock request BLOCKS (deterministically —\n"
                        "        it is started as a task and only awaited after A commits), so B's\n"
                        "        COUNT runs AFTER A's insert is committed and visible: the writes\n"
                        "        serialize on the row lock and every slot number is unique.\n"
                        "        \"\"\"\n"
                        "        async with _two_connections(self._engine) as (conn_a, conn_b):\n"
                        "            tx_a = await conn_a.begin()\n"
                        "            tx_b = await conn_b.begin()\n"
                        "            try:\n"
                        "                await conn_a.execute(\n"
                        "                    sa.text(\"SELECT id FROM posts WHERE id = :post_id FOR UPDATE\"),\n"
                        "                    {\"post_id\": post_id},\n"
                        "                )\n"
                        "                lock_b = asyncio.create_task(\n"
                        "                    conn_b.execute(\n"
                        "                        sa.text(\"SELECT id FROM posts WHERE id = :post_id FOR UPDATE\"),\n"
                        "                        {\"post_id\": post_id},\n"
                        "                    )\n"
                        "                )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-race-lock-reading",
                    text=(
                        "The lock turns a race into an order: B's read "
                        "happens after A's commit because B cannot read "
                        "until it holds the lock A holds. The demo makes "
                        "the interleaving deterministic — B's lock "
                        "request is started as a task and awaited only "
                        "after A commits, so the pinned test asserts the "
                        "serialization rather than hoping for it — and "
                        "the same discipline answers any read-modify-"
                        "write over shared rows. The lighter alternative, "
                        "optimistic versioning (topic 18's posts.version "
                        "column), suits contention that is rare: no "
                        "locks, but a writer whose version went stale "
                        "gets StaleDataError and retries the whole unit "
                        "of work — pessimistic locks pay always and "
                        "never collide; optimistic ones pay only on the "
                        "collision and suit the workloads where collisions "
                        "are the exception."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-race-idem-pitch",
                    text=(
                        "The stream answer is idempotence. At-least-once "
                        "delivery — the only honest guarantee a queue "
                        "with retries can give — means every consumer "
                        "WILL see some events twice; the exactly-once "
                        "EXPERIENCE is built on the consuming side, and "
                        "topic 22's engine is its whole shape:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-race-idem-quote",
                    language="py",
                    caption="The idempotent consumer: check the processed-set before the work, remember after it.",
                    source="server/guide/domain/messaging/idempotence.py",
                    snippet=(
                        "        processed: list[str] = []\n"
                        "        skipped_duplicates: list[str] = []\n"
                        "        for entry in entries:\n"
                        "            if await self._store.seen(self._set_key, entry.event_id):\n"
                        "                skipped_duplicates.append(entry.event_id)\n"
                        "                continue\n"
                        "            await self._store.remember(self._set_key, entry.event_id)\n"
                        "            processed.append(entry.event_id)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-race-coda",
                    text=(
                        "The order of those two calls is the guarantee, "
                        "and the trade is explicit in the module: "
                        "remember BEFORE the work and a crash mid-work "
                        "loses the event forever; remember AFTER it and a "
                        "crash between work and remember replays the work "
                        "on redelivery — duplicates are auditable, "
                        "losses are not, so the engine takes the "
                        "duplicate window and closes it by making the "
                        "work itself idempotent when that matters. That "
                        "same posture is why the retry engines of "
                        "section 3 are safe: a retried job or webhook "
                        "that writes through a seen-before check cannot "
                        "double-apply, whatever the delivery count. "
                        "Reliability's last rule is this section in one "
                        "sentence: design every operation as if it will "
                        "run twice, because under every mechanism this "
                        "topic built — timeouts that retry, breakers "
                        "that probe, queues that redeliver — eventually "
                        "it will."
                    ),
                ),
            ],
        ),
        # ── 9. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="Reliability from a shell: the breaker's full cycle, the fail-fast evidence, the chaos lever, this topic's shape.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rel-terminal-intro",
                    text=(
                        "Five stops on the running stack: the breaker "
                        "panel's policy and state line, its per-call log "
                        "with the latency evidence, the fail-fast vs "
                        "real-failure contrast, a REAL chaos round trip "
                        "through the scenario store and the probe, and "
                        "this topic's own shape through both ports."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-terminal-cycle",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the policy knobs and the full-cycle state line\n"
                        "curl -s localhost:8000/api/demo/reliability/breaker | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for f in panel[\"policy\"]:\n"
                        "    print(\"%-20s %s\" % (f[\"id\"], f[\"value\"]))\n"
                        "print()\n"
                        "print(panel[\"stateLine\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-terminal-calls",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the walk's call log: states, verdicts, latencies, reasons\n"
                        "curl -s localhost:8000/api/demo/reliability/breaker | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for c in panel[\"calls\"]:\n"
                        "    if c[\"action\"] == \"advance-clock\":\n"
                        "        print(\"%-2d  %-38s %s\" % (c[\"step\"], c[\"label\"], c[\"outcome\"]))\n"
                        "        continue\n"
                        "    print(\"%-2d  %-38s %-8s %-9s probe=%-5s touched=%-5s %5.1fms  fails=%d  %s\" % (\n"
                        "        c[\"step\"], c[\"label\"], c[\"stateBefore\"], c[\"outcome\"],\n"
                        "        c[\"isProbe\"], c[\"dependencyTouched\"], c[\"elapsedMs\"],\n"
                        "        c[\"consecutiveFailures\"], c[\"reason\"][:60]))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-terminal-latency",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the fail-fast vs real-failure contrast, computed from the measured rows\n"
                        "curl -s localhost:8000/api/demo/reliability/breaker | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for f in panel[\"latency\"]:\n"
                        "    print(\"%-14s %s\" % (f[\"id\"], f[\"value\"]))\n"
                        "print(\"states:\", panel[\"statesVisited\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-terminal-chaos",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — a REAL chaos round trip: inject an error, watch the 500 envelope, restore\n"
                        "curl -s -X PATCH localhost:8000/api/demo/scenario \\\n"
                        "  -H 'content-type: application/json' -d '{\"injectFailure\":\"error\"}'\n"
                        "echo; curl -s localhost:8000/api/demo/errors/probe | python3 -c '\n"
                        "import json, sys\n"
                        "e = json.load(sys.stdin)[\"error\"]\n"
                        "print(\"probe answered:\", e[\"code\"], \"· requestId\", e[\"requestId\"])'\n"
                        "curl -s -X PATCH localhost:8000/api/demo/scenario \\\n"
                        "  -H 'content-type: application/json' -d '{\"injectFailure\":\"none\"}'\n"
                        "echo; curl -s localhost:8000/api/demo/errors/probe > /dev/null && echo 'probe healthy again'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rel-terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — this topic's shape, and the same panel through the client proxy\n"
                        "curl -s localhost:8000/api/content | python3 -c '\n"
                        "import json, sys\n"
                        "index = json.load(sys.stdin)\n"
                        "print(len(index[\"topics\"]), \"topics /\", len(index[\"groups\"]), \"groups\")'\n"
                        "curl -s localhost:8000/api/content/reliability | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'\n"
                        "curl -s localhost:5174/api/demo/reliability/breaker \\\n"
                        "  | python3 -c 'import json,sys; p=json.load(sys.stdin); print(\"proxy cycle:\", p[\"stateLine\"][:46])'\n"
                        "curl -s -o /dev/null -w 'health: %{http_code} in %{time_total}s\\n' localhost:8000/api/health"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rel-terminal-coda",
                    text=(
                        "Stops 1–3 are the breaker's whole argument in one "
                        "payload: the trip, the fast-fails that never "
                        "touched the dependency, the timeout elapsed on "
                        "an injected clock, the probe that earned the "
                        "recovery — every row a verdict the real "
                        "substrate returned. Stop 4 stages a genuine "
                        "outage and its honest 500 envelope in four "
                        "calls, then puts the stack back. Stop 5 closes "
                        "the loop the family always closes: the topic "
                        "that taught survival under failure is served by "
                        "a stack that never went down to teach it."
                    ),
                ),
            ],
        ),
    ],
)
