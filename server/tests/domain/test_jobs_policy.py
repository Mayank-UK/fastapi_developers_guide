"""The jobs retry policy as a pure table: curves, budgets, poison verdicts.

Mirrors the webhooks retry-policy test: every number the panel teaches
is derived here from the policy alone — the fixed and exponential
curves, the accumulated offsets a walk actually runs at, the poison
classification, and the dead-letter verdicts at the budget's edge.
"""


import pytest
from pydantic import BaseModel, Field, ValidationError

from guide.domain.jobs.comparison import (
    COMPARISON_STEP_SECONDS,
    COMPARISON_STEPS,
    run_comparison_work,
)
from guide.domain.jobs.policy import (
    DEMO_JOB_POLICY,
    JobRetryPolicy,
    classify_failure,
    decide_retry,
)
from guide.domain.jobs.ports import oldest_age_seconds


class TestTheCurves:
    def test_exponential_doubles_each_pause(self) -> None:
        policy = JobRetryPolicy(max_attempts=5, strategy="exponential", base_delay_seconds=1)
        assert [policy.delay_before(n) for n in range(1, 5)] == [1, 2, 4, 8]

    def test_fixed_stays_flat(self) -> None:
        policy = JobRetryPolicy(max_attempts=4, strategy="fixed", base_delay_seconds=0.5)
        assert [policy.delay_before(n) for n in range(1, 4)] == [0.5, 0.5, 0.5]

    def test_offsets_accumulate_the_pauses(self) -> None:
        policy = JobRetryPolicy(max_attempts=4, strategy="exponential", base_delay_seconds=1)
        assert policy.attempt_offsets() == [0, 1, 3, 7]

    def test_the_demo_policy_walks_in_under_two_seconds(self) -> None:
        assert DEMO_JOB_POLICY.attempt_offsets() == [0, 0.25, 0.75]

    def test_attempt_zero_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="1-based"):
            DEMO_JOB_POLICY.delay_before(0)

    @pytest.mark.parametrize(
        ("kwargs", "match"),
        [
            ({"max_attempts": 0}, "max_attempts"),
            ({"base_delay_seconds": 0}, "base_delay_seconds"),
        ],
    )
    def test_invalid_policies_refuse_construction(self, kwargs: dict[str, int], match: str) -> None:
        with pytest.raises(ValueError, match=match):
            JobRetryPolicy(**kwargs)  # type: ignore[arg-type]


class TestPoisonClassification:
    def test_value_errors_are_poison(self) -> None:
        assert classify_failure(ValueError("bad payload")) == "poison"

    def test_pydantic_validation_errors_are_poison(self) -> None:
        with pytest.raises(ValidationError) as raised:
            _ShapedDraft(to="ab")  # too short for the field
        assert classify_failure(raised.value) == "poison"  # ValidationError derives from ValueError

    def test_transient_world_failures_are_retryable(self) -> None:
        assert classify_failure(TimeoutError("smtp slow")) == "retryable"
        assert classify_failure(ConnectionError("dns lies")) == "retryable"

    def test_unknown_failures_default_retryable_like_arq_and_celery(self) -> None:
        assert classify_failure(RuntimeError("mystery")) == "retryable"


class TestTheVerdicts:
    def test_retryable_failure_mid_budget_retries_on_the_curve(self) -> None:
        verdict = decide_retry(DEMO_JOB_POLICY, attempt=1, failure_class="retryable")
        assert verdict.action == "retry"
        assert verdict.delay_seconds == 0.25
        assert "1/3" in verdict.reason

    def test_the_last_allowed_attempt_dead_letters(self) -> None:
        verdict = decide_retry(DEMO_JOB_POLICY, attempt=3, failure_class="retryable")
        assert verdict.action == "dead_letter"
        assert verdict.delay_seconds is None
        assert "budget spent" in verdict.reason

    def test_poison_dead_letters_without_spending_the_budget(self) -> None:
        verdict = decide_retry(DEMO_JOB_POLICY, attempt=1, failure_class="poison")
        assert verdict.action == "dead_letter"
        assert verdict.delay_seconds is None
        assert "poison" in verdict.reason

    def test_poison_outranks_a_remaining_budget(self) -> None:
        # even with attempts left, poison never re-asks the broken question
        verdict = decide_retry(DEMO_JOB_POLICY, attempt=2, failure_class="poison")
        assert verdict.action == "dead_letter"


class TestTheQueueAge:
    def test_empty_queue_has_no_oldest_job(self) -> None:
        assert oldest_age_seconds(1_000, None) is None

    def test_future_score_clamps_to_zero(self) -> None:
        now = 10_000
        assert oldest_age_seconds(now, oldest_score_ms=float(now + 5_000)) == 0.0

    def test_past_score_measures_the_wait(self) -> None:
        assert oldest_age_seconds(10_000, oldest_score_ms=7_500) == 2.5


class TestTheSharedWorkload:
    async def test_the_workload_runs_every_step_through_the_injected_sleeper(self) -> None:
        pauses: list[float] = []

        async def sleeper(seconds: float) -> None:
            pauses.append(seconds)

        await run_comparison_work(sleeper)
        assert pauses == [COMPARISON_STEP_SECONDS] * COMPARISON_STEPS


class _ShapedDraft(BaseModel):
    """The poison probe's model — min_length forces a real ValidationError."""

    to: str = Field(min_length=3)
