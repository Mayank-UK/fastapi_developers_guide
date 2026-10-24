"""Topic 38 — Performance: measure first, then change one thing.

The topic teaches performance as a measurement discipline applied to this
repo's real stack: the instruments it already runs (perf_counter pairs in
the access log, the loop-lag probe topic 35 built), the async hygiene
rule that dwarfs every other FastAPI lever, a REAL compression benchmark
over the bytes this API actually serves, uvicorn's auto-selected
uvloop/httptools introspected live instead of assumed, the engine pool's
actual counters, and the stdlib GC read plus one measured collection.
Everything quoted here is this repository's real code; the demo is
perf:bench, INLINE in the compression section, and every number it serves
was measured on the request that served it.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="performance",
    title="Performance",
    subtitle=(
        "Measure first: the instruments this repo already runs, the async "
        "hygiene rule (never block the loop) with the on-loop vs threadpool "
        "comparison measured live, a real compression benchmark over the "
        "bytes this API actually serves beside the nginx edge's gzip, "
        "uvicorn's auto-selected uvloop and httptools introspected from the "
        "serving process, the SQLAlchemy async engine's pool counters and "
        "the exhaustion pathology, and the stdlib garbage collector read "
        "honestly — every number measured, none asserted."
    ),
    group="ship",
    order=38,
    sections=[
        # ── 1. measure first ──────────────────────────────────────────────
        Section(
            id="measure-first",
            title="Measure first",
            blocks=[
                TextBlock(
                    kind="text",
                    id="prf-measure-pitch",
                    text=(
                        "Performance work has exactly one unforgivable sin: "
                        "changing code before measuring it. Everything else "
                        "in this topic — async hygiene, compression, "
                        "uvloop, pools, GC — is a lever, and levers are "
                        "cheap to pull and expensive to pull blindly, "
                        "because the code you 'optimized' now carries "
                        "complexity that must be understood, tested, and "
                        "maintained forever, whether or not it moved the "
                        "number. Measurement is what converts a hunch "
                        "('the API feels slow') into an addressable fact "
                        "('p95 of GET /api/content is 40ms and 35 of them "
                        "are serialization'). This repo practices the "
                        "discipline on itself: the request you are reading "
                        "was timed by middleware before it ever reached "
                        "this paragraph."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-measure-instrument-pitch",
                    text=(
                        "The instrument is deliberately boring — a "
                        "perf_counter pair around the inner call — and it "
                        "already ships on every request. Topic 33's access "
                        "log layer starts the clock at request-enter and "
                        "reads it in the finally block after the last "
                        "response chunk flushed, which is why its "
                        "duration_ms covers the whole onion beneath it: "
                        "middleware, routing, dependencies, the handler, "
                        "and response serialization, end to end."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-measure-request-log-quote",
                    language="py",
                    caption="The repo's own timing instrument: one perf_counter pair per request, in the access-log middleware.",
                    source="server/guide/presentation/middleware/request_log.py",
                    snippet=(
                        "        method = scope.get(\"method\", \"?\")\n"
                        "        path = scope.get(\"path\", \"?\")\n"
                        "        started = time.perf_counter()\n"
                        "        status: list[int] = []\n"
                        "        request_id: list[str] = []\n"
                        "\n"
                        "        async def send_observing(message: Message) -> None:\n"
                        "            # The response side: headers ride exactly one message — read the\n"
                        "            # status and the stamped id there, let every body chunk pass.\n"
                        "            if message[\"type\"] == \"http.response.start\":\n"
                        "                status.append(int(message[\"status\"]))\n"
                        "                request_id.append(Headers(scope=message).get(REQUEST_ID_HEADER, \"\"))\n"
                        "            await send(message)\n"
                        "\n"
                        "        try:\n"
                        "            await self.app(scope, receive, send_observing)\n"
                        "        finally:\n"
                        "            duration_ms = round((time.perf_counter() - started) * 1000, 1)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-measure-reading",
                    text=(
                        "Two details make that quote worth more than a "
                        "tutorial timer. First, time.perf_counter, never "
                        "time.time: the perf clock is monotonic (immune to "
                        "NTP jumps and wall-clock resets) and its "
                        "resolution is the finest the platform offers — "
                        "the stdlib documents it as the clock for "
                        "benchmarking. Second, the reading happens in a "
                        "finally block, so the duration lands even when "
                        "the inner call raised; a timing instrument that "
                        "silently disappears on the slow path (the error "
                        "path) measures only the happy requests, which is "
                        "exactly backwards. Every http_request row in the "
                        "log viewer demo carries this number, correlated "
                        "by request id — an accidental profile of the "
                        "whole app, collected as a side effect of "
                        "observability."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-measure-instruments-framing",
                    text=(
                        "One clock is not enough, because 'how long' has "
                        "different meanings depending on where the time "
                        "went. The instruments this repo reaches for, in "
                        "escalating power — each one real, each one "
                        "already demonstrated by an earlier topic:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="prf-measure-instruments",
                    ordered=True,
                    items=[
                        "perf_counter — wall-clock elapsed around a scope; "
                        "the access-log pair above, and the pair around "
                        "every phase of this topic's demo.",
                        "Loop lag — a concurrent probe task whose sleep "
                        "overshoot exposes a starved event loop; topic "
                        "35's instrument, reused by this topic's hygiene "
                        "comparison.",
                        "tracemalloc — a stdlib window over allocations, "
                        "current vs peak; topic 35's heap section used it "
                        "to separate churn from leaks.",
                        "Duration logs — http_request rows over time; "
                        "topic 33's viewer turns them into the slowest-"
                        "routes list you actually look at.",
                        "Sampling profilers — py-spy and pyinstrument, "
                        "outside or around the process; topic 35 taught "
                        "them honestly as recipes (not installed here).",
                    ],
                ),
                CodeBlock(
                    kind="code",
                    id="prf-measure-lag-quote",
                    language="py",
                    caption="The loop-lag instrument, quoted from topic 35's stall demo — the probe this topic's hygiene rows reuse.",
                    source="server/guide/domain/demos/debug_stall.py",
                    snippet=(
                        "async def _loop_lag_samples(*, ticks: int, interval_s: float) -> list[float]:\n"
                        "    # …\n"
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
                    id="prf-measure-method",
                    text=(
                        "Method, so the numbers mean something: baseline "
                        "BEFORE the change, on the same payload, on the "
                        "same machine, with the process warm — a cold "
                        "first request pays imports, JIT-less bytecode "
                        "compilation, and pool warm-up, and comparing "
                        "cold-to-warm proves nothing except that caches "
                        "work. Change one variable at a time; the moment "
                        "two things move, the result belongs to neither. "
                        "And prefer distributions to single numbers — run "
                        "the measurement repeatedly and read the median "
                        "or the tail, because a single sample on a shared "
                        "machine is a lottery ticket. The benchmark in "
                        "this topic's demo follows exactly this shape: "
                        "fixed payloads, fixed iteration counts, mean "
                        "timings, and every duration bounded so the "
                        "measurement can never itself become the "
                        "incident."
                    ),
                ),
            ],
        ),
        # ── 2. async hygiene ──────────────────────────────────────────────
        Section(
            id="async-hygiene",
            title="Async hygiene: never block the loop",
            blocks=[
                TextBlock(
                    kind="text",
                    id="prf-hygiene-pitch",
                    text=(
                        "If FastAPI performance has one rule that dwarfs "
                        "every other, it is this: never run blocking code "
                        "on the event loop. The loop is a single-threaded "
                        "cooperative scheduler — every handler runs on it, "
                        "and control passes between handlers only at "
                        "await points. The moment one handler executes "
                        "sync code that takes 100ms — a blocking driver "
                        "call, time.sleep, a tight CPU loop, a huge "
                        "pandas import — the ENTIRE process serves "
                        "nothing for 100ms: not health checks, not other "
                        "requests, not websocket pings. One slow handler "
                        "is every handler's latency. Topic 2 built the "
                        "loop mechanics and topic 35 diagnosed the "
                        "pathology with four measured phases; this "
                        "section compresses that lesson into the rule you "
                        "apply while writing code."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-hygiene-two-rows-pitch",
                    text=(
                        "The mechanism, side by side. The same bounded "
                        "80ms CPU budget runs twice: once offloaded "
                        "through asyncio.to_thread, once directly on the "
                        "loop — while a real internal health request and "
                        "a loop-lag probe watch each run. This is exactly "
                        "the runner the demo below serves, quoted from "
                        "the payload builder:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-hygiene-runner-quote",
                    language="py",
                    caption="The comparison this topic's demo measures live: same block, contained vs on the loop.",
                    source="server/guide/domain/demos/perf_bench.py",
                    snippet=(
                        "    started = time.perf_counter()\n"
                        "    if offload:\n"
                        "        await asyncio.to_thread(_burn_cpu_budget_ms, HYGIENE_BUDGET_MS)\n"
                        "    else:\n"
                        "        _burn_cpu_budget_ms(HYGIENE_BUDGET_MS)\n"
                        "    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-hygiene-reading",
                    text=(
                        "Read the two rows the demo produces. The "
                        "threadpool row: 80ms elapsed for THIS request, "
                        "loop lag quiet, and the concurrent health probe "
                        "answered in single-digit milliseconds mid-block "
                        "— the block was contained, scheduling preserved "
                        "for everyone else. The on-loop row: the same "
                        "budget run directly on the loop starved the "
                        "in-flight lag tick and made the health request "
                        "wait out nearly the whole block. Topic 35's "
                        "debug:stall ran this same experiment at full "
                        "depth with four phases; the functions it used "
                        "are the two-line essence of the rule:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-hygiene-pair-quote",
                    language="py",
                    caption="Topic 35's containment pair: to_thread is the escape hatch; the second function is the pathology.",
                    source="server/guide/domain/demos/debug_stall.py",
                    snippet=(
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
                TextBlock(
                    kind="text",
                    id="prf-hygiene-when-threads-dont-help",
                    text=(
                        "to_thread is the escape hatch, and knowing when "
                        "it does NOT help is half the lesson. Threads "
                        "solve WAITING: a sync database driver, a "
                        "requests call, time.sleep, file I/O, a Pillow "
                        "resize — the thread parks while the operation "
                        "completes, and the GIL is released while it "
                        "parks, so the loop keeps running. Threads do "
                        "NOT solve pure-Python CPU work: the GIL means "
                        "only one thread executes Python bytecode at a "
                        "time, so 80ms of bytecode on a worker thread "
                        "still competes with the loop's thread — "
                        "contained is not free, which is why the "
                        "threadpool row's health probe slows a little. "
                        "Genuine CPU-bound work belongs in a process "
                        "(a worker like topic 29's arq tasks, or another "
                        "uvicorn worker), and the correct long-term fix "
                        "for a blocking library is an async-native one — "
                        "the reason this repo uses asyncpg, motor, and "
                        "redis.asyncio instead of their sync twins."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-hygiene-field-guide-framing",
                    text=(
                        "The rule becomes muscle memory as a field guide "
                        "— what to do the moment you recognize each "
                        "shape in review:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="prf-hygiene-field-guide",
                    ordered=False,
                    items=[
                        "Sync SDK call — the library has no async API: "
                        "wrap it in asyncio.to_thread and name the "
                        "threadpool cost in the review.",
                        "time.sleep — always a bug in a handler; replace "
                        "with await asyncio.sleep, which yields control.",
                        "Heavy CPU (parsing, hashing, image work) — move "
                        "to a worker queue like topic 29's arq tasks, or "
                        "accept to_thread as containment, not a fix.",
                        "File I/O — small reads tolerate to_thread; real "
                        "streams belong in an async generator like topic "
                        "26's paced upload reader.",
                        "Accidental imports — a lazy import inside a "
                        "hot handler can cost tens of ms on first call; "
                        "import at module top or warm it in lifespan.",
                        "Background work in the handler — "
                        "BackgroundTasks is the sanctioned 'after the "
                        "response' seam (topic 29 measured in-process "
                        "vs queued), never a bare asyncio.create_task "
                        "that outlives its error handling.",
                    ],
                ),
            ],
        ),
        # ── 3. compression benchmark + demo ───────────────────────────────
        Section(
            id="compression-bench",
            title="Compression, benchmarked",
            lead="This section carries the topic's demo — the live perf bench.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="prf-compression-pitch",
                    text=(
                        "Compression is the rare performance lever that "
                        "trades a resource you have (CPU) for one your "
                        "users feel (bytes on the wire), and it deserves "
                        "a benchmark rather than a habit because the "
                        "trade is genuinely two-sided: JSON and "
                        "JavaScript are text, text gzips to a fraction "
                        "of itself, but every byte saved is paid for at "
                        "encode time somewhere. Topic 9 recorded that "
                        "response compression is transport policy that "
                        "belongs in middleware or the server, never in "
                        "handlers, and left this topic a promise to "
                        "decide with a benchmark whether the app layer "
                        "should mount Starlette's GZipMiddleware at all."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-compression-edge-pitch",
                    text=(
                        "The repo's answer today lives at the edge, not "
                        "in the app. The client image's nginx gzips "
                        "text-shaped responses before they leave the "
                        "box — a belt-and-suspenders layer, because the "
                        "shared Caddy at the TLS edge compresses "
                        "domain-wide already and skips upstreams that "
                        "arrive pre-encoded:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-compression-nginx-quote",
                    language="nginx",
                    caption="The repo's real edge gzip: text types over 1KB, at nginx's default compression level.",
                    source=".docker/client/nginx.conf",
                    snippet=(
                        "    # Gzip text assets (belt-and-suspenders: the central Caddy edge already\n"
                        "    # compresses, and skips already-encoded upstreams).\n"
                        "    gzip on;\n"
                        "    gzip_types text/plain text/css application/javascript application/json image/svg+xml;\n"
                        "    gzip_min_length 1024;"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-compression-edge-reading",
                    text=(
                        "Three decisions are packed into those four "
                        "lines. The type list excludes everything "
                        "already binary (png, woff2, mp4 — gzip cannot "
                        "shrink them and wastes the attempt). The 1024-"
                        "byte floor skips responses where the gzip "
                        "header would eat the savings. And the level is "
                        "deliberately absent: nginx defaults to "
                        "compression level 1 — cheap, fast, good enough "
                        "— which is why the benchmark below measures "
                        "level 1 as the edge's live setting beside "
                        "level 6, the stdlib gzip default, so the "
                        "trade-off is visible instead of assumed. The "
                        "bigger static win, for the record, is not "
                        "compression at all: topic 37's hashed-assets "
                        "cache policy means a repeat visitor downloads "
                        "NOTHING, which beats gzipping what you no "
                        "longer send."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-compression-demo-pitch",
                    text=(
                        "The benchmark is honest by construction: it "
                        "does not gzip a synthetic fixture — it drives "
                        "real internal rounds through this very app, "
                        "takes the actual response bytes of the served "
                        "topic index and of THIS page's own detail "
                        "payload, and gzips those, timing encode and "
                        "decode over bounded iterations."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="perf:bench",
                    title="The performance bench",
                    description=(
                        "GET /api/demo/perf/bench measures, on the very "
                        "request that serves it: REAL gzip over the "
                        "bytes of two payloads this API serves (the "
                        "topic index from GET /api/content and this "
                        "topic's own detail page, fetched through real "
                        "internal rounds), at level 1 (the nginx edge's "
                        "live default) and level 6 (the stdlib default) "
                        "— bytes before and after, percent saved, mean "
                        "encode and decode timing. The async-hygiene "
                        "pair runs the same 80ms CPU block on-loop vs "
                        "in a threadpool with a concurrent real "
                        "/api/health and a loop-lag probe witnessing "
                        "each. The loop rows introspect uvicorn's "
                        "auto-selected event loop and HTTP parser from "
                        "THIS process. The pool rows snapshot the "
                        "composition root's engine pool counters. The "
                        "GC rows read the stdlib collector and measure "
                        "one full collection off the loop. Every "
                        "duration is bounded, and the panel's last row "
                        "is a real /api/health measured after the whole "
                        "bench — the loop's receipt for staying "
                        "responsive."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-compression-demo-reading",
                    text=(
                        "How to read the compression rows. The percent "
                        "saved is the headline — JSON full of repeated "
                        "keys and prose compresses dramatically, and "
                        "both real payloads land well past half their "
                        "bytes saved at either level. The instructive "
                        "comparison is the cost column: level 6 spends "
                        "measurably more encode time than level 1 for a "
                        "modest few extra percent — the exact "
                        "arithmetic behind nginx's default — and decode "
                        "is nearly free at both levels, because "
                        "gunzip is dramatically cheaper than gzip at "
                        "every level. The timings are microsecond-"
                        "scale honesty: milliseconds measured over "
                        "single-digit iterations on a shared container, "
                        "not a certification lab. The measurement "
                        "machinery itself is three stdlib calls:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-compression-timings-quote",
                    language="py",
                    caption="The bench's timing loop: gzip.compress for the bytes, perf_counter pairs for the means.",
                    source="server/guide/domain/demos/perf_bench.py",
                    snippet=(
                        "def _gzip_timings(raw: bytes, level: int, iterations: int) -> tuple[int, float, float]:\n"
                        "    \"\"\"Bytes out + mean encode/decode milliseconds over bounded iterations.\"\"\"\n"
                        "    gzipped = gzip.compress(raw, compresslevel=level)\n"
                        "    # …\n"
                        "    started = time.perf_counter()\n"
                        "    for _ in range(iterations):\n"
                        "        gzip.compress(raw, compresslevel=level)\n"
                        "    encode_ms = (time.perf_counter() - started) / iterations * 1000"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-compression-tradeoff",
                    text=(
                        "So should the app mount GZipMiddleware? The "
                        "benchmark says this repo should NOT, and the "
                        "reasoning generalizes. The app tier would pay "
                        "per-request encode CPU inside every uvicorn "
                        "worker to produce bytes the edge compresses "
                        "anyway — double compression is pure waste, "
                        "which is why Caddy skips already-encoded "
                        "upstreams. App-layer compression EARNS its "
                        "keep only when there is no edge in front — a "
                        "directly exposed uvicorn service, an "
                        "internal API consumed cross-machine, a "
                        "LAN-deployed tool — and then Starlette's "
                        "GZipMiddleware is one line at the composition "
                        "root, with the same caveats nginx encodes: "
                        "exclude already-compressed types, floor the "
                        "minimum length, and let streamed responses "
                        "(topic 28's SSE) pass unbuffered. Decision "
                        "made by measurement, applied at the layer "
                        "that owns it: that is this whole topic in one "
                        "paragraph."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-compression-router-quote",
                    language="py",
                    caption="The demo's thin router: one GET, the payload builder, a declared response model.",
                    source="server/guide/presentation/routers/demo/perf.py",
                    snippet=(
                        "@router.get(BENCH_PATH, response_model=PerfBenchPanel)\n"
                        "async def read_perf_bench_panel(\n"
                        "    request: Request, pool_facts: PoolFactsDep\n"
                        ") -> PerfBenchPanel:\n"
                        "    \"\"\"Serve the live bench: measured compression, hygiene, loop, pool, GC.\"\"\"\n"
                        "    return await build_perf_bench_payload(\n"
                        "        app=request.app,\n"
                        "        pool_facts=pool_facts,\n"
                        "    )"
                    ),
                ),
            ],
        ),
        # ── 4. uvloop / httptools ─────────────────────────────────────────
        Section(
            id="uvloop-httptools",
            title="uvloop and httptools",
            blocks=[
                TextBlock(
                    kind="text",
                    id="prf-loop-pitch",
                    text=(
                        "Two drop-in accelerators ship inside a single "
                        "dependency extra. uvloop replaces the stdlib "
                        "asyncio event loop with a Cython "
                        "implementation built on libuv (the loop Node "
                        "uses); httptools replaces uvicorn's pure-"
                        "Python HTTP/1.1 parser with a binding to the "
                        "C parser behind the llhttp engine. Neither "
                        "changes your code — the APIs are the same — "
                        "and both are delivered by the uvicorn[standard] "
                        "extra this repo has carried since its first "
                        "commit:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-loop-pyproject-quote",
                    language="toml",
                    caption="The extra that carries the accelerators: uvicorn[standard] pulls uvloop, httptools, websockets, and friends.",
                    source="server/pyproject.toml",
                    snippet=(
                        "    \"sqlalchemy[asyncio]>=2.1.4\",\n"
                        "    \"strawberry-graphql[fastapi]>=0.335.0\",\n"
                        "    \"structlog>=24.4\",\n"
                        "    \"uvicorn[standard]>=0.30\",\n"
                        "]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-loop-auto",
                    text=(
                        "How they get chosen matters more than the "
                        "speed claims. Uvicorn's --loop and --http "
                        "settings default to auto: at boot it tries "
                        "uvloop and falls back to the stdlib asyncio "
                        "loop; it tries httptools and falls back to "
                        "h11, the pure-Python parser. So 'is this "
                        "server running the accelerators' is never a "
                        "matter of faith in your configuration — it is "
                        "an introspectable fact of the running process, "
                        "and the bench panel reports it by reading the "
                        "process rather than reciting the docs: the "
                        "running loop's actual class, and which "
                        "protocol module uvicorn actually loaded:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-loop-introspection-quote",
                    language="py",
                    caption="Introspection, not assumption: the panel names the loop that is running this very request.",
                    source="server/guide/domain/demos/perf_bench.py",
                    snippet=(
                        "    loop = asyncio.get_running_loop()\n"
                        "    loop_module = type(loop).__module__\n"
                        "    loop_class = f\"{loop_module}.{type(loop).__qualname__}\"\n"
                        "    loop_value = (\n"
                        "        f\"{loop_class} — uvloop is running this very event loop\"\n"
                        "        if loop_module == \"uvloop\"\n"
                        "        else f\"{loop_class} — the stdlib asyncio loop (pytest/TestClient, or uvicorn \"\n"
                        "        \"started without uvloop)\"\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-loop-live-truth",
                    text=(
                        "The live truth of this dev stack, reported by "
                        "the panel's rows: uvicorn 0.54 with uvloop "
                        "0.23 and httptools 0.9 installed, the running "
                        "loop's class is uvloop.Loop, and uvicorn's "
                        "httptools_impl protocol module is the loaded "
                        "one — auto selected both, because the standard "
                        "extra installed both. Under pytest the same "
                        "rows say so honestly: TestClient drives the "
                        "app in-process on a stdlib loop with no "
                        "uvicorn modules loaded, and the row reports "
                        "that instead of pretending. The flags exist "
                        "for the day you must pin the choice explicitly "
                        "— the honest recipe shape this repo never "
                        "needed, since auto already resolves the "
                        "installed accelerators:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-loop-recipe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# Pinning the choices explicitly (NOT what this repo runs — auto does it):\n"
                        "uvicorn guide.main:app --loop uvloop --http httptools   # exactly what auto picked\n"
                        "uvicorn guide.main:app --loop asyncio --http h11       # the pure-Python fallbacks\n"
                        "# Useful when profiling (isolate ONE variable) or when a C extension\n"
                        "# misbehaves on an exotic platform and you need the escape hatch."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-loop-what-they-change",
                    text=(
                        "What they actually change, honestly: uvloop "
                        "and httptools shine on I/O-dense micro-"
                        "benchmarks — tens of thousands of small "
                        "requests per second, where per-event loop "
                        "overhead and per-request parsing dominate. "
                        "This teaching app's real request cost is "
                        "elsewhere: pydantic validation, JSON "
                        "serialization of large content payloads, "
                        "PostgreSQL round-trips — none of which the "
                        "accelerators touch. That is not an argument "
                        "against them (they are free — install the "
                        "extra, win the overhead), it is the measure-"
                        "first posture applied to hype: the panel "
                        "proves they are ON, the access log tells you "
                        "they were never your bottleneck, and your "
                        "optimization hour goes where the milliseconds "
                        "actually are. One operational note: the "
                        "production image runs the same standard extra "
                        "and the same default CMD, so dev, CI, and "
                        "prod all resolve the same loop and parser — "
                        "parity by construction, not by hope."
                    ),
                ),
            ],
        ),
        # ── 5. connection pooling ─────────────────────────────────────────
        Section(
            id="connection-pooling",
            title="Connection pooling",
            blocks=[
                TextBlock(
                    kind="text",
                    id="prf-pool-pitch",
                    text=(
                        "The most expensive millisecond in a database-"
                        "backed request is the one you spend re-meeting "
                        "the database. Opening a PostgreSQL connection "
                        "means TCP handshake, TLS (when used), "
                        "authentication, and backend process spawn on "
                        "the server side — single-digit to tens of "
                        "milliseconds, EVERY time. A pool amortizes it: "
                        "N connections opened once, checked out for the "
                        "duration of a unit of work, returned to the "
                        "pool instead of torn down. This repo's entire "
                        "pool policy lives in one factory function "
                        "every database adapter shares — and its "
                        "docstring contains a promise this topic is "
                        "here to keep:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-pool-engine-quote",
                    language="py",
                    caption="The one place pool policy lives — and the comment that names this topic.",
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
                    id="prf-pool-numbers",
                    text=(
                        "So measure: the bench panel snapshots the live "
                        "pool — pool class AsyncAdaptedQueuePool, size "
                        "5, timeout 30 seconds, plus the checked-out "
                        "and idle counts at the moment of the request, "
                        "read straight off the composition root's "
                        "engine. The verdict for this workload: the "
                        "defaults hold. This app's database requests "
                        "are short, seeded, and rarely concurrent — "
                        "five steady connections with up to ten more "
                        "on overflow is generous headroom, and the "
                        "honest result of the measurement is that no "
                        "knob needs turning. The pre_ping line earns "
                        "its place separately: it trades one cheap "
                        "liveness ping per checkout so a PostgreSQL "
                        "restart surfaces as a clean reconnect instead "
                        "of a stale-socket 500 to one unlucky user."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-pool-router-quote",
                    language="py",
                    caption="How the panel reads the pool: counters only, no connection opened, in the router's snapshot.",
                    source="server/guide/presentation/routers/demo/perf.py",
                    snippet=(
                        "    pool = engine.pool\n"
                        "    if not isinstance(pool, QueuePool):\n"
                        "        raise AppError(FailureKind.INTERNAL, f\"Unexpected pool type: {type(pool).__name__}\")\n"
                        "    return PoolFacts(\n"
                        "        pool_class=type(pool).__name__,\n"
                        "        dialect=engine.dialect.name,\n"
                        "        driver=engine.dialect.driver,\n"
                        "        size=pool.size(),\n"
                        "        checked_in=pool.checkedin(),\n"
                        "        checked_out=pool.checkedout(),\n"
                        "        timeout_s=pool.timeout(),\n"
                        "        status=pool.status(),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-pool-exhaustion",
                    text=(
                        "The pathology to recognize is pool exhaustion, "
                        "and async makes its shape sneakier. When every "
                        "connection is checked out and overflow is "
                        "spent, the next request WAITS — up to the "
                        "pool's 30-second timeout, then a TimeoutError "
                        "envelope. The async twist: a connection is "
                        "held across every await inside the "
                        "transaction, so one handler that awaits a "
                        "slow external call mid-transaction parks a "
                        "pool slot while doing no database work at "
                        "all. Six such handlers and a five-slot pool "
                        "is exhausted by parking, not by load — the "
                        "fix is shrinking the transaction (topic 22's "
                        "outbox exists precisely to keep slow work "
                        "OUT of transactions), not growing the pool. "
                        "Growing past your database's real capacity is "
                        "its own failure: PostgreSQL's max_connections "
                        "is a wall every uvicorn worker's pool runs "
                        "toward, and the correct big-system answer is "
                        "fewer, busier connections — a sidecar pooler "
                        "like pgbouncer when the worker count grows."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-pool-discipline-framing",
                    text=(
                        "The discipline, as the four rules the repo "
                        "actually follows plus the two that keep pools "
                        "honest at scale:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="prf-pool-discipline",
                    ordered=False,
                    items=[
                        "One pool per process — the engine is created "
                        "once in create_app and every adapter shares "
                        "it; engines are lazy so boot connects to "
                        "nothing.",
                        "Pre-ping on checkout — pool_pre_ping turns a "
                        "database restart into a reconnect instead of "
                        "a user-visible stale-socket error.",
                        "Dispose on shutdown — the lifespan's engine "
                        "dispose closes every pooled connection when "
                        "the process drains (topic 37 quoted it).",
                        "Defaults until measured — sizing is a load "
                        "fact, not a superstition; this panel is the "
                        "measurement that says five is fine here.",
                        "Bound the transaction — never await slow "
                        "external work inside a database transaction; "
                        "a parked slot starves the pool worse than a "
                        "busy one.",
                        "Watch checkedout — a counter pinned at the "
                        "max under normal load is the early-warning "
                        "shape of exhaustion, visible before the "
                        "timeouts start.",
                    ],
                ),
            ],
        ),
        # ── 6. GC tuning ──────────────────────────────────────────────────
        Section(
            id="gc-tuning",
            title="GC tuning",
            blocks=[
                TextBlock(
                    kind="text",
                    id="prf-gc-model",
                    text=(
                        "CPython's memory story, compressed to what "
                        "performance work needs (topic 2 taught the "
                        "full version): almost everything is freed by "
                        "reference counting the instant its last "
                        "reference dies; the garbage collector exists "
                        "ONLY to catch reference cycles — objects that "
                        "directly or indirectly point at themselves, "
                        "which refcounting cannot retire. The collector "
                        "works in three generations: new objects start "
                        "in gen0; survivors of a gen0 collection are "
                        "promoted to gen1, then gen2, on the reasoning "
                        "that the longer something has survived, the "
                        "less likely it is to be garbage soon."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-gc-thresholds",
                    text=(
                        "The knobs are the generation thresholds, and "
                        "their live values in this stack read (2000, "
                        "10, 10): gen0 collects after 2000 net "
                        "allocations minus deallocations; every 10 "
                        "gen0 collections triggers a gen1 sweep; every "
                        "10 gen1 sweeps, a gen2 full collection. The "
                        "2000 is itself a performance decision you "
                        "benefit from without knowing: CPython 3.13 "
                        "raised it from the long-standing 700 after "
                        "measuring that modern web workloads spend "
                        "real time in gen0 scans — the interpreter's "
                        "own developers doing exactly what this topic "
                        "preaches, measuring and turning one knob."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-gc-panel-reading",
                    text=(
                        "The bench panel reads the collector live — "
                        "enabled, thresholds, the pending counts at "
                        "this instant, cumulative collections per "
                        "generation — and then measures one full "
                        "gc.collect(), the whole-tree sweep, off the "
                        "loop. Expect tens of milliseconds on this "
                        "app's heap (the live dev server measures "
                        "roughly sixty) and a small collected count: "
                        "a request-served API heap is mostly acyclic, "
                        "refcounting has already reclaimed the churn, "
                        "and the sweep finds little — which is the "
                        "honest answer to 'should we tune the GC "
                        "here?' No. The measurement, not vibes:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-gc-measure-quote",
                    language="py",
                    caption="One real full collection, timed — and contained off the loop, practicing this topic's own hygiene rule.",
                    source="server/guide/domain/demos/perf_bench.py",
                    snippet=(
                        "    started = time.perf_counter()\n"
                        "    collected = await asyncio.to_thread(gc.collect)\n"
                        "    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-gc-when-it-matters",
                    text=(
                        "When GC tuning DOES matter, the symptom finds "
                        "you before the theory does: periodic latency "
                        "spikes at a steady interval, visible as a "
                        "comb pattern in request durations — the "
                        "signature of full collections over a huge "
                        "long-lived heap, the fate of apps that hold "
                        "large caches, big model objects, or long "
                        "connection registries in memory. The toolbox, "
                        "in escalating commitment: raise the gen0 "
                        "threshold to collect less often (trading "
                        "memory for fewer pauses); gc.freeze() after "
                        "startup to move warm long-lived objects out "
                        "of the collector's way entirely — the "
                        "technique behind pre-fork servers' copy-on-"
                        "write hygiene; and, at the extreme, gc."
                        "disable() with manual collection at chosen "
                        "moments — defensible only with evidence and "
                        "a leak-free codebase, because cyclical "
                        "garbage then accumulates silently. What GC "
                        "tuning never fixes: a leak that is NOT "
                        "garbage — objects still referenced by a "
                        "cache, a callback, a closure. That is a "
                        "retained-reference bug, found with "
                        "tracemalloc and the heap tools topic 35 "
                        "taught, and no threshold value will release "
                        "it."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-gc-coda",
                    text=(
                        "The honest position for this repo, then: "
                        "defaults, measured once, revisited only on "
                        "evidence. The panel gives you the same "
                        "readout on any deployment of this app — if "
                        "some future feature parks a million-object "
                        "cache in memory, the gen2 collections row "
                        "climbs and the measured collection time "
                        "grows, and THAT is the moment to reach for "
                        "freeze or thresholds, with a before-and-"
                        "after measurement in hand."
                    ),
                ),
            ],
        ),
        # ── 7. checklist ──────────────────────────────────────────────────
        Section(
            id="checklist",
            title="The performance checklist",
            blocks=[
                TextBlock(
                    kind="text",
                    id="prf-checklist-pitch",
                    text=(
                        "A topic about discipline should end in a "
                        "checklist, because discipline is what you "
                        "practice when nobody is watching. These are "
                        "the rules this repo holds itself to, each one "
                        "taught and measured earlier in the topic — "
                        "run down them the way the best-practices "
                        "topic's audit runs its rows: every claim "
                        "backed by a number or an introspection, never "
                        "an assertion."
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="prf-checklist-items",
                    ordered=True,
                    items=[
                        "Measure first — baseline with perf_counter "
                        "before changing code; same payload, same "
                        "machine, warm process, one variable at a "
                        "time.",
                        "Never block the loop — no sync I/O, "
                        "time.sleep, or heavy CPU inside async "
                        "handlers; offload with to_thread or move to "
                        "a worker, and remember threads fix waiting, "
                        "not CPU.",
                        "Compress at the edge — gzip belongs to the "
                        "proxy tier by default (nginx/Caddy); mount "
                        "app-layer GZipMiddleware only when no edge "
                        "fronts the service, and exclude binary types "
                        "and streams either way.",
                        "Cache before you compute — immutable hashed "
                        "assets with a no-cache entry document beat "
                        "any compression of bytes never sent.",
                        "Introspect accelerators — uvloop and "
                        "httptools are on when uvicorn[standard] is "
                        "installed (auto-selects both); verify from "
                        "the running process, not the README.",
                        "Pool deliberately — one engine per process, "
                        "pre_ping on, defaults until measured, "
                        "transactions bounded, checkedout watched.",
                        "Tune GC only on evidence — defaults unless "
                        "duration logs show collection-spaced spikes; "
                        "freeze beats thresholds beats disable, and "
                        "leaks are a tracemalloc question, not a GC "
                        "knob.",
                        "Bound every benchmark — a measurement that "
                        "can wedge the loop it measures is an "
                        "outage with extra steps; every timing loop "
                        "this demo runs is capped by construction.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="prf-checklist-coda",
                    text=(
                        "Where this topic stops, the next two pick "
                        "up: reliability turns performance's steady "
                        "state into survival under failure (timeouts, "
                        "retries, circuit breakers over these same "
                        "pools and loops), and scaling asks what one "
                        "process's numbers mean multiplied across "
                        "replicas behind a load balancer. The thread "
                        "through all three is the same: know your "
                        "baseline, change one thing, measure again."
                    ),
                ),
            ],
        ),
        # ── 8. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="Performance from a shell: the bench panel's real numbers, the loop's live truth, the receipt, this topic's detail.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="prf-terminal-intro",
                    text=(
                        "Five stops on the running stack: the bench "
                        "panel with its measured rows (compression "
                        "first, then the rest), the loop/pool/GC "
                        "readout, the health receipt that proves the "
                        "bench never wedged the loop, and this "
                        "topic's own detail through both ports."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-terminal-bench",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the bench: real gzip over the bytes this API serves\n"
                        "curl -s localhost:8000/api/demo/perf/bench | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for r in panel[\"compression\"]:\n"
                        "    print(\"%-22s level %d  %6d -> %-6d bytes  saved %5.1f%%  enc %.3fms  dec %.3fms\" % (\n"
                        "        r[\"payloadId\"], r[\"level\"], r[\"rawBytes\"], r[\"gzippedBytes\"],\n"
                        "        r[\"savedPercent\"], r[\"encodeMs\"], r[\"decodeMs\"]))'\n"
                        "# two real payloads × two levels — measured on the request, never asserted"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-terminal-hygiene",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the hygiene pair + the loop's live truth\n"
                        "curl -s localhost:8000/api/demo/perf/bench | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for r in panel[\"hygiene\"]:\n"
                        "    print(\"%-18s elapsed %6.1fms  lag max %5.1fms  health %5.1fms\" % (\n"
                        "        r[\"label\"], r[\"elapsedMs\"], r[\"loopLagMaxMs\"], r[\"concurrentHealthMs\"]))\n"
                        "for f in panel[\"loop\"]:\n"
                        "    print(\"%-20s %s\" % (f[\"id\"], f[\"value\"]))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-terminal-pool-gc",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the pool counters, the GC readout, and the receipt\n"
                        "curl -s localhost:8000/api/demo/perf/bench | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for f in panel[\"pool\"] + panel[\"gcFacts\"]:\n"
                        "    print(\"%-14s %s\" % (f[\"id\"], f[\"value\"]))\n"
                        "g = panel[\"gcCollection\"]\n"
                        "print(\"gc.collect: %sms, %d objects, off_loop=%s\" % (g[\"elapsedMs\"], g[\"collected\"], g[\"offLoop\"]))\n"
                        "h = panel[\"healthAfter\"]\n"
                        "print(\"health after the bench: %d in %.1fms — the loop never wedged\" % (h[\"status\"], h[\"elapsedMs\"]))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the curriculum this bench rides in, and this topic's own shape\n"
                        "curl -s localhost:8000/api/content | python3 -c '\n"
                        "import json, sys\n"
                        "index = json.load(sys.stdin)\n"
                        "print(len(index[\"topics\"]), \"topics /\", len(index[\"groups\"]), \"groups\")'\n"
                        "curl -s localhost:8000/api/content/performance | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="prf-terminal-proxy",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the same bench through the client proxy (the edge gzip tier in dev is 5174's vite)\n"
                        "curl -s localhost:5174/api/demo/perf/bench \\\n"
                        "  | python3 -c 'import json,sys; p=json.load(sys.stdin); print(\"proxy compression rows:\", len(p[\"compression\"]))'\n"
                        "curl -s -o /dev/null -w 'health: %{http_code} in %{time_total}s\\n' localhost:8000/api/health"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="prf-terminal-coda",
                    text=(
                        "Stops 1–3 are the topic's whole argument in "
                        "one payload: measured compression over real "
                        "bytes, the hygiene comparison with live "
                        "probes, the serving loop introspected, the "
                        "pool counted, the GC read and timed — and "
                        "the final health row as the receipt that "
                        "measurement never became the incident. Stops "
                        "4–5 close the standing loop: the topic that "
                        "taught measurement is served by the stack it "
                        "measured, its bench the evidence and its "
                        "companion the transcript."
                    ),
                ),
            ],
        ),
    ],
)
