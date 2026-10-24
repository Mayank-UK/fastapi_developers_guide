"""The performance-bench demo (topic 38, area ``perf``).

Thin router (family invariant): one GET, the payload builder does the
work, a declared response model. The panel measures the real things this
process does — gzip over the REAL bytes of two payloads this API serves
(fetched through internal rounds to the app itself), the on-loop vs
threadpool hygiene comparison with live probes, uvicorn's auto-selected
loop and HTTP parser introspected from THIS process, the composition
root's engine-pool counters snapshotted here in the router (the builder
never touches the data layer), and the stdlib GC read plus one measured
off-loop collection. Every duration is bounded; the panel's last row is a
real /api/health after the whole bench.
"""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import QueuePool

from guide.core.errors import AppError, FailureKind
from guide.domain.demos.perf_bench import (
    PerfBenchPanel,
    PoolFacts,
    build_perf_bench_payload,
)

router = APIRouter(prefix="/api/demo/perf", tags=["demo:perf"])

BENCH_PATH: Final = "/bench"
"""The router's one path (prefix-relative) — the terminal companion names it."""


def _pool_facts(request: Request) -> PoolFacts:
    """Snapshot the composition root's engine pool — counters only, no I/O.

    The engine is wired on ``app.state`` by ``create_app``; reading its
    pool's COUNTERS (size, checked-out/in, timeout, status) opens no
    connection and imports nothing from the data layer here — the plain
    ``PoolFacts`` record crosses into the domain builder.
    """
    engine = request.app.state.db_engine
    if not isinstance(engine, AsyncEngine):
        raise AppError(FailureKind.INTERNAL, "Async engine not wired on app.state")
    pool = engine.pool
    if not isinstance(pool, QueuePool):
        raise AppError(FailureKind.INTERNAL, f"Unexpected pool type: {type(pool).__name__}")
    return PoolFacts(
        pool_class=type(pool).__name__,
        dialect=engine.dialect.name,
        driver=engine.dialect.driver,
        size=pool.size(),
        checked_in=pool.checkedin(),
        checked_out=pool.checkedout(),
        timeout_s=pool.timeout(),
        status=pool.status(),
    )


PoolFactsDep = Annotated[PoolFacts, Depends(_pool_facts)]


@router.get(BENCH_PATH, response_model=PerfBenchPanel)
async def read_perf_bench_panel(
    request: Request, pool_facts: PoolFactsDep
) -> PerfBenchPanel:
    """Serve the live bench: measured compression, hygiene, loop, pool, GC."""
    return await build_perf_bench_payload(
        app=request.app,
        pool_facts=pool_facts,
    )
