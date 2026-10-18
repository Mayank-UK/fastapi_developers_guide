"""Async-timing demo payload: the event loop, measured — not asserted.

``GET /api/demo/runtime/async`` serves this payload. Three simulated-I/O
coroutines (tiny ``asyncio.sleep`` delays standing in for network calls)
run twice — sequentially, one ``await`` after another, and concurrently
under ``asyncio.gather`` — with ``time.perf_counter`` measuring both runs
and the real completion order recorded. Every number in the payload was
measured on this process, this request: the sequential run costs the SUM
of the waits, the gathered run costs the LONGEST of them, and a two-actor
trace proves ``await`` genuinely yields control (the loop interleaves the
coroutines step by step, in first-in-first-out order).

Nothing here touches real I/O: the builder is pure scheduling plus
measurement, so two calls produce equal shapes with honestly different
milliseconds.
"""

import asyncio
import time
from typing import Final, Literal

from guide.core.serialization import CamelModel

_IO_PLAN: Final[tuple[tuple[str, int], ...]] = (
    ("orders", 60),
    ("billing", 40),
    ("inventory", 20),
)
"""Three simulated I/O calls: name + wall-clock delay in milliseconds.

Deliberately in DESCENDING delay order, so the sequential run completes in
start order while the gathered run completes in delay order (fastest
first) — two genuinely different orderings from the same three coroutines.
"""

_TRACE_STEPS: Final[int] = 3
"""Steps per actor in the interleaving trace (``asyncio.sleep(0)`` yields)."""


class IoTask(CamelModel):
    """One planned simulated-I/O call: a name and its delay."""

    name: str
    simulated_io_ms: int


class TaskTiming(CamelModel):
    """One task's measured outcome inside a run."""

    name: str
    simulated_io_ms: int
    measured_ms: float


class TimingRun(CamelModel):
    """One full pass over the plan: strategy, cost, and completion order."""

    strategy: Literal["sequential", "gathered"]
    elapsed_ms: float
    completion_order: list[str]
    per_task: list[TaskTiming]


class TraceEvent(CamelModel):
    """One step of the interleaving proof: which actor, what happened."""

    actor: str
    event: str


class AsyncTimingPayload(CamelModel):
    """Wire shape of ``GET /api/demo/runtime/async`` (camelCase)."""

    io_plan: list[IoTask]
    sequential: TimingRun
    gathered: TimingRun
    speedup: float
    trace: list[TraceEvent]


async def _simulate_io(name: str, io_ms: int, done: list[str]) -> TaskTiming:
    """One simulated network call: sleep, record completion, report cost."""
    started = time.perf_counter()
    await asyncio.sleep(io_ms / 1000)
    done.append(name)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return TaskTiming(name=name, simulated_io_ms=io_ms, measured_ms=round(elapsed_ms, 2))


async def _run_sequential() -> TimingRun:
    """Await each call in turn — the run costs the sum of the waits."""
    started = time.perf_counter()
    done: list[str] = []
    per_task: list[TaskTiming] = []
    for name, io_ms in _IO_PLAN:
        per_task.append(await _simulate_io(name, io_ms, done))
    return TimingRun(
        strategy="sequential",
        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        completion_order=done,
        per_task=per_task,
    )


async def _run_gathered() -> TimingRun:
    """Start all three at once — the run costs the longest single wait."""
    started = time.perf_counter()
    done: list[str] = []
    calls = [_simulate_io(name, io_ms, done) for name, io_ms in _IO_PLAN]
    per_task = await asyncio.gather(*calls)
    return TimingRun(
        strategy="gathered",
        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        completion_order=done,
        per_task=list(per_task),
    )


async def _traced_actor(name: str, sink: list[TraceEvent]) -> None:
    """Log an event per step, yielding control between steps (the proof)."""
    sink.append(TraceEvent(actor=name, event="start"))
    for step in range(_TRACE_STEPS):
        await asyncio.sleep(0)  # yield control: no waiting, just rescheduling
        sink.append(TraceEvent(actor=name, event=f"step-{step}"))
    await asyncio.sleep(0)  # one more yield so even the done events alternate
    sink.append(TraceEvent(actor=name, event="done"))


async def _trace_interleaving() -> list[TraceEvent]:
    """Run two traced actors concurrently; the sink records who ran when."""
    sink: list[TraceEvent] = []
    await asyncio.gather(_traced_actor("alpha", sink), _traced_actor("beta", sink))
    return sink


async def build_async_timing_payload() -> AsyncTimingPayload:
    """Measure both runs and the trace; report the honest speedup number."""
    sequential = await _run_sequential()
    gathered = await _run_gathered()
    return AsyncTimingPayload(
        io_plan=[IoTask(name=name, simulated_io_ms=io_ms) for name, io_ms in _IO_PLAN],
        sequential=sequential,
        gathered=gathered,
        speedup=round(sequential.elapsed_ms / gathered.elapsed_ms, 2),
        trace=await _trace_interleaving(),
    )
