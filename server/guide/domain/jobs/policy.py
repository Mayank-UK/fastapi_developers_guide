"""The jobs retry policy: the schedule, the budget, the poison verdict.

A job that fails in a worker is a different animal from a request that
fails in a handler: nobody is standing there waiting for an answer, so
"retry" costs nothing in latency and everything in load — the worker
owns reliability the way the webhook sender does (topic 14), but with a
LONGER memory. This module is that posture as PURE computation: given a
policy it derives the exact attempt schedule (fixed or exponential
offsets, deterministic), and given one failed attempt it decides the
next step — retry on the schedule, or park in the dead-letter queue —
including the classification that decides some failures must NEVER be
retried.

No sleeping and no network live here — the worker turns
``delay_seconds`` into an arq ``Retry(defer_by=…)`` elsewhere. Like the
webhook policy, the schedule is JITTER-FREE so it is exactly teachable
and testable; production adds random jitter to these same offsets so a
fleet of workers backing off after the same incident does not retry in
a synchronized thundering herd.
"""

from dataclasses import dataclass
from typing import Final, Literal, final

RetryStrategy = Literal["fixed", "exponential"]
"""Two curves a retry schedule can walk: flat, or doubling."""

FailureClass = Literal["retryable", "poison"]
"""The verdict on one failure: the world is wrong (retry), or the input
is wrong (never retry — re-asking the same broken question cannot fix
it, so the job goes straight to the dead-letter queue)."""

DEFAULT_MAX_ATTEMPTS: Final = 3
DEFAULT_BASE_DELAY_SECONDS: Final = 0.25


@final
@dataclass(frozen=True, slots=True)
class JobRetryPolicy:
    """How hard a worker tries: attempt budget + the delay curve between tries.

    ``delay_before(attempt)`` — the pause AFTER a failed attempt (1-based)
    — is ``base_delay_seconds`` on the fixed curve (every pause equal) and
    ``base_delay_seconds * 2 ** (attempt - 1)`` on the exponential one
    (each pause double the last). ``attempt_offsets()`` accumulates the
    pauses into where each attempt RUNS, measured from the first
    attempt's start: the demo policy (3 attempts, exponential, 0.25 s
    base) runs at 0 s / 0.25 s / 0.75 s. Sub-second by design — the
    console's retry timeline is watchable live; production policies
    trade up to seconds or minutes for recovery room.
    """

    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    strategy: RetryStrategy = "exponential"
    base_delay_seconds: float = DEFAULT_BASE_DELAY_SECONDS

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {self.max_attempts}")
        if self.base_delay_seconds <= 0:
            raise ValueError(
                f"base_delay_seconds must be > 0, got {self.base_delay_seconds}"
            )

    def delay_before(self, attempt: int) -> float:
        """Seconds to wait after failed ``attempt`` (1-based) before the next one."""
        if attempt < 1:
            raise ValueError(f"attempt is 1-based, got {attempt}")
        if self.strategy == "fixed":
            return self.base_delay_seconds
        return self.base_delay_seconds * (2.0 ** (attempt - 1))

    def attempt_offsets(self) -> list[float]:
        """The whole schedule at a glance — the panel's timeline shows exactly this."""
        offsets: list[float] = []
        offset = 0.0
        for attempt in range(1, self.max_attempts + 1):
            offsets.append(offset)
            offset += self.delay_before(attempt)
        return offsets


DEMO_JOB_POLICY: Final[JobRetryPolicy] = JobRetryPolicy()
"""The console's policy: 3 attempts, exponential, 0.25 s base — offsets
0 / 0.25 / 0.75, so a fail-always walk exhausts and dead-letters inside
two seconds live."""


TRANSIENT_EXCEPTIONS: Final[tuple[type[BaseException], ...]] = (
    TimeoutError,
    ConnectionError,
    OSError,
)
"""The world-is-wrong family: timeouts and unreachable peers are the
canonical retryable failures (``TimeoutError`` is an ``OSError`` under
the hood, so the tuple reads as one idea — the network layer lied)."""


def classify_failure(exc: BaseException) -> FailureClass:
    """Decide whether one failure deserves another attempt.

    POISON is the input-is-wrong family: ``ValueError`` and everything
    that derives from it (pydantic's ``ValidationError`` included) mean
    the payload itself is malformed — attempt two would re-ask the same
    broken question. Everything else defaults RETRYABLE, matching the
    posture arq and Celery ship with; tighten that default deliberately
    in your own shop if you would rather fail fast on the unfamiliar.
    """
    if isinstance(exc, ValueError):
        return "poison"
    return "retryable"


@final
@dataclass(frozen=True, slots=True)
class RetryVerdict:
    """What the worker does after one failed attempt: the action and why."""

    action: Literal["retry", "dead_letter"]
    delay_seconds: float | None
    reason: str


def decide_retry(
    policy: JobRetryPolicy, *, attempt: int, failure_class: FailureClass
) -> RetryVerdict:
    """The next step after attempt ``attempt`` (1-based) failed.

    Poison fails fast — no attempt is spent re-asking a broken question;
    a retryable failure spends the budget on the policy's curve, and the
    attempt that exhausts it is the one that parks the job in the
    dead-letter queue.
    """
    if failure_class == "poison":
        return RetryVerdict(
            action="dead_letter",
            delay_seconds=None,
            reason=(
                f"failure on attempt {attempt} classified poison — retrying would "
                "re-ask the same broken question"
            ),
        )
    if attempt >= policy.max_attempts:
        return RetryVerdict(
            action="dead_letter",
            delay_seconds=None,
            reason=(
                f"attempt budget spent: {attempt}/{policy.max_attempts} tries on "
                f"the {policy.strategy} curve"
            ),
        )
    delay = policy.delay_before(attempt)
    return RetryVerdict(
        action="retry",
        delay_seconds=delay,
        reason=(
            f"attempt {attempt}/{policy.max_attempts} failed retryable — "
            f"next attempt scheduled in {delay:.2f}s"
        ),
    )
