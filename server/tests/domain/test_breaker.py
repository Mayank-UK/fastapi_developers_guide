"""The circuit breaker as a pure table: states, thresholds, probe edges.

The same posture as the jobs/webhook policy tests: every transition is
driven through an injected clock with integer inputs — no sleeping, no
timed tests — so the threshold off-by-one, the open-timeout boundary, the
single-flight half-open probe, and the fresh-timer reopen are all pinned
as arithmetic, not timing.
"""

import pytest

from guide.domain.reliability.breaker import (
    DEMO_BREAKER_POLICY,
    BreakerPolicy,
    CircuitBreaker,
)


class CounterClock:
    """An injected clock the test advances in exact integer steps."""

    def __init__(self, start: float = 100.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _trip(breaker: CircuitBreaker, clock: CounterClock) -> None:
    """Fail exactly failure_threshold times, all admitted, all recorded."""
    for _ in range(breaker.policy.failure_threshold):
        assert breaker.acquire(clock.now).allowed
        breaker.record_failure(clock.now)


class TestThePolicy:
    def test_demo_policy_shape(self) -> None:
        assert DEMO_BREAKER_POLICY == BreakerPolicy(
            failure_threshold=3, open_timeout_s=2.0, half_open_successes=1
        )

    @pytest.mark.parametrize(
        ("kwargs", "match"),
        [
            ({"failure_threshold": 0}, "failure_threshold"),
            ({"open_timeout_s": 0}, "open_timeout_s"),
            ({"half_open_successes": 0}, "half_open_successes"),
        ],
    )
    def test_invalid_policies_refuse_construction(
        self, kwargs: dict[str, int], match: str
    ) -> None:
        with pytest.raises(ValueError, match=match):
            BreakerPolicy(**kwargs)  # type: ignore[arg-type]


class TestTheTrip:
    def test_threshold_minus_one_stays_closed(self) -> None:
        clock = CounterClock()
        breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
        for _ in range(DEMO_BREAKER_POLICY.failure_threshold - 1):
            assert breaker.acquire(clock.now).allowed
            breaker.record_failure(clock.now)
        assert breaker.state(clock.now) == "closed", "two failures must not trip a 3-threshold"
        assert breaker.consecutive_failures == 2

    def test_the_exact_threshold_trips_on_that_failure(self) -> None:
        clock = CounterClock()
        breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
        _trip(breaker, clock)
        assert breaker.state(clock.now) == "open"
        assert breaker.consecutive_failures == 3

    def test_the_tripping_record_names_it(self) -> None:
        clock = CounterClock()
        breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
        for _ in range(2):
            breaker.acquire(clock.now)
            breaker.record_failure(clock.now)
        breaker.acquire(clock.now)
        record = breaker.record_failure(clock.now)
        assert record.tripped is True
        assert record.state_after == "open"
        assert "reached the threshold" in record.reason

    def test_success_while_closed_resets_the_count(self) -> None:
        clock = CounterClock()
        breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
        breaker.acquire(clock.now)
        breaker.record_failure(clock.now)
        breaker.acquire(clock.now)
        breaker.record_success(clock.now)
        assert breaker.consecutive_failures == 0
        # Two more failures after the reset are 1-and-2 of a NEW count: still closed.
        for _ in range(2):
            breaker.acquire(clock.now)
            breaker.record_failure(clock.now)
        assert breaker.state(clock.now) == "closed"


class TestTheOpenGate:
    def test_open_rejects_with_the_probe_countdown(self) -> None:
        clock = CounterClock()
        breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
        _trip(breaker, clock)
        verdict = breaker.acquire(clock.now)
        assert verdict.allowed is False
        assert verdict.state == "open"
        assert verdict.is_probe is False
        assert verdict.retry_after_s == 2.0
        assert "fast-fail" in verdict.reason

    def test_the_countdown_shrinks_as_the_clock_advances(self) -> None:
        clock = CounterClock()
        breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
        _trip(breaker, clock)
        clock.advance(1.0)
        assert breaker.seconds_until_probe(clock.now) == pytest.approx(1.0)
        verdict = breaker.acquire(clock.now)
        assert verdict.retry_after_s == 1.0

    def test_one_moment_before_the_timeout_still_rejects(self) -> None:
        clock = CounterClock()
        breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
        _trip(breaker, clock)
        clock.advance(DEMO_BREAKER_POLICY.open_timeout_s - 0.001)
        assert breaker.acquire(clock.now).allowed is False

    def test_exactly_at_the_timeout_the_probe_is_already_allowed(self) -> None:
        clock = CounterClock()
        breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
        _trip(breaker, clock)
        clock.advance(DEMO_BREAKER_POLICY.open_timeout_s)
        verdict = breaker.acquire(clock.now)
        assert verdict.allowed is True, "the boundary is inclusive: the wait is over"
        assert verdict.is_probe is True

    def test_state_flips_lazily_on_touch(self) -> None:
        clock = CounterClock()
        breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
        _trip(breaker, clock)
        clock.advance(DEMO_BREAKER_POLICY.open_timeout_s + 5.0)
        assert breaker._state == "open", "untouched, the transition has not happened yet"
        assert breaker.state(clock.now) == "half_open"


class TestTheHalfOpenProbe:
    def _open_and_wait(self) -> tuple[CircuitBreaker, CounterClock]:
        clock = CounterClock()
        breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
        _trip(breaker, clock)
        clock.advance(DEMO_BREAKER_POLICY.open_timeout_s)
        return breaker, clock

    def test_probe_success_closes_and_resets_everything(self) -> None:
        breaker, clock = self._open_and_wait()
        assert breaker.acquire(clock.now).is_probe is True
        record = breaker.record_success(clock.now)
        assert record.closed is True
        assert breaker.state(clock.now) == "closed"
        assert breaker.consecutive_failures == 0

    def test_the_probe_is_single_flight(self) -> None:
        breaker, clock = self._open_and_wait()
        first = breaker.acquire(clock.now)
        assert first.allowed and first.is_probe
        second = breaker.acquire(clock.now)
        assert second.allowed is False
        assert second.is_probe is False
        assert "probe is already in flight" in second.reason

    def test_after_a_rejected_concurrent_call_the_probe_still_admits(self) -> None:
        breaker, clock = self._open_and_wait()
        breaker.acquire(clock.now)  # the probe
        breaker.acquire(clock.now)  # a concurrent caller: rejected
        record = breaker.record_success(clock.now)  # the probe's verdict
        assert record.closed is True
        assert breaker.acquire(clock.now).allowed, "the gate reopens once the probe closes"

    def test_probe_failure_reopens_with_a_fresh_timeout(self) -> None:
        breaker, clock = self._open_and_wait()
        breaker.acquire(clock.now)
        clock.advance(50.0)  # a long time passes while the probe is in flight
        record = breaker.record_failure(clock.now)
        assert record.reopened is True
        assert record.state_after == "open"
        # FRESH: measured from the failed probe, not the original trip 52s ago.
        assert breaker.seconds_until_probe(clock.now) == pytest.approx(
            DEMO_BREAKER_POLICY.open_timeout_s
        )
        assert breaker.acquire(clock.now).allowed is False

    def test_multi_success_policies_stay_half_open_until_the_bar(self) -> None:
        clock = CounterClock()
        policy = BreakerPolicy(failure_threshold=2, open_timeout_s=1.0, half_open_successes=2)
        breaker = CircuitBreaker(policy, clock)
        _trip(breaker, clock)
        clock.advance(policy.open_timeout_s)
        assert breaker.acquire(clock.now).is_probe is True
        record = breaker.record_success(clock.now)
        assert record.closed is False
        assert breaker.state(clock.now) == "half_open", "one success of two needed"
        assert breaker.acquire(clock.now).is_probe is True, "a new probe is admitted"
        record = breaker.record_success(clock.now)
        assert record.closed is True


class TestLateVerdicts:
    def test_late_success_while_open_changes_nothing(self) -> None:
        clock = CounterClock()
        breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
        breaker.acquire(clock.now)  # an admitted call that will answer late
        _trip(breaker, clock)  # other callers' failures trip the gate meanwhile
        record = breaker.record_success(clock.now)  # the late verdict arrives
        assert record.state_after == "open"
        assert record.closed is False
        assert "late success" in record.reason

    def test_late_failure_while_open_keeps_the_original_deadline(self) -> None:
        clock = CounterClock()
        breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
        breaker.acquire(clock.now)
        _trip(breaker, clock)
        clock.advance(1.5)
        record = breaker.record_failure(clock.now)
        assert record.state_after == "open"
        assert breaker.seconds_until_probe(clock.now) == pytest.approx(0.5), (
            "a late failure must not push the probe window out"
        )


class TestReset:
    def test_reset_returns_a_fresh_closed_breaker(self) -> None:
        clock = CounterClock()
        breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
        _trip(breaker, clock)
        breaker.reset()
        assert breaker.state(clock.now) == "closed"
        assert breaker.consecutive_failures == 0
        assert breaker.acquire(clock.now).allowed is True

    def test_the_demo_walk_is_deterministic_under_the_injected_clock(self) -> None:
        """The full cycle, twice, from identical inputs — identical verdicts."""
        reasons: list[list[str]] = []
        for _ in range(2):
            clock = CounterClock()
            breaker = CircuitBreaker(DEMO_BREAKER_POLICY, clock)
            walk: list[str] = []
            for healthy, advance in [
                (True, 0.0),
                (True, 0.0),
                (False, 0.0),
                (False, 0.0),
                (False, 0.0),
                (True, 0.0),
                (True, 1.0),
                (True, 1.5),
                (True, 0.0),
                (True, 0.0),
            ]:
                clock.advance(advance)
                verdict = breaker.acquire(clock.now)
                walk.append(
                    f"{verdict.state}:{verdict.allowed}:{verdict.is_probe}"
                )
                if verdict.allowed:
                    breaker.record_success(clock.now) if healthy else breaker.record_failure(
                        clock.now
                    )
            walk.append(breaker.state(clock.now))
            reasons.append(walk)
        assert reasons[0] == reasons[1]
        assert reasons[0][-1] == "closed"
