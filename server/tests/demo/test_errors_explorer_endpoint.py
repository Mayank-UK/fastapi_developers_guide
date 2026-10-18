"""The errors explorer endpoints — the panel and the scenario-honoring probe.

The panel must serve the taxonomy's own tables (eight kinds, exact
statuses, the taxonomy's default messages) with six LIVE triggers against
real endpoints and two honest RECIPE rows. The probe is the scenario
store's first live failure-injection reader: healthy at none, a genuine
unhandled RuntimeError at error (the outermost handler answers the
generic 500 envelope — no traceback on the wire, request id on header and
body), and a delayed 200 at latency.
"""

from time import monotonic

from fastapi import FastAPI
from fastapi.testclient import TestClient

PANEL_PATH = "/api/demo/errors"
PROBE_PATH = "/api/demo/errors/probe"
SCENARIO_PATH = "/api/demo/scenario"

EXPECTED_KINDS: list[tuple[str, int, str]] = [
    ("validation_failed", 422, "live"),
    ("unauthorized", 401, "live"),
    ("forbidden", 403, "live"),
    ("not_found", 404, "live"),
    ("conflict", 409, "recipe"),
    ("rate_limited", 429, "live"),
    ("service_unavailable", 503, "recipe"),
    ("internal", 500, "live"),
]


# ── The panel ─────────────────────────────────────────────────────────────────


def test_panel_serves_the_eight_kinds_from_the_taxonomy(client: TestClient) -> None:
    body = client.get(PANEL_PATH).json()
    rows = [(row["kind"], row["httpStatus"], row["trigger"]["mode"]) for row in body["kinds"]]
    assert rows == EXPECTED_KINDS
    by_kind = {row["kind"]: row for row in body["kinds"]}
    assert by_kind["not_found"]["defaultMessage"] == "Resource not found."
    assert by_kind["internal"]["defaultMessage"] == "Internal server error."
    # Every row names its raiser and its log event — no orphan vocabulary.
    for row in body["kinds"]:
        assert row["raisedBy"]
        assert row["loggedAs"]
        assert row["trigger"]["method"]
        assert row["trigger"]["path"]
        assert row["trigger"]["note"]


def test_panel_marks_the_two_recipe_kinds_honestly(client: TestClient) -> None:
    body = client.get(PANEL_PATH).json()
    by_kind = {row["kind"]: row for row in body["kinds"]}
    assert "never sends" in by_kind["conflict"]["trigger"]["note"]
    assert "store down" in by_kind["service_unavailable"]["trigger"]["note"]
    # The scenario sub-panel names the real endpoints and all three modes.
    assert body["scenario"]["getEndpoint"] == SCENARIO_PATH
    assert body["scenario"]["patchEndpoint"] == SCENARIO_PATH
    assert list(body["scenario"]["modes"]) == ["none", "error", "latency"]
    assert body["probe"]["probeEndpoint"] == PROBE_PATH


# ── The probe: the scenario's first live failure reader ───────────────────────


def test_probe_answers_healthy_at_none(client: TestClient) -> None:
    response = client.get(PROBE_PATH)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["injectFailure"] == "none"
    assert "500" in body["detail"]


def test_probe_with_error_injection_is_the_generic_500_envelope(
    app: FastAPI, client: TestClient
) -> None:
    # TestClient re-raises unhandled exceptions by default; the probe's
    # raise is SUPPOSED to reach the outermost handler, so the injected
    # round rides a client that lets ServerErrorMiddleware answer.
    answering = TestClient(app, raise_server_exceptions=False)
    patched = client.patch(SCENARIO_PATH, json={"injectFailure": "error"})
    assert patched.status_code == 200
    assert patched.json()["injectFailure"] == "error"

    response = answering.get(PROBE_PATH)
    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal"
    # Generic message only — the raise's text and type never reach the wire.
    assert error["message"] == "Internal server error."
    assert "RuntimeError" not in response.text
    assert "scenario-injected" not in response.text
    # The request id survives unwinding: on the header AND in the body.
    assert response.headers["x-request-id"] == error["requestId"]


def test_probe_returns_to_healthy_after_the_reset(app: FastAPI) -> None:
    answering = TestClient(app, raise_server_exceptions=False)
    assert answering.patch(SCENARIO_PATH, json={"injectFailure": "error"}).status_code == 200
    assert answering.get(PROBE_PATH).status_code == 500
    reset = answering.patch(SCENARIO_PATH, json={"injectFailure": "none"})
    assert reset.status_code == 200
    response = answering.get(PROBE_PATH)
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_probe_with_latency_injection_answers_slow_but_healthy(
    client: TestClient,
) -> None:
    client.patch(SCENARIO_PATH, json={"injectFailure": "latency"})
    started = monotonic()
    response = client.get(PROBE_PATH)
    elapsed = monotonic() - started
    assert response.status_code == 200
    assert response.json()["injectFailure"] == "latency"
    assert elapsed >= 1.0, "the latency injection must actually delay the answer"
