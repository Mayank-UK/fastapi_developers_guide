"""The reliability-breaker endpoint (topic 39, area ``reliability``).

Pins the wire contract (GET /api/demo/reliability/breaker): the policy
rows, the eleven-step walk (two healthy calls, three failing ones with the
third tripping, a fail-fast at the trip and at the timeout's midpoint, two
logical clock advances, the half-open probe, the recovery receipt), the
full-cycle state line, and the fail-fast vs real-failure latency contrast
computed from the measured rows. Latency asserts are RELATIVE or
generously floored (the 35/38 precedent: shared hardware is noisy) and the
bounded-cost contract is pinned — the whole panel stays well under a
second of real time because the open timeout elapses on the injected
clock, never by sleeping.
"""

from fastapi.testclient import TestClient

BREAKER_PATH = "/api/demo/reliability/breaker"

POLICY_ROW_IDS = ["failure-threshold", "open-timeout", "half-open-successes", "failure-latency"]
LATENCY_ROW_IDS = ["fail-fast", "real-failure", "contrast"]


def test_serves_the_policy_rows_and_the_full_cycle_line(client: TestClient) -> None:
    response = client.get(BREAKER_PATH)
    assert response.status_code == 200
    body = response.json()
    assert [row["id"] for row in body["policy"]] == POLICY_ROW_IDS
    assert "3" in next(r for r in body["policy"] if r["id"] == "failure-threshold")["value"]
    assert body["statesVisited"] == ["closed", "open", "half_open", "closed"]
    assert "closed → open → half-open → closed" in body["stateLine"]
    assert "fast-failed" in body["stateLine"]


def test_the_walk_is_eleven_steps_with_the_trip_at_five(client: TestClient) -> None:
    body = client.get(BREAKER_PATH).json()
    calls = body["calls"]
    assert [c["step"] for c in calls] == list(range(1, 12))
    assert [(c["action"], c["outcome"]) for c in calls] == [
        ("call", "success"),
        ("call", "success"),
        ("call", "failure"),
        ("call", "failure"),
        ("call", "failure"),
        ("call", "rejected"),
        ("advance-clock", "clock-advanced"),
        ("call", "rejected"),
        ("advance-clock", "clock-advanced"),
        ("call", "success"),
        ("call", "success"),
    ]
    # The failure count climbs to the threshold of three and the third names the trip.
    assert [c["consecutiveFailures"] for c in calls if c["outcome"] == "failure"] == [1, 2, 3]
    assert "reached the threshold" in calls[4]["reason"]
    # Clock rows carry no admission verdict.
    assert all(c["admitted"] is None for c in calls if c["action"] == "advance-clock")


def test_fail_fast_never_touches_the_dependency_and_carries_the_countdown(
    client: TestClient,
) -> None:
    body = client.get(BREAKER_PATH).json()
    rejected = [c for c in body["calls"] if c["outcome"] == "rejected"]
    assert len(rejected) == 2
    assert all(c["dependencyTouched"] is False for c in rejected)
    assert all(c["elapsedMs"] < 5.0 for c in rejected), "a rejection is instant"
    assert rejected[0]["retryAfterS"] == 2.0, "the full open timeout right after the trip"
    assert rejected[1]["retryAfterS"] == 1.0, "half of it after the 1s logical advance"
    assert "fast-fail" in rejected[0]["reason"]


def test_the_probe_is_marked_and_the_recovery_closes(client: TestClient) -> None:
    body = client.get(BREAKER_PATH).json()
    probe = body["calls"][9]
    assert probe["stateBefore"] == "half_open"
    assert probe["isProbe"] is True
    assert probe["outcome"] == "success"
    assert "probe succeeded" in probe["reason"]
    receipt = body["calls"][10]
    assert receipt["stateBefore"] == "closed", "the call after recovery flows normally"
    assert receipt["isProbe"] is False


def test_the_latency_contrast_is_measured_not_asserted(client: TestClient) -> None:
    body = client.get(BREAKER_PATH).json()
    rows = {row["id"]: row for row in body["latency"]}
    assert list(rows) == LATENCY_ROW_IDS
    fail_fast_ms = float(rows["fail-fast"]["value"].split("ms")[0])
    real_failure_ms = float(rows["real-failure"]["value"].split("ms")[0])
    # The 60ms failure budget is real wall time (small overshoot); the rejections are ~0ms.
    assert fail_fast_ms < 5.0, f"fail-fast must be ~0ms, got {fail_fast_ms}ms"
    assert 40.0 <= real_failure_ms <= 200.0, (
        f"the real failure latency rides the bounded 60ms, got {real_failure_ms}ms"
    )
    assert real_failure_ms > 10 * fail_fast_ms, "the contrast must be overwhelming"
    assert "2 rejected calls skipped 120ms" in rows["contrast"]["value"]


def test_the_walk_is_bounded_and_the_honesty_note_names_the_clock(
    client: TestClient,
) -> None:
    response = client.get(BREAKER_PATH)
    assert response.elapsed.total_seconds() < 5.0, (
        "the open timeout elapses on the injected clock — only 3x60ms is real"
    )
    note = response.json()["honestyNote"]
    assert "injected" in note
    assert "60ms" in note
    assert "fresh instance per run" in note


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][BREAKER_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("BreakerPanel")
