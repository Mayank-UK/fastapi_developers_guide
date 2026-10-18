"""Builder unit tests: the async-timing payload's pure helpers + measurements.

The builder's timings are MEASURED (they differ run to run), so these tests
pin the deterministic parts exactly (plans, trace alternation, completion
orders) and the physical invariants with generous headroom: sequential
elapsed ≥ sum of waits, gathered elapsed ≥ longest wait, gathered strictly
cheaper than sequential.
"""

from guide.domain.demos.runtime_async import (
    _IO_PLAN,
    build_async_timing_payload,
)

EXPECTED_TRACE: tuple[str, ...] = (
    "alpha:start",
    "beta:start",
    "alpha:step-0",
    "beta:step-0",
    "alpha:step-1",
    "beta:step-1",
    "alpha:step-2",
    "beta:step-2",
    "alpha:done",
    "beta:done",
)


def test_plan_is_three_tasks_in_descending_delay_order() -> None:
    assert [name for name, _ in _IO_PLAN] == ["orders", "billing", "inventory"]
    assert [io_ms for _, io_ms in _IO_PLAN] == [60, 40, 20]


async def test_payload_echoes_the_plan() -> None:
    payload = await build_async_timing_payload()
    assert [(t.name, t.simulated_io_ms) for t in payload.io_plan] == [
        ("orders", 60),
        ("billing", 40),
        ("inventory", 20),
    ]


async def test_sequential_costs_at_least_the_sum_of_waits() -> None:
    payload = await build_async_timing_payload()
    floor = sum(io_ms for _, io_ms in _IO_PLAN)  # 120 ms of scheduled sleep
    assert payload.sequential.elapsed_ms >= floor - 0.1


async def test_sequential_completes_in_start_order() -> None:
    payload = await build_async_timing_payload()
    assert payload.sequential.completion_order == ["orders", "billing", "inventory"]


async def test_gathered_costs_at_least_the_longest_wait() -> None:
    payload = await build_async_timing_payload()
    floor = max(io_ms for _, io_ms in _IO_PLAN)  # 60 ms of scheduled sleep
    assert payload.gathered.elapsed_ms >= floor - 0.1


async def test_gathered_completes_in_delay_order_not_start_order() -> None:
    payload = await build_async_timing_payload()
    assert payload.gathered.completion_order == ["inventory", "billing", "orders"]


async def test_gathered_is_measurably_cheaper_than_sequential() -> None:
    payload = await build_async_timing_payload()
    assert payload.gathered.elapsed_ms < payload.sequential.elapsed_ms
    # Expected speedup is ~2.0 (120/60); the generous floor rides out jitter.
    assert payload.speedup > 1.3


async def test_trace_proves_await_yields_control_in_fifo_order() -> None:
    payload = await build_async_timing_payload()
    assert [f"{event.actor}:{event.event}" for event in payload.trace] == list(
        EXPECTED_TRACE
    )


async def test_each_measured_task_covers_its_simulated_io() -> None:
    payload = await build_async_timing_payload()
    for run in (payload.sequential, payload.gathered):
        by_name = {t.name: t for t in run.per_task}
        for name, io_ms in _IO_PLAN:
            assert by_name[name].measured_ms >= io_ms - 0.1
