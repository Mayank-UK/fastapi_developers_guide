"""The comparison workload: the SAME work, two execution homes.

The honest comparison needs identical work on both sides, so the
workload is ONE function with its sleeper injected — starlette's
``BackgroundTasks`` runs it in the server process right after the
response, the arq worker runs it in the worker process when the queue
hands it over, and both time it with the same clock. The pacing is a
labeled simulation (four sleeps of 150 ms stand in for four chunks of
real work — theorem: never benchmark I/O you do not have).
"""

import time
from collections.abc import Awaitable, Callable
from typing import Final

COMPARISON_STEPS: Final = 4
COMPARISON_STEP_SECONDS: Final = 0.15
"""The workload's shape: four paced steps, ~600 ms total (simulated)."""

Sleeper = Callable[[float], Awaitable[None]]
"""The injected pause — ``asyncio.sleep`` in production, instant in tests."""

IN_PROCESS_HOME: Final = "server process — starlette BackgroundTasks"
QUEUED_HOME: Final = "arq worker process"


async def run_comparison_work(sleep: Sleeper) -> float:
    """Run the four paced steps; answer the elapsed seconds they took.

    Pure of transport and clock policy: the caller injects the sleeper,
    and the returned duration is ``time.perf_counter``'s honest window —
    the number both homes report, so any difference in the ledger is the
    HANDOFF, never the work.
    """
    started = time.perf_counter()
    for _ in range(COMPARISON_STEPS):
        await sleep(COMPARISON_STEP_SECONDS)
    return time.perf_counter() - started
