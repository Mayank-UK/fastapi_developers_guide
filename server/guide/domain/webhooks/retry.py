"""The webhook retry policy: the schedule, the budget, the dead-letter verdict.

Sending a webhook is calling an API you do not control, so the SENDER owns
reliability: the receiver was down at T, the network partitioned, the
response never came. The answer is at-least-once delivery — re-send until
the receiver answers 2xx — and this module is that policy as PURE
computation: given a policy and the attempt a flaky receiver would
finally succeed on, it derives the exact attempt schedule (exponential
backoff, deterministic offsets) and the verdict when the attempt budget
is spent: delivered, or parked in a dead-letter queue a human can inspect
and replay.

No sleeping and no network live here — a scheduler elsewhere turns
``scheduled_offset`` into real timers. The offsets are deliberately
JITTER-FREE so the schedule is exactly teachable and testable; production
systems add random jitter to those same offsets so thousands of
subscribers backing off after the same incident do not retry in a
synchronized thundering herd (section 4 of the webhooks topic makes the
same trade explicit).
"""

from dataclasses import dataclass
from typing import Final, Literal, final

DEFAULT_MAX_ATTEMPTS: Final = 5
DEFAULT_BASE_DELAY_SECONDS: Final = 1
DEFAULT_BACKOFF_FACTOR: Final = 2


@final
@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """How hard a sender tries: attempt budget + the backoff curve between tries.

    ``delay_before(attempt)`` — the pause AFTER a failed attempt — grows
    exponentially: ``base_delay_seconds * backoff_factor ** (attempt - 1)``,
    so the default policy waits 1s, 2s, 4s, 8s and runs attempts at
    offsets 0s, 1s, 3s, 7s, 15s after the fire time. Exponential rather
    than fixed because a receiver that is down needs recovery ROOM, not a
    hammer; the factor is validated ``>= 2`` so the curve genuinely grows.
    """

    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    base_delay_seconds: int = DEFAULT_BASE_DELAY_SECONDS
    backoff_factor: int = DEFAULT_BACKOFF_FACTOR

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {self.max_attempts}")
        if self.base_delay_seconds < 1:
            raise ValueError(f"base_delay_seconds must be >= 1, got {self.base_delay_seconds}")
        if self.backoff_factor < 2:
            raise ValueError(f"backoff_factor must be >= 2, got {self.backoff_factor}")

    def delay_before(self, attempt: int) -> int:
        """Seconds to wait after failed ``attempt`` (1-based) before the next one."""
        delay = self.base_delay_seconds
        for _ in range(attempt - 1):
            delay *= self.backoff_factor
        return delay

    def scheduled_offset(self, attempt: int) -> int:
        """Seconds after the fire time when ``attempt`` (1-based) runs.

        The first attempt runs immediately (offset 0); every later one runs
        after the accumulated pauses of the attempts before it.
        """
        offset = 0
        for prior in range(1, attempt):
            offset += self.delay_before(prior)
        return offset

    def attempt_offsets(self) -> list[int]:
        """The whole schedule at a glance — the demo's roster shows exactly this."""
        return [self.scheduled_offset(attempt) for attempt in range(1, self.max_attempts + 1)]


DEFAULT_RETRY_POLICY: Final[RetryPolicy] = RetryPolicy()
"""The sender's default posture: 5 attempts, 1s base, doubling — offsets 0/1/3/7/15."""


@final
@dataclass(frozen=True, slots=True)
class AttemptStep:
    """One delivery attempt as the walk records it: when, what the target answered."""

    attempt: int
    offset_seconds: int
    status: int
    delivered: bool


@final
@dataclass(frozen=True, slots=True)
class DeadLetterEntry:
    """What lands in the dead-letter queue when the attempt budget is spent."""

    event_id: str
    attempts: int
    last_status: int
    final_offset_seconds: int
    reason: str


@final
@dataclass(frozen=True, slots=True)
class DeliveryWalk:
    """A full simulated delivery: every attempt, and where the event ended up."""

    steps: tuple[AttemptStep, ...]
    verdict: Literal["delivered", "dead-lettered"]
    attempts_used: int
    delivered_at_offset: int | None
    dead_letter: DeadLetterEntry | None


def walk_delivery(
    policy: RetryPolicy, *, event_id: str, success_on_attempt: int | None
) -> DeliveryWalk:
    """Walk the lifecycle: attempts on schedule until 2xx or a dead-letter verdict.

    ``success_on_attempt`` is the scenario fact the caller supplies — the
    attempt a flaky receiver would finally answer 2xx on, or ``None`` for
    a target that never succeeds. A success beyond ``max_attempts``
    honestly dead-letters: the event WOULD have landed on attempt 9, but
    the budget is 5, and the dead letter records both facts for the human
    who decides whether to replay.
    """
    succeeds_within_budget = success_on_attempt is not None and success_on_attempt <= (
        policy.max_attempts
    )
    steps: list[AttemptStep] = []
    for attempt in range(1, policy.max_attempts + 1):
        offset = policy.scheduled_offset(attempt)
        delivered = succeeds_within_budget and attempt == success_on_attempt
        steps.append(
            AttemptStep(
                attempt=attempt,
                offset_seconds=offset,
                status=200 if delivered else 500,
                delivered=delivered,
            )
        )
        if delivered:
            return DeliveryWalk(
                steps=tuple(steps),
                verdict="delivered",
                attempts_used=attempt,
                delivered_at_offset=offset,
                dead_letter=None,
            )
    final = steps[-1]
    return DeliveryWalk(
        steps=tuple(steps),
        verdict="dead-lettered",
        attempts_used=policy.max_attempts,
        delivered_at_offset=None,
        dead_letter=DeadLetterEntry(
            event_id=event_id,
            attempts=policy.max_attempts,
            last_status=final.status,
            final_offset_seconds=final.offset_seconds,
            reason=(
                f"Event {event_id} failed all {policy.max_attempts} attempts "
                f"(last answer {final.status}); parked for inspection and replay."
            ),
        ),
    )
