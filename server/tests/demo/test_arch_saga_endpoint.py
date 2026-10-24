"""The arch-saga endpoint (topic 43, area ``arch``).

Pins the wire contract (GET /api/demo/arch/saga): the four-step
workflow definition, the happy run committed with four forward entries,
and — the panel's headline — the failing run whose compensations ran
in REVERSE order over the completed steps (refund-card then
release-item) with per-step ledger evidence, plus the balance rows
proving the undo returned every metric to its starting value. The
durability rows name the outbox and the event stream as the two halves
a production saga adds around this in-process coordinator.
"""

from fastapi.testclient import TestClient

SAGA_PATH = "/api/demo/arch/saga"

WORKFLOW_STEPS = [
    ("reserve-item", "release-item"),
    ("charge-card", "refund-card"),
    ("book-shipment", "cancel-shipment"),
    ("announce-order", "retract-announce"),
]


def test_the_workflow_is_the_four_step_order_saga(client: TestClient) -> None:
    body = client.get(SAGA_PATH).json()
    workflow = body["workflow"]
    assert workflow["name"] == "order-fulfillment"
    assert [(s["action"], s["compensates"]) for s in workflow["steps"]] == WORKFLOW_STEPS
    assert all(s["describes"] for s in workflow["steps"])


def test_the_happy_run_commits_all_four_forward_steps(client: TestClient) -> None:
    run = client.get(SAGA_PATH).json()["happyRun"]
    assert run["outcome"] == "committed"
    assert run["failureStep"] is None
    assert run["compensationOrder"] == []
    assert [(e["phase"], e["step"], e["outcome"]) for e in run["entries"]] == [
        ("forward", "reserve-item", "done"),
        ("forward", "charge-card", "done"),
        ("forward", "book-shipment", "done"),
        ("forward", "announce-order", "done"),
    ]
    # Per-step evidence: the ledger's own arithmetic in every line.
    assert "stock widgets 2 -> 1" in run["entries"][0]["evidence"]
    assert "balance 0 -> 4900" in run["entries"][1]["evidence"]
    # The clock is deterministic and ordered: T+1..T+4.
    assert [e["at"] for e in run["entries"]] == ["T+1", "T+2", "T+3", "T+4"]


def test_the_failing_run_compensates_in_reverse_order_with_evidence(
    client: TestClient,
) -> None:
    run = client.get(SAGA_PATH).json()["failureRun"]
    assert run["outcome"] == "compensated"
    assert run["failureStep"] == "book-shipment"
    # THE proof: undo over the two COMPLETED steps, newest-first.
    assert run["compensationOrder"] == ["refund-card", "release-item"]
    assert [(e["phase"], e["step"], e["outcome"]) for e in run["entries"]] == [
        ("forward", "reserve-item", "done"),
        ("forward", "charge-card", "done"),
        ("forward", "book-shipment", "failed"),
        ("compensate", "refund-card", "compensated"),
        ("compensate", "release-item", "compensated"),
    ]
    # The failure carries its injected reason; the undo carries its arithmetic.
    assert "carrier full" in run["entries"][2]["evidence"]
    assert "balance 4900 -> 0" in run["entries"][3]["evidence"]
    assert "stock widgets 1 -> 2" in run["entries"][4]["evidence"]
    # The never-reached fourth step left no trace.
    assert "announce-order" not in [e["step"] for e in run["entries"]]


def test_the_balances_prove_the_undo_undid(client: TestClient) -> None:
    rows = {row["metric"]: row for row in client.get(SAGA_PATH).json()["balances"]}
    assert set(rows) == {
        "stock (widgets)",
        "balance (cents)",
        "carrier slots held",
        "announcements",
    }
    assert rows["stock (widgets)"]["before"] == "2"
    assert rows["stock (widgets)"]["afterHappy"] == "1"
    assert rows["stock (widgets)"]["afterFailure"] == "2"
    assert rows["balance (cents)"]["afterHappy"] == "4900"
    assert rows["balance (cents)"]["afterFailure"] == "0"
    assert rows["carrier slots held"]["afterFailure"] == "0"
    assert rows["announcements"]["afterFailure"] == "0"
    assert all("UNEXPECTED" not in row["verdict"] for row in rows.values())


def test_the_durability_rows_name_both_production_halves(client: TestClient) -> None:
    body = client.get(SAGA_PATH).json()
    assert [row["half"] for row in body["durability"]] == ["the steps", "the run log"]
    by_half = {row["half"]: row for row in body["durability"]}
    assert "outbox" in by_half["the steps"]["what"]
    assert "at-least-once" in by_half["the steps"]["what"]
    assert "event stream" in by_half["the run log"]["what"]
    assert "outbox_service.py" in by_half["the steps"]["where"]
    assert "event_store.py" in by_half["the run log"]["where"]


def test_the_honesty_note_pins_the_real_substrate_claim(client: TestClient) -> None:
    note = client.get(SAGA_PATH).json()["honestyNote"]
    assert "real SagaCoordinator" in note
    assert "injected raise" in note
    assert "in-process" in note


def test_the_panel_is_deterministic_across_requests(client: TestClient) -> None:
    first = client.get(SAGA_PATH).json()
    second = client.get(SAGA_PATH).json()
    # Fresh scratch per request: identical runs, identical balances.
    assert first["happyRun"]["entries"] == second["happyRun"]["entries"]
    assert first["failureRun"]["entries"] == second["failureRun"]["entries"]
    assert first["balances"] == second["balances"]


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][SAGA_PATH]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert ref.endswith("ArchSagaPanel")
