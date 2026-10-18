"""The bounded event ring: retention, replay, and the honest gap edge."""

import pytest

from guide.domain.realtime.log import BoundedEventLog


def log_of(capacity: int, count: int) -> BoundedEventLog[str]:
    log: BoundedEventLog[str] = BoundedEventLog(capacity)
    for seq in range(1, count + 1):
        log.append(seq, f"e{seq}")
    return log


def test_replay_after_returns_the_contiguous_run() -> None:
    log = log_of(capacity=10, count=5)
    assert log.events_after(2) == ["e3", "e4", "e5"]


def test_replay_after_zero_replays_everything_retained() -> None:
    log = log_of(capacity=10, count=5)
    assert log.events_after(0) == ["e1", "e2", "e3", "e4", "e5"]


def test_current_client_gets_nothing_not_a_duplicate() -> None:
    log = log_of(capacity=10, count=5)
    assert log.events_after(5) == []
    assert log.events_after(9) == []


def test_gap_case_is_empty_never_a_partial_replay() -> None:
    log = log_of(capacity=3, count=10)  # retains 8..10 only
    assert log.oldest_seq == 8
    assert log.newest_seq == 10
    assert log.events_after(6) == []  # would need e7, gone forever
    assert log.events_after(7) == ["e8", "e9", "e10"]  # exactly reachable


def test_capacity_drop_is_silent_amnesia() -> None:
    log = log_of(capacity=3, count=10)
    assert len(log) == 3
    assert log.tail(10) == ["e8", "e9", "e10"]


def test_tail_returns_the_last_n_oldest_first() -> None:
    log = log_of(capacity=10, count=5)
    assert log.tail(2) == ["e4", "e5"]
    assert log.tail(50) == ["e1", "e2", "e3", "e4", "e5"]


def test_empty_log_is_honest_about_itself() -> None:
    log: BoundedEventLog[str] = BoundedEventLog(5)
    assert log.events_after(0) == []
    assert log.tail(3) == []
    assert log.oldest_seq is None
    assert log.newest_seq is None


def test_capacity_must_be_positive() -> None:
    with pytest.raises(ValueError, match="capacity"):
        BoundedEventLog[str](0)
