"""The recent-events ring (``core/logging.py``): capture, bounds, lookups.

The ring is the structured-log viewer's substrate — the processor
``configure_logging`` installs snapshots every event between the processors
and the renderer. These unit tests pin its contract directly: the snapshot
lifts the four named keys and keeps everything else as field rows, the
bound actually evicts oldest-first, sequences never contradict order, the
pass-through never mutates the event dict, and lookups by request id are
the correlation read the trace demo performs.
"""

import pytest

from guide.core.logging import RECENT_EVENT_CAPACITY, RecentEvent, RecentLog, recent_log

RING_EVENTS: list[tuple[str, dict[str, object]]] = [
    ("info", {"event": "a", "request_id": "r1", "detail_count": 2}),
    ("warning", {"event": "b", "request_id": "r2"}),
    ("error", {"event": "c"}),  # no request id on purpose
]


def test_capture_lifts_named_keys_and_keeps_the_rest_as_fields() -> None:
    ring = RecentLog(capacity=10)
    ring.capture(None, "info", {"event": "app_error", "request_id": "r1", "kind": "not_found"})

    [event] = ring.tail()
    assert event.level == "info"
    assert event.event == "app_error"
    assert event.request_id == "r1"
    assert event.sequence == 0
    # kind is not a reserved key — it stays a rendered field row (verbatim:
    # string values render as themselves, containers as JSON below).
    assert event.fields == (("kind", "not_found"),)


def test_capture_renders_containers_as_json_and_scalars_verbatim() -> None:
    ring = RecentLog()
    ring.capture(
        None,
        "info",
        {"event": "e", "count": 3, "flag": True, "nested": {"b": 1, "a": 2}, "text": "plain"},
    )
    [event] = ring.tail()
    fields = dict(event.fields)
    assert fields["count"] == "3"
    assert fields["text"] == "plain"
    # Non-string scalars and containers render as JSON (sorted, deterministic).
    assert fields["flag"] == "true"
    assert fields["nested"] == '{"a": 2, "b": 1}'


def test_capture_passes_the_event_dict_through_unchanged() -> None:
    ring = RecentLog()
    event_dict: dict[str, object] = {"event": "e", "level": "info", "request_id": "r"}
    returned = ring.capture(None, "info", event_dict)
    assert returned is event_dict
    assert event_dict == {"event": "e", "level": "info", "request_id": "r"}


def test_the_ring_evicts_oldest_first_and_never_exceeds_capacity() -> None:
    ring = RecentLog(capacity=3)
    for index in range(8):
        ring.capture(None, "info", {"event": f"e{index}"})

    assert ring.capacity == 3
    held = ring.tail()
    assert [event.event for event in held] == ["e5", "e6", "e7"]
    # Sequences keep counting across eviction — the order stays the truth.
    assert [event.sequence for event in held] == [5, 6, 7]


def test_tail_limit_returns_the_last_n_oldest_first() -> None:
    ring = RecentLog(capacity=10)
    for index in range(5):
        ring.capture(None, "info", {"event": f"e{index}"})
    assert [event.event for event in ring.tail(2)] == ["e3", "e4"]
    assert ring.tail(0) == []


def test_by_request_id_is_the_correlation_read() -> None:
    ring = RecentLog(capacity=10)
    for method_name, payload in RING_EVENTS:
        ring.capture(None, method_name, dict(payload, timestamp="2026-10-24T00:00:00Z"))

    correlated = ring.by_request_id("r1")
    assert [event.event for event in correlated] == ["a"]
    assert correlated[0].timestamp == "2026-10-24T00:00:00Z"
    assert ring.by_request_id("r2")[0].level == "warning"
    # Unknown ids — and the empty id, the "outside any request" case — read empty.
    assert ring.by_request_id("nope") == []
    assert ring.by_request_id("") == []


def test_clear_drops_events_but_sequences_keep_counting() -> None:
    ring = RecentLog(capacity=5)
    ring.capture(None, "info", {"event": "a"})
    ring.clear()
    assert ring.tail() == []
    ring.capture(None, "info", {"event": "b"})
    [event] = ring.tail()
    assert event.event == "b"
    assert event.sequence == 1


def test_capacity_must_be_at_least_one() -> None:
    with pytest.raises(ValueError, match="capacity"):
        RecentLog(capacity=0)


def test_the_process_ring_is_the_singleton_the_pipeline_feeds() -> None:
    assert recent_log() is recent_log()
    assert recent_log().capacity == RECENT_EVENT_CAPACITY


def test_recent_event_is_an_immutable_snapshot() -> None:
    event = RecentEvent(
        sequence=0,
        level="info",
        event="e",
        timestamp="",
        request_id="",
        fields=(("k", "v"),),
    )
    assert event.fields == (("k", "v"),)
