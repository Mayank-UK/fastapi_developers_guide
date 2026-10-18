"""The webhook simulator builder: pure, canonical, and honest per scenario.

The demo's payload IS the lesson, so the builder is pinned hard: the
roster offers the three scenarios and the exact schedule, the body
string is canonical JSON (sorted keys, no whitespace), every attempt's
signature verifies against the domain verifier at that attempt's own
timestamp, ``deliverByHand`` is a genuinely fireable signed round, and
identical inputs produce identical payloads — no hidden clock, no I/O.
"""

import json

from guide.core.result import Ok
from guide.domain.demos.webhook_simulator import (
    WEBHOOK_EVENT_TYPES,
    build_webhook_simulator_payload,
    build_webhook_simulator_roster,
)
from guide.domain.webhooks.signing import (
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    sign_payload,
    verify_payload,
)

SECRET = "whsec_builder_test_secret"
RECEIVE = "/api/demo/api/webhooks/receive"
FIRED_AT = 1_760_000_000


def _build(scenario: str, note: str = "hello from the test"):
    return build_webhook_simulator_payload(
        subscription_id="sub_abc123",
        event_id="evt_def456",
        fired_at=FIRED_AT,
        event_type="post.published",
        scenario=scenario,  # type: ignore[arg-type]
        note=note,
        secret=SECRET,
        receive_endpoint=RECEIVE,
    )


def test_roster_offers_three_scenarios_and_the_exact_schedule() -> None:
    roster = build_webhook_simulator_roster(secret=SECRET, receive_endpoint=RECEIVE)
    assert [card.id for card in roster.scenarios] == [
        "immediate-2xx",
        "always-500",
        "flaky-then-success",
    ]
    assert [card.success_on_attempt for card in roster.scenarios] == [1, None, 3]
    assert roster.event_types == list(WEBHOOK_EVENT_TYPES)
    assert roster.secret == SECRET
    assert roster.receive_endpoint == RECEIVE
    assert roster.policy.offsets == [0, 1, 3, 7, 15]
    assert roster.policy.max_attempts == 5
    assert "jitter-free" in roster.reasoning


def test_builder_is_pure_identical_inputs_identical_payloads() -> None:
    first = _build("flaky-then-success")
    second = _build("flaky-then-success")
    assert first.model_dump() == second.model_dump()


def test_immediate_scenario_delivers_once_at_offset_zero() -> None:
    payload = _build("immediate-2xx")
    assert payload.verdict == "delivered"
    assert payload.delivered_at_offset == 0
    assert payload.dead_letter is None
    assert len(payload.attempts) == 1
    attempt = payload.attempts[0]
    assert (attempt.attempt, attempt.offset_seconds, attempt.status, attempt.outcome) == (
        1,
        0,
        200,
        "delivered",
    )


def test_always_500_scenario_spends_the_budget_and_mints_a_dead_letter() -> None:
    payload = _build("always-500")
    assert payload.verdict == "dead-lettered"
    assert payload.delivered_at_offset is None
    assert [attempt.status for attempt in payload.attempts] == [500] * 5
    assert [attempt.outcome for attempt in payload.attempts] == [
        "retry-scheduled",
        "retry-scheduled",
        "retry-scheduled",
        "retry-scheduled",
        "exhausted",
    ]
    dead = payload.dead_letter
    assert dead is not None
    assert dead.event_id == "evt_def456"
    assert dead.attempts == 5
    assert dead.last_status == 500
    assert dead.final_offset_seconds == 15


def test_flaky_scenario_lands_on_attempt_three_at_offset_three() -> None:
    payload = _build("flaky-then-success")
    assert payload.verdict == "delivered"
    assert len(payload.attempts) == 3
    assert [attempt.offset_seconds for attempt in payload.attempts] == [0, 1, 3]
    assert [attempt.status for attempt in payload.attempts] == [500, 500, 200]
    assert payload.attempts[2].outcome == "delivered"
    assert payload.delivered_at_offset == 3


def test_every_attempt_signature_verifies_at_its_own_timestamp() -> None:
    payload = _build("always-500")
    body = payload.deliver_by_hand.body
    for attempt in payload.attempts:
        assert attempt.timestamp == FIRED_AT + attempt.offset_seconds
        result = verify_payload(
            secret=SECRET,
            timestamp=attempt.timestamp,
            signature=attempt.signature,
            payload=body,
            now=attempt.timestamp,
        )
        assert isinstance(result, Ok), f"attempt {attempt.attempt} signature failed"


def test_attempt_signatures_differ_per_attempt_and_recompute_exactly() -> None:
    payload = _build("always-500")
    body = payload.deliver_by_hand.body
    signatures = set()
    for attempt in payload.attempts:
        expected = sign_payload(
            secret=SECRET, timestamp=FIRED_AT + attempt.offset_seconds, payload=body
        )
        assert attempt.signature == expected
        signatures.add(attempt.signature)
    assert len(signatures) == 5  # fresh timestamp per attempt → fresh signature


def test_deliver_by_hand_is_a_fireable_signed_round() -> None:
    payload = _build("immediate-2xx", note="hand round")
    hand = payload.deliver_by_hand
    assert hand.method == "POST"
    assert hand.url == RECEIVE
    assert hand.headers["content-type"] == "application/json"
    assert hand.headers[TIMESTAMP_HEADER] == str(FIRED_AT)
    expected = sign_payload(secret=SECRET, timestamp=FIRED_AT, payload=hand.body)
    assert hand.headers[SIGNATURE_HEADER] == expected
    result = verify_payload(
        secret=SECRET,
        timestamp=FIRED_AT,
        signature=hand.headers[SIGNATURE_HEADER],
        payload=hand.body,
        now=FIRED_AT,
    )
    assert isinstance(result, Ok)


def test_event_body_carries_the_envelope_and_the_caller_note() -> None:
    payload = _build("immediate-2xx", note="a caller note")
    assert payload.event.id == "evt_def456"
    assert payload.event.type == "post.published"
    assert payload.event.body["id"] == "evt_def456"
    assert payload.event.body["type"] == "post.published"
    assert payload.event.body["data"] == {"note": "a caller note"}
    assert payload.event.body["createdAt"]
    # The parsed body and the signed body string agree.
    assert json.loads(payload.deliver_by_hand.body) == payload.event.body


def test_empty_note_gets_the_default_data_text() -> None:
    payload = _build("immediate-2xx", note="")
    assert payload.event.body["data"] == {"note": "the event's facts would live here"}


def test_subscription_names_the_simulated_target_and_scenario() -> None:
    payload = _build("flaky-then-success")
    assert payload.subscription.id == "sub_abc123"
    assert payload.subscription.url == "https://client.example/hooks/sub_abc123"
    assert payload.subscription.scenario == "flaky-then-success"


def test_wire_keys_are_camel_case() -> None:
    payload = _build("immediate-2xx").model_dump(mode="json", by_alias=True)
    assert "deliveredAtOffset" in payload
    assert "deliverByHand" in payload
    assert "offsetSeconds" in payload["attempts"][0]
    assert "successOnAttempt" in (
        build_webhook_simulator_roster(secret=SECRET, receive_endpoint=RECEIVE)
        .model_dump(mode="json", by_alias=True)["scenarios"][0]
    )
