"""The circuit breaker: states, thresholds, and the half-open probe.

A retry policy answers "ONE call failed — try again?"; a circuit breaker
answers the question retries cannot: "this dependency has failed so many
times in a row that every further call is wasted work — stop calling it
entirely for a while." The pattern is three states with two controlled
transitions: ``closed`` (calls flow; consecutive failures are counted),
``open`` (calls are rejected fast, without touching the dependency, until
the open timeout elapses), and ``half_open`` (exactly one probe call goes
through to test the water; its verdict closes the breaker again or
re-opens it with a fresh timeout).

This module is that pattern as PURE bookkeeping — no sleeping and no
network live here, exactly like the sliding-window limiter in
``guide.domain.security.rate_limit`` and the retry engines in
``guide.domain.jobs.policy`` and ``guide.domain.webhooks.retry``. The
caller supplies ``now`` (monotonic seconds; the constructor takes an
injected clock defaulting to ``time.monotonic``), so every transition
sequence — closed → open → open-timeout → half-open probe → closed — is a
unit test with integer inputs, never a timed test. The acquire/record
protocol is the concurrency story: ``acquire`` is the gate every caller
passes BEFORE the call, ``record_success``/``record_failure`` is the
verdict AFTER it, and the half-open state admits one probe at a time —
a second caller arriving while the probe is in flight is rejected with a
reason that names it, so the dependency sees exactly one trial request,
never a stampede.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, Literal, final

Clock = Callable[[], float]
"""Monotonic seconds. Injected at construction; tests inject counters."""

BreakerState = Literal["closed", "open", "half_open"]
"""The three states: calls flow · calls fast-fail · one probe tests the water."""


@final
@dataclass(frozen=True, slots=True)
class BreakerPolicy:
    """The knobs: when to trip, how long to stay open, what closes it again.

    ``failure_threshold`` counts CONSECUTIVE failures (a success resets the
    count) — three in a row is evidence of an outage where three spread
    over an hour is evidence of nothing. ``open_timeout_s`` is how long the
    open state refuses calls before allowing one half-open probe; the demo
    policy keeps it at two seconds so the full cycle is watchable live.
    ``half_open_successes`` is how many consecutive half-open successes
    close the breaker (one: a single healthy probe is enough — the
    conservative production choice is a small odd number like three, at
    the cost of keeping the gate half-closed longer).
    """

    failure_threshold: int = 3
    open_timeout_s: float = 2.0
    half_open_successes: int = 1

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError(f"failure_threshold must be >= 1, got {self.failure_threshold}")
        if self.open_timeout_s <= 0:
            raise ValueError(f"open_timeout_s must be > 0, got {self.open_timeout_s}")
        if self.half_open_successes < 1:
            raise ValueError(
                f"half_open_successes must be >= 1, got {self.half_open_successes}"
            )


DEMO_BREAKER_POLICY: Final = BreakerPolicy()
"""The demo's policy: 3 failures trip · 2 s open · one probe closes — small
enough to walk a full cycle by hand, honest enough to teach the shape."""


@final
@dataclass(frozen=True, slots=True)
class Admission:
    """The gate's verdict for one caller: pass, or fast-fail with the reason.

    ``retry_after_s`` is set only while open — the seconds until the
    half-open probe is allowed (``Retry-After``-shaped, for callers that
    honor it). ``is_probe`` marks the one admitted call that is the
    half-open test.
    """

    allowed: bool
    state: BreakerState
    is_probe: bool
    retry_after_s: float | None
    reason: str


@final
@dataclass(frozen=True, slots=True)
class BreakerRecord:
    """What one recorded outcome did to the breaker — the audit row.

    ``tripped`` is the closed→open transition (this failure reached the
    threshold); ``reopened`` is the half-open→open one (the probe failed,
    so the breaker re-opens with a FRESH timeout); ``closed`` is the
    half-open→closed recovery. A record while closed that neither trips
    nor closes anything is the common case — the count moving by one.
    """

    state_after: BreakerState
    previous_state: BreakerState
    tripped: bool
    reopened: bool
    closed: bool
    consecutive_failures: int
    reason: str


@final
class CircuitBreaker:
    """Consecutive-failure gating over an injected clock; pure bookkeeping."""

    def __init__(self, policy: BreakerPolicy, clock: Clock = time.monotonic) -> None:
        """Hold the policy, the clock, and a fresh closed state."""
        self._policy = policy
        self._clock = clock
        self._state: BreakerState = "closed"
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._half_open_wins = 0
        self._probe_in_flight = False

    @property
    def policy(self) -> BreakerPolicy:
        """The configured threshold/timeout/successes — served to the demo panel."""
        return self._policy

    @property
    def consecutive_failures(self) -> int:
        """The current consecutive-failure count (evidence, not a verdict)."""
        return self._consecutive_failures

    def state(self, now: float | None = None) -> BreakerState:
        """The effective state at ``now`` (default: the injected clock).

        Read-with-refresh, like the limiter's lazy prune: an open breaker
        whose timeout has elapsed reports (and becomes) half-open the
        moment anyone looks. The boundary is inclusive — at EXACTLY
        ``open_timeout_s`` after the trip the probe is already allowed,
        because the timeout is a wait duration, not a fence post.
        """
        moment = self._clock() if now is None else now
        self._refresh(moment)
        return self._state

    def seconds_until_probe(self, now: float | None = None) -> float:
        """Seconds until the half-open probe is allowed (0 once it is).

        Meaningful only while open — the value a rejected caller's
        ``Retry-After`` would carry.
        """
        moment = self._clock() if now is None else now
        if self._opened_at is None:
            return 0.0
        return max(0.0, self._opened_at + self._policy.open_timeout_s - moment)

    def acquire(self, now: float | None = None) -> Admission:
        """The gate every caller passes BEFORE the call.

        Closed admits everyone; open admits nobody (fast-fail, with the
        seconds until the probe); half-open admits exactly ONE probe — a
        concurrent second caller arriving while the probe is in flight is
        rejected with a reason that names it, so the recovering dependency
        is never stampeded by its own recovery window.
        """
        moment = self._clock() if now is None else now
        self._refresh(moment)
        if self._state == "closed":
            return Admission(
                allowed=True,
                state="closed",
                is_probe=False,
                retry_after_s=None,
                reason="closed — calls flow through to the dependency",
            )
        if self._state == "open":
            wait_s = self.seconds_until_probe(moment)
            return Admission(
                allowed=False,
                state="open",
                is_probe=False,
                retry_after_s=round(wait_s, 2),
                reason=(
                    f"open — fast-fail without touching the dependency; "
                    f"half-open probe allowed in {wait_s:.2f}s"
                ),
            )
        if self._probe_in_flight:
            return Admission(
                allowed=False,
                state="half_open",
                is_probe=False,
                retry_after_s=None,
                reason=(
                    "half-open — a probe is already in flight; concurrent "
                    "callers wait for its verdict rather than stampeding the "
                    "recovering dependency"
                ),
            )
        self._probe_in_flight = True
        return Admission(
            allowed=True,
            state="half_open",
            is_probe=True,
            retry_after_s=None,
            reason="half-open — this call is the probe; its verdict decides open vs closed",
        )

    def record_success(self, now: float | None = None) -> BreakerRecord:
        """Record one successful call (the verdict AFTER ``acquire`` admitted it).

        A half-open success counts toward ``half_open_successes`` and closes
        the breaker when the bar is met (the default one probe = instant
        close). A closed success resets the consecutive-failure count. A
        LATE success arriving after other callers' failures tripped the
        breaker open changes nothing — the trip decision stands and the
        half-open probe, not a late arrival, decides recovery.
        """
        moment = self._clock() if now is None else now
        self._refresh(moment)
        previous = self._state
        if self._state == "half_open":
            self._probe_in_flight = False
            self._half_open_wins += 1
            if self._half_open_wins >= self._policy.half_open_successes:
                return self._close(
                    previous,
                    reason=(
                        f"half-open probe succeeded ({self._half_open_wins}/"
                        f"{self._policy.half_open_successes} needed) — breaker "
                        "closes, calls flow again"
                    ),
                )
            return BreakerRecord(
                state_after="half_open",
                previous_state=previous,
                tripped=False,
                reopened=False,
                closed=False,
                consecutive_failures=self._consecutive_failures,
                reason=(
                    f"half-open success {self._half_open_wins}/"
                    f"{self._policy.half_open_successes} — staying half-open "
                    "until enough consecutive probe successes"
                ),
            )
        if self._state == "closed":
            self._consecutive_failures = 0
            return BreakerRecord(
                state_after="closed",
                previous_state=previous,
                tripped=False,
                reopened=False,
                closed=False,
                consecutive_failures=0,
                reason="success while closed — the consecutive-failure count resets",
            )
        return BreakerRecord(
            state_after="open",
            previous_state=previous,
            tripped=False,
            reopened=False,
            closed=False,
            consecutive_failures=self._consecutive_failures,
            reason=(
                "late success while open — the trip stands; the half-open "
                "probe, not a late arrival, decides recovery"
            ),
        )

    def record_failure(self, now: float | None = None) -> BreakerRecord:
        """Record one failed call (the verdict AFTER ``acquire`` admitted it).

        A closed failure moves the count toward the threshold and TRIPS open
        on the one that reaches it. A half-open probe failure RE-OPENS with
        a fresh timeout (the dependency is still sick; the original open
        moment must not keep an already-elapsed deadline). A LATE failure
        arriving while already open changes nothing — re-tripping an open
        breaker would let persistent late failures postpone the probe
        forever.
        """
        moment = self._clock() if now is None else now
        self._refresh(moment)
        previous = self._state
        if self._state == "half_open":
            self._probe_in_flight = False
            self._half_open_wins = 0
            self._consecutive_failures += 1
            self._state = "open"
            self._opened_at = moment
            return BreakerRecord(
                state_after="open",
                previous_state=previous,
                tripped=False,
                reopened=True,
                closed=False,
                consecutive_failures=self._consecutive_failures,
                reason=(
                    "half-open probe failed — breaker re-opens with a fresh "
                    f"{self._policy.open_timeout_s:g}s timeout (the dependency "
                    "is still sick)"
                ),
            )
        if self._state == "closed":
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._policy.failure_threshold:
                self._state = "open"
                self._opened_at = moment
                self._half_open_wins = 0
                return BreakerRecord(
                    state_after="open",
                    previous_state=previous,
                    tripped=True,
                    reopened=False,
                    closed=False,
                    consecutive_failures=self._consecutive_failures,
                    reason=(
                        f"{self._consecutive_failures} consecutive failures "
                        f"reached the threshold of {self._policy.failure_threshold} "
                        f"— breaker opens for {self._policy.open_timeout_s:g}s"
                    ),
                )
            return BreakerRecord(
                state_after="closed",
                previous_state=previous,
                tripped=False,
                reopened=False,
                closed=False,
                consecutive_failures=self._consecutive_failures,
                reason=(
                    f"failure {self._consecutive_failures}/"
                    f"{self._policy.failure_threshold} — still below the "
                    "threshold; calls keep flowing"
                ),
            )
        return BreakerRecord(
            state_after="open",
            previous_state=previous,
            tripped=False,
            reopened=False,
            closed=False,
            consecutive_failures=self._consecutive_failures,
            reason=(
                "late failure while open — already open; the open timeout "
                "keeps its original deadline"
            ),
        )

    def reset(self) -> None:
        """Return to a fresh closed breaker (the demo's repeat-run guarantee)."""
        self._state = "closed"
        self._consecutive_failures = 0
        self._opened_at = None
        self._half_open_wins = 0
        self._probe_in_flight = False

    def _refresh(self, moment: float) -> None:
        """Flip an elapsed open state to half-open (lazy — on touch)."""
        if self._state == "open" and self._opened_at is not None:
            if moment - self._opened_at >= self._policy.open_timeout_s:
                self._state = "half_open"
                self._half_open_wins = 0

    def _close(self, previous: BreakerState, *, reason: str) -> BreakerRecord:
        """The half-open→closed transition: every counter back to zero."""
        self._state = "closed"
        self._consecutive_failures = 0
        self._opened_at = None
        self._half_open_wins = 0
        return BreakerRecord(
            state_after="closed",
            previous_state=previous,
            tripped=False,
            reopened=False,
            closed=True,
            consecutive_failures=0,
            reason=reason,
        )
