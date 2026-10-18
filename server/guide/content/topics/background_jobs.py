"""Topic 29 — Background jobs (BackgroundTasks + worker queues; the
media-realtime group's last topic).

Everything before this topic did its work inside a request. This one
takes the work OUT: it opens with why the request/response cycle cannot
hold slow or risky work (and the honest cost model of moving it), takes
starlette's ``BackgroundTasks`` for the in-process spin (runs after the
response, dies with the process — this repo's real usage quoted, its
limits stated plainly), then moves to the separate-process answer the
stack actually runs: an arq worker against redis (Celery surveyed as
prose), the enqueuer → broker → worker → result-store architecture, a
PURE retry policy that owns every schedule decision (the console demo
INLINE: attempt trails with retries visible), the dead-letter queue and
its replay as the operational loop, cron scheduling with a heartbeat,
email as the classic deferred job (recorded against a mailbox, no SMTP
— topic 42 wires the real client), and the two observability numbers
that catch most worker incidents. Terminal companion last: a curl tour
that enqueues all three scenarios, polls a retry to completion, walks a
job into the DLQ and back out, reads the queue's pulse, and fires the
BackgroundTasks-vs-worker comparison.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="background-jobs",
    title="Background jobs: BackgroundTasks and worker queues",
    subtitle=(
        "Why work leaves the request, starlette's in-process spin and its "
        "limits, the arq worker against redis with retries, dead letters and "
        "cron on a pure policy, email as the classic deferred job, and the two "
        "numbers that catch worker incidents."
    ),
    group="media-realtime",
    order=29,
    sections=[
        # ── 1. Why background ────────────────────────────────────────────────
        Section(
            id="why-background",
            title="Why background",
            blocks=[
                TextBlock(
                    kind="text",
                    id="why-pitch",
                    text=(
                        "A request is a promise with a clock on it: the client "
                        "asked, the connection is open, and every millisecond "
                        "your handler spends is a millisecond the user waits, a "
                        "connection held, a worker occupied. Some work simply "
                        "does not fit inside that promise — sending an email to "
                        "a server that takes four seconds to answer, "
                        "transcoding an upload, calling a flaky third party, "
                        "rebuilding a search index. Holding the request while "
                        "that work runs inverts every timeout in the stack: "
                        "proxies give up, clients retry, and the slow work "
                        "multiplies. The fix is a vocabulary distinction this "
                        "whole topic hangs on: FIRE-AND-FORGET (the request's "
                        "outcome does not depend on the work — acknowledge "
                        "now, do the work later) versus DEFERRED WORK (the "
                        "work must happen, must survive failure, and must be "
                        "observable while it waits). BackgroundTasks serves "
                        "the first; a worker queue serves the second; "
                        "pretending the first is the second is how systems "
                        "lose emails."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-costs",
                    text=(
                        "The honest cost model, before any code: moving work "
                        "out of a request trades LATENCY for a list of new "
                        "obligations, and each one is a thing you now own:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="why-cost-list",
                    ordered=False,
                    items=[
                        "Durability — in-process work dies with the process: a "
                        "deploy, a crash, a ``kill -9`` takes pending work with "
                        "it; a broker (redis) holds the job until a worker "
                        "survives long enough to run it.",
                        "Retries — a request that fails is the caller's "
                        "problem; a job that fails is YOURS: something must "
                        "decide how many attempts, on what schedule, and where "
                        "the failures park when the budget is spent.",
                        "Observability — a request is visible in logs and "
                        "traces by construction; a job is invisible unless you "
                        "build the window: status, attempt trail, queue depth.",
                        "Idempotence — at-least-once delivery means the same "
                        "job can run twice (a worker dies mid-flight, the job "
                        "is redelivered); the task must tolerate its own "
                        "repetition (topic 22's consumer discipline, applied).",
                        "Ordering — queues generally promise per-worker order, "
                        "not global order; if job B needs job A's effect, that "
                        "dependency is yours to model, not the broker's.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="why-close",
                    text=(
                        "So the decision tree is small. Work that is fast, "
                        "non-critical, and useless after a crash (log scraping, "
                        "cache warming, metric bumps) can live in-process with "
                        "``BackgroundTasks`` and lose nothing. Work a user "
                        "would notice losing (emails, payments, exports, "
                        "anything with a receipt) needs the worker queue: a "
                        "broker that survives the process, a worker that "
                        "survives the failure, and a policy that decides what "
                        "happens between attempts. This topic builds both "
                        "halves for real — and deliberately shows the seam "
                        "between them with one workload timed in both homes."
                    ),
                ),
            ],
        ),
        # ── 2. BackgroundTasks ───────────────────────────────────────────────
        Section(
            id="backgroundtasks",
            title="BackgroundTasks",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bt-pitch",
                    text=(
                        "Starlette's answer is one parameter and a list: "
                        "declare ``background_tasks: BackgroundTasks`` on the "
                        "handler, call ``add_task(callable, *args)``, and the "
                        "callables run AFTER the response has been sent — "
                        "same process, same event loop, zero new "
                        "infrastructure. This repo's real usage is the jobs "
                        "console's comparison endpoint, which fires the SAME "
                        "paced workload into both execution homes; the "
                        "in-process half is scheduled here and measured "
                        "honestly around the handoff:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bt-router-quote",
                    language="py",
                    caption="The comparison endpoint: schedule one half, enqueue the other, time the request.",
                    source="server/guide/presentation/routers/demo/jobs.py",
                    snippet=(
                        "    handler_started = time.perf_counter()\n"
                        "    run_id, ticket = await service.fire_comparison(background_tasks.add_task)\n"
                        "    return CompareFired(\n"
                        "        run_id=run_id,\n"
                        "        queued_job_id=ticket.job_id,\n"
                        "        handler_duration_ms=(time.perf_counter() - handler_started) * 1000,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bt-semantics",
                    text=(
                        "Two mechanics worth stating precisely because they "
                        "are the whole contract. First, ``add_task`` only "
                        "APPENDS — the service's ``fire_comparison`` receives "
                        "``background_tasks.add_task`` as an injected "
                        "scheduler (the same dependency inversion the "
                        "realtime topic used for ``is_disconnected``, keeping "
                        "starlette types out of the domain), and nothing runs "
                        "until the response is off the wire. Second, the "
                        "scheduled callable is an ``async def`` on the "
                        "service, and starlette awaits it on the serving "
                        "loop — the same loop the next request needs — so "
                        "the work must be async-honest (never block; topic 38 "
                        "repeats this with benchmarks). The callable files "
                        "its own half of the ledger:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bt-task-quote",
                    language="py",
                    caption="The scheduled callable: the same injected-sleeper workload, timed and filed.",
                    source="server/guide/domain/jobs/service.py",
                    snippet=(
                        "        work_started = _now_ms()\n"
                        "        work_seconds = await run_comparison_work(asyncio.sleep)\n"
                        "        await self._store.record(\n"
                        "            ComparisonRunRow(\n"
                        "                run_id=run_id,\n"
                        "                side=\"in_process\",\n"
                        "                ran_on=IN_PROCESS_HOME,\n"
                        "                handoff_duration_ms=work_started - decided_at_ms,\n"
                        "                work_duration_ms=work_seconds * 1000,\n"
                        "                finished_at_ms=_now_ms(),\n"
                        "            )\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bt-limits",
                    text=(
                        "Now the limits, said plainly because ``BackgroundTasks`` "
                        "looks like more than it is. It is FIRE-AND-FORGET, "
                        "not deferred work: no retries (a raised exception in "
                        "a background task logs and is gone), no durability "
                        "(a restart between response and task loses the task "
                        "— and deploys create exactly that window on every "
                        "release), no visibility (there is no list of pending "
                        "tasks, no status endpoint, nothing to poll), and no "
                        "backpressure beyond the event loop itself. It is "
                        "exactly right for work whose loss is a shrug, and it "
                        "LIES the moment you use it for work whose loss is a "
                        "support ticket. The test is not \"is this slow\" but "
                        "\"would anyone care if this silently vanished during "
                        "a deploy\" — emails and payments fail that test, "
                        "metric bumps and cache warming pass it. Everything "
                        "that fails it moves to the worker queue this topic "
                        "builds next."
                    ),
                ),
            ],
        ),
        # ── 3. Worker queues ─────────────────────────────────────────────────
        Section(
            id="worker-queues",
            title="Worker queues",
            blocks=[
                TextBlock(
                    kind="text",
                    id="wq-pitch",
                    text=(
                        "The separate-process answer is one architecture with "
                        "interchangeable parts: an ENQUEUER (your FastAPI "
                        "handler serializes the work and hands it to a "
                        "broker), a BROKER (a queue that outlives any "
                        "process — redis, in this stack), a WORKER (a "
                        "separate process that pulls jobs and runs them), and "
                        "a RESULT STORE (where outcomes land for polling). "
                        "The enqueuer answers the request in milliseconds "
                        "with a job id; everything slow happens in the "
                        "worker; failure between the processes is the "
                        "broker's problem, which is the point — redis "
                        "survives the deploy that kills your web process. "
                        "This repo's worker is arq: async-native (its tasks "
                        "are the same ``async def`` you already write), "
                        "redis-backed (one dependency this stack already "
                        "runs), and small enough to read in an afternoon — "
                        "the whole worker is a settings class:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="wq-settings-quote",
                    language="py",
                    caption="The entire worker configuration — functions by name, cron, budget, redis.",
                    source="server/guide/worker.py",
                    snippet=(
                        "    functions = [fast, fail_once, fail_always, slow, send_email, comparison_work]\n"
                        "    cron_jobs = [cron(heartbeat, minute=None, run_at_startup=True)]\n"
                        "    redis_settings = RedisSettings.from_dsn(get_config().redis_url)\n"
                        "    max_tries = DEMO_JOB_POLICY.max_attempts\n"
                        "    retry_jobs = True\n"
                        "    job_timeout = 30"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="wq-enqueue",
                    text=(
                        "Dispatch is BY NAME: the enqueuer sends the string "
                        "``\"fail_once\"`` and the worker looks it up in "
                        "``functions`` — which makes the name table a "
                        "cross-process contract (this repo writes it down as "
                        "the catalog the demo router validates against, so an "
                        "unknown name fails at the boundary instead of "
                        "becoming a job id that quietly never runs). The "
                        "enqueue side is one call over a lazily-created arq "
                        "pool — ``args: tuple[str, ...] = () if payload is "
                        "None else (payload,)`` then ``job = await "
                        "pool.enqueue_job(function_name, *args)`` — and the "
                        "answered ticket carries the minted id the client "
                        "polls. In compose the worker is its own service "
                        "(``arq-worker``, same image, command ``arq "
                        "guide.worker.WorkerSettings``) so it scales, "
                        "restarts, and dies independently of the API."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="wq-celery",
                    text=(
                        "Celery deserves the survey paragraph because you "
                        "will meet it first in most codebases. It is the "
                        "veteran: brokers galore (redis, RabbitMQ, SQS), "
                        "mature tooling (flower's dashboard, beat's "
                        "scheduler), and a habit of threading through "
                        "everything. The tradeoffs that pushed this stack to "
                        "arq: Celery's default execution model is a "
                        "multiprocessing PREFORK pool — wrapping an "
                        "asyncio app means managing two concurrency worlds, "
                        "while arq IS an asyncio loop running your existing "
                        "async tasks; Celery's configuration surface "
                        "(backend URLs, serializers, queues, routes) is a "
                        "discipline of its own, while arq's is one settings "
                        "class; and Celery's retries-and-results machinery "
                        "is powerful but framework-shaped, while arq's is "
                        "small enough that THIS topic can teach every "
                        "decision it makes. Choose Celery when you need its "
                        "ecosystem (broadcast tasks, complex routing, "
                        "existing dashboards); choose arq when your app is "
                        "already asyncio + redis and you want a worker you "
                        "fully understand — which, for a teaching guide, is "
                        "the whole game."
                    ),
                ),
            ],
        ),
        # ── 4. Retries & backoff ─────────────────────────────────────────────
        Section(
            id="retries-and-backoff",
            title="Retries and backoff",
            lead="This section carries the topic's demo — the jobs console.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="retry-pitch",
                    text=(
                        "A job nobody is waiting on can afford to try again — "
                        "but \"try again\" is three decisions pretending to be "
                        "one: how MANY attempts, on what SCHEDULE, and which "
                        "failures deserve another try at all. This repo "
                        "answers all three in a pure engine (the webhook "
                        "topic's retry ideas, restated for a worker that "
                        "owns longer-lived reliability): the policy knows the "
                        "curve, the classifier knows poison when it sees it, "
                        "and the worker just obeys the verdict. The curve "
                        "first — fixed (every pause equal: for failures that "
                        "heal at a known rate) or exponential (each pause "
                        "double the last: for a struggling dependency that "
                        "needs recovery ROOM, not a hammer):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="retry-curve-quote",
                    language="py",
                    caption="The schedule as pure math: one curve, offsets derived, jitter deliberately absent.",
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
                    id="retry-walk",
                    text=(
                        "The console's policy is 3 attempts, exponential, "
                        "0.25 s base — the demo policy runs its attempts at "
                        "offsets 0 / 0.25 / 0.75 s so a fail-always walk "
                        "exhausts inside two seconds while you watch; "
                        "production trades up to seconds or minutes on the "
                        "same code. The worker's part is deliberately thin — "
                        "read the attempt number arq hands you, ask the "
                        "policy for the verdict, and either raise arq's "
                        "``Retry`` with the computed delay or park the job "
                        "(the dead-letter half is next section's subject):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="retry-task-quote",
                    language="py",
                    caption="The worker's whole retry obligation: obey the verdict, leave a trail note.",
                    source="server/guide/worker.py",
                    snippet=(
                        "    attempt = int(ctx[\"job_try\"])\n"
                        "    verdict = decide_retry(DEMO_JOB_POLICY, attempt=attempt, failure_class=\"retryable\")\n"
                        "    if verdict.action == \"retry\":\n"
                        "        await _note(str(ctx[\"job_id\"]), attempt, \"retry_scheduled\", verdict.reason)\n"
                        "        assert verdict.delay_seconds is not None  # retry verdicts always carry one\n"
                        "        raise Retry(defer=timedelta(seconds=verdict.delay_seconds))\n"
                        "    await park_dead_letter(\n"
                        "        _jobs(),\n"
                        "        job_id=str(ctx[\"job_id\"]),\n"
                        "        function_name=\"fail_always\",\n"
                        "        attempts=attempt,\n"
                        "        reason=verdict.reason,\n"
                        "        payload=\"\",  # fail_always takes no payload — replay re-enqueues it arg-less\n"
                        "        failed_at_ms=_now_ms(),\n"
                        "    )\n"
                        "    # A plain error (NOT Retry) is permanent — the trail says dead-lettered, arq says failed.\n"
                        "    raise RuntimeError(\n"
                        "        f\"fail_always exhausted {attempt} attempts — parked in the dead-letter queue\"\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="retry-poison",
                    text=(
                        "The third decision — WHEN NOT TO RETRY — is the one "
                        "teams skip and regret. A failure caused by the "
                        "INPUT (a malformed payload, an invalid address) is "
                        "POISON: attempt two re-asks the same broken "
                        "question, spends your budget, and delays the "
                        "dead-letter entry that would have told a human the "
                        "truth. The classifier is one rule made explicit — "
                        "``ValueError`` and its children (pydantic's "
                        "``ValidationError`` included) mean the payload was "
                        "wrong, so they park immediately; timeouts and "
                        "connection errors mean the world was wrong, so they "
                        "retry; everything else defaults retryable, matching "
                        "arq and Celery's shipping posture, and a shop that "
                        "prefers failing fast on the unfamiliar tightens "
                        "that default deliberately. Watch all of it live:"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="jobs:console",
                    title="The jobs console",
                    description=(
                        "GET /api/demo/jobs/console serves the panel (the "
                        "retry policy's exact schedule — 3 attempts, "
                        "exponential, offsets 0/0.25/0.75s — the task "
                        "catalog with what each teaches, the worker command "
                        "and its cron schedule, the endpoint tour, honesty "
                        "notes). The LIVE queue is the centerpiece: enqueue "
                        "fast (one attempt, done), fail_once (attempt 1 "
                        "fails, the policy defers 0.25s, attempt 2 lands — "
                        "the trail shows both), fail_always (three attempts "
                        "on the curve, then the dead-letter queue), slow "
                        "(2s paced, visible in the stats while it waits and "
                        "runs); poll any job's snapshot for its attempt "
                        "timeline with outcomes per attempt; the two "
                        "observability numbers update live (queue depth + "
                        "oldest job age); the DLQ lists parked jobs with "
                        "reasons and a replay button (replay re-enqueues "
                        "FRESH — new job id, attempts reset); the mailbox "
                        "records send_email jobs (compose one with a "
                        "not-an-address to watch POISON park it after ONE "
                        "attempt, no retry spent); the heartbeat shows the "
                        "cron's last beat; and the comparison fires the "
                        "same workload in-process (BackgroundTasks) and "
                        "queued (worker) with honest timings for both."
                    ),
                ),
            ],
        ),
        # ── 5. DLQ & replay ──────────────────────────────────────────────────
        Section(
            id="dlq-and-replay",
            title="DLQ and replay",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dlq-pitch",
                    text=(
                        "When the attempt budget is spent (or the failure "
                        "was poison all along), the job parks in the "
                        "DEAD-LETTER QUEUE — a list a human can read, which "
                        "is the entire point: retries are how a system "
                        "heals itself, and a DLQ is how it asks for help. "
                        "The parking write is one shared flow both failure "
                        "paths call — build the audit row (the job id, the "
                        "function, how hard it was tried, WHY, the payload "
                        "for replay), append it to the list, and leave the "
                        "matching final note on the attempt trail so the "
                        "job's own snapshot agrees with the parking lot:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dlq-park-quote",
                    language="py",
                    caption="Parking: the audit row, the list append, and the trail note — one transaction of meaning.",
                    source="server/guide/domain/jobs/service.py",
                    snippet=(
                        "    entry = DeadLetterRow(\n"
                        "        entry_id=uuid.uuid4().hex[:RUN_ID_LENGTH],\n"
                        "        job_id=job_id,\n"
                        "        function_name=function_name,\n"
                        "        attempts=attempts,\n"
                        "        reason=reason,\n"
                        "        failed_at_ms=failed_at_ms,\n"
                        "        payload=payload,\n"
                        "    )\n"
                        "    await store.record_dead_letter(entry)\n"
                        "    await store.note(\n"
                        "        job_id,\n"
                        "        AttemptStepRow(\n"
                        "            attempt=attempts,\n"
                        "            outcome=\"failed_final\",\n"
                        "            detail=f\"dead-lettered: {reason}\",\n"
                        "            at_ms=failed_at_ms,\n"
                        "        ),\n"
                        "    )\n"
                        "    return entry"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dlq-replay-pitch",
                    text=(
                        "REPLAY is the second half of the operational loop: "
                        "a human reads the entry (the reason usually names "
                        "the fix — the dependency came back, the payload "
                        "was repaired upstream), decides it is worth "
                        "another life, and re-enqueues it. The semantics "
                        "are a decision made deliberately: replay mints a "
                        "NEW job id and RESETS the attempt counter to one — "
                        "a replay is a fresh run with the original's "
                        "payload, not a continuation — while the parked "
                        "entry STAYS as the audit record and grows a "
                        "``replayed_as`` link, so the trail of evidence "
                        "only ever grows:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dlq-replay-quote",
                    language="py",
                    caption="Replay: fresh id, attempts reset, the entry updated in place — audit grows, never loses.",
                    source="server/guide/data/jobs/arq_jobs.py",
                    snippet=(
                        "            for index, item in enumerate(raw):\n"
                        "                entry = DeadLetterRow.model_validate_json(item)\n"
                        "                if entry.entry_id != entry_id:\n"
                        "                    continue\n"
                        "                ticket = await self.enqueue(entry.function_name, entry.payload or None)\n"
                        "                updated = entry.model_copy(update={\"replayed_as\": ticket.job_id})\n"
                        "                await pool.lset(DLQ_KEY, index, updated.model_dump_json())\n"
                        "                return ticket"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dlq-loop",
                    text=(
                        "Note the payload rule hiding in that line — "
                        "``entry.payload or None``: an empty payload "
                        "re-enqueues ARG-LESS, which matters because arq "
                        "dispatches positionally (this topic's own "
                        "fail_always parks with an empty payload; a "
                        "send_email parks with its JSON). The loop this "
                        "gives an operator is short enough to say in one "
                        "breath: retry automatically while the failure "
                        "looks transient, park with a reason when it is "
                        "not, show the parking lot on a page, replay with "
                        "one button when a human judges the cause fixed. "
                        "What replay deliberately does NOT do is auto-"
                        "replay — a DLQ that empties itself is a retry "
                        "policy with extra steps, and the thundering herd "
                        "it can unleash on a recovering dependency is "
                        "exactly the synchronized-storm problem the "
                        "jitter note warned about. The human in the loop "
                        "is not ceremony; it is the rate limiter."
                    ),
                ),
            ],
        ),
        # ── 6. Scheduling (cron) ─────────────────────────────────────────────
        Section(
            id="scheduling-cron",
            title="Scheduling (cron)",
            blocks=[
                TextBlock(
                    kind="text",
                    id="cron-pitch",
                    text=(
                        "Deferred work has a sibling: work that runs with no "
                        "trigger at all — nightly digest emails, hourly "
                        "cleanups, every-minute metrics rolls. arq's answer "
                        "is cron jobs declared IN the worker settings, "
                        "parsed at boot into the same queue machinery the "
                        "tasks use: each entry is a function plus a "
                        "five-field schedule (month/day/weekday/hour/minute, "
                        "``None`` meaning every), and the worker computes "
                        "the next due time itself. This worker runs one: a "
                        "heartbeat that beats every minute and once at "
                        "startup, so a tour (or a health check) never waits "
                        "a full minute for proof of life:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cron-quote",
                    language="py",
                    caption="The schedule, in the worker settings: a function, every minute, plus once at boot.",
                    source="server/guide/worker.py",
                    snippet=(
                        "    cron_jobs = [cron(heartbeat, minute=None, run_at_startup=True)]"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cron-task-quote",
                    language="py",
                    caption="The scheduled task itself: a beat function like any other task.",
                    source="server/guide/worker.py",
                    snippet=(
                        "async def heartbeat(ctx: dict[str, Any]) -> None:\n"
                        "    \"\"\"The cron heartbeat: one beat a minute, plus one at boot for the tour.\"\"\"\n"
                        "    await _jobs().beat()"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cron-beat-quote",
                    language="py",
                    caption="The beat: stamp the last run, bump the counter — the schedule's pulse, readable.",
                    source="server/guide/data/jobs/arq_jobs.py",
                    snippet=(
                        "    async def beat(self) -> int:\n"
                        "        \"\"\"One beat: stamp the last-run ms, bump the counter, answer it.\"\"\"\n"
                        "        with _map_jobs_failures(\"beat\"):\n"
                        "            pool = await self._pool()\n"
                        "            await pool.set(HEARTBEAT_LAST_KEY, _now_ms())\n"
                        "            return int(await pool.incr(HEARTBEAT_BEATS_KEY))"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cron-read",
                    text=(
                        "Why cron-in-the-worker rather than the system "
                        "crontab you already have? Because the schedule and "
                        "the code it runs ship TOGETHER: the same image, "
                        "the same environment, the same redis, versioned in "
                        "the same repository — a crontab entry is "
                        "configuration on a machine the deploy does not "
                        "touch, drifting quietly until 3 a.m. one night. "
                        "In-app cron also gives the job what every job "
                        "here gets: the worker's retry posture, the "
                        "attempt trail, the dead-letter path when a "
                        "nightly job breaks for a week — a broken "
                        "crontab just silently stops. The tradeoffs are "
                        "real and worth naming: the schedule lives only "
                        "while a worker does (this stack's compose "
                        "restarts it; system cron needs no such care), "
                        "precision is only as good as the worker's poll "
                        "loop (a beat can land seconds late under load — "
                        "fine for digests, wrong for sub-second timing), "
                        "and EVERY worker replica runs the schedule unless "
                        "you shard by queue (arq de-duplicates a cron job "
                        "by its computed run time per worker, so N replicas "
                        "mean N beats — this demo runs ONE worker "
                        "replica, and the panel's heartbeat is honest "
                        "about it). The heartbeat pattern itself — a "
                        "tiny scheduled task whose only job is to prove "
                        "the scheduler lives — is worth stealing for any "
                        "worker you run: when the heartbeat stops, you "
                        "know within a minute that ALL scheduled work "
                        "stopped, not just one flaky task."
                    ),
                ),
            ],
        ),
        # ── 7. Email as a job ────────────────────────────────────────────────
        Section(
            id="email-as-a-job",
            title="Email as a job",
            blocks=[
                TextBlock(
                    kind="text",
                    id="email-pitch",
                    text=(
                        "Email is the canonical deferred workload — slow "
                        "(SMTP handshakes take seconds), flaky (recipient "
                        "servers greylist and throttle), and "
                        "receipt-carrying (a user who was told \"check your "
                        "inbox\" cares that it arrived). The pattern is four "
                        "beats: COMPOSE at the boundary (the request "
                        "validates shape and answers 201 with a job ticket), "
                        "DEFER the send (enqueue the draft as JSON), SEND in "
                        "the worker (where seconds of latency cost nothing), "
                        "and RECORD the outcome (a row a support human can "
                        "read). One wrinkle this repo makes explicit: the "
                        "worker validates the payload AGAIN — the queue has "
                        "more doors than your router (replay, other "
                        "enqueuers, a manual redis call), so the task "
                        "re-derives the contract, and a draft that fails "
                        "validation there is POISON, parked without "
                        "spending one retry:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="email-quote",
                    language="py",
                    caption="The worker's email task: validate again, park poison, or record the send.",
                    source="server/guide/worker.py",
                    snippet=(
                        "    try:\n"
                        "        draft = EmailDraft.model_validate_json(payload)\n"
                        "        _require_address(draft.to)\n"
                        "    except ValueError as exc:  # ValidationError derives from ValueError: both are poison\n"
                        "        verdict_reason = (\n"
                        "            f\"failure classified {classify_failure(exc)}: payload rejected by the \"\n"
                        "            \"worker's own validation — retrying would re-ask the same broken question\"\n"
                        "        )\n"
                        "        await park_dead_letter(\n"
                        "            _jobs(),\n"
                        "            job_id=str(ctx[\"job_id\"]),\n"
                        "            function_name=\"send_email\",\n"
                        "            attempts=int(ctx[\"job_try\"]),\n"
                        "            reason=verdict_reason,\n"
                        "            payload=payload,\n"
                        "            failed_at_ms=_now_ms(),\n"
                        "        )\n"
                        "        raise ValueError(\"email payload is malformed — parked as poison\") from exc"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="email-honesty",
                    text=(
                        "Full honesty about this demo's mailbox: there is NO "
                        "SMTP client here — the send is a RECORD into a "
                        "mailbox list, because the pattern is the lesson and "
                        "the transport is a topic of its own (topic 42 "
                        "wires aiosmtplib into exactly this seam and "
                        "nothing else changes). That seam is the point of "
                        "the recorder port: compose, defer, send, record "
                        "are decisions about WORK; which SMTP relay, which "
                        "credentials, which retry posture the transport "
                        "itself needs — those are decisions about a "
                        "DEPENDENCY, and swapping the recorder for a real "
                        "client is one adapter change. Two production notes "
                        "to carry when you make that swap: email sending "
                        "is idempotence-hostile (at-least-once delivery "
                        "can double-send — carry the job id in a header "
                        "and check it server-side if you must dedupe), and "
                        "the address rule belongs at BOTH ends even though "
                        "it looks redundant: the boundary check gives the "
                        "user a fast 422, the worker check keeps the queue "
                        "honest for every other door."
                    ),
                ),
            ],
        ),
        # ── 8. Two observability numbers ─────────────────────────────────────
        Section(
            id="two-observability-numbers",
            title="Two observability numbers",
            blocks=[
                TextBlock(
                    kind="text",
                    id="obs-pitch",
                    text=(
                        "A queue you cannot see is an outage you haven't "
                        "met yet. The full observability stack is topic "
                        "33's subject; for workers, two numbers catch most "
                        "incidents between them: QUEUE DEPTH (how many jobs "
                        "are waiting) and OLDEST-JOB AGE (how long the "
                        "longest-waiting job has waited). Depth alone lies "
                        "— a healthy batch system can sit at thousands "
                        "nightly — and age alone lies (one stuck job "
                        "makes it scream while throughput is fine); "
                        "TOGETHER they say nearly everything: depth rising "
                        "with rising age means the workers are gone or "
                        "stuck (the classic worker-crashed incident); "
                        "depth rising with YOUNG age means enqueue rate "
                        "spiked past capacity (shed, or scale); depth flat "
                        "with age climbing means one poison-shaped job is "
                        "blocking a single worker (a stuck task — the "
                        "timeout's job); both flat means the queue is "
                        "healthy. arq's design makes them nearly free — "
                        "the queue is a sorted set whose SCORE is each "
                        "job's due time, so depth is one ZCARD and the "
                        "oldest age is the lowest score:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-quote",
                    language="py",
                    caption="The two numbers from the queue's own geometry: ZCARD depth, lowest-score age.",
                    source="server/guide/data/jobs/arq_jobs.py",
                    snippet=(
                        "            depth = int(await pool.zcard(QUEUE_KEY))\n"
                        "            oldest = await pool.zrange(QUEUE_KEY, start=0, end=0, withscores=True)\n"
                        "            # zrange's withscores pairs are loosely typed (bytes|str|num); the\n"
                        "            # score is always numeric on a decoded pool — carry it across as one.\n"
                        "            oldest_score = float(oldest[0][1]) if oldest else None\n"
                        "            return QueueStatsRow(\n"
                        "                depth=depth,\n"
                        "                oldest_age_seconds=oldest_age_seconds(_now_ms(), oldest_score),\n"
                        "            )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-read",
                    text=(
                        "Two correctness details in that pure helper are "
                        "worth reading twice. An EMPTY queue answers age "
                        "``None`` — not zero, because \"the oldest job is "
                        "0 seconds old\" and \"there is no oldest job\" are "
                        "different facts, and a dashboard that cannot tell "
                        "them apart will hide the moment the queue drains "
                        "versus the moment it jammed. And a DEFERRED "
                        "retry's score sits in the future (it is the "
                        "scheduled run time), so the age clamps at zero — "
                        "a job politely waiting for its own backoff is not "
                        "\"waiting too long\", and conflating the two "
                        "teaches a team to ignore the alarm. The console's "
                        "stats endpoint serves exactly these two numbers "
                        "and the panel polls them live — enqueue a slow "
                        "job and watch the depth tick up and the age "
                        "start climbing while the worker is busy, then "
                        "watch both fall when it drains. The "
                        "attempt trail per job (section 4) is the "
                        "per-story view; these two are the queue's pulse; "
                        "topic 33 wires the same numbers into metrics and "
                        "alerts, where they belong on every worker you "
                        "run."
                    ),
                ),
            ],
        ),
        # ── 9. Terminal companion ────────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole topic, from a shell — three walks, a dead letter and its replay, the pulse, the comparison.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Seven stops, all against the running stack with "
                        "the worker container up: the happy path polled to "
                        "completion, the retry made visible in an attempt "
                        "trail, the full walk into the dead-letter queue "
                        "and back out by replay, the queue's two numbers, "
                        "the cron heartbeat's pulse, and the "
                        "BackgroundTasks-vs-worker comparison with honest "
                        "timings. Every command answers from the real "
                        "broker and the real worker process this topic "
                        "built."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-fast",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the happy path: enqueue fast, poll the snapshot to completion\n"
                        "JOB=$(curl -s -X POST localhost:8000/api/demo/jobs/enqueue/fast \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"jobId\"])')\n"
                        "sleep 1\n"
                        "curl -s localhost:8000/api/demo/jobs/jobs/$JOB \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(b[\"status\"], \"|\", b[\"attempts\"][-1][\"detail\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-retry",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the retry visible: fail_once walks two attempts on the policy's curve\n"
                        "JOB=$(curl -s -X POST localhost:8000/api/demo/jobs/enqueue/fail_once \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"jobId\"])')\n"
                        "sleep 2\n"
                        "curl -s localhost:8000/api/demo/jobs/jobs/$JOB \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin);\n"
                        "print(b[\"status\"]); [print(f\"  attempt {a[\\\"attempt\\\"]}: {a[\\\"outcome\\\"]} — {a[\\\"detail\\\"]}\") for a in b[\"attempts\"]]'\n"
                        "# → attempt 1: retry_scheduled (policy defers 0.25s) · attempt 2: succeeded"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-dlq",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the budget's edge: fail_always walks all three attempts, then parks\n"
                        "JOB=$(curl -s -X POST localhost:8000/api/demo/jobs/enqueue/fail_always \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"jobId\"])')\n"
                        "sleep 3\n"
                        "curl -s localhost:8000/api/demo/jobs/jobs/$JOB \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin);\n"
                        "print(b[\"status\"], \"| attempts:\", len(b[\"attempts\"]), \"| deadLettered:\", b[\"deadLettered\"])'\n"
                        "# stop 4 — the parking lot and the replay: fresh job id, attempts reset\n"
                        "ENTRY=$(curl -s localhost:8000/api/demo/jobs/dlq \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"entries\"][0][\"entryId\"])')\n"
                        "curl -s -X POST localhost:8000/api/demo/jobs/dlq/$ENTRY/replay \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"replayed as:\", b[\"jobId\"])'\n"
                        "curl -s localhost:8000/api/demo/jobs/dlq \\\n"
                        "  | python3 -c 'import json,sys; e=json.load(sys.stdin)[\"entries\"][0]; print(\"entry kept, replayedAs:\", e[\"replayedAs\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-stats",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the two numbers: enqueue a slow job, watch depth tick and age climb\n"
                        "curl -s -X POST localhost:8000/api/demo/jobs/enqueue/slow > /dev/null\n"
                        "for i in 1 2 3; do\n"
                        "  curl -s localhost:8000/api/demo/jobs/stats \\\n"
                        "    | python3 -c 'import json,sys; b=json.load(sys.stdin); print(f\"depth {b[\\\"depth\\\"]} · oldest {b[\\\"oldestAgeSeconds\\\"]}s\")'\n"
                        "  sleep 0.7\n"
                        "done"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-heartbeat",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — the cron heartbeat: last beat and the running count (beats while you read)\n"
                        "curl -s localhost:8000/api/demo/jobs/heartbeat | python3 -m json.tool\n"
                        "# stop 7 — the comparison: same workload, two homes, honest timings\n"
                        "curl -s -X POST localhost:8000/api/demo/jobs/compare \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"fired in\", round(b[\"handlerDurationMs\"],1), \"ms\")'\n"
                        "sleep 2.5\n"
                        "curl -s localhost:8000/api/demo/jobs/compare \\\n"
                        "  | python3 -c 'import json,sys;\n"
                        "runs=json.load(sys.stdin)[\"runs\"][:2];\n"
                        "[print(f\"{r[\\\"side\\\"]:>10}: handoff {r[\\\"handoffDurationMs\\\"]:>6.1f}ms · work {r[\\\"workDurationMs\\\"]:>6.1f}ms — {r[\\\"ranOn\\\"]}\") for r in runs]'\n"
                        "# in_process handoff ≈ ms (a list append after the response);\n"
                        "# queued handoff ≈ the worker's poll interval — the honest price of the queue"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stops 1–3 are the lifecycle in one breath: a job "
                        "that needed no retry, a job that needed exactly "
                        "one (with the policy's 0.25 s pause visible "
                        "between the trail's rows), and a job that spent "
                        "the whole budget and parked. Stop 4 is the "
                        "operational loop — the parking lot read, the "
                        "replay minting a fresh id, the audit entry kept. "
                        "Stop 5 is the queue's pulse while work waits and "
                        "drains; stop 6 is the scheduler's; stop 7 times "
                        "the same work in both homes and shows what each "
                        "charges for the handoff. That closes topic 29 — "
                        "and with it the media-realtime group and Phase "
                        "8: requests, streams, and now the work that "
                        "outlives them both. Phase 9 turns to the "
                        "platform itself — errors, dependencies, "
                        "architecture, observability."
                    ),
                ),
            ],
        ),
    ],
)
