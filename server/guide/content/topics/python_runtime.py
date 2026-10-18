"""Topic 02 — python-runtime (authored after the 3.1 exemplar pattern).

What actually runs the code this server is written in: the CPython
interpreter's compile-and-cache pipeline · the asyncio event loop and
await · the GIL and the free-threading experiment · memory (refcounting,
the generational GC, __slots__) · sync vs async iteration with the topic's
streaming demo INLINE · the uv toolchain · process, environment, and
signals · concurrency decision-making with the topic's async-timing demo
INLINE · the terminal companion.

Every code block below quotes a real repo file (the snippet ratchet
verifies it); bash blocks are the sourcing-exempt exception, and the one
dockerfile quote is exempt by language.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="python-runtime",
    title="The CPython runtime",
    subtitle=(
        "What actually runs your code — bytecode, the event loop, the GIL, "
        "memory, and processes — with measurements, not folklore."
    ),
    group="foundations",
    order=2,
    sections=[
        # ── 1. What CPython does with your .py files ────────────────────────
        Section(
            id="what-cpython-does",
            title="What CPython does with your .py files",
            blocks=[
                TextBlock(
                    kind="text",
                    id="cpython-pipeline",
                    text=(
                        "\"Interpreted\" undersells CPython. When uvicorn imports "
                        "guide.main:app, every module on that import path goes through a "
                        "real compilation pipeline before anything executes: source text is "
                        "tokenized, parsed into an abstract syntax tree, compiled into "
                        "bytecode — a code object of stack-machine instructions plus "
                        "constants — and only then does CPython's evaluation loop start "
                        "executing those instructions one by one. The bytecode is what "
                        "runs; \"interpreted\" describes the last step only. You can watch "
                        "each stage with the standard library: dis.dis(f) pretty-prints "
                        "the bytecode a function compiles to (LOAD_FAST, BINARY_OP, "
                        "RETURN_VALUE and friends), and python -m py_compile file.py runs "
                        "just the compile step with no execution."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cpython-cache",
                    text=(
                        "Compilation is pure work, so CPython caches it: the first import "
                        "of a module writes its bytecode to __pycache__/module.cpython-"
                        "313.pyc next to the source, and later imports load that file "
                        "instead of re-parsing. The cache is validated cheaply — since "
                        "Python 3.7 the default checks the source file's mtime and size "
                        "recorded in the .pyc header, so editing the file (or touching it "
                        "to a new size or timestamp) invalidates the entry automatically. "
                        "A deployed image can skip validation entirely and, better, skip "
                        "the cold-start compile entirely: this repo's production build "
                        "sets UV_COMPILE_BYTECODE=1 so uv compiles every installed file "
                        "to .pyc at image-build time — one compile at build, zero parses "
                        "per container start. That flag lives in .docker/server/"
                        "Dockerfile.prod, whose language is exempt from this guide's "
                        "source-quote ratchet, so it is cited here in prose rather than "
                        "quoted; what the manifest CAN show is why a build backend "
                        "exists at all:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cpython-build-system",
                    language="toml",
                    caption="Why the project builds a wheel: the prod image installs a static copy.",
                    source="server/pyproject.toml",
                    snippet=(
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
                    id="cpython-vm-honesty",
                    text=(
                        "Because the prod image installs the guide package as a built "
                        "wheel rather than a live source tree, bytecode-compiling it at "
                        "image build is compiling exactly the bytes that will ship. The "
                        "same discipline explains a detail from topic 01: annotations are "
                        "stored but not enforced — enforcement would be compile-time "
                        "work, and CPython's compile step deliberately does almost no "
                        "semantic analysis. It resolves names to a limited degree and "
                        "emits instructions; mypy is the pass that proves types, run "
                        "separately over the same source."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cpython-folklore",
                    text=(
                        "Two honest clarifications keep this section folklore-free. "
                        "First, bytecode is not machine code: the evaluation loop is a "
                        "big interpreter switch over those instructions, and since 3.11 "
                        "it is a specializing adaptive one (PEP 659) — hot instructions "
                        "rewrite themselves into faster specialized forms at runtime "
                        "(an ADD of two ints becomes a pre-checked INT_ADD), which is "
                        "where much of 3.11's speedup came from. Second, the JIT "
                        "question: Python 3.13 does ship a JIT (PEP 744, a copy-and-"
                        "patch design), but as an experimental feature that must be "
                        "enabled when CPython itself is built (--enable-experimental-"
                        "jit) — it is not present in the standard CPython builds, "
                        "including the python:3.13 image this repo runs. The honest "
                        "status: the interpreter you deploy today executes bytecode in "
                        "the eval loop; a production-default JIT is a future, not a "
                        "present."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cpython-shell-tour",
                    text=(
                        "The shell makes the pipeline tangible in four commands — "
                        "compile one module, find its cached bytecode, and disassemble "
                        "a function to see what the VM actually runs:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cpython-bash",
                    language="bash",
                    source=None,
                    snippet=(
                        "# from server/ — compile without executing, then find the cache\n"
                        "python3 -m py_compile guide/main.py && ls __pycache__/\n"
                        "# what a def really becomes: bytecode for the VM's stack machine\n"
                        "python3 -c \"import dis; dis.dis(lambda x: x * 2)\""
                    ),
                ),
            ],
        ),
        # ── 2. The event loop ───────────────────────────────────────────────
        Section(
            id="event-loop",
            title="The event loop and await",
            blocks=[
                TextBlock(
                    kind="text",
                    id="loop-model",
                    text=(
                        "asyncio's event loop is a scheduler with three moving parts:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="loop-parts-list",
                    ordered=False,
                    items=[
                        "Ready queue — callbacks to run.",
                        "Timer heap — things to wake later.",
                        "OS readiness selector — (epoll/kqueue) for sockets and files.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="loop-rule",
                    text=(
                        "The loop's rule is simple — run whatever is ready, "
                        "in first-in-first-out order; when nothing is ready, park in the "
                        "selector until something is. A coroutine is a pausable "
                        "function: calling it creates an object that runs in steps; a "
                        "Task wraps one and drives it on the loop. The suspension "
                        "mechanism is await: reaching an await that cannot finish yet "
                        "yields control back to the loop, which runs someone else and "
                        "resumes this coroutine when its result is ready. That is the "
                        "whole trick behind every async def handler this server has — "
                        "the error handlers run on the loop, and while one request's "
                        "handler waits, the loop serves others:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="loop-async-handler",
                    language="py",
                    caption="A real async handler from the error taxonomy.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:\n"
                        "    \"\"\"AppError → its mapped status + envelope; logged with the request id.\"\"\"\n"
                        "    logger.warning(\n"
                        "        \"app_error\",\n"
                        "        request_id=resolve_request_id(request),\n"
                        "        kind=exc.kind.value,\n"
                        "        message=exc.message,\n"
                        "    )\n"
                        "    return _build_error_response(\n"
                        "        request,\n"
                        "        http_status_for(exc.kind),\n"
                        "        exc.kind,\n"
                        "        exc.message,\n"
                        "        exc.details,\n"
                        "        extra_headers=exc.headers,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="loop-cooperation",
                    text=(
                        "Note what that handler does not do: await anything. async def "
                        "does not require awaiting inside — it makes the function a "
                        "coroutine the loop can interleave, which FastAPI exploits to "
                        "run handlers concurrently under load even when a handler is "
                        "CPU-light. The costs of the model are equally real and worth "
                        "stating: the loop is cooperative, so ONE blocking call (time."
                        "sleep, requests.get, a slow hash loop) freezes every task on "
                        "that loop — there is no pre-emption. And the concurrency is "
                        "within a single thread: awaits overlap WAITING, they never "
                        "overlap COMPUTING. Section 8 measures exactly that distinction "
                        "on this repo's demo endpoint."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="loop-tasks",
                    text=(
                        "The unit of scheduled work is the Task, and asyncio.gather is "
                        "the classic way to run several at once: it wraps each argument "
                        "in a Task, awaits them all, and returns their results in "
                        "ARGUMENT order — not completion order — while each task "
                        "proceeds independently. The simulated-I/O coroutine below is "
                        "the demo's stand-in for a network call; timing it is the "
                        "subject of Section 8:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="loop-simulate-io",
                    language="py",
                    caption="The demo's simulated network call, from the timing builder.",
                    source="server/guide/domain/demos/runtime_async.py",
                    snippet=(
                        "async def _simulate_io(name: str, io_ms: int, done: list[str]) -> TaskTiming:\n"
                        "    \"\"\"One simulated network call: sleep, record completion, report cost.\"\"\"\n"
                        "    started = time.perf_counter()\n"
                        "    await asyncio.sleep(io_ms / 1000)\n"
                        "    done.append(name)\n"
                        "    elapsed_ms = (time.perf_counter() - started) * 1000\n"
                        "    return TaskTiming(name=name, simulated_io_ms=io_ms, measured_ms=round(elapsed_ms, 2))"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="loop-sleep",
                    text=(
                        "asyncio.sleep is a real await: unlike time.sleep it never "
                        "blocks the thread — it schedules a wakeup on the timer heap "
                        "and yields. asyncio.sleep(0) is the pure form: no timer "
                        "at all, just yield control to the loop and come back on the next "
                        "pass — the canonical way to say \"let others run\", and the "
                        "primitive the demo's interleaving trace (Section 8) uses to "
                        "prove that await really suspends."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="loop-tests",
                    text=(
                        "Tests need the same machinery, one loop per test: pytest-"
                        "asyncio provides it, and this repo runs it in auto mode so "
                        "every async def test just works — the configuration is one "
                        "manifest line, quoted below. One loop per test is also why "
                        "the fixture design in tests/conftest.py stays synchronous: "
                        "TestClient runs the app on its own portal loop, so sync test "
                        "code drives async endpoints without ceremony."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="loop-pytest-asyncio",
                    language="toml",
                    caption="One line makes every async test run on its own loop.",
                    source="server/pyproject.toml",
                    snippet=(
                        "[tool.pytest.ini_options]\n"
                        "asyncio_mode = \"auto\"\n"
                        "testpaths = [\"tests\"]"
                    ),
                ),
            ],
        ),
        # ── 3. The GIL and free-threading ───────────────────────────────────
        Section(
            id="gil-and-free-threading",
            title="The GIL and free-threading",
            blocks=[
                TextBlock(
                    kind="text",
                    id="gil-what",
                    text=(
                        "The Global Interpreter Lock is a mutex inside CPython that a "
                        "thread must hold to execute Python bytecode. It exists because "
                        "the interpreter's core state is shared and not thread-safe "
                        "most famously reference counts, which every assignment and "
                        "every name binding updates: without a lock, two threads "
                        "updating one object's refcount concurrently could leak or "
                        "free objects prematurely. CPython's answer was to serialize "
                        "execution — one thread bytecode-interpretting at a time per "
                        "process — and the consequences follow mechanically. CPU-bound "
                        "threads do not parallelize: two threads computing in pure "
                        "Python on many cores use roughly one core's worth of "
                        "throughput, plus context-switch overhead. I/O-bound threads DO "
                        "help: blocking calls made through C extensions (sockets, "
                        "file reads, time.sleep, database drivers) release the GIL "
                        "while waiting, so other threads run — which is why thread "
                        "pools remain a legitimate answer for blocking libraries even "
                        "on an async codebase, usually via asyncio.to_thread."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="gil-conflations",
                    text=(
                        "It is worth separating two things beginners conflate: the GIL "
                        "is not why Python is \"slow\", and asyncio does not \"beat\" "
                        "the GIL. The GIL limits THREAD parallelism of the interpreter; "
                        "asyncio sidesteps the question entirely by being one thread, "
                        "one loop — it overlaps waits, never computes in parallel. This "
                        "repo's server is a single-threaded event loop inside one "
                        "process; the GIL is present and irrelevant to its "
                        "concurrency profile. You can probe which kind of build you "
                        "are running:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="gil-probe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# standard build → None (or 0); free-threaded build → 1\n"
                        "python3 -c \"import sysconfig; print(sysconfig.get_config_var('Py_GIL_DISABLED'))\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="gil-free-threading",
                    text=(
                        "Free-threading is the project to remove that mutex (PEP 703). "
                        "The engineering is real: reference counting becomes biased "
                        "(thread-local counts flushed to shared ones) so the hottest "
                        "shared state stops needing the lock, per-object locks cover "
                        "the rest, immortal objects (already in 3.12) stop common "
                        "singletons from churning counts at all, and the GC learned to "
                        "scan in a world that mutates concurrently. Python 3.13 ships "
                        "this as an experimental, SEPARATE build (the python3.13t "
                        "binary, built with --disable-gil; the probe above returns 1 "
                        "there), and its GIL can even be re-enabled at runtime via the "
                        "PYTHON_GIL environment variable for A/B testing. It is not the "
                        "build any mainstream distribution installs by default, and it "
                        "is not what this repo runs — the uv python3.13 image is the "
                        "standard GIL build, as the probe in the tour of Section 9 "
                        "shows. The status line worth remembering: 3.13 proved it "
                        "works, 3.14 promotes it toward officially supported while "
                        "still optional, and the deciding vote is the C-extension "
                        "ecosystem adopting free-threaded wheels."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="gil-subinterpreters",
                    text=(
                        "A related-but-distinct feature sometimes gets folded into "
                        "this story and should not be: per-interpreter GILs (PEP 684) "
                        "give each subinterpreter its own GIL inside one process — a "
                        "middle ground the interpreter itself is growing toward. For "
                        "practical decisions today:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="gil-practical-choices-list",
                    ordered=False,
                    items=[
                        "I/O-bound workloads — asyncio (this repo).",
                        "Blocking libraries — threads via to_thread.",
                        "CPU-bound Python — separate PROCESSES (multiprocessing, "
                        "ProcessPoolExecutor, or simply more containers — each process "
                        "has its own interpreter and its own GIL).",
                        "CPU-bound algorithms — NumPy/compiled extensions, which hold "
                        "the GIL only briefly.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="gil-decision-table-ahead",
                    text="Section 8 turns this into a decision table.",
                ),
            ],
        ),
        # ── 4. Memory: refcounting, GC, __slots__ ───────────────────────────
        Section(
            id="memory",
            title="Memory: refcounting, the GC, and __slots__",
            blocks=[
                TextBlock(
                    kind="text",
                    id="memory-refcounting",
                    text=(
                        "CPython's primary memory management is reference counting, "
                        "and it is deterministic: every object carries a count of "
                        "references to it; binding a name (x = obj), putting it in a "
                        "container, or passing it to a function increments the count; "
                        "rebinding, del, a container going away, or a frame exiting "
                        "decrements it. When the count hits zero the object is freed "
                        "immediately — not \"at some point\", now, on the thread that "
                        "dropped the last reference. sys.getrefcount(x) reports the "
                        "count (one higher than you expect, transiently: the call's "
                        "own argument binding is itself a reference). Deterministic "
                        "destruction is why file objects close reasonably promptly when "
                        "they go out of scope, and why __del__ can serve as a "
                        "last-resort safety net — though an explicit with (topic 01, "
                        "context managers) remains the disciplined form."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="memory-cycles",
                    text=(
                        "Refcounting's blind spot is cycles: a.b = b; b.a = a leaves "
                        "two objects with nonzero counts and no outside references. "
                        "That is the garbage collector's job — a generational, "
                        "TRACING collector that periodically walks objects to find "
                        "unreachable cycles refcounting cannot free. It organizes "
                        "objects into three generations by survival; allocation "
                        "counters trip collections (young collections are frequent and "
                        "cheap; promotion to older generations means scanned rarely). "
                        "The gc module exposes the machinery:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="memory-gc-api-list",
                    ordered=False,
                    items=[
                        "gc.collect() — forces a walk.",
                        "gc.disable() — turns cyclic collection off entirely — "
                        "refcounting keeps working, only cycles would leak.",
                        "gc.set_threshold — tunes the trip points.",
                        "gc.freeze — one niche-but-real production trick: right after "
                        "startup it marks long-lived startup objects as permanent so "
                        "fork-based worker pools never rescan (or dirty) them.",
                    ],
                ),
                CodeBlock(
                    kind="code",
                    id="memory-refcount-bash",
                    language="bash",
                    source=None,
                    snippet=(
                        "# deterministic lifetime: count drops to zero, object frees NOW\n"
                        "python3 -c \"import gc, sys; xs = [1, 2]; print(sys.getrefcount(xs)); del xs; print(gc.isenabled())\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="memory-slots",
                    text=(
                        "Instance layout is the third lever. A normal object carries a "
                        "per-instance __dict__ — flexible, but each instance pays for a "
                        "hash table, and attribute access goes through it. A class "
                        "declaring __slots__ replaces that dict with fixed slot "
                        "descriptors: instances get a flat, fixed-size layout — "
                        "measurably less memory per instance and faster attribute "
                        "access, at the cost of no undeclared attributes (usually a "
                        "feature) and some multiple-inheritance friction. This repo's "
                        "records opt in wholesale: every dataclass below is declared "
                        "@dataclass(frozen=True, slots=True), so slots generation is "
                        "one decorator flag instead of a hand-written slot list. The "
                        "snippet matcher's result type is the canonical small record:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="memory-snippet-match",
                    language="py",
                    caption="frozen + slots: an immutable, flat, hashable record.",
                    source="server/guide/content/snippet_matcher.py",
                    snippet=(
                        "@dataclass(frozen=True, slots=True)\n"
                        "class SnippetMatch:\n"
                        "    \"\"\"Outcome of one snippet verification; truthy when ok.\"\"\"\n"
                        "\n"
                        "    ok: bool\n"
                        "    reason: str | None = None\n"
                        "\n"
                        "    def __bool__(self) -> bool:\n"
                        "        return self.ok"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="memory-comment-style",
                    language="py",
                    caption="The same flags on a config-holding record — docstrings included.",
                    source="server/guide/content/snippet_matcher.py",
                    snippet=(
                        "@dataclass(frozen=True, slots=True)\n"
                        "class _CommentStyle:\n"
                        "    \"\"\"How comments are written in one language family.\"\"\"\n"
                        "\n"
                        "    line_tokens: tuple[str, ...] = ()\n"
                        "    \"\"\"Trailing/full-line tokens that start a comment anywhere on the line.\"\"\"\n"
                        "\n"
                        "    # …\n"
                        "\n"
                        "    quote_aware: bool = True"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="memory-coda",
                    text=(
                        "Why a server cares: a registry holding thousands of frozen "
                        "records (this guide's content model) or an endpoint juggling "
                        "thousands of small value objects feels the per-instance "
                        "dict cost directly — slots is the cheap, honest fix, and "
                        "pydantic models support it too. The two memory stories also "
                        "compose differently than people expect: pydantic's Rust core "
                        "validates outside the GIL's bytecode tax, but instances are "
                        "still Python objects under refcounting; and for the "
                        "free-threaded build (previous section) biased refcounting is "
                        "precisely the change that makes dropping the GIL viable. "
                        "Memory here is not a tuning afterthought — it is the design "
                        "pressure that shaped the interpreter's concurrency story."
                    ),
                ),
            ],
        ),
        # ── 5. Streams: sync vs async iteration (inline demo) ───────────────
        Section(
            id="streams",
            title="Streams: sync iteration vs async iteration",
            lead="This section carries the topic's streaming demo — beside the teaching it proves.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="streams-two-protocols",
                    text=(
                        "Python has two iteration protocols, and the difference is "
                        "exactly the difference between this section's halves. Sync "
                        "iteration — __iter__/__next__, the for loop — assumes each "
                        "step is CPU work: get the next item now. Sync generators "
                        "(yield inside a plain def, topic 01) produce items lazily but "
                        "still on the caller's clock, and a slow producer BLOCKS the "
                        "thread. Async iteration replaces both halves with awaitable "
                        "forms: __aiter__/__anext__, where each anext() may suspend "
                        "until data exists; async for consumes them; async "
                        "comprehensions collect them. An async generator is async def "
                        "plus yield: calling it yields (no pun intended) an async "
                        "generator object whose body runs only as far as the next "
                        "yield per anext — the producer is a coroutine the loop can "
                        "interleave with everything else, waiting on I/O between "
                        "items without holding the thread hostage."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="streams-anatomy",
                    text=(
                        "On a server this is the anatomy of every streamed response: "
                        "the handler does not build a list and return it (materialize "
                        "everything, then send); it hands the framework an async "
                        "generator, and the framework pulls items as the socket "
                        "accepts them — production and consumption interleave, memory "
                        "stays O(item), and the first byte leaves before the last "
                        "item exists. This repo's streaming demo endpoint is built "
                        "exactly that way, and its generator is real code worth "
                        "reading in full:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="streams-generator",
                    language="py",
                    caption="The demo's async generator: awaited ticks between yields.",
                    source="server/guide/domain/demos/runtime_streaming.py",
                    snippet=(
                        "async def stream_runtime_chunks(\n"
                        "    item_count: int = STREAM_ITEMS, tick: float = STREAM_TICK\n"
                        ") -> AsyncIterator[str]:\n"
                        "    \"\"\"The demo's async generator: open line, awaited items, closing line.\"\"\"\n"
                        "    started = time.perf_counter()\n"
                        "    yield _encode(\n"
                        "        StreamChunk(\n"
                        "            seq=0,\n"
                        "            kind=\"open\",\n"
                        "            # …\n"
                        "        )\n"
                        "    )\n"
                        "    for index in range(1, item_count + 1):\n"
                        "        await asyncio.sleep(tick)  # the simulated I/O between yields\n"
                        "        yield _encode(\n"
                        "            StreamChunk(\n"
                        "                seq=index,\n"
                        "                kind=\"item\",\n"
                        "                # …\n"
                        "            )\n"
                        "        )\n"
                        "    elapsed_ms = (time.perf_counter() - started) * 1000\n"
                        "    yield _encode(\n"
                        "        StreamChunk(\n"
                        "            seq=item_count + 1,\n"
                        "            kind=\"closed\",\n"
                        "            # …\n"
                        "        )\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="streams-ndjson",
                    text="Three details make this honest demo code rather than a toy.",
                ),
                ListBlock(
                    kind="list",
                    id="streams-ndjson-details-list",
                    ordered=False,
                    items=[
                        "The shape is deterministic — one open line, a fixed item "
                        "count, one closing line carrying the measured wall-clock "
                        "cost — so tests can pin count and order while the payload "
                        "still contains a genuinely measured number.",
                        "Each item is preceded by a real await — a 2 ms sleep standing "
                        "in for a query or queue read: remove it and the generator "
                        "still yields lazily, but nothing would ever interleave with "
                        "the producer — the await is what makes it a STREAM rather "
                        "than a deferred list.",
                        "The wire format is NDJSON — newline-delimited JSON, media "
                        "type application/x-ndjson — the deliberately boring choice "
                        "real log tails and event feeds use: each line parses on its "
                        "own, consumers process complete lines as they arrive, and "
                        "no single envelope has to fit the whole payload.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="streams-router-two-statements",
                    text="The router is two statements:",
                ),
                CodeBlock(
                    kind="code",
                    id="streams-router",
                    language="py",
                    caption="StreamingResponse pulls the generator as the client reads.",
                    source="server/guide/presentation/routers/demo/runtime.py",
                    snippet=(
                        "@router.get(\"/streaming\")\n"
                        "async def read_streaming() -> StreamingResponse:\n"
                        "    \"\"\"Stream the async generator's chunks as NDJSON lines, as produced.\"\"\"\n"
                        "    return StreamingResponse(stream_runtime_chunks(), media_type=NDJSON_MEDIA_TYPE)"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="runtime:streaming",
                    title="An async generator, streamed — the proof",
                    description=(
                        "GET /api/demo/runtime/streaming serves a real async generator "
                        "as NDJSON: an open line, six items each preceded by an "
                        "awaited tick, and a closing line with the measured cost of "
                        "the whole stream. Watch the lines arrive as they are "
                        "produced."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="streams-coda",
                    text=(
                        "Read the demo with the protocol in mind: every line you see "
                        "is one anext() on the generator above; the pauses between "
                        "arrivals are the awaited ticks; the closing line's totalMs "
                        "is measured around the entire production. The client renders "
                        "each line as it arrives where the browser's stream seam "
                        "allows, falling back to the collected result otherwise — "
                        "the same producer either way, which is the point: the "
                        "producer's contract (async iteration) does not change with "
                        "the consumer's rendering strategy. Sync iteration remains "
                        "the right tool when data is in memory and steps are pure "
                        "CPU — comprehensions (topic 01) are sync iteration doing its "
                        "best work. Async iteration earns its complexity exactly when "
                        "producing the next item means waiting on the world."
                    ),
                ),
            ],
        ),
        # ── 6. The toolchain: uv, venv, lockfile ────────────────────────────
        Section(
            id="toolchain",
            title="The toolchain: uv, venvs, and the lockfile",
            blocks=[
                TextBlock(
                    kind="text",
                    id="toolchain-uv",
                    text=(
                        "The interpreter needs a manager, and this repo standardized "
                        "on uv — one Rust binary replacing venv, pip, pip-tools, and "
                        "pyenv-shaped workflow:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="toolchain-uv-commands-list",
                    ordered=False,
                    items=[
                        "uv venv — creates environments.",
                        "uv add / uv remove — edits dependencies.",
                        "uv sync — materializes an environment from a lockfile.",
                        "uv run — executes any command inside the project "
                        "environment.",
                        "uv python — installs interpreters.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="toolchain-two-file-split",
                    text=(
                        "The discipline that makes it all trustworthy "
                        "is the two-file split. server/pyproject.toml declares "
                        "INTENT: dependency RANGES (fastapi>=0.115) plus the dev "
                        "group carrying the verifier tooling. server/uv.lock records "
                        "RESOLUTION: the exact version and hash of every package in "
                        "the closed graph, platform-marked, committed to git. Ranges "
                        "say what you accept; the lock says what you run — and "
                        "`uv sync --locked` installs exactly the lock, refusing if "
                        "the manifest has drifted without a re-lock. Every "
                        "verification command in this guide's README funnels through "
                        "that flag, which is why \"green on my machine\" is "
                        "meaningful here."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="toolchain-dev-group",
                    language="toml",
                    caption="PEP 735 dev group: the verifier toolchain rides with the project.",
                    source="server/pyproject.toml",
                    snippet=(
                        "# Dev tooling rides in the PEP 735 dev group (the uv convention): `uv sync`\n"
                        "# installs it by default; production image builds pass --no-dev.\n"
                        "[dependency-groups]\n"
                        "dev = [\n"
                        "    \"httpx>=0.27\",\n"
                        "    \"mypy>=1.13\",\n"
                        "    \"pytest>=8.3\",\n"
                        "    \"pytest-asyncio>=0.24\",\n"
                        "    \"ruff>=0.8\",\n"
                        "]"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="toolchain-lock-head",
                    language="toml",
                    caption="The lock's own header: the interpreter contract, pinned repo-wide.",
                    source="server/uv.lock",
                    snippet=(
                        "version = 1\n"
                        "revision = 3\n"
                        "requires-python = \">=3.13\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="toolchain-discipline",
                    text=(
                        "The quoted lock header is doing real work: requires-python "
                        "at the lock level means the resolution is valid for a whole "
                        "interpreter floor, and the resolution-markers inside handle "
                        "per-platform differences. The workflow around it stays "
                        "small: add or bump in pyproject, run uv lock to re-resolve "
                        "(the lock diff is reviewable — versions, hashes, markers), "
                        "uv lock --check in a pinch to assert the lock still matches "
                        "the manifest, uv sync --locked everywhere you install. "
                        "Upgrades are therefore deliberate acts with diffs, not "
                        "ambushes."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="toolchain-contracts",
                    text=(
                        "Two more contracts complete the toolchain. .python-version "
                        "pins the interpreter (3.13) so uv run and IDEs agree; and "
                        "because this family keeps the HOST clean — no project venv "
                        "on the laptop, no host node_modules — every verification "
                        "runs in an ephemeral container with shared cache volumes, "
                        "flocked against concurrent runs. The one-liner is the "
                        "README's, verbatim:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="toolchain-verify",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the family verification gate: lock-exact env, then the suite\n"
                        "docker run --rm -v \"$PWD\":/repo -w /repo/server -v fdg-uv:/root/.cache/uv \\\n"
                        "  ghcr.io/astral-sh/uv:python3.13-bookworm \\\n"
                        "  bash -lc 'flock /repo/server/.verify.lock bash -c \"uv sync --locked && uv run pytest -q\"'"
                    ),
                ),
            ],
        ),
        # ── 7. Process, environment, signals ────────────────────────────────
        Section(
            id="process-env-signals",
            title="Process, environment, and signals",
            blocks=[
                TextBlock(
                    kind="text",
                    id="process-boundary",
                    text=(
                        "A process is the runtime's hard boundary: one OS process "
                        "holds one interpreter, one event loop, one memory space, and "
                        "— practically for servers — one immutable snapshot of its "
                        "start-time environment. Twelve-factor discipline says "
                        "configuration lives in the environment, not the code; "
                        "pydantic-settings is this repo's typed reader of it. "
                        "AppConfig declares every knob as a field whose name doubles "
                        "as its FDG_-prefixed env var; instances are frozen (a config "
                        "is a snapshot, never mutated); and get_config() caches one "
                        "instance per process — the cache is the code making the "
                        "\"env is read once\" rule literal. A changed environment "
                        "variable reaches the app through a RESTART, not a refresh:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="process-get-config",
                    language="py",
                    caption="One process, one config snapshot — lru_cache is the proof.",
                    source="server/guide/core/config.py",
                    snippet=(
                        "@lru_cache(maxsize=1)\n"
                        "def get_config() -> AppConfig:\n"
                        "    \"\"\"Return the process-wide config instance (one per process).\"\"\"\n"
                        "    return AppConfig()"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="process-compose-env",
                    language="yaml",
                    caption="The compose dev stack wires the FDG_ rails per service.",
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
                    id="process-env-targets",
                    text=(
                        "The environment also differs per deployment target in that "
                        "quote: inside compose the data services are reachable by "
                        "service name (postgres, redis, mongo), while the manifest "
                        "defaults point at localhost for bare runs — one config class, "
                        "two environments, zero code branches. os.environ is the raw "
                        "floor under all of it (a real dict-like your code can read, "
                        "though this repo never does directly — AppConfig is the only "
                        "reader, so a typo in an env var name surfaces as a pydantic "
                        "error, not a silent None)."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="process-signals",
                    text=(
                        "Signals are how the outside world talks to a process, and a "
                        "server must answer two of them well: SIGTERM (\"stop, "
                        "gracefully\" — what docker stop and every orchestrator "
                        "sends) and SIGINT (Ctrl-C's interrupt). Uvicorn's graceful "
                        "shutdown sequence is:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="process-shutdown-steps-list",
                    ordered=True,
                    items=[
                        "Stop accepting new connections.",
                        "Let in-flight requests finish.",
                        "Close keep-alive connections.",
                        "Exit.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="process-shutdown-ceiling",
                    text=(
                        "The escape hatch is a ceiling — the longest a stubborn "
                        "request may hold the process open — and this repo sets it to "
                        "30 seconds in the production image's entrypoint, the last "
                        "line of which is quoted here (a Dockerfile, whose language "
                        "the ratchet exempts):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="process-cmd",
                    language="dockerfile",
                    caption="The prod entrypoint: uvicorn as PID 1, draining on SIGTERM.",
                    source=None,
                    snippet=(
                        "# Graceful shutdown: in-flight requests get 30s to drain before exit.\n"
                        "CMD [\"uvicorn\", \"guide.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\", \"--timeout-graceful-shutdown\", \"30\"]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="process-coda",
                    text=(
                        "Two process details in that CMD repay attention. It is exec "
                        "form (JSON array), so uvicorn IS the container's PID 1 and "
                        "receives signals directly — shell form would leave a shell "
                        "as PID 1 swallowing SIGTERM, the classic container-never-"
                        "stops bug. And one process here means one event loop and one "
                        "config snapshot; when you scale by running more worker "
                        "processes (the deployment topic), each worker re-reads the "
                        "environment and builds its own loop — the process boundary "
                        "is what makes horizontal scaling conceptually clean. You can "
                        "watch the env rail work from your own shell:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="process-env-bash",
                    language="bash",
                    source=None,
                    snippet=(
                        "# from server/ — the rail overrides, the default holds otherwise\n"
                        "FDG_ENV=prod uv run python -c \"from guide.core.config import get_config; print(get_config().env)\""
                    ),
                ),
            ],
        ),
        # ── 8. Concurrency patterns (inline demo) ───────────────────────────
        Section(
            id="concurrency-patterns",
            title="Concurrency patterns: choosing your mechanism",
            lead="This section carries the topic's async-timing demo — beside the decision table it proves.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="concurrency-table",
                    text="Everything so far collapses into one decision.",
                ),
                ListBlock(
                    kind="list",
                    id="concurrency-mechanisms-list",
                    ordered=False,
                    items=[
                        "asyncio — I/O-bound work, thousands of concurrent waits, "
                        "cooperative yielding on a single thread — cheapest in memory "
                        "and switching, but one blocking call poisons the loop and "
                        "CPU-heavy handlers serialize.",
                        "Threads — pre-emptive, the answer for blocking libraries and "
                        "legacy SDKs (bridge with asyncio.to_thread so they stop "
                        "blocking the loop) — the GIL still serializes bytecode, "
                        "though waits release it, and each thread costs real memory.",
                        "Processes — actual parallel compute — separate interpreters, "
                        "separate GILs, at the price of startup, IPC serialization, "
                        "and per-process memory; in container-land you usually get "
                        "this by running more replicas rather than multiprocessing.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="concurrency-rules-of-thumb",
                    text=(
                        "The rules of thumb "
                        "this repo follows: async by default at the edges; to_thread "
                        "for the blocking corner; never pure-Python CPU work at "
                        "scale (push it to NumPy, an extension, or another process)."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="concurrency-function-scale",
                    text=(
                        "Inside asyncio the same choice recurses at function scale: "
                        "await one thing at a time (sequential — total time is the "
                        "sum) versus gather/TaskGroup them (concurrent — total time "
                        "is the longest). The demo below runs the SAME three "
                        "simulated-I/O calls both ways and measures; its two runners "
                        "are the entire difference:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="concurrency-sequential",
                    language="py",
                    caption="Sequential: each await finishes before the next begins.",
                    source="server/guide/domain/demos/runtime_async.py",
                    snippet=(
                        "async def _run_sequential() -> TimingRun:\n"
                        "    \"\"\"Await each call in turn — the run costs the sum of the waits.\"\"\"\n"
                        "    started = time.perf_counter()\n"
                        "    done: list[str] = []\n"
                        "    per_task: list[TaskTiming] = []\n"
                        "    for name, io_ms in _IO_PLAN:\n"
                        "        per_task.append(await _simulate_io(name, io_ms, done))\n"
                        "    return TimingRun(\n"
                        "        strategy=\"sequential\",\n"
                        "        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),\n"
                        "        completion_order=done,\n"
                        "        per_task=per_task,\n"
                        "    )"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="concurrency-gathered",
                    language="py",
                    caption="Gathered: all three run at once; the wall clock is the longest.",
                    source="server/guide/domain/demos/runtime_async.py",
                    snippet=(
                        "async def _run_gathered() -> TimingRun:\n"
                        "    \"\"\"Start all three at once — the run costs the longest single wait.\"\"\"\n"
                        "    started = time.perf_counter()\n"
                        "    done: list[str] = []\n"
                        "    calls = [_simulate_io(name, io_ms, done) for name, io_ms in _IO_PLAN]\n"
                        "    per_task = await asyncio.gather(*calls)\n"
                        "    return TimingRun(\n"
                        "        strategy=\"gathered\",\n"
                        "        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),\n"
                        "        completion_order=done,\n"
                        "        per_task=list(per_task),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="concurrency-completion-order",
                    text=(
                        "The plan is deliberately ordered slowest-first (orders 60 ms, "
                        "billing 40 ms, inventory 20 ms), so the two runs also differ "
                        "in ORDER: sequential completes in start order; gathered "
                        "completes in delay order — inventory first despite being "
                        "started last. asyncio.gather returns results in argument "
                        "order regardless, which is why the builder records real "
                        "completion separately. For new code, prefer asyncio."
                        "TaskGroup (3.11+): the structured-concurrency form that "
                        "cancels siblings when one fails and reports the failures as "
                        "one ExceptionGroup, where gather by default lets you collect "
                        "exceptions as values (return_exceptions=True) — the demo "
                        "uses gather for the bare measurement; TaskGroup is the same "
                        "concurrency with better failure hygiene."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="concurrency-trace-proof",
                    text=(
                        "The demo's second exhibit proves the mechanism itself: two "
                        "actors log one event per step, separated by asyncio.sleep(0) "
                        "— a yield with no waiting — and the recorded trace shows "
                        "strict alternation, alpha and beta interleaving step for "
                        "step, because each await hands the loop back and the loop's "
                        "ready queue is first-in-first-out:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="concurrency-trace",
                    language="py",
                    caption="sleep(0): the explicit yield that makes interleaving visible.",
                    source="server/guide/domain/demos/runtime_async.py",
                    snippet=(
                        "async def _traced_actor(name: str, sink: list[TraceEvent]) -> None:\n"
                        "    \"\"\"Log an event per step, yielding control between steps (the proof).\"\"\"\n"
                        "    sink.append(TraceEvent(actor=name, event=\"start\"))\n"
                        "    for step in range(_TRACE_STEPS):\n"
                        "        await asyncio.sleep(0)  # yield control: no waiting, just rescheduling\n"
                        "        sink.append(TraceEvent(actor=name, event=f\"step-{step}\"))\n"
                        "    await asyncio.sleep(0)  # one more yield so even the done events alternate\n"
                        "    sink.append(TraceEvent(actor=name, event=\"done\"))"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="concurrency-router",
                    language="py",
                    caption="The demo endpoint: await the builder, declare the model.",
                    source="server/guide/presentation/routers/demo/runtime.py",
                    snippet=(
                        "@router.get(\"/async\", response_model=AsyncTimingPayload)\n"
                        "async def read_async_timing() -> AsyncTimingPayload:\n"
                        "    \"\"\"Serve the measured sequential-vs-gathered timing payload.\"\"\"\n"
                        "    return await build_async_timing_payload()"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="runtime:async",
                    title="Sequential vs gathered — measured, live",
                    description=(
                        "GET /api/demo/runtime/async runs three simulated-I/O "
                        "coroutines twice — awaited one after another, then under "
                        "asyncio.gather — and returns real timings, per-task costs, "
                        "completion orders, the speedup ratio, and a two-actor trace "
                        "proving await yields control step by step."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="concurrency-coda",
                    text=(
                        "Read the demo's numbers as claims about the loop, not about "
                        "hardware: sequential elapsed ≈ 60+40+20 = 120 ms (the sum); "
                        "gathered elapsed ≈ 60 ms (the longest); speedup ≈ 2x, "
                        "honest for three overlapping waits — it approaches the "
                        "NUMBER OF TASKS only when waits are equal, and approaches 1x "
                        "when one wait dominates, which is why the first question is "
                        "always \"what fraction of this request is waiting?\". Every "
                        "millisecond in the payload was measured on the request you "
                        "are reading; rerun it and the shape holds while the "
                        "milliseconds move — that is the difference between a "
                        "measurement and a slogan."
                    ),
                ),
            ],
        ),
        # ── 9. Terminal companion ───────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="The runtime's own API — read it from the shell.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-pitch",
                    text=(
                        "With the stack up (server on :8000), this tour walks the "
                        "runtime's observable surface: the curriculum index, this "
                        "topic, both demo endpoints — including the raw NDJSON "
                        "stream, best read unbuffered — and the error envelope "
                        "again, this time reached from the runtime's own demo area. "
                        "python3 -m json.tool remains the only helper installed:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-index",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the curriculum index: python-runtime sits in foundations\n"
                        "curl -s localhost:8000/api/content | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# this topic in full: nine sections, both demo blocks inline\n"
                        "curl -s localhost:8000/api/content/python-runtime | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-async",
                    language="bash",
                    source=None,
                    snippet=(
                        "# measured, not asserted: sum vs longest, per task, plus the trace\n"
                        "curl -s localhost:8000/api/demo/runtime/async | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-streaming",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the async generator's wire face: open, six items, closed — raw NDJSON\n"
                        "curl -s localhost:8000/api/demo/runtime/streaming"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-oneliner",
                    language="bash",
                    source=None,
                    snippet=(
                        "# one line, both measurements: sum → longest, in milliseconds\n"
                        "python3 -c \"import json,urllib.request as u; d=json.load(u.urlopen('http://localhost:8000/api/demo/runtime/async')); print(d['sequential']['elapsedMs'], '→', d['gathered']['elapsedMs'], 'ms')\""
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-404",
                    language="bash",
                    source=None,
                    snippet=(
                        "# unknown topic → the shared error envelope + x-request-id\n"
                        "curl -s -i localhost:8000/api/content/nope"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "The async demo answers with fresh measurements on every "
                        "call; the streaming endpoint answers line by line as its "
                        "generator produces. That pair is this topic in miniature: "
                        "a scheduler you can time, and iteration that waits without "
                        "blocking. The next topic stays at the boundary of that "
                        "runtime — HTTP itself, the protocol every handler here "
                        "speaks."
                    ),
                ),
            ],
        ),
    ],
)
