"""Topic 35 — Debugging: the mindset, then the instruments, honestly.

The topic teaches debugging as a discipline (reproduce, isolate,
hypothesize, verify) and then walks the instruments in escalating power:
print and its limits against the structured logging this repo really runs
(topic 33's pipeline, quoted), the stdlib debugger pdb, the sampling
profiler py-spy (NOT installed here — concept-first, honest recipes, and
one demo that produces the evidence py-spy would sample from outside),
tracemalloc and the heap (stdlib, used for a REAL allocation measurement),
pyinstrument (not installed — concept-first again), and what changes when
the bug is in production (logs, metrics, traces — topic 33's instruments
read with a debugger's eye). The demo is debug:stall, INLINE in the py-spy
section: a slow endpoint diagnosed with real measurements — four bounded
phases, loop-lag probes, a concurrent REAL /api/health, a tracemalloc
window, and the request's own correlated log rows — never wedging the
shared event loop.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="debugging",
    title="Debugging",
    subtitle=(
        "Finding out why, as a discipline: the reproduce-isolate-hypothesize-"
        "verify loop, why print loses to structured logs (this repo's real "
        "pipeline quoted), the stdlib debugger pdb, the sampling profiler "
        "py-spy taught concept-first beside a live stall-diagnosis demo with "
        "real loop-lag and concurrent-health measurements, tracemalloc and "
        "the heap for memory questions, pyinstrument for focused profiling, "
        "and what debugging becomes in production — logs, metrics, and "
        "traces read with a debugger's eye."
    ),
    group="platform",
    order=35,
    sections=[
        # ── 1. Mindset ────────────────────────────────────────────────────
        Section(
            id="mindset",
            title="Mindset",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dbg-mindset-pitch",
                    text=(
                        "Debugging is not the art of staring at code until "
                        "confession; it is experimental method applied to a "
                        "running system. You have a system that behaved "
                        "badly, you do not know why, and every debugging "
                        "technique — print, logs, breakpoints, profilers, "
                        "memory snapshots — is just a way of asking the "
                        "system a question and trusting the answer more than "
                        "you trust your mental model. The model is the thing "
                        "that broke: somewhere you believe something about "
                        "the code that is false, and the bug is the gap "
                        "between belief and reality. That framing sets the "
                        "posture for this whole topic: the goal is never "
                        "'make the symptom stop', it is 'find the false "
                        "belief' — because the symptom is one instance of "
                        "the belief being wrong, and the wrong belief will "
                        "produce more instances the moment you look away."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-mindset-loop-framing",
                    text=(
                        "Every effective debugging session, whatever the "
                        "tool, runs the same four-step loop — and naming the "
                        "steps matters because knowing WHICH step you are in "
                        "tells you which tool to pick up:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="dbg-mindset-loop",
                    ordered=True,
                    items=[
                        "Reproduce — make the failure happen on demand; a "
                        "bug you cannot summon cannot be studied, and a "
                        "flaky bug is usually a repro you have not "
                        "understood yet.",
                        "Isolate — shrink the repro: fewer inputs, shorter "
                        "path, smaller data, until only the guilty "
                        "mechanism remains.",
                        "Hypothesize — state a falsifiable cause in one "
                        "sentence ('the retry double-spends because the "
                        "offset is committed before the work'), never "
                        "'maybe it's caching'.",
                        "Verify — design an observation that would come out "
                        "DIFFERENT if the hypothesis were false, make it, "
                        "and let the system vote.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="dbg-mindset-binary-search",
                    text=(
                        "Isolation deserves its own habit because it is "
                        "where time dies. The workhorse is binary search at "
                        "every scale: bisect the input data (does it fail on "
                        "the first half?), bisect the code path (does an "
                        "older commit fail?), bisect the request's journey "
                        "(does the handler see the bad value, or did it "
                        "arrive bad?). Each halving is one question that "
                        "removes half the search space, and ten questions "
                        "remove 99.9 percent of it. The git twin is 'git "
                        "bisect' — feed it a good and a bad commit and it "
                        "drives the halving for you. What makes isolation "
                        "stick as discipline is writing the minimal repro "
                        "down: a failing test that reproduces the bug is "
                        "the isolate step made permanent, and this "
                        "repository's whole verification posture — every "
                        "fix lands with the test that would have caught it "
                        "— exists so the loop's last step leaves an "
                        "artifact behind."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-mindset-taxonomy-pitch",
                    text=(
                        "Before touching any exotic tool: a huge share of "
                        "server bugs are failures your framework ALREADY "
                        "caught, classified, and logged — if you know where "
                        "to look, the debugging started before you did. "
                        "This app's error taxonomy is exactly that: eight "
                        "failure kinds, one envelope, and one handler per "
                        "class that logs the failure with the request id "
                        "before answering. The typed-application-error "
                        "handler is the cleanest instance, and it is worth "
                        "reading as a debugging instrument, not just error "
                        "handling:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-mindset-handler-quote",
                    language="py",
                    caption="Failures log themselves: event name, request id, kind, message.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:\n"
                        "    \"\"\"AppError → its mapped status + envelope; logged with the request id.\"\"\"\n"
                        "    logger.warning(\n"
                        "        \"app_error\",\n"
                        "        request_id=resolve_request_id(request),\n"
                        "        kind=exc.kind.value,\n"
                        "        message=exc.message,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-mindset-correlation",
                    text=(
                        "The request id in that log call is the debugging "
                        "link that makes everything else in this topic "
                        "work. A failure without correlation is an "
                        "anecdote; a failure stamped with the id of the "
                        "request that produced it is a fact you can walk: "
                        "the client reports the envelope's requestId, that "
                        "id retrieves the failure row AND the access-log "
                        "row for the same request, and every intermediate "
                        "line the request logged joins the same thread. "
                        "When a bug report arrives saying 'POST /api/posts "
                        "gave me a 409', the first move is not the "
                        "debugger — it is the id, then the logs. The rest "
                        "of this topic is what you reach for when the logs "
                        "answer 'the request took 900ms and nothing "
                        "failed', because that is the moment the question "
                        "changes from what happened to where did the time "
                        "go."
                    ),
                ),
            ],
        ),
        # ── 2. print limits ───────────────────────────────────────────────
        Section(
            id="print-limits",
            title="print limits",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dbg-print-pitch",
                    text=(
                        "Print debugging — dropping 'print(x)' into the "
                        "suspicious function and running it — is the first "
                        "tool everyone reaches for, and it is a fine first "
                        "tool: it is immediate, it needs no setup, and for "
                        "a pure function with three inputs it often "
                        "settles the hypothesis in one run. Nothing in "
                        "this section is a complaint about using print on "
                        "a Tuesday afternoon. The section's point is that "
                        "print has STRUCTURAL limits that show up exactly "
                        "when debugging gets hard, and knowing them tells "
                        "you when to switch instruments."
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="dbg-print-limits",
                    ordered=False,
                    items=[
                        "No identity — a bare 'here 2' line cannot be "
                        "joined to the request that produced it, so "
                        "concurrent traffic turns your console into an "
                        "unlabeled interleaving.",
                        "No levels or lifecycle — debug prints ship to "
                        "production stdout or get deleted before the "
                        "commit, and both outcomes are wrong.",
                        "Mutation by observing — adding prints means "
                        "editing the code under test, re-deploying the "
                        "experiment, and hoping the edit did not move the "
                        "bug (Heisenbugs love this).",
                        "Cost per question — every new question is another "
                        "edit-and-rerun cycle, while a debugger asks "
                        "dozens of questions in one paused process.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="dbg-print-structured-pitch",
                    text=(
                        "The fix for the first two limits is not 'better "
                        "print'; it is the structured logging this app "
                        "already runs — topic 33 built it and this topic "
                        "reads it. One JSON object per line, an event name, "
                        "a level, a timestamp, and the request id merged "
                        "into every line the request's code writes. The "
                        "pipeline is six processors in one configure call, "
                        "and it is the baseline every debugging technique "
                        "in this topic stands on:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-print-pipeline-quote",
                    language="py",
                    caption="The structured pipeline every line rides: merge, stamp, fold, capture, render.",
                    source="server/guide/core/logging.py",
                    snippet=(
                        "    structlog.configure(\n"
                        "        processors=[\n"
                        "            structlog.contextvars.merge_contextvars,\n"
                        "            structlog.processors.add_log_level,\n"
                        "            structlog.processors.TimeStamper(fmt=\"iso\"),\n"
                        "            structlog.processors.format_exc_info,\n"
                        "            recent_log().capture,\n"
                        "            structlog.processors.JSONRenderer(),\n"
                        "        ],\n"
                        "        wrapper_class=structlog.make_filtering_bound_logger(_numeric_level(level)),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-print-what-a-line-gives",
                    text=(
                        "Read what one such line gives the debugger that "
                        "print cannot. The access-log middleware writes "
                        "exactly one http_request event per request — "
                        "method, path, status, duration, id — in a finally "
                        "so even crashed requests are recorded. That "
                        "duration field alone answers the profiler's first "
                        "question (was it actually slow?) for every "
                        "request the server has ever served, no re-run "
                        "required:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-print-access-quote",
                    language="py",
                    caption="One http_request event per request: the duration field is a free profile.",
                    source="server/guide/presentation/middleware/request_log.py",
                    snippet=(
                        "        try:\n"
                        "            await self.app(scope, receive, send_observing)\n"
                        "        finally:\n"
                        "            duration_ms = round((time.perf_counter() - started) * 1000, 1)\n"
                        "            logger.info(\n"
                        "                \"http_request\",\n"
                        "                method=method,\n"
                        "                path=path,\n"
                        "                status=status[0] if status else 0,\n"
                        "                duration_ms=duration_ms,\n"
                        "                request_id=request_id[0] if request_id else \"\",\n"
                        "            )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-print-failure-lines",
                    text=(
                        "And when the failure is an exception nobody "
                        "caught, the last-resort handler logs the single "
                        "richest debugging artifact this app produces: the "
                        "type name and the full traceback, folded into the "
                        "same structured line, under the request's id. A "
                        "print cannot capture a traceback you did not know "
                        "was coming; the pipeline folds whatever "
                        "exc_info is attached at error time:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-print-unhandled-quote",
                    language="py",
                    caption="The one error-level producer: type name and traceback, request-correlated.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "    request_id = resolve_request_id(request)\n"
                        "    logger.error(\n"
                        "        \"unhandled_exception\",\n"
                        "        request_id=request_id,\n"
                        "        error=type(exc).__name__,\n"
                        "        exc_info=exc,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-print-coda",
                    text=(
                        "So the practical ladder is: print for thirty-"
                        "second hypotheses in pure code, structured logs "
                        "for anything that involves a request, other "
                        "processes, or production — and the sections that "
                        "follow for the questions neither can answer, "
                        "which come in exactly two flavors: questions "
                        "about STATE at a moment (what did the variables "
                        "actually hold right there?), answered by the "
                        "debugger, and questions about TIME (where did "
                        "the 900ms go?), answered by profilers. Python's "
                        "standard library ships the state tool; the time "
                        "tools are one uv command away, and this guide "
                        "teaches them honestly — concept-first, with the "
                        "real commands, and no pretend integrations."
                    ),
                ),
            ],
        ),
        # ── 3. pdb/debugger ───────────────────────────────────────────────
        Section(
            id="pdb-debugger",
            title="pdb/debugger",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dbg-pdb-pitch",
                    text=(
                        "A debugger is a program that pauses your program "
                        "at a chosen point and lets you interrogate the "
                        "live process: inspect variables, evaluate "
                        "expressions, walk the stack. Python ships one in "
                        "the standard library — pdb — so there is nothing "
                        "to install and nothing to configure; this "
                        "repository deliberately has no debugger wiring of "
                        "its own to quote, and needs none, because the "
                        "entry points are language-level. The modern door "
                        "is the breakpoint() builtin: call it anywhere and "
                        "the running process drops into the debugger at "
                        "that line, with the whole local scope in hand."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-pdb-session-pitch",
                    text=(
                        "The working vocabulary is about ten commands, and "
                        "a session reads better than a table. Below is a "
                        "genuine pdb session shape against a deliberately "
                        "broken pure function — the commands are real, "
                        "runnable in any Python 3.13 process:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-pdb-session",
                    language="bash",
                    source=None,
                    snippet=(
                        "$ python3 -m pdb demo_broken.py\n"
                        "> /repo/demo_broken.py(2)<module>()\n"
                        "-> def average(values):\n"
                        "(Pdb) break demo_broken.py:4      # stop before the return line\n"
                        "(Pdb) continue\n"
                        "> /repo/demo_broken.py(4)average()\n"
                        "-> return sum(values) / len(values)\n"
                        "(Pdb) p values                     # print the live local\n"
                        "[]\n"
                        "(Pdb) p len(values)                # any expression, really\n"
                        "0\n"
                        "(Pdb) where                        # the stack that got here\n"
                        "  /repo/demo_broken.py(8)<module>()\n"
                        "> /repo/demo_broken.py(4)average()\n"
                        "(Pdb) continue                     # release: ZeroDivisionError surfaces"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-pdb-vocabulary-framing",
                    text=(
                        "That session used most of the daily vocabulary — "
                        "the commands worth carrying, with what each is "
                        "FOR:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="dbg-pdb-vocabulary",
                    ordered=False,
                    items=[
                        "n / s — next stays in the current function; step "
                        "dives INTO the next call — the pair that walks "
                        "code one decision at a time.",
                        "p / pp — print one expression (pretty-printed for "
                        "containers) against the paused scope, the "
                        "question-asking primitive.",
                        "break / tbreak — stop at a file:line (tbreak once "
                        "only) — how you park near the crime instead of "
                        "stepping to it.",
                        "where / up / down — the call stack, and movement "
                        "in it — how you find WHO passed the bad value "
                        "down.",
                        "until / return — run to the next line past loops, "
                        "or to the function's return — skipping the boring "
                        "middle of a suspect function.",
                        "q — quit and kill the process — a debugging "
                        "session is allowed to end in a murder.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="dbg-pdb-postmortem",
                    text=(
                        "The two moves that earn their own paragraphs: "
                        "post-mortem and breakpoints-in-situ. Post-mortem "
                        "is for the crash you keep missing — run 'python3 "
                        "-m pdb -c continue script.py' and when the "
                        "exception fires, pdb stops INSIDE the dying "
                        "frame with the full traceback live: every local "
                        "on the path from main to the crash is "
                        "inspectable, which no log line and no print "
                        "gives you. Breakpoint-in-situ is 'breakpoint()' "
                        "dropped at the exact suspicious line of a test "
                        "or script — under pytest, run with '-s' so the "
                        "debugger keeps your terminal (pytest captures "
                        "stdout otherwise, and a debugger behind captured "
                        "output is a very quiet room)."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-pdb-async-honesty",
                    text=(
                        "The honest caveat for this stack: pdb pauses ONE "
                        "thread of a process, and a FastAPI server is an "
                        "event loop plus a threadpool plus worker "
                        "processes — pausing a uvicorn worker inside a "
                        "breakpoint() freezes every request that worker "
                        "owns, health checks included, and anything with "
                        "a timeout will start failing around you. That is "
                        "why breakage-in-place debugging on a LIVE server "
                        "is mostly a local-dev move; against a running "
                        "service the observability topic's instruments "
                        "(request ids, the log ring, the access log) ARE "
                        "the debugger, and the py-spy section adds the "
                        "tool that observes a running process WITHOUT "
                        "pausing it. Use pdb where the repro is yours — "
                        "tests, scripts, a local boot of the app with one "
                        "worker — and measure the running thing instead "
                        "of freezing it."
                    ),
                ),
            ],
        ),
        # ── 4. py-spy ─────────────────────────────────────────────────────
        Section(
            id="py-spy",
            title="py-spy",
            lead="This section carries the topic's demo — the stall diagnosis.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dbg-pyspy-pitch",
                    text=(
                        "py-spy is a sampling profiler: it attaches to an "
                        "ALREADY-RUNNING Python process from outside, reads "
                        "the interpreter's stack for every thread many "
                        "times a second, and reports where the samples "
                        "landed — no code changes, no restarts, and "
                        "crucially no pausing (it samples; a debugger "
                        "freezes). It answers the two questions a slow "
                        "server poses: 'py-spy dump' photographs every "
                        "thread's current stack once — the go-to when a "
                        "process is wedged and you want to see WHERE "
                        "without touching it — and 'py-spy top' streams "
                        "live samples like htop for Python, showing which "
                        "functions eat CPU right now. It exists precisely "
                        "because breakpoint-debugging a production process "
                        "is usually not an option."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-pyspy-honest",
                    text=(
                        "Honest position, stated plainly: py-spy is NOT "
                        "installed in this repo and no integration is "
                        "pretended below — it is a host-side tool you run "
                        "with 'uv tool run py-spy …' against a process id, "
                        "one command, zero project dependencies, which is "
                        "exactly why this guide teaches it without adding "
                        "it. What CAN be shown for real, from inside, is "
                        "the evidence py-spy would sample from outside: "
                        "what a profiler classifies — waiting on I/O, "
                        "burning CPU off the loop, or starving the loop — "
                        "measured live. That is this section's demo: a "
                        "slow endpoint that diagnoses ITSELF with real "
                        "instruments while you watch. The core instrument "
                        "is loop-lag sampling, and it is five lines worth "
                        "understanding deeply:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-pyspy-lag-quote",
                    language="py",
                    caption="Loop-lag sampling: a sleep's overshoot is the loop's starvation, measured.",
                    source="server/guide/domain/demos/debug_stall.py",
                    snippet=(
                        "async def _loop_lag_samples(*, ticks: int, interval_s: float) -> list[float]:\n"
                        "    \"\"\"Sample event-loop lag: each tick's sleep overshoot beyond its interval.\n"
                        "\n"
                        "    A healthy loop fires each sleep within microseconds of schedule; a loop\n"
                        "    blocked by sync code cannot fire ANY timer until the block ends, so the\n"
                        "    in-flight tick overshoots by (up to) the block's whole duration. This is\n"
                        "    the same measurement asyncio's own debug mode (slow-callback warnings)\n"
                        "    performs.\n"
                        "    \"\"\"\n"
                        "    samples: list[float] = []\n"
                        "    for _ in range(ticks):\n"
                        "        before = time.perf_counter()\n"
                        "        await asyncio.sleep(interval_s)\n"
                        "        samples.append((time.perf_counter() - before - interval_s) * 1000)\n"
                        "    return samples"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-pyspy-phases-pitch",
                    text=(
                        "A sleep scheduled for 25 milliseconds that fires "
                        "after 120 told you the loop was unavailable for "
                        "95 of them — that overshoot is exactly what "
                        "asyncio's own debug mode warns about, measured by "
                        "hand. The demo runs four bounded phases through "
                        "this instrument, one per way a handler can be "
                        "slow, each phase a real awaitable the panel "
                        "executes while a lag probe and a REAL concurrent "
                        "GET /api/health (driven through the app at the "
                        "ASGI boundary, the obs-trace fan-out's channel) "
                        "run alongside it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-pyspy-phases-quote",
                    language="py",
                    caption="The four ways a handler can be slow — each bounded, each a real awaitable.",
                    source="server/guide/domain/demos/debug_stall.py",
                    snippet=(
                        "async def _baseline_work() -> None:\n"
                        "    \"\"\"One scheduler yield — the cheapest thing a handler can do.\"\"\"\n"
                        "    await asyncio.sleep(0)\n"
                        "\n"
                        "\n"
                        "async def _async_stall_work() -> None:\n"
                        "    \"\"\"A bounded await: the request is slow, the loop stays free.\"\"\"\n"
                        "    await asyncio.sleep(ASYNC_STALL_SECONDS)\n"
                        "\n"
                        "\n"
                        "async def _threadpool_work() -> None:\n"
                        "    \"\"\"A bounded blocking call done right: offloaded via asyncio.to_thread.\"\"\"\n"
                        "    await asyncio.to_thread(_burn_cpu_ms, BLOCK_BUDGET_MS)\n"
                        "\n"
                        "\n"
                        "async def _on_loop_work() -> None:\n"
                        "    \"\"\"The anti-pattern, bounded on purpose: sync CPU run directly ON the loop.\"\"\"\n"
                        "    _burn_cpu_ms(BLOCK_BUDGET_MS)"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="debug:stall",
                    title="The stall diagnosis",
                    description=(
                        "GET /api/demo/debug/stall runs four bounded "
                        "phases and reports REAL measurements for each: "
                        "elapsed from perf_counter, loop lag from a "
                        "concurrent probe task's sleep overshoot, and a "
                        "REAL internal GET /api/health driven through "
                        "the app WHILE the phase ran — plus a genuine "
                        "tracemalloc window and this request's own log "
                        "rows from the recent-events ring, correlated by "
                        "the x-request-id the response echoes. The read "
                        "that matters: async-await-stall is the slowest "
                        "phase yet its concurrent health answers in "
                        "single-digit milliseconds (slow request, "
                        "healthy loop), while the same 120ms of CPU run "
                        "directly on the loop starves the lag probe and "
                        "makes health wait out the whole block — the "
                        "classification py-spy top would give you from "
                        "outside. Every duration is bounded by design "
                        "(≤350ms), so the shared dev loop is never "
                        "wedged; the health answers before and after "
                        "prove it."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-pyspy-demo-reading",
                    text=(
                        "Read the panel the way a profiler would: group by "
                        "verdict, not by size. The 350ms async phase is "
                        "'slow' and harmless — py-spy would show it as a "
                        "parked stack waiting on I/O, and the right fix "
                        "is not code speed but a faster dependency or a "
                        "cache. The threadpool phase is real CPU, "
                        "contained — visible in this request's elapsed, "
                        "invisible in the lag probe (the GIL still taxes "
                        "other threads a little, and the panel's health "
                        "row shows that honestly). The on-loop phase is "
                        "the pathology: identical CPU budget, but the lag "
                        "probe's max jumps to nearly the whole block and "
                        "the concurrent health request waited ~120ms for "
                        "a handler that normally answers in two. One "
                        "request's block, everyone's latency. The "
                        "endpoint behind the panel is the usual thin "
                        "router:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-pyspy-router-quote",
                    language="py",
                    caption="One GET, the payload builder, a declared response model.",
                    source="server/guide/presentation/routers/demo/debug.py",
                    snippet=(
                        "@router.get(STALL_PATH, response_model=StallPanel)\n"
                        "async def read_stall_panel(request: Request) -> StallPanel:\n"
                        "    \"\"\"Serve the live stall panel: four bounded phases, measured evidence.\"\"\"\n"
                        "    return await build_stall_payload(\n"
                        "        app=request.app,\n"
                        "        request_id=resolve_request_id(request),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-pyspy-test-pitch",
                    text=(
                        "The measurements are pinned by the endpoint's "
                        "test — timing asserts are deliberately RELATIVE "
                        "or generously floored, because absolute timing "
                        "on shared CI hardware is noise, while the "
                        "starvation contrast is physics: a blocked loop "
                        "cannot fire timers, so the on-loop phase's lag "
                        "maximum must dominate the contained phase's, and "
                        "a health request concurrent with the block must "
                        "wait longer than one concurrent with a mere "
                        "await:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-pyspy-test-quote",
                    language="py",
                    caption="The endpoint test pins the contrast the demo exists to show.",
                    source="server/tests/demo/test_debug_stall_endpoint.py",
                    snippet=(
                        "    assert on_loop[\"loopLagMaxMs\"] > threadpool[\"loopLagMaxMs\"]\n"
                        "    assert on_loop[\"loopLagMaxMs\"] >= 40.0\n"
                        "    assert on_loop[\"concurrentHealthMs\"] > async_row[\"concurrentHealthMs\"]\n"
                        "    assert on_loop[\"concurrentHealthStatus\"] == 200"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-pyspy-recipe-pitch",
                    text=(
                        "And the real tool, honestly, as the recipe you "
                        "would run from the host against this very stack "
                        "— 'uv tool run' executes it without adding it to "
                        "the project, and the pid comes from the "
                        "container. Note the --nonblocking flag on dump: "
                        "the default briefly pauses the target, and on a "
                        "shared live stack you take the photograph "
                        "without waking the subject:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-pyspy-recipe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# The recipe this repo would run (py-spy NOT installed here — honest recipe):\n"
                        "# 1. find the server pid inside the dev container\n"
                        "docker exec fastapi_developers_guide_server_dev pgrep -f 'uvicorn guide.main'\n"
                        "# 2. photograph every thread's stack, without pausing the process\n"
                        "docker exec fastapi_developers_guide_server_dev \\\n"
                        "  sh -c 'uv tool run py-spy dump --pid $(pgrep -f \"uvicorn guide.main\") --nonblocking'\n"
                        "# 3. live view: which function eats CPU right now (Ctrl-C to stop)\n"
                        "docker exec -it fastapi_developers_guide_server_dev \\\n"
                        "  sh -c 'uv tool run py-spy top --pid $(pgrep -f \"uvicorn guide.main\")'\n"
                        "# a flamegraph, if you want the whole minute as a picture:\n"
                        "# py-spy record -o profile.svg --pid <pid> --duration 30"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-pyspy-coda",
                    text=(
                        "What the demo and the tool agree on is the "
                        "taxonomy of slow: WAITING (async stall — parked "
                        "stack, fix the wait), COMPUTING (threadpool — "
                        "hot stack, fix the algorithm or the amount), and "
                        "BLOCKING (on-loop — one hot stack poisoning "
                        "every request, fix the containment first). Every "
                        "slow-endpoint incident is one of those three or "
                        "a mix, and the mix is why you measure before "
                        "optimizing — the performance topic's first law, "
                        "seen here from the debugging side."
                    ),
                ),
            ],
        ),
        # ── 5. tracemalloc/heap ───────────────────────────────────────────
        Section(
            id="tracemalloc-heap",
            title="tracemalloc/heap",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dbg-heap-pitch",
                    text=(
                        "Memory bugs have a different shape from time "
                        "bugs: nothing crashes, nothing logs, and the "
                        "symptom is a slowly rising RSS number on a graph "
                        "weeks later. Python's mental model first — the "
                        "runtime allocates every object on a private "
                        "heap, frees them primarily by REFERENCE COUNTING "
                        "(the count hits zero, the object dies "
                        "immediately), with a cyclic garbage collector "
                        "sweeping the mutual-reference islands counting "
                        "cannot reach (the python-runtime topic walks "
                        "this machinery). Two failure shapes follow. A "
                        "LEAK is objects that stay reachable forever — "
                        "an unbounded cache, a list that only grows, a "
                        "callback registry nobody unsubscribes from. "
                        "CHURN is objects that die almost immediately — "
                        "fast, harmless individually, but each allocation "
                        "costs time and each survivor-tide pressures the "
                        "heap at peak. Different diseases, different "
                        "cures, and the first debugging step is telling "
                        "them apart."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-heap-tracemalloc-pitch",
                    text=(
                        "The tool that tells them apart is tracemalloc — "
                        "standard library, no install. It hooks the "
                        "allocator and records, for every allocation made "
                        "while tracing, the traceback of the line that "
                        "made it. You get two numbers per window — "
                        "current (bytes still alive) and peak (the "
                        "high-water mark inside the window) — and, more "
                        "powerful, per-line statistics that rank which "
                        "source lines hold the memory. The stall demo "
                        "already ran one real window for you; this is "
                        "the entire measurement:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-heap-window-quote",
                    language="py",
                    caption="A real tracemalloc window: start, do bounded work, read current and peak, stop.",
                    source="server/guide/domain/demos/debug_stall.py",
                    snippet=(
                        "    tracemalloc.start()\n"
                        "    try:\n"
                        "        rows = [\n"
                        "            {\"id\": index, \"kind\": \"demo-row\", \"values\": [index, index * 2, index * 3]}\n"
                        "            for index in range(ALLOCATION_OBJECTS)\n"
                        "        ]\n"
                        "        current, peak = tracemalloc.get_traced_memory()\n"
                        "    finally:\n"
                        "        tracemalloc.stop()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-heap-reading",
                    text=(
                        "Read the demo's allocation row with the "
                        "taxonomy: two thousand small dict rows, current "
                        "in the hundreds of kilobytes, peak a hair above "
                        "current — the signature of a working set that "
                        "survives the window (not churn). If instead peak "
                        "towers over current, the window allocated and "
                        "freed a tower transiently — churn, and the fix "
                        "is fewer or smaller transients (generators "
                        "instead of lists, batched reads). If current "
                        "CLIMBS window over window and never falls, that "
                        "is the leak signature — and the follow-up is "
                        "'snapshot = tracemalloc.take_snapshot()' at two "
                        "moments, diff the snapshots' statistics, and the "
                        "top-growing file:line names the culprit with no "
                        "guessing. One honest cost note, visible in the "
                        "demo's design: tracing slows every allocation it "
                        "watches, so the window opens late and closes "
                        "early — in production you would enable it for "
                        "diagnosis windows, not forever."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-heap-gc-pitch",
                    text=(
                        "The module beside tracemalloc is gc — the "
                        "garbage collector's control panel and a "
                        "debugger in its own right. It answers 'what is "
                        "KEEPING this alive', the question reference "
                        "counting hides from you, and its two calls are "
                        "a complete first kit:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-heap-gc-recipe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# The leak-hunting kit (stdlib gc, run inside any Python process):\n"
                        "python3 -c '\n"
                        "import gc, sys\n"
                        "print(len(gc.get_objects()), \"objects tracked\")   # the heap census\n"
                        "print(gc.get_count(), \"(gen0, gen1, gen2) pending\")  # collector pressure'\n"
                        "# find back-references to a suspect object (who is holding it?):\n"
                        "# gc.get_referrers(obj)  — the leak question, answered directly\n"
                        "# sys.getrefcount(obj)   — how many references are pinning it (returns +1)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-heap-coda",
                    text=(
                        "Where memory debugging usually ENDS in this "
                        "codebase's world: servers do not leak often when "
                        "they build on request-scoped discipline — every "
                        "request's state dies with the request, the "
                        "recent-events ring is capacity-bounded BY "
                        "design, caches carry TTLs, and the leak "
                        "candidates are always the deliberate globals "
                        "(an in-memory store that grows, a registry that "
                        "never shrinks). The discipline worth internal-"
                        "izing: anything process-global that can grow "
                        "must have a bound someone chose — that single "
                        "rule prevents more memory incidents than any "
                        "tool catches."
                    ),
                ),
            ],
        ),
        # ── 6. pyinstrument profiling ─────────────────────────────────────
        Section(
            id="pyinstrument-profiling",
            title="pyinstrument profiling",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dbg-prof-pitch",
                    text=(
                        "Between logs (coarse: one duration per request) "
                        "and py-spy (outside-in samples of a live "
                        "process) sits the deterministic profiler: run "
                        "the suspicious code under instrumentation and "
                        "get a tree of where its time went, function by "
                        "function. Python ships cProfile in the stdlib; "
                        "the tool this section teaches is pyinstrument, "
                        "and the honest position is the same as py-spy's: "
                        "NOT installed here, no integration pretended — "
                        "it is a one-command tool ('uv tool run "
                        "pyinstrument') you point at a script when you "
                        "need it, which keeps the dependency surface this "
                        "repo curates clean."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-prof-why-sampling",
                    text=(
                        "Why teach pyinstrument over the stdlib cProfile? "
                        "Two reasons that matter for servers. First, "
                        "measurement overhead: cProfile hooks EVERY "
                        "function call, and a call-heavy web request "
                        "under cProfile can double or triple in wall time "
                        "— the profiler distorts the thing it measures — "
                        "while pyinstrument samples at intervals "
                        "(statistical profiling), so overhead stays small "
                        "and proportions stay honest. Second, the output: "
                        "pyinstrument reports an inclusive-time TREE with "
                        "the honest note that sampling is statistical, "
                        "and it marks 'await' time explicitly — for an "
                        "async app, distinguishing 'inside this "
                        "coroutine, waiting' from 'this function, "
                        "computing' is exactly the stall demo's taxonomy "
                        "rendered per function. cProfile's flat "
                        "cumulative table makes you do that "
                        "interpretation by hand."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-prof-recipe-pitch",
                    text=(
                        "The recipe, honestly marked, against this "
                        "stack's own machinery — profile the test suite's "
                        "slowest slice or a small script that drives the "
                        "real app, and read the tree top-down hunting for "
                        "the first suspicious frame:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-prof-recipe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# The recipe this repo would run (pyinstrument NOT installed — honest recipe):\n"
                        "# 1. profile a script that exercises the slow path (uv tool run, no dep added)\n"
                        "uv tool run pyinstrument -o profile.html drive_slow_path.py\n"
                        "# 2. or profile the server handling real traffic for 30s\n"
                        "#    pyinstrument --from-single-thread targets a specific thread\n"
                        "#    py-spy record (previous section) is the non-attaching alternative\n"
                        "# 3. read profile.html top-down: the first wide frame you don't\n"
                        "#    recognize by name is where the next question goes\n"
                        "# the stdlib fallback, no install at all:\n"
                        "python3 -m cProfile -s cumulative script.py | head -25"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-prof-coda",
                    text=(
                        "The reading skill is the same one the stall "
                        "panel trained, one level deeper: in an inclusive "
                        "tree, a wide frame that is mostly its CHILDREN "
                        "is a caller passing cost through (fix below it); "
                        "a wide frame that is mostly ITSELF is the hot "
                        "code (fix here); and in async code a frame that "
                        "is mostly 'await' is latency, not CPU — take it "
                        "out of the CPU conversation entirely. Which "
                        "closes the loop with the guide's standing rule, "
                        "the performance topic's first law and this "
                        "topic's too: measure first. The profiler does "
                        "not tell you what to fix; it tells you where to "
                        "look so that the fixing is not a guess."
                    ),
                ),
            ],
        ),
        # ── 7. Production ─────────────────────────────────────────────────
        Section(
            id="production",
            title="Production",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dbg-prod-pitch",
                    text=(
                        "Everything so far assumed you can run the code, "
                        "edit it, or attach to it. Production revokes all "
                        "three: you cannot breakpoint a paying customer's "
                        "request, editing the binary to add prints is not "
                        "a deploy strategy, and freezing a worker to "
                        "inspect it fails health checks. Production "
                        "debugging is therefore mostly the observability "
                        "topic's instruments read with a debugger's eye, "
                        "plus a small set of habits that decide whether "
                        "an incident takes minutes or a weekend."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-prod-envelope-pitch",
                    text=(
                        "The first habit is already built into every "
                        "error this app produces: the correlation "
                        "contract. One envelope shape for every failure, "
                        "carrying the request id both ways — in the body "
                        "the client can report, and in the header "
                        "middleware can log — so the walk from 'a "
                        "customer said it failed' to 'the exact lines "
                        "this request logged' is one id long. The "
                        "envelope builder is the mechanism, and every "
                        "debugging session in anger starts at what it "
                        "stamps:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-prod-envelope-quote",
                    language="py",
                    caption="The correlation contract: one id, in the body clients report and the header logs.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "    request_id = resolve_request_id(request)\n"
                        "    body = ErrorResponse(\n"
                        "        error=ErrorBody(code=kind.value, message=message, request_id=request_id, details=details)\n"
                        "    )\n"
                        "    headers = {\"x-request-id\": request_id}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-prod-instruments-framing",
                    text=(
                        "The second habit is knowing which instrument "
                        "answers which question, because at 3am you do "
                        "not browse — you query. The division of labor "
                        "the observability topic built, read as a "
                        "debugging playbook:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="dbg-prod-instruments",
                    ordered=False,
                    items=[
                        "Logs — the per-request narrative: grep the id, "
                        "read the story; diagnosis lives here, and this "
                        "app's access-log duration line is a free "
                        "per-request profile.",
                        "Metrics — the shape of the incident: when did "
                        "the error rate move, is latency uniform or "
                        "tail-only, is it one endpoint or all of them; "
                        "metrics pick WHICH logs to grep.",
                        "Traces — the where across boundaries: the "
                        "fan-out demo's correlated ids are the local "
                        "seed; OTel's span trees are the scaled version.",
                        "Health signals — the dependency confessions: a "
                        "burst of service_unavailable envelopes or "
                        "degradation warnings names the sick dependency "
                        "without a debugger in sight.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="dbg-prod-two-numbers",
                    text=(
                        "A concrete instance the repo already computes: "
                        "the jobs queue's two numbers. When 'the system "
                        "feels slow' arrives with no failing request, "
                        "the queue's depth and oldest-job age answer "
                        "whether work is piling up (a consumer died) or "
                        "trickling (a dependency slowed) — a debugging "
                        "verdict from two gauges, no reproduction "
                        "needed:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-prod-queue-quote",
                    language="py",
                    caption="Two gauges, one verdict: ZCARD depth and the oldest job's age, live.",
                    source="server/guide/data/jobs/arq_jobs.py",
                    snippet=(
                        "    async def queue_stats(self) -> QueueStatsRow:\n"
                        "        \"\"\"The two numbers: ZCARD depth, oldest age from the lowest score.\"\"\"\n"
                        "        with _map_jobs_failures(\"queue_stats\"):\n"
                        "            pool = await self._pool()\n"
                        "            depth = int(await pool.zcard(QUEUE_KEY))\n"
                        "            oldest = await pool.zrange(QUEUE_KEY, start=0, end=0, withscores=True)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-prod-habits",
                    text=(
                        "The habits that finish the kit: reproduce in a "
                        "LOWER environment with production's DATA shape, "
                        "not its traffic (the repro rarely needs the "
                        "load, only the bytes); read the deployment "
                        "diff first, because the best predictor of a new "
                        "bug is the newest change ('what shipped in the "
                        "last 48 hours' is a debugging command); keep "
                        "debug-level logging one env-var away rather "
                        "than always-on, so the cost is paid only during "
                        "diagnosis — this app's FDG_LOG_LEVEL does "
                        "exactly that; and when you must observe "
                        "production state directly, prefer the "
                        "non-pausing instruments (py-spy --nonblocking, "
                        "log-level changes, metrics scrapes) over "
                        "anything that freezes a paying-customer's "
                        "thread. The last resort remains legitimate: "
                        "take one instance out of rotation, THEN freeze "
                        "and inspect it — a debugger pointed at a "
                        "process nothing routes to is harmless, which is "
                        "the debuggable-production trick in one sentence."
                    ),
                ),
            ],
        ),
        # ── 8. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="Debugging from a shell: the stall panel, the evidence, the tools' recipes, the recovery proof.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dbg-terminal-intro",
                    text=(
                        "Six stops on the running stack: the stall "
                        "diagnosis with every measurement, this panel "
                        "request's own correlated log rows, the "
                        "self-limiting proof (health timed immediately "
                        "after the demo), the pdb and py-spy recipes as "
                        "runnable commands, and this topic's own detail "
                        "through both ports."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-terminal-stall",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the stall diagnosis: four phases, every instrument\n"
                        "curl -s localhost:8000/api/demo/debug/stall | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for p in panel[\"phases\"]:\n"
                        "    print(\"%-24s elapsed=%6.1fms lagMax=%6.1fms health=%5.1fms/%d\" % (\n"
                        "        p[\"label\"], p[\"elapsedMs\"], p[\"loopLagMaxMs\"],\n"
                        "        p[\"concurrentHealthMs\"], p[\"concurrentHealthStatus\"]))\n"
                        "a = panel[\"allocations\"]\n"
                        "print(\"alloc:\", a[\"objects\"], \"objects, current\", a[\"currentKb\"],\n"
                        "      \"KB, peak\", a[\"peakKb\"], \"KB\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-terminal-correlation",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — this panel's own log rows, correlated by its request id\n"
                        "curl -s -D /tmp/h.txt localhost:8000/api/demo/debug/stall -o /tmp/p.json\n"
                        "RID=$(grep -i x-request-id /tmp/h.txt | awk '{print $2}' | tr -d '\\r')\n"
                        "RID=$RID python3 -c '\n"
                        "import json, os\n"
                        "panel = json.load(open(\"/tmp/p.json\"))\n"
                        "assert panel[\"panelRequestId\"] == os.environ[\"RID\"], \"id mismatch\"\n"
                        "for e in panel[\"logEvents\"]:\n"
                        "    fields = \" \".join(f[\"name\"] + \"=\" + f[\"value\"] for f in e[\"fields\"])\n"
                        "    print(\" \", e[\"level\"], e[\"event\"], fields)'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-terminal-responsive",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the self-limiting proof: health answers fast right after the demo\n"
                        "curl -s localhost:8000/api/demo/debug/stall > /dev/null\n"
                        "time curl -s -m 5 localhost:8000/api/health\n"
                        "# a slow answer here would mean the demo wedged the shared loop — it must not"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-terminal-tools",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the state tool (stdlib): post-mortem a crashing script, no install\n"
                        "printf 'def average(values):\\n    return sum(values) / len(values)\\naverage([])\\n' > /tmp/demo_broken.py\n"
                        "python3 -m pdb -c continue /tmp/demo_broken.py   # stops INSIDE the dying frame\n"
                        "# quit with q; rerun interactively to p values / where"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-terminal-pyspy",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the time tool (honest recipe — py-spy is NOT installed here):\n"
                        "docker exec fastapi_developers_guide_server_dev pgrep -f 'uvicorn guide.main'\n"
                        "# then, from a host with the tool:  py-spy dump --pid <pid> --nonblocking\n"
                        "# and live:                        py-spy top   --pid <pid>\n"
                        "# run the demo in one terminal and top in another — the on-loop phase is\n"
                        "# the moment _burn_cpu_ms lights up while every other stack parks"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dbg-terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — this topic's own detail: demo inline in py-spy, companion last\n"
                        "curl -s localhost:8000/api/content/debugging | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'\n"
                        "curl -s localhost:5174/api/content/debugging \\\n"
                        "  | python3 -c 'import json,sys; print(\"proxy sections:\", len(json.load(sys.stdin)[\"sections\"]))'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dbg-terminal-coda",
                    text=(
                        "Stops 1–3 are the loop in miniature: reproduce the "
                        "slow (the demo does it), measure (elapsed, lag, "
                        "concurrent health — all real), verify the "
                        "hypothesis each phase embodies, and prove the "
                        "system recovered. Stop 4 hands you the state "
                        "tool for the next crash; stop 5 the time tool "
                        "for the next stall, honestly marked as recipes "
                        "until you run them; stop 6 closes the loop the "
                        "guide always closes — the topic that taught "
                        "debugging is debugged itself, its own demo the "
                        "exhibit and its companion the transcript."
                    ),
                ),
            ],
        ),
    ],
)
