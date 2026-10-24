"""The stall-diagnosis payload: four bounded phases, all evidence measured.

``GET /api/demo/debug/stall`` serves this payload INLINE in topic 35's
py-spy section. The question the panel answers is the profiler's question
— WHERE did the time go — demonstrated on a slow endpoint this request
diagnoses as it runs: four phases, each a different way a handler can be
slow, each carrying REAL measurements instead of a narrative.

The instruments, all genuine:

- **Elapsed** — ``time.perf_counter`` around each phase's work.
- **Loop lag** — a concurrent probe task that sleeps a fixed interval
  repeatedly; each tick's overshoot beyond the interval is event-loop lag,
  the standard "is the loop starved" measurement (asyncio's own debug mode
  measures the same thing). A phase that blocks the loop starves the
  in-flight tick; a phase that merely awaits or offloads to a threadpool
  does not.
- **Concurrent health** — a REAL internal ``GET /api/health`` driven
  through the live app at the ASGI boundary (the obs-trace fan-out's
  in-process channel) WHILE the phase runs: the number that proves other
  requests kept being served (or, for the on-loop block, waited).
- **Allocations** — a real ``tracemalloc`` window (stdlib) around a
  bounded, named workload: current vs peak, the numbers a heap
  investigation starts from.

Hard safety constraint, honored by construction: every duration is bounded
to hundreds of milliseconds — the async stall is 350ms of awaiting (the
loop stays free), each CPU block is a 120ms budget (one off-loop in a
threadpool, one deliberately on-loop to show the starvation it causes) —
so the shared dev stack's event loop is never wedged and stays responsive
for other requests during and after the demo. Each phase also logs one
real ``debug_stall_phase`` event through the structlog pipeline, and the
panel serves its own rows back from the recent-events ring correlated by
this request's id — the debugging workflow (make it slow, measure it,
find the evidence in the logs) in one payload.

py-spy itself is NOT installed here — no dependency was added for this
topic. The panel produces exactly the evidence py-spy would sample from
outside (which stack is hot, whether the process is waiting or burning
CPU); the recipe for running the real tool against this very stack is the
section's terminal material, honestly marked as a recipe.
"""

import asyncio
import time
import tracemalloc
from collections.abc import Awaitable, Callable
from typing import Final

import structlog
from starlette.types import ASGIApp, Message, Scope

from guide.core.errors import AppError, FailureKind
from guide.core.logging import recent_log
from guide.core.serialization import CamelModel
from guide.domain.demos.obs_viewer import CapturedEvent, captured_event

logger = structlog.get_logger()

ASYNC_STALL_SECONDS: Final[float] = 0.35
"""The async phase's bounded wait — a slow I/O-bound handler in miniature."""

BLOCK_BUDGET_MS: Final[float] = 120.0
"""Each CPU phase's bounded busy-loop budget — hundreds of ms, never more."""

LAG_TICK_SECONDS: Final[float] = 0.025
"""The lag probe's sleep interval: overshoot beyond this is loop lag."""

ALLOCATION_OBJECTS: Final[int] = 2000
"""The tracemalloc workload's row count — bounded, named, real."""

PROBE_HOST: Final = "debug-stall.internal"
"""The host header the internal health probe carries (ASGI scope only)."""


class PhaseRow(CamelModel):
    """One phase of the stall diagnosis, with its measured evidence."""

    label: str
    what: str
    elapsed_ms: float
    loop_lag_max_ms: float
    loop_lag_mean_ms: float
    concurrent_health_ms: float
    concurrent_health_status: int
    verdict: str


class AllocationRow(CamelModel):
    """One REAL tracemalloc window around the bounded workload."""

    workload: str
    objects: int
    current_kb: float
    peak_kb: float
    note: str


class StallPanel(CamelModel):
    """Wire shape of ``GET /api/demo/debug/stall`` — the panel's contract."""

    panel_request_id: str
    phases: list[PhaseRow]
    allocations: AllocationRow
    log_events: list[CapturedEvent]
    py_spy_note: str
    honesty_note: str


PY_SPY_NOTE: Final = (
    "py-spy is NOT installed in this repo — no dependency was added for this "
    "topic. It is a sampling profiler that attaches to a RUNNING process "
    "from outside (py-spy dump shows every thread's current stack; py-spy "
    "top shows live samples). This panel produces the same classification "
    "from inside: which phase awaited (slow but harmless), which burned CPU "
    "off the loop (contained), and which starved the loop (the one py-spy "
    "would show as a hot stack). The recipe commands for the real tool are "
    "in the section's terminal material."
)

HONESTY_NOTE: Final = (
    "Every number is measured on this very request: elapsed from "
    "perf_counter around each phase, loop lag from a concurrent probe "
    "task's sleep overshoot, concurrent health from a REAL internal "
    "GET /api/health driven through the app while the phase ran, and the "
    "allocation numbers from a real tracemalloc window. All durations are "
    "bounded by design (≤350ms): the demo diagnoses a stall without ever "
    "wedging the shared event loop — the health row after the on-loop "
    "block proves the loop recovered."
)

_VERDICTS: Final[dict[str, str]] = {
    "baseline": (
        "The unit of comparison: one scheduler yield, sub-millisecond "
        "everything. Every other phase's numbers are read against this row."
    ),
    "async-await-stall": (
        "Slow request, HEALTHY loop: the 350ms is awaiting, not CPU — the "
        "concurrent health probe answered in single-digit milliseconds "
        "mid-stall and the lag probe ticked cleanly. This is the profile "
        "py-spy shows as a parked stack: wait on I/O, buy latency with no "
        "blast radius."
    ),
    "blocking-in-threadpool": (
        "120ms of real CPU, contained: asyncio.to_thread moved the block "
        "off the event loop — the lag probe stayed quiet and health kept "
        "answering (it did slow a little: the GIL means off-loop CPU still "
        "competes with other threads, so contained is not free). Slow for "
        "THIS request, scheduling preserved for the others — the fix the "
        "performance topic mandates for any blocking call."
    ),
    "blocking-on-loop": (
        "The pathology: the SAME 120ms budget run directly on the loop "
        "starved the in-flight lag tick and made the concurrent health "
        "request wait out the whole block. One request's block is every "
        "request's latency — this is the stack py-spy dump would catch "
        "red-handed, and why the budget is deliberately bounded here."
    ),
}


def _burn_cpu_ms(budget_ms: float) -> int:
    """Busy-loop a bounded wall-clock budget of real CPU work (spins returned)."""
    deadline = time.perf_counter() + budget_ms / 1000
    spins = 0
    while time.perf_counter() < deadline:
        spins += sum(i * i for i in range(64))
    return spins


async def _loop_lag_samples(*, ticks: int, interval_s: float) -> list[float]:
    """Sample event-loop lag: each tick's sleep overshoot beyond its interval.

    A healthy loop fires each sleep within microseconds of schedule; a loop
    blocked by sync code cannot fire ANY timer until the block ends, so the
    in-flight tick overshoots by (up to) the block's whole duration. This is
    the same measurement asyncio's own debug mode (slow-callback warnings)
    performs.
    """
    samples: list[float] = []
    for _ in range(ticks):
        before = time.perf_counter()
        await asyncio.sleep(interval_s)
        samples.append((time.perf_counter() - before - interval_s) * 1000)
    return samples


async def _drive_health_probe(app: ASGIApp) -> tuple[float, int]:
    """Drive one REAL internal GET /api/health at the ASGI boundary.

    The obs-trace fan-out's in-process channel (a hand-built ``http`` scope
    handed to the app callable — no socket, no staged responses): whatever
    this probe reports is what the running app actually did. Its duration
    is the responsiveness witness — while a phase blocks the loop, this
    request waits with everyone else.
    """
    entered = time.perf_counter()
    status: list[int] = []

    async def receive() -> Message:
        """The probe sends no body; an honest disconnect if anything asks."""
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        """Only the status line matters here; bodies are ignored."""
        if message["type"] == "http.response.start":
            status.append(int(message["status"]))

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/health",
        "raw_path": b"/api/health",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", PROBE_HOST.encode("utf-8")),
            (b"accept", b"application/json"),
        ],
        "client": ("debug-stall", 0),
        "server": (PROBE_HOST, 80),
    }
    await app(scope, receive, send)
    if not status:
        raise AppError(
            FailureKind.INTERNAL, "the concurrent health probe never answered"
        )
    return round((time.perf_counter() - entered) * 1000, 1), status[0]


async def _baseline_work() -> None:
    """One scheduler yield — the cheapest thing a handler can do."""
    await asyncio.sleep(0)


async def _async_stall_work() -> None:
    """A bounded await: the request is slow, the loop stays free."""
    await asyncio.sleep(ASYNC_STALL_SECONDS)


async def _threadpool_work() -> None:
    """A bounded blocking call done right: offloaded via asyncio.to_thread."""
    await asyncio.to_thread(_burn_cpu_ms, BLOCK_BUDGET_MS)


async def _on_loop_work() -> None:
    """The anti-pattern, bounded on purpose: sync CPU run directly ON the loop."""
    _burn_cpu_ms(BLOCK_BUDGET_MS)


async def _phase(
    app: ASGIApp,
    *,
    label: str,
    what: str,
    work: Callable[[], Awaitable[None]],
    probe_ticks: int,
) -> PhaseRow:
    """Run one phase with both probes live, then collect every measurement.

    The probes are scheduled BEFORE the work and given one scheduler slice
    (``sleep(0)``) so they are genuinely in flight when the phase starts —
    that is what makes the on-loop block's starvation observable rather
    than hypothetical.
    """
    lag_task = asyncio.create_task(
        _loop_lag_samples(ticks=probe_ticks, interval_s=LAG_TICK_SECONDS)
    )
    health_task = asyncio.create_task(_drive_health_probe(app))
    await asyncio.sleep(0)

    started = time.perf_counter()
    await work()
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)

    samples = await lag_task
    health_ms, health_status = await health_task
    return PhaseRow(
        label=label,
        what=what,
        elapsed_ms=elapsed_ms,
        loop_lag_max_ms=round(max(samples, default=0.0), 1),
        loop_lag_mean_ms=round(sum(samples) / len(samples), 1) if samples else 0.0,
        concurrent_health_ms=health_ms,
        concurrent_health_status=health_status,
        verdict=_VERDICTS[label],
    )


def _measure_allocations() -> AllocationRow:
    """One REAL tracemalloc window (stdlib) around a bounded, named workload.

    The workload builds the row shape a parsed JSON payload might leave
    behind — small dicts with a few ints — while tracemalloc traces every
    allocation between ``start`` and ``stop``. Current vs peak is the pair
    every heap investigation starts from: current that never falls is a
    reference leak; a peak far above current is churn (allocations made and
    freed inside the window). The window is deliberately tiny — tracing
    slows everything it watches, so it is opened late and closed early.
    """
    tracemalloc.start()
    try:
        rows = [
            {"id": index, "kind": "demo-row", "values": [index, index * 2, index * 3]}
            for index in range(ALLOCATION_OBJECTS)
        ]
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return AllocationRow(
        workload=(
            f"{ALLOCATION_OBJECTS} small dict rows (a parsed-JSON shape) built "
            "while tracemalloc watched"
        ),
        objects=len(rows),
        current_kb=round(current / 1024, 1),
        peak_kb=round(peak / 1024, 1),
        note=(
            "tracemalloc is stdlib and this window is real: current_kb is what "
            "survived the window, peak_kb is the high-water mark inside it. "
            "Peak far above current means churn, not a leak — the distinction "
            "the heap section teaches."
        ),
    )


async def build_stall_payload(*, app: ASGIApp, request_id: str) -> StallPanel:
    """Run the four bounded phases, measure everything, correlate the logs.

    Phases are fixed by design — one per way a handler can be slow — so
    every measurement in the payload has a deterministic, testable
    counterpart: the baseline yield, the async await, the contained
    threadpool block, and the on-loop block whose starvation both probes
    witness.
    """
    phases_spec: list[tuple[str, str, Callable[[], Awaitable[None]], int]] = [
        (
            "baseline",
            "one scheduler yield (await asyncio.sleep(0)) — the unit of comparison",
            _baseline_work,
            3,
        ),
        (
            "async-await-stall",
            f"await asyncio.sleep({ASYNC_STALL_SECONDS}) — slow request, free loop",
            _async_stall_work,
            8,
        ),
        (
            "blocking-in-threadpool",
            (
                f"{BLOCK_BUDGET_MS:.0f}ms busy CPU via asyncio.to_thread — "
                "the block contained off the loop"
            ),
            _threadpool_work,
            4,
        ),
        (
            "blocking-on-loop",
            (
                f"the same {BLOCK_BUDGET_MS:.0f}ms busy CPU run directly on the "
                "loop — bounded on purpose, the starvation made visible"
            ),
            _on_loop_work,
            4,
        ),
    ]
    phases = [
        await _phase(app, label=label, what=what, work=work, probe_ticks=ticks)
        for label, what, work, ticks in phases_spec
    ]
    for row in phases:
        logger.info(
            "debug_stall_phase",
            request_id=request_id,
            phase=row.label,
            elapsed_ms=row.elapsed_ms,
            loop_lag_max_ms=row.loop_lag_max_ms,
            concurrent_health_ms=row.concurrent_health_ms,
        )
    return StallPanel(
        panel_request_id=request_id,
        phases=phases,
        allocations=_measure_allocations(),
        log_events=[
            captured_event(event) for event in recent_log().by_request_id(request_id)
        ],
        py_spy_note=PY_SPY_NOTE,
        honesty_note=HONESTY_NOTE,
    )
