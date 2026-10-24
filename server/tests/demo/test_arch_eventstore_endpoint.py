"""The arch-eventstore endpoint (topic 43, area ``arch``).

Pins the wire contract (GET /api/demo/arch/eventstore): five facts
appended with dense versions and stamped clocks, the state folded back
out ONE event at a time (each fold step its own evidence row), the
rebuild in a second store instance matching the first exactly (the
replay promise, checked on the wire), the stale writer refused with a
VersionConflict that stored NOTHING, and the audit-kinship row naming
audit_log (migration 0001) as the repo's append-only relative —
side-band beside mutable rows, not the source of truth.
"""

from fastapi.testclient import TestClient

EVENTSTORE_PATH = "/api/demo/arch/eventstore"

APPENDED_TYPES = [
    "PostCreated",
    "PostEdited",
    "TagAdded",
    "TagAdded",
    "PostPublished",
]


def test_the_store_facts_and_appended_history(client: TestClient) -> None:
    body = client.get(EVENTSTORE_PATH).json()
    assert body["store"] == {
        "port": "EventStore",
        "adapter": "InMemoryEventStore",
        "stream": "post:advanced-tour",
        "events": 5,
    }
    appended = body["appended"]
    assert [e["eventType"] for e in appended] == APPENDED_TYPES
    assert [e["version"] for e in appended] == [1, 2, 3, 4, 5]
    # The adapter's stamps: minted ids (uuid4 hex) and the injected clock.
    assert all(len(e["eventId"]) == 32 for e in appended)
    assert [e["occurredAt"] for e in appended] == ["t1", "t2", "t3", "t4", "t5"]
    assert "The advanced architecture tour" in appended[0]["payload"]


def test_the_fold_derives_state_event_by_event(client: TestClient) -> None:
    body = client.get(EVENTSTORE_PATH).json()
    steps = body["foldSteps"]
    assert [s["afterVersion"] for s in steps] == [1, 2, 3, 4, 5]
    # Per-event evidence: the create builds the state, the edit rewrites the
    # title and counts an edit, the tags accumulate, the publish flips status.
    assert "status=draft" in steps[0]["stateNow"]
    assert "revised" in steps[1]["stateNow"]
    assert "tags=[architecture]" in steps[2]["stateNow"]
    assert "tags=[architecture, sagas]" in steps[3]["stateNow"]
    assert "status=published" in steps[4]["stateNow"]
    # The final folded state, exactly.
    assert body["currentState"] == {
        "title": "The advanced architecture tour, revised",
        "author": "ada",
        "tags": ["architecture", "sagas"],
        "edits": 1,
        "status": "published",
    }


def test_the_rebuild_in_a_second_store_matches(client: TestClient) -> None:
    rebuild = client.get(EVENTSTORE_PATH).json()["rebuild"]
    assert rebuild["matches"] is True
    assert rebuild["state"]["title"] == "The advanced architecture tour, revised"
    assert rebuild["state"]["tags"] == ["architecture", "sagas"]
    assert "second InMemoryEventStore" in rebuild["method"]
    assert "replay determinism" in rebuild["evidence"]


def test_the_stale_write_is_refused_totally(client: TestClient) -> None:
    conflict = client.get(EVENTSTORE_PATH).json()["concurrency"]
    assert conflict["expectedVersion"] == 3
    assert conflict["actualVersion"] == 5
    assert conflict["storedEventsAfter"] == 5, "the losing write stored nothing"
    assert "VersionConflict" in conflict["evidence"]
    assert "re-fold, retry" in conflict["evidence"]


def test_the_contrast_rows_argue_both_sides(client: TestClient) -> None:
    rows = {row["approach"]: row for row in client.get(EVENTSTORE_PATH).json()["contrast"]}
    assert "4 of the 5 facts gone" in rows["mutable row (the familiar way)"]["history"]
    assert "5 of 5 facts retained" in rows["event stream (this demo's store)"]["history"]
    assert "what IS the current state?" in rows["mutable row (the familiar way)"]["answers"]
    assert "what HAPPENED?" in rows["event stream (this demo's store)"]["answers"]


def test_the_audit_kinship_is_honestly_drawn(client: TestClient) -> None:
    kinship = client.get(EVENTSTORE_PATH).json()["kinship"]
    assert kinship["relative"] == "audit_log (migration 0001)"
    assert kinship["where"] == "server/alembic/versions/0001_guide_schema.py"
    assert "append-only" in kinship["same"]
    assert "SIDE-BAND" in kinship["different"]
    assert "source of truth" in kinship["different"]


def test_the_honesty_note_pins_the_real_calls_claim(client: TestClient) -> None:
    note = client.get(EVENTSTORE_PATH).json()["honestyNote"]
    assert "real calls on this request" in note
    assert "process memory" in note
    assert "migration 0004" in note


def test_the_panel_is_deterministic_across_requests(client: TestClient) -> None:
    first = client.get(EVENTSTORE_PATH).json()
    second = client.get(EVENTSTORE_PATH).json()
    assert first["foldSteps"] == second["foldSteps"]
    assert first["currentState"] == second["currentState"]
    assert first["rebuild"]["matches"] and second["rebuild"]["matches"]
    assert first["concurrency"] == second["concurrency"]


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][EVENTSTORE_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("ArchEventStorePanel")
