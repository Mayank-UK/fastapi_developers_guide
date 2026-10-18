"""The rate-limit policy engine: a sliding window, deterministic by clock injection.

``SlidingWindowLimiter`` is the algorithm half of topic 25's rate-limiting
section — pure bookkeeping over ``(key → hit timestamps)`` with NO clock and
NO sleeping of its own: the caller supplies ``now`` (monotonic seconds), so
every decision sequence — allow…allow → 429 → window slide → allow — is a
unit test with integer inputs, never a timed test. The wiring in
``create_app`` injects ``time.monotonic``; the dependency in
``presentation/dependencies/rate_limit.py`` supplies the key (client IP +
route) and translates a denial into the 429 envelope plus ``Retry-After``.

The window is the true sliding form (not fixed buckets): a request at time
``t`` is allowed when fewer than ``budget`` hits fall inside the window
``(t - window_s, t]`` — which is why ``retry_after_s`` is computed from the
OLDEST in-window hit (``oldest + window_s - now``), the exact instant a slot
reopens. Denied hits are NOT recorded (they consumed nothing), so a client
hammering past the limit does not extend its own lockout — the classic
fail-open mistake fixed-bucket implementations invite. Pruning is lazy (on
each touch): the map holds at most one empty deque per key ever seen, and a
key's expired hits cost nothing once touched again.
"""

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

Clock = Callable[[], float]
"""Monotonic seconds. Injected at construction; tests inject counters."""


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    """The knobs: how many hits inside how many seconds, per key.

    ``keying`` is documentation-with-teeth: it names what the wiring keys on
    (client IP + route template), and it rides the 429 envelope's details so
    a throttled caller can see WHICH budget they burned.
    """

    window_s: float
    budget: int
    keying: str


@dataclass(frozen=True, slots=True)
class RateLimitVerdict:
    """One decision: allowed or throttled, with the numbers that prove it.

    ``retry_after_s`` is set only on a denial — the seconds until the oldest
    in-window hit expires and a slot reopens (the value ``Retry-After``
    carries, rounded up by the dependency).
    """

    allowed: bool
    limit: int
    remaining: int
    window_s: float
    retry_after_s: float | None


DEMO_POLICY: Final[RateLimitPolicy] = RateLimitPolicy(
    window_s=10.0, budget=5, keying="client ip + route"
)
"""The burner endpoint's policy: five hits per ten seconds — small enough to
burn by hand in the demo, honest enough to teach the shape."""


class SlidingWindowLimiter:
    """Sliding-window admission per key; deterministic under an injected clock."""

    def __init__(self, policy: RateLimitPolicy, clock: Clock = time.monotonic) -> None:
        """Hold the policy, the clock, and the per-key hit log (empty)."""
        self._policy = policy
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    @property
    def policy(self) -> RateLimitPolicy:
        """The configured window/budget/keying — served to the demo panel."""
        return self._policy

    def hit(self, key: str, now: float | None = None) -> RateLimitVerdict:
        """Consume one unit for ``key`` at ``now`` (default: the injected clock).

        Prunes the key's log to the window first; admits when the log is
        below budget (and records the hit), denies otherwise without
        recording — a denied request must not push honest traffic further
        out. Empty keys whose logs pruned to nothing are dropped so the
        map tracks live budgets, not history.
        """
        moment = self._clock() if now is None else now
        hits = self._prune(key, moment)
        if len(hits) >= self._policy.budget:
            retry_after = hits[0] + self._policy.window_s - moment
            return self._verdict(allowed=False, remaining=0, retry_after_s=retry_after)
        hits.append(moment)
        return self._verdict(
            allowed=True, remaining=self._policy.budget - len(hits), retry_after_s=None
        )

    def peek(self, key: str, now: float | None = None) -> RateLimitVerdict:
        """The verdict a hit WOULD get, without consuming anything.

        Prunes exactly like ``hit`` (a peek over a stale log would lie about
        remaining budget), but never appends.
        """
        moment = self._clock() if now is None else now
        hits = self._prune(key, moment)
        retry_after = None
        if len(hits) >= self._policy.budget:
            retry_after = hits[0] + self._policy.window_s - moment
        return self._verdict(
            allowed=len(hits) < self._policy.budget,
            remaining=max(0, self._policy.budget - len(hits)),
            retry_after_s=retry_after,
        )

    def _prune(self, key: str, now: float) -> deque[float]:
        """Drop expired hits for ``key`` (lazily — on touch, not on a timer)."""
        hits = self._hits.get(key)
        if hits is None:
            hits = deque()
            self._hits[key] = hits
            return hits
        horizon = now - self._policy.window_s
        while hits and hits[0] <= horizon:
            hits.popleft()
        return hits

    def _verdict(
        self, *, allowed: bool, remaining: int, retry_after_s: float | None
    ) -> RateLimitVerdict:
        return RateLimitVerdict(
            allowed=allowed,
            limit=self._policy.budget,
            remaining=remaining,
            window_s=self._policy.window_s,
            retry_after_s=retry_after_s,
        )
