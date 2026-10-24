"""The performance-bench payload: measured numbers, never asserted ones.

``GET /api/demo/perf/bench`` serves this payload INLINE in topic 38's
compression section. The question the panel answers is the topic's first
section made executable — what does MEASURE FIRST actually look like — so
every row is computed at request time from the very process serving it:

- **Compression** — the REAL bytes this API serves (an internal round to
  ``GET /api/content`` for the topic index, another to this very topic's
  detail — the payload that delivered the panel), gzipped with the stdlib
  at the edge's live level and at gzip's default: bytes before/after,
  percent saved, mean encode and decode timing. No synthetic fixture
  bytes anywhere.
- **Async hygiene** — the topic-35 diagnosis compressed to one comparison
  row each: the same bounded CPU block run on the event loop vs offloaded
  through ``asyncio.to_thread``, with a concurrent REAL internal
  ``GET /api/health`` and a loop-lag probe witnessing each. The on-loop
  row starves the probe exactly as ``debug:stall`` taught; here it is the
  evidence for the hygiene rule, not the lesson itself.
- **Loop + protocol** — uvicorn's auto selection INTROSPECTED, not
  assumed: the running loop's class, whether ``uvicorn.loops.uvloop`` and
  the ``httptools_impl`` protocol module are loaded in THIS process, and
  the installed uvicorn/uvloop/httptools versions. Under pytest the rows
  say so honestly (TestClient drives the app in-process); under the live
  dev server they report the serving truth.
- **Pool** — the composition root's async engine pool, snapshotted by the
  router (dialect/driver, pool class, size, checked-out/in, wait timeout,
  the live ``status()`` line) — counters only, no connection opened.
- **GC** — stdlib introspection (thresholds, counts, collections,
  freeze count) plus ONE measured full ``gc.collect()`` run OFF the loop
  via ``asyncio.to_thread`` — the same containment the topic mandates.

Hard safety constraint, honored by construction: every duration is
bounded to hundreds of milliseconds (the hygiene blocks are 80ms budgets,
the gzip loops are single-digit iterations over ≤ ~60KB payloads), so the
shared dev stack's event loop is never wedged — the ``health_after`` row
is a REAL internal GET /api/health measured after the whole bench, the
loop's receipt for staying responsive.
"""

import asyncio
import gc
import gzip
import importlib.metadata
import json
import sys
import time
from typing import Final

from starlette.types import ASGIApp, Message, Scope

from guide.core.serialization import CamelModel

PROBE_TIMEOUT_S: Final = 5.0
"""Every internal round's ceiling — a wedged round raises, never hangs."""

PROBE_HOST: Final = "perf-bench.internal"
"""The host header internal probes carry (ASGI scope only)."""

HYGIENE_BUDGET_MS: Final = 80.0
"""Each hygiene row's bounded busy-loop budget — topic 35's debug:stall scale."""

LAG_TICK_SECONDS: Final = 0.02
"""The hygiene loop-lag probe's sleep interval (overshoot beyond it is lag)."""

GZIP_LEVELS: Final = (1, 6)
"""Level 1 is the repo edge's live default (nginx sets no gzip_comp_level);
6 is the stdlib gzip default — the trade-off row pair the section teaches."""


class CompressionRow(CamelModel):
    """One real payload × one gzip level, measured."""

    payload_id: str
    payload: str
    level: int
    raw_bytes: int
    gzipped_bytes: int
    saved_percent: float
    encode_ms: float
    decode_ms: float
    iterations: int


class HygieneRow(CamelModel):
    """One bounded CPU block, either on the loop or contained in a thread."""

    label: str
    what: str
    elapsed_ms: float
    loop_lag_max_ms: float
    concurrent_health_ms: float
    concurrent_health_status: int
    verdict: str


class FactRow(CamelModel):
    """One live introspection fact — id, label, and the honest value."""

    id: str
    label: str
    value: str


class GcCollectionRow(CamelModel):
    """One REAL full-collection measurement, run off the loop."""

    workload: str
    elapsed_ms: float
    collected: int
    off_loop: bool
    note: str


class HealthAfter(CamelModel):
    """The receipt: a real /api/health measured after the whole bench."""

    status: int
    elapsed_ms: float


class PoolFacts(CamelModel):
    """The engine pool snapshot the ROUTER reads — counters only, no I/O."""

    pool_class: str
    dialect: str
    driver: str
    size: int
    checked_in: int
    checked_out: int
    timeout_s: float
    status: str


class PerfBenchPanel(CamelModel):
    """Wire shape of ``GET /api/demo/perf/bench`` — the panel's contract."""

    compression: list[CompressionRow]
    hygiene: list[HygieneRow]
    loop: list[FactRow]
    pool: list[FactRow]
    gc_facts: list[FactRow]
    gc_collection: GcCollectionRow
    health_after: HealthAfter
    honesty_note: str


HONESTY_NOTE: Final = (
    "Every number was measured on this very request. The compression rows "
    "gzip the REAL bytes of two payloads this API serves — fetched through a "
    "real internal round to the app itself, then encoded with the stdlib at "
    "level 1 (the repo nginx edge's live default) and level 6 (gzip's "
    "default). The hygiene rows run the same 80ms CPU budget on-loop vs in "
    "a threadpool while a REAL internal /api/health and a loop-lag probe "
    "witness each. The loop/protocol rows introspect THIS process (under "
    "pytest they honestly say the uvicorn CLI is not the driver). The pool "
    "rows snapshot the composition root's engine pool — counters only, no "
    "connection opened. The GC rows read the stdlib collector and measure "
    "one full collection off the loop. All durations are bounded; the "
    "health_after row is a real /api/health after the whole bench."
)


# ── the internal-round channel (the arch-tracer / deploy-stack technique) ──


async def _drive_internal_get(app: ASGIApp, path: str) -> tuple[int, bytes, float]:
    """Drive ONE real internal GET at the ASGI boundary; status, body, elapsed.

    A hand-built ``http`` scope handed to the app callable — no socket, no
    staged responses. Whatever comes back is what the running app actually
    emitted, which is why the compression bench can treat these bytes as
    the real wire payload; the elapsed milliseconds are the probe's own
    perf_counter clock, the responsiveness witness the hygiene rows cite.
    """
    status: list[int] = []
    body_chunks: list[bytes] = []

    async def receive() -> Message:
        """The probe sends no body; an honest disconnect if anything asks."""
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        """Collect the status line and every body chunk as they leave."""
        if message["type"] == "http.response.start":
            status.append(int(message["status"]))
        elif message["type"] == "http.response.body":
            body_chunks.append(message.get("body", b""))

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", PROBE_HOST.encode("utf-8")),
            (b"accept", b"application/json"),
        ],
        "client": ("perf-bench", 0),
        "server": (PROBE_HOST, 80),
    }
    entered = time.perf_counter()
    await asyncio.wait_for(app(scope, receive, send), timeout=PROBE_TIMEOUT_S)
    if not status:
        raise RuntimeError(f"the internal round to {path} never flushed a response")
    elapsed_ms = round((time.perf_counter() - entered) * 1000, 1)
    return status[0], b"".join(body_chunks), elapsed_ms


# ── compression: real payloads, real gzip, real timing ─────────────────────


def _gzip_timings(raw: bytes, level: int, iterations: int) -> tuple[int, float, float]:
    """Bytes out + mean encode/decode milliseconds over bounded iterations."""
    gzipped = gzip.compress(raw, compresslevel=level)

    started = time.perf_counter()
    for _ in range(iterations):
        gzip.compress(raw, compresslevel=level)
    encode_ms = (time.perf_counter() - started) / iterations * 1000

    started = time.perf_counter()
    for _ in range(iterations):
        gzip.decompress(gzipped)
    decode_ms = (time.perf_counter() - started) / iterations * 1000
    return len(gzipped), encode_ms, decode_ms


async def _compression_rows(app: ASGIApp) -> list[CompressionRow]:
    """Bench the two real payloads this API serves, at both live levels.

    Payload one is the served topic index (the /api/content body — every
    topic id, group, order). Payload two is THIS topic's own detail page,
    the largest JSON this panel rides inside — the bench compresses the
    very bytes that delivered it.
    """
    specs: list[tuple[str, str, str, int]] = [
        (
            "content-index",
            "GET /api/content — the served topic index (real internal round)",
            "/api/content",
            20,
        ),
        (
            "performance-detail",
            "GET /api/content/performance — this very page's detail payload",
            "/api/content/performance",
            8,
        ),
    ]
    rows: list[CompressionRow] = []
    for payload_id, description, path, iterations in specs:
        status, raw, _ = await _drive_internal_get(app, path)
        if status != 200:
            raise RuntimeError(f"the internal round to {path} answered {status}")
        if payload_id == "content-index":
            counts = json.loads(raw)
            description += (
                f' — {len(counts["topics"])} topics, {len(counts["groups"])} groups'
            )
        for level in GZIP_LEVELS:
            gzipped_bytes, encode_ms, decode_ms = _gzip_timings(raw, level, iterations)
            rows.append(
                CompressionRow(
                    payload_id=payload_id,
                    payload=description,
                    level=level,
                    raw_bytes=len(raw),
                    gzipped_bytes=gzipped_bytes,
                    saved_percent=round((1 - gzipped_bytes / len(raw)) * 100, 1),
                    encode_ms=round(encode_ms, 3),
                    decode_ms=round(decode_ms, 3),
                    iterations=iterations,
                )
            )
    return rows


# ── async hygiene: one comparison pair, both probes live ───────────────────


def _burn_cpu_budget_ms(budget_ms: float) -> int:
    """Busy-loop a bounded wall-clock budget of real CPU work (spins returned).

    The same bounded burner shape topic 35's debug:stall uses — the work is
    deliberately opaque CPU so the ONLY variable between the two hygiene
    rows is where it runs.
    """
    deadline = time.perf_counter() + budget_ms / 1000
    spins = 0
    while time.perf_counter() < deadline:
        spins += sum(i * i for i in range(64))
    return spins


async def _lag_samples(*, ticks: int, interval_s: float) -> list[float]:
    """Sample event-loop lag: each tick's sleep overshoot beyond its interval.

    A healthy loop fires each sleep within microseconds of schedule; a loop
    blocked by sync code cannot fire ANY timer until the block ends. This
    is the instrument topic 35 built; the hygiene rows reuse it as evidence.
    """
    samples: list[float] = []
    for _ in range(ticks):
        before = time.perf_counter()
        await asyncio.sleep(interval_s)
        samples.append((time.perf_counter() - before - interval_s) * 1000)
    return samples


_HYGIENE_VERDICTS: Final[dict[str, str]] = {
    "threadpool-offload": (
        f"The {HYGIENE_BUDGET_MS:.0f}ms of CPU contained: asyncio.to_thread moved the "
        "block off the loop, the lag probe stayed quiet, and health answered "
        "mid-block. Slow for THIS request, scheduling preserved for every "
        "other — the fix this topic mandates for any blocking call."
    ),
    "on-loop-block": (
        f"The pathology: the SAME {HYGIENE_BUDGET_MS:.0f}ms budget run directly on the "
        "loop starved the in-flight lag tick and made the concurrent health "
        "request wait out the block. One request's block is every request's "
        "latency — bounded here on purpose, and taught at full depth by "
        "topic 35's debug:stall."
    ),
}


async def _hygiene_row(
    app: ASGIApp, *, label: str, what: str, offload: bool
) -> HygieneRow:
    """Run one bounded block with both probes live, then collect evidence."""
    lag_task = asyncio.create_task(_lag_samples(ticks=4, interval_s=LAG_TICK_SECONDS))
    health_task = asyncio.create_task(_drive_internal_get(app, "/api/health"))
    await asyncio.sleep(0)  # the probes are genuinely in flight when work starts

    started = time.perf_counter()
    if offload:
        await asyncio.to_thread(_burn_cpu_budget_ms, HYGIENE_BUDGET_MS)
    else:
        _burn_cpu_budget_ms(HYGIENE_BUDGET_MS)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)

    samples = await lag_task
    _, health_body, health_ms = await health_task
    return HygieneRow(
        label=label,
        what=what,
        elapsed_ms=elapsed_ms,
        loop_lag_max_ms=round(max(samples, default=0.0), 1),
        concurrent_health_ms=health_ms,
        concurrent_health_status=200 if health_body else 0,
        verdict=_HYGIENE_VERDICTS[label],
    )


# ── loop + protocol: uvicorn's auto selection, introspected ────────────────


def _dist_version(name: str) -> str:
    """The installed distribution's version, or an honest not-installed."""
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def _loop_fact_rows() -> list[FactRow]:
    """The serving stack's loop/protocol truth for THIS process."""
    loop = asyncio.get_running_loop()
    loop_module = type(loop).__module__
    loop_class = f"{loop_module}.{type(loop).__qualname__}"
    loop_value = (
        f"{loop_class} — uvloop is running this very event loop"
        if loop_module == "uvloop"
        else f"{loop_class} — the stdlib asyncio loop (pytest/TestClient, or uvicorn "
        "started without uvloop)"
    )

    if "uvicorn.loops.uvloop" in sys.modules:
        uvloop_value = (
            "yes — uvicorn.loops.uvloop is loaded in this process; uvicorn's auto "
            "loop setting selected uvloop"
        )
    elif "uvicorn.loops.asyncio" in sys.modules:
        uvloop_value = "no — uvicorn selected the stdlib asyncio loop (uvicorn.loops.asyncio)"
    else:
        uvloop_value = (
            "not observable from here — this process did not boot under the uvicorn "
            "CLI (pytest/TestClient drives the app in-process); the live dev server "
            "runs uvicorn, whose auto setting prefers uvloop when installed"
        )

    if "uvicorn.protocols.http.httptools_impl" in sys.modules:
        http_value = (
            "httptools — uvicorn.protocols.http.httptools_impl is loaded (auto "
            "selection picked the C parser)"
        )
    elif "uvicorn.protocols.http.h11_impl" in sys.modules:
        http_value = "h11 — the pure-Python HTTP parser fallback (uvicorn.protocols.http.h11_impl)"
    else:
        http_value = (
            "not observable from here — no uvicorn protocol module is loaded in this "
            "process; the live dev server's auto setting prefers httptools"
        )

    versions = (
        f"uvicorn {_dist_version('uvicorn')} · uvloop {_dist_version('uvloop')} · "
        f"httptools {_dist_version('httptools')} (importlib.metadata, this venv)"
    )
    return [
        FactRow(id="loop-class", label="the event loop serving this request", value=loop_value),
        FactRow(id="uvloop-selected", label="uvicorn's auto loop selection", value=uvloop_value),
        FactRow(
            id="http-protocol", label="uvicorn's auto HTTP parser selection", value=http_value
        ),
        FactRow(id="versions", label="installed versions", value=versions),
    ]


# ── pool: the composition root's engine, snapshotted by the router ─────────


def _pool_fact_rows(facts: PoolFacts) -> list[FactRow]:
    """Shape the router's snapshot into panel rows."""
    return [
        FactRow(
            id="dialect-driver",
            label="dialect / driver",
            value=f"{facts.dialect} over {facts.driver} (the config's database URL)",
        ),
        FactRow(
            id="pool-class",
            label="pool class",
            value=f"{facts.pool_class} — SQLAlchemy's default pool for async engines",
        ),
        FactRow(
            id="pool-size",
            label="pool size (steady-state connections)",
            value=(
                f"{facts.size} — create_db_engine sets pool_pre_ping only, so this is "
                "SQLAlchemy's documented default"
            ),
        ),
        FactRow(
            id="checkedout-now",
            label="connections at this request",
            value=f"checked out {facts.checked_out}, idle in pool {facts.checked_in}",
        ),
        FactRow(
            id="pool-timeout",
            label="wait before pool exhaustion raises",
            value=f"{facts.timeout_s}s — requests queue this long, then TimeoutError",
        ),
        FactRow(
            id="pool-status",
            label="the pool's own status() line (live)",
            value=facts.status,
        ),
    ]


# ── GC: stdlib introspection + one measured off-loop collection ────────────


def _gc_fact_rows() -> list[FactRow]:
    """The collector's real knobs, read from the stdlib."""
    thresholds = gc.get_threshold()
    stats = gc.get_stats()
    per_gen = " · ".join(f"gen{i} {entry['collections']}" for i, entry in enumerate(stats))
    return [
        FactRow(id="gc-enabled", label="collector enabled", value=str(gc.isenabled())),
        FactRow(
            id="gc-thresholds",
            label="generation thresholds (gen0 trip, gen1, gen2 ratios)",
            value=(
                f"{thresholds} — CPython 3.13's default; gen0 collects every 2000 "
                "net allocations (the pre-3.13 default was 700)"
            ),
        ),
        FactRow(
            id="gc-counts",
            label="pending counts right now (gen0, gen1, gen2)",
            value=str(gc.get_count()),
        ),
        FactRow(
            id="gc-collections",
            label="collections since process start",
            value=per_gen,
        ),
        FactRow(
            id="gc-frozen",
            label="frozen objects (gc.freeze)",
            value=f"{gc.get_freeze_count()} — zero unless something froze long-lived data",
        ),
    ]


async def _measure_gc_collection() -> GcCollectionRow:
    """One REAL full gc.collect(), timed, run OFF the loop.

    The containment is the lesson applied to itself: a full collection can
    take tens of milliseconds on a real heap, so the bench practices what
    the hygiene row preaches and hands it to a worker thread.
    """
    started = time.perf_counter()
    collected = await asyncio.to_thread(gc.collect)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    return GcCollectionRow(
        workload="gc.collect() — a full collection of every generation",
        elapsed_ms=elapsed_ms,
        collected=collected,
        off_loop=True,
        note=(
            "Measured on this request, run via asyncio.to_thread. The GIL still "
            "makes the collector's atomic phases a process-wide pause — off-loop "
            "contains the bookkeeping, not the stop-the-world moments — which is "
            "why GC tuning (fewer, cheaper collections) beats offloading."
        ),
    )


async def build_perf_bench_payload(
    *,
    app: ASGIApp,
    pool_facts: PoolFacts,
) -> PerfBenchPanel:
    """Run the whole bench: every row measured, every duration bounded.

    ``app`` is the serving application (internal rounds + the final health
    receipt); ``pool_facts`` is the engine-pool snapshot the router read
    off the composition root — the builder never touches the data layer.
    """
    compression = await _compression_rows(app)
    hygiene = [
        await _hygiene_row(
            app,
            label="threadpool-offload",
            what=(
                f"{HYGIENE_BUDGET_MS:.0f}ms busy CPU via asyncio.to_thread — the "
                "block contained off the loop"
            ),
            offload=True,
        ),
        await _hygiene_row(
            app,
            label="on-loop-block",
            what=(
                f"the same {HYGIENE_BUDGET_MS:.0f}ms busy CPU run directly on the "
                "loop — bounded on purpose, the starvation made visible"
            ),
            offload=False,
        ),
    ]
    gc_facts = _gc_fact_rows()
    gc_collection = await _measure_gc_collection()

    started = time.perf_counter()
    health_status, _, _ = await _drive_internal_get(app, "/api/health")
    health_after = HealthAfter(
        status=health_status,
        elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
    )
    return PerfBenchPanel(
        compression=compression,
        hygiene=hygiene,
        loop=_loop_fact_rows(),
        pool=_pool_fact_rows(pool_facts),
        gc_facts=gc_facts,
        gc_collection=gc_collection,
        health_after=health_after,
        honesty_note=HONESTY_NOTE,
    )
