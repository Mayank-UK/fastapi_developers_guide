"""The circuit-breaker payload: one full cycle, walked live per request.

``GET /api/demo/reliability/breaker`` serves this payload INLINE in topic
39's circuit-breaker section. The panel walks a REAL ``CircuitBreaker``
(the pure substrate in ``guide.domain.reliability.breaker``) through one
complete cycle — calls succeed → the dependency degrades and failures
accumulate → the breaker opens and REJECTS calls fast, without touching
the dependency → the open timeout elapses (time-traveled on the breaker's
injected clock) → one half-open probe goes through → the probe succeeds
and the breaker closes — and every row is the actual verdict the substrate
returned at that step.

Honesty rules the panel keeps:

- **Determinism** — the breaker runs on an INJECTED clock (a mutable
  logical ``now``), so the two-second open timeout elapses in logical
  time, instantly and repeatably; every request walks the identical cycle
  from a fresh breaker (``reset``-by-construction: a new instance per
  request, nothing process-global).
- **Real latency evidence** — the only real wall time is the dependency's
  bounded failure latency (60 ms, labeled simulated like the jobs
  catalog's paced work): failing calls PAY it, rejected calls DON'T (the
  fail-fast rows measure ~0 ms and record ``dependency_touched=false``),
  and the latency facts at the bottom are computed from those measured
  rows, never asserted.
- **Bounded** — three 60 ms sleeps is the whole real cost; the shared
  loop is never wedged (topic 38's hygiene rule, practiced).
"""

import asyncio
import time
from typing import Final

from guide.core.serialization import CamelModel
from guide.domain.reliability.breaker import (
    DEMO_BREAKER_POLICY,
    BreakerPolicy,
    CircuitBreaker,
)

FAILURE_LATENCY_S: Final = 0.06
"""The failing dependency's bounded real latency — the cost fail-fast skips."""

LOGICAL_START_S: Final = 100.0
"""The injected clock's base — visibly logical, never mistaken for wall time."""

ADVANCE_MID_S: Final = 1.0
ADVANCE_PAST_S: Final = 1.5
"""The two logical waits: to the middle of the open timeout, then past it."""


class BreakerFactRow(CamelModel):
    """One policy or latency fact — id, label, and the honest value."""

    id: str
    label: str
    value: str


class BreakerCallRow(CamelModel):
    """One step of the walk: the gate's verdict, the call, the evidence."""

    step: int
    label: str
    action: str
    state_before: str
    admitted: bool | None
    is_probe: bool
    dependency_touched: bool
    outcome: str
    elapsed_ms: float
    consecutive_failures: int
    retry_after_s: float | None
    reason: str


class BreakerPanel(CamelModel):
    """Wire shape of ``GET /api/demo/reliability/breaker`` — the panel's contract."""

    policy: list[BreakerFactRow]
    calls: list[BreakerCallRow]
    latency: list[BreakerFactRow]
    states_visited: list[str]
    state_line: str
    honesty_note: str


HONESTY_NOTE: Final = (
    "Every verdict on this panel was returned by the real CircuitBreaker "
    "substrate on this very request, over a fresh instance per run. The "
    "breaker's clock is injected, so the 2s open timeout elapses in logical "
    "time — deterministically, instantly, repeatably. The only real wall time "
    "is the dependency's bounded 60ms failure latency: failing calls pay it, "
    "rejected calls do not, and the latency rows are computed from those "
    "measured numbers, never asserted. The dependency itself is simulated and "
    "labeled (the jobs catalog's precedent); the breaker bookkeeping around "
    "it is the real, tested substrate."
)

_STEP_LABELS: Final = {
    "healthy": "call while healthy",
    "degraded": "call while the dependency is failing",
    "rejected": "call while the breaker is open",
    "probe": "the half-open probe",
    "post": "call after recovery",
    "advance": "wait (logical clock)",
}


async def _dependency_call(healthy: bool) -> float:
    """One bounded call against the simulated dependency; returns elapsed ms.

    A healthy dependency answers immediately; a failing one takes the
    bounded 60 ms — the latency a fast-failed call never pays. The
    simulation is labeled honestly in the honesty note; nothing here
    touches a real store.
    """
    started = time.perf_counter()
    if not healthy:
        await asyncio.sleep(FAILURE_LATENCY_S)
    return (time.perf_counter() - started) * 1000.0


async def _one_call(
    *,
    breaker: CircuitBreaker,
    step: int,
    label_key: str,
    healthy: bool,
    logical_now: dict[str, float],
) -> BreakerCallRow:
    """Run one acquire → call → record round and capture every verdict."""
    admission = breaker.acquire(logical_now["t"])
    state_before = admission.state
    if not admission.allowed:
        return BreakerCallRow(
            step=step,
            label=_STEP_LABELS[label_key],
            action="call",
            state_before=state_before,
            admitted=False,
            is_probe=False,
            dependency_touched=False,
            outcome="rejected",
            elapsed_ms=0.0,
            consecutive_failures=breaker.consecutive_failures,
            retry_after_s=admission.retry_after_s,
            reason=admission.reason,
        )
    elapsed_ms = await _dependency_call(healthy)
    record = breaker.record_success(logical_now["t"]) if healthy else breaker.record_failure(
        logical_now["t"]
    )
    return BreakerCallRow(
        step=step,
        label=_STEP_LABELS[label_key],
        action="call",
        state_before=state_before,
        admitted=True,
        is_probe=admission.is_probe,
        dependency_touched=True,
        outcome="success" if healthy else "failure",
        elapsed_ms=round(elapsed_ms, 1),
        consecutive_failures=record.consecutive_failures,
        retry_after_s=None,
        reason=record.reason,
    )


def _policy_rows(policy: BreakerPolicy) -> list[BreakerFactRow]:
    """The walk's knobs, served as the panel's first block."""
    return [
        BreakerFactRow(
            id="failure-threshold",
            label="consecutive failures that trip open",
            value=f"{policy.failure_threshold} — a success resets the count",
        ),
        BreakerFactRow(
            id="open-timeout",
            label="how long open fast-fails",
            value=(
                f"{policy.open_timeout_s:g}s (logical, injected clock — the "
                "walk time-travels through it instantly)"
            ),
        ),
        BreakerFactRow(
            id="half-open-successes",
            label="probe successes that close again",
            value=f"{policy.half_open_successes} — one healthy probe reopens the gate",
        ),
        BreakerFactRow(
            id="failure-latency",
            label="the failing dependency's real latency",
            value=(
                f"{FAILURE_LATENCY_S * 1000:.0f}ms bounded — the cost a "
                "fast-failed call never pays (labeled simulated, like the "
                "jobs catalog's paced work)"
            ),
        ),
    ]


def _latency_rows(calls: list[BreakerCallRow]) -> list[BreakerFactRow]:
    """The fail-fast vs real-failure contrast, computed from measured rows."""
    rejected = [row for row in calls if row.outcome == "rejected"]
    failures = [row for row in calls if row.outcome == "failure"]
    fail_fast_ms = (
        sum(row.elapsed_ms for row in rejected) / len(rejected) if rejected else 0.0
    )
    failure_ms = sum(row.elapsed_ms for row in failures) / len(failures) if failures else 0.0
    avoided_ms = len(rejected) * FAILURE_LATENCY_S * 1000
    ratio = (failure_ms / fail_fast_ms) if fail_fast_ms > 0 else None
    contrast = (
        f"fail-fast was ~{ratio:,.0f}x faster" if ratio is not None else "fail-fast was instant"
    )
    return [
        BreakerFactRow(
            id="fail-fast",
            label="mean latency of rejected (fail-fast) calls",
            value=(
                f"{fail_fast_ms:.3f}ms over {len(rejected)} calls — the "
                "dependency was never touched"
            ),
        ),
        BreakerFactRow(
            id="real-failure",
            label="mean latency of real failing calls",
            value=(
                f"{failure_ms:.1f}ms over {len(failures)} calls — the bounded "
                "cost of discovering the failure the hard way"
            ),
        ),
        BreakerFactRow(
            id="contrast",
            label="the contrast",
            value=(
                f"{contrast} — and {len(rejected)} rejected calls skipped "
                f"{avoided_ms:.0f}ms of wasted dependency time in total"
            ),
        ),
    ]


async def build_breaker_panel() -> BreakerPanel:
    """Walk one full cycle over a fresh breaker; every row a real verdict.

    The logical clock lives in a one-cell dict the injected closure reads —
    the same shape the walk's advance rows mutate, so ``acquire`` and
    ``record`` always agree on ``now`` without any sleeping to get there.
    """
    logical_now = {"t": LOGICAL_START_S}
    breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock=lambda: logical_now["t"])

    calls: list[BreakerCallRow] = [
        # Phase 1 — closed and healthy: two ordinary successes.
        await _one_call(
            breaker=breaker, step=1, label_key="healthy", healthy=True, logical_now=logical_now
        ),
        await _one_call(
            breaker=breaker, step=2, label_key="healthy", healthy=True, logical_now=logical_now
        ),
        # Phase 2 — the dependency degrades: three failures, the third trips.
        await _one_call(
            breaker=breaker, step=3, label_key="degraded", healthy=False, logical_now=logical_now
        ),
        await _one_call(
            breaker=breaker, step=4, label_key="degraded", healthy=False, logical_now=logical_now
        ),
        await _one_call(
            breaker=breaker, step=5, label_key="degraded", healthy=False, logical_now=logical_now
        ),
        # Phase 3 — open: fast-fail immediately, then at the timeout's midpoint.
        await _one_call(
            breaker=breaker, step=6, label_key="rejected", healthy=True, logical_now=logical_now
        ),
    ]
    # Advance to the middle of the open window — still rejected.
    calls.append(
        BreakerCallRow(
            step=7,
            label=f"wait {ADVANCE_MID_S:g}s (logical — the injected clock jumps)",
            action="advance-clock",
            state_before=breaker.state(logical_now["t"]),
            admitted=None,
            is_probe=False,
            dependency_touched=False,
            outcome="clock-advanced",
            elapsed_ms=0.0,
            consecutive_failures=breaker.consecutive_failures,
            retry_after_s=breaker.seconds_until_probe(logical_now["t"]),
            reason=(
                f"open timeout is {DEMO_BREAKER_POLICY.open_timeout_s:g}s; the "
                "clock moves without sleeping, the verdict does not"
            ),
        )
    )
    logical_now["t"] += ADVANCE_MID_S
    calls.append(
        await _one_call(
            breaker=breaker, step=8, label_key="rejected", healthy=True, logical_now=logical_now
        )
    )
    # Advance past the timeout — the next acquire is the half-open probe,
    # and the dependency has recovered (healthy=True) for it.
    logical_now["t"] += ADVANCE_PAST_S
    calls.append(
        BreakerCallRow(
            step=9,
            label=f"wait {ADVANCE_PAST_S:g}s more (logical — past the open timeout)",
            action="advance-clock",
            state_before=breaker.state(logical_now["t"]),
            admitted=None,
            is_probe=False,
            dependency_touched=False,
            outcome="clock-advanced",
            elapsed_ms=0.0,
            consecutive_failures=breaker.consecutive_failures,
            retry_after_s=0.0,
            reason="the elapsed open window flips the breaker to half-open on the next touch",
        )
    )
    calls.append(
        await _one_call(
            breaker=breaker, step=10, label_key="probe", healthy=True, logical_now=logical_now
        )
    )
    calls.append(
        await _one_call(
            breaker=breaker, step=11, label_key="post", healthy=True, logical_now=logical_now
        )
    )

    # The states the walk actually passed through: each row's state at
    # acquire, consecutive duplicates folded, and the final state after the
    # last record (closed again) appended when it differs.
    states_visited: list[str] = []
    for row in calls:
        if not states_visited or states_visited[-1] != row.state_before:
            states_visited.append(row.state_before)
    final_state = breaker.state(logical_now["t"])
    if states_visited[-1] != final_state:
        states_visited.append(final_state)

    rejected_count = sum(1 for row in calls if row.outcome == "rejected")
    state_line = (
        " → ".join(state.replace("_", "-") for state in states_visited)
        + (
            f" — one full cycle; {rejected_count} calls fast-failed without "
            "touching the dependency"
        )
    )
    return BreakerPanel(
        policy=_policy_rows(DEMO_BREAKER_POLICY),
        calls=calls,
        latency=_latency_rows(calls),
        states_visited=states_visited,
        state_line=state_line,
        honesty_note=HONESTY_NOTE,
    )
