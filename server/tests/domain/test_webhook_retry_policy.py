"""The retry-policy engine: exact schedules, budgets, and the DLQ verdict.

Topic 14's §4 machinery as pure computation — no sleeping, no network,
so exactness is assertable: the default policy's offsets are 0/1/3/7/15
seconds, a custom curve is honored to the second, success on the last
attempt is still a delivery (the boundary), success BEYOND the budget
honestly dead-letters, and the dead-letter entry carries every fact a
human needs to decide about a replay.
"""

import pytest

from guide.domain.webhooks.retry import (
    DEFAULT_RETRY_POLICY,
    DeliveryWalk,
    RetryPolicy,
    walk_delivery,
)


def test_default_policy_schedule_is_exact() -> None:
    policy = DEFAULT_RETRY_POLICY
    assert policy.attempt_offsets() == [0, 1, 3, 7, 15]
    assert [policy.delay_before(attempt) for attempt in range(1, 5)] == [1, 2, 4, 8]


def test_custom_curve_is_honored_to_the_second() -> None:
    policy = RetryPolicy(max_attempts=4, base_delay_seconds=2, backoff_factor=3)
    # Waits after attempts 1..3: 2s, 6s, 18s → attempts run at 0, 2, 8, 26.
    assert policy.attempt_offsets() == [0, 2, 8, 26]


def test_first_attempt_always_runs_immediately() -> None:
    assert RetryPolicy(max_attempts=1).scheduled_offset(1) == 0


def test_policy_refuses_degenerate_shapes() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError, match="base_delay_seconds"):
        RetryPolicy(base_delay_seconds=0)
    with pytest.raises(ValueError, match="backoff_factor"):
        RetryPolicy(backoff_factor=1)


def test_success_on_first_attempt_is_one_step_delivered() -> None:
    walk: DeliveryWalk = walk_delivery(DEFAULT_RETRY_POLICY, event_id="evt_a", success_on_attempt=1)
    assert walk.verdict == "delivered"
    assert walk.attempts_used == 1
    assert walk.delivered_at_offset == 0
    assert walk.dead_letter is None
    assert [(step.attempt, step.status, step.delivered) for step in walk.steps] == [
        (1, 200, True)
    ]


def test_success_on_attempt_three_walks_the_backoff_curve() -> None:
    walk = walk_delivery(DEFAULT_RETRY_POLICY, event_id="evt_b", success_on_attempt=3)
    assert walk.verdict == "delivered"
    assert walk.attempts_used == 3
    assert walk.delivered_at_offset == 3
    assert [(step.attempt, step.offset_seconds, step.status) for step in walk.steps] == [
        (1, 0, 500),
        (2, 1, 500),
        (3, 3, 200),
    ]


def test_success_on_the_last_attempt_is_still_a_delivery() -> None:
    walk = walk_delivery(DEFAULT_RETRY_POLICY, event_id="evt_c", success_on_attempt=5)
    assert walk.verdict == "delivered"
    assert walk.attempts_used == 5
    assert walk.delivered_at_offset == 15
    assert walk.dead_letter is None


def test_never_succeeding_spends_the_whole_budget_and_dead_letters() -> None:
    walk = walk_delivery(DEFAULT_RETRY_POLICY, event_id="evt_d", success_on_attempt=None)
    assert walk.verdict == "dead-lettered"
    assert walk.attempts_used == 5
    assert walk.delivered_at_offset is None
    assert [step.status for step in walk.steps] == [500] * 5
    dead = walk.dead_letter
    assert dead is not None
    assert dead.event_id == "evt_d"
    assert dead.attempts == 5
    assert dead.last_status == 500
    assert dead.final_offset_seconds == 15
    assert "evt_d" in dead.reason
    assert "replay" in dead.reason


def test_success_beyond_the_budget_honestly_dead_letters() -> None:
    """Would have landed on attempt 9; the budget is 5 — the DLQ records the miss."""
    walk = walk_delivery(DEFAULT_RETRY_POLICY, event_id="evt_e", success_on_attempt=9)
    assert walk.verdict == "dead-lettered"
    assert [step.status for step in walk.steps] == [500] * 5
    assert walk.dead_letter is not None


def test_walk_is_pure_same_inputs_same_verdict() -> None:
    first = walk_delivery(DEFAULT_RETRY_POLICY, event_id="evt_f", success_on_attempt=2)
    second = walk_delivery(DEFAULT_RETRY_POLICY, event_id="evt_f", success_on_attempt=2)
    assert first == second


def test_custom_policy_budget_bounds_the_walk() -> None:
    policy = RetryPolicy(max_attempts=2, base_delay_seconds=1, backoff_factor=2)
    walk = walk_delivery(policy, event_id="evt_g", success_on_attempt=None)
    assert walk.verdict == "dead-lettered"
    assert [(step.attempt, step.offset_seconds) for step in walk.steps] == [(1, 0), (2, 1)]
    assert walk.dead_letter is not None
    assert walk.dead_letter.attempts == 2
    assert walk.dead_letter.final_offset_seconds == 1
