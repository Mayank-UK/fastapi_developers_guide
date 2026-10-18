"""The /api/demo/api/webhook-simulator endpoints + the REAL /webhooks/receive.

Topic 14's demo pinned end to end against the per-test app: the roster
serves the scenarios and schedule, each simulation scenario walks its
honest lifecycle (one delivery / a dead letter / flaky attempt-3), the
None-valued facts are ABSENT from the wire (exclude_none — the client's
DTO treats null as invalid), and the receive endpoint is exercised as a
real verifier would exercise it: raw-body signing round trips to 202,
while tampering, re-serialization, missing headers, and a stale
timestamp each earn the 401 envelope.
"""

import json
import time

from fastapi.testclient import TestClient

from guide.domain.webhooks.signing import (
    DEMO_SHARED_SECRET,
    TIMESTAMP_HEADER,
    signed_headers,
)

SIMULATOR = "/api/demo/api/webhook-simulator"
RECEIVE = "/api/demo/api/webhooks/receive"


def _simulate(client: TestClient, scenario: str) -> dict:
    response = client.post(
        SIMULATOR,
        json={"eventType": "post.published", "scenario": scenario, "note": "endpoint test"},
    )
    assert response.status_code == 200
    return response.json()


def test_roster_serves_scenarios_catalog_secret_and_schedule(client: TestClient) -> None:
    body = client.get(SIMULATOR).json()
    assert [card["id"] for card in body["scenarios"]] == [
        "immediate-2xx",
        "always-500",
        "flaky-then-success",
    ]
    # exclude_none: the broken receiver's card omits successOnAttempt entirely.
    assert "successOnAttempt" not in body["scenarios"][1]
    assert body["eventTypes"] == ["post.published", "post.updated", "comment.created"]
    assert body["secret"] == DEMO_SHARED_SECRET
    assert body["receiveEndpoint"] == RECEIVE
    assert body["policy"]["offsets"] == [0, 1, 3, 7, 15]


def test_immediate_scenario_answers_one_delivered_attempt(client: TestClient) -> None:
    body = _simulate(client, "immediate-2xx")
    assert body["verdict"] == "delivered"
    assert body["deliveredAtOffset"] == 0
    assert "deadLetter" not in body
    assert len(body["attempts"]) == 1
    assert body["attempts"][0]["signature"].startswith("v1=")
    assert body["deliverByHand"]["url"] == RECEIVE


def test_always_500_scenario_answers_a_dead_letter(client: TestClient) -> None:
    body = _simulate(client, "always-500")
    assert body["verdict"] == "dead-lettered"
    assert "deliveredAtOffset" not in body  # exclude_none, not null
    assert [attempt["status"] for attempt in body["attempts"]] == [500] * 5
    assert body["deadLetter"]["attempts"] == 5
    assert body["deadLetter"]["lastStatus"] == 500
    assert body["deadLetter"]["finalOffsetSeconds"] == 15


def test_flaky_scenario_lands_on_attempt_three(client: TestClient) -> None:
    body = _simulate(client, "flaky-then-success")
    assert body["verdict"] == "delivered"
    assert [attempt["offsetSeconds"] for attempt in body["attempts"]] == [0, 1, 3]
    assert body["attempts"][2]["status"] == 200
    assert body["deliveredAtOffset"] == 3


def test_unknown_scenario_is_the_edge_422_envelope(client: TestClient) -> None:
    response = client.post(
        SIMULATOR, json={"eventType": "post.published", "scenario": "sometimes-418"}
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["requestId"]


def test_signed_delivery_round_trips_to_202(client: TestClient) -> None:
    body = _simulate(client, "immediate-2xx")
    hand = body["deliverByHand"]
    response = client.post(
        hand["url"], content=hand["body"], headers=dict(hand["headers"])
    )
    assert response.status_code == 202
    receipt = response.json()
    assert receipt["eventId"] == body["event"]["id"]
    assert receipt["ageSeconds"] <= 60  # fired this same test, fresh by construction
    assert "constant time" in receipt["detail"]


def test_tampered_body_earns_the_401_envelope(client: TestClient) -> None:
    body = _simulate(client, "immediate-2xx")
    hand = body["deliverByHand"]
    tampered = hand["body"].replace("endpoint test", "tampered!!!")
    response = client.post(
        hand["url"], content=tampered, headers=dict(hand["headers"])
    )
    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "unauthorized"
    assert "signature" in error["message"]
    assert response.headers["x-request-id"] == error["requestId"]


def test_reserialized_json_is_not_the_signed_bytes(client: TestClient) -> None:
    """Same object, different bytes (pretty-printed) — the signature refuses it."""
    body = _simulate(client, "immediate-2xx")
    hand = body["deliverByHand"]
    reprinted = json.dumps(json.loads(hand["body"]), indent=2)
    response = client.post(
        hand["url"], content=reprinted, headers=dict(hand["headers"])
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_missing_signature_headers_is_401(client: TestClient) -> None:
    response = client.post(RECEIVE, content="{}", headers={})
    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "unauthorized"
    assert "x-webhook-timestamp" in error["message"]


def test_malformed_timestamp_header_is_401(client: TestClient) -> None:
    payload = '{"id":"evt_x"}'
    headers = signed_headers(
        secret=DEMO_SHARED_SECRET, timestamp=int(time.time()), payload=payload
    )
    headers[TIMESTAMP_HEADER] = "not-a-number"
    response = client.post(RECEIVE, content=payload, headers=headers)
    assert response.status_code == 401
    assert "not an integer" in response.json()["error"]["message"]


def test_stale_timestamp_is_401(client: TestClient) -> None:
    payload = '{"id":"evt_old"}'
    stale = int(time.time()) - 3_600
    headers = signed_headers(secret=DEMO_SHARED_SECRET, timestamp=stale, payload=payload)
    response = client.post(RECEIVE, content=payload, headers=headers)
    assert response.status_code == 401
    assert "freshness window" in response.json()["error"]["message"]


def test_non_json_body_with_valid_signature_still_accepts(client: TestClient) -> None:
    """Verify first, parse later: a signed non-JSON body 202s with no eventId."""
    payload = "not json at all, but genuinely signed"
    headers = signed_headers(
        secret=DEMO_SHARED_SECRET, timestamp=int(time.time()), payload=payload
    )
    response = client.post(RECEIVE, content=payload, headers=headers)
    assert response.status_code == 202
    receipt = response.json()
    assert "eventId" not in receipt
    assert receipt["ageSeconds"] <= 5


def test_both_simulator_endpoints_are_documented_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert paths[SIMULATOR]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("WebhookSimulatorRoster")
    assert paths[SIMULATOR]["post"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("WebhookSimulatorPayload")
    assert paths[RECEIVE]["post"]["responses"]["202"] is not None
