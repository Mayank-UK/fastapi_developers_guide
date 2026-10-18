"""Webhook simulator: one registered subscription, one fired event, the whole walk.

``GET /api/demo/api/webhook-simulator`` and ``POST /api/demo/api/webhook-simulator``
serve these payloads — topic 14's demo. The caller registers a subscription
by picking a target scenario and fires an event; the payload then walks
the FULL simulated delivery lifecycle the real sender machinery would run:

- every attempt with its own signing timestamp (``fired_at`` plus that
  attempt's backoff offset) and the HMAC-SHA256 signature computed over
  EXACTLY that attempt's timestamp + body — a retry is a new HTTP request,
  so it gets a fresh signature;
- the scheduled-at offsets straight from the pure ``RetryPolicy`` engine;
- each attempt's outcome and the final verdict — delivered, or the
  dead-letter entry the exhausted budget mints;
- a ready-to-fire ``deliverByHand`` round (headers + the exact signed
  body string) so the caller can ALSO deliver for real to this repo's
  live receive endpoint and watch the §5 verifier answer 202 — or tamper
  with one byte and watch it answer 401.

The builder is pure: ids, clock, and vocabulary arrive as parameters (the
router mints identity, like every adapter in this guide), no I/O happens
here, and the body string is canonical JSON so the same inputs always
produce byte-identical signatures.
"""

import json
from datetime import UTC, datetime
from typing import Annotated, Final, Literal

from pydantic import Field

from guide.core.serialization import CamelModel
from guide.domain.webhooks.retry import (
    DEFAULT_RETRY_POLICY,
    AttemptStep,
    DeliveryWalk,
    RetryPolicy,
    walk_delivery,
)
from guide.domain.webhooks.signing import sign_payload, signed_headers

WebhookScenario = Literal["immediate-2xx", "always-500", "flaky-then-success"]
"""The three target behaviors the simulator can deliver against."""

WebhookEventType = Literal["post.published", "post.updated", "comment.created"]
"""The event catalog — a closed vocabulary, like every Literal in this guide."""

WEBHOOK_EVENT_TYPES: Final[tuple[WebhookEventType, ...]] = (
    "post.published",
    "post.updated",
    "comment.created",
)
"""Runtime spelling of the catalog (tests pin it to the Literal)."""

SIMULATED_TARGET_HOST: Final[str] = "https://client.example/hooks"
"""The fictional receiver this simulator delivers to; this repo's real one is local."""

_SCENARIO_SUCCESS: Final[dict[WebhookScenario, int | None]] = {
    "immediate-2xx": 1,
    "always-500": None,
    "flaky-then-success": 3,
}
"""Scenario → the attempt the target would finally answer 2xx on (None: never)."""


class WebhookSimulatorRequest(CamelModel):
    """One simulation round: register a subscription (scenario) + fire an event."""

    event_type: WebhookEventType
    scenario: WebhookScenario
    note: Annotated[str, Field(max_length=200)] = ""


class ScenarioCard(CamelModel):
    """One target scenario as the roster offers it."""

    id: WebhookScenario
    label: str
    description: str
    success_on_attempt: int | None


class PolicyCard(CamelModel):
    """The retry policy facts the simulation runs under — schedule included."""

    max_attempts: int
    base_delay_seconds: int
    backoff_factor: int
    offsets: list[int]


class WebhookSimulatorRoster(CamelModel):
    """Wire shape of ``GET /api/demo/api/webhook-simulator``."""

    scenarios: list[ScenarioCard]
    event_types: list[WebhookEventType]
    secret: str
    receive_endpoint: str
    policy: PolicyCard
    reasoning: str


class SubscriptionFact(CamelModel):
    """The subscription the round registered — the receiver's own address."""

    id: str
    url: str
    scenario: WebhookScenario


class EventFact(CamelModel):
    """The fired event: identity, type, and the payload body as an object."""

    id: str
    type: str
    body: dict[str, object]


class AttemptFact(CamelModel):
    """One delivery attempt: when, signed how, answered with what."""

    attempt: int
    offset_seconds: int
    timestamp: int
    signature: str
    status: int
    outcome: Literal["delivered", "retry-scheduled", "exhausted"]


class DeadLetterFact(CamelModel):
    """The dead-letter entry an exhausted attempt budget mints."""

    event_id: str
    attempts: int
    last_status: int
    final_offset_seconds: int
    reason: str


class SignedDelivery(CamelModel):
    """A ready-to-fire REAL round at this repo's live receive endpoint."""

    method: Literal["POST"]
    url: str
    headers: dict[str, str]
    body: str


class WebhookReceiptPayload(CamelModel):
    """Wire shape of ``POST /api/demo/api/webhooks/receive`` (202 Accepted).

    The receipt is deliberately thin: the receiver's whole job was to
    verify the signature over the raw bytes and say yes FAST — processing
    happens after the acknowledgment, which is what receiving well means.
    """

    event_id: str | None
    received_at: int
    age_seconds: int
    detail: str


class WebhookSimulatorPayload(CamelModel):
    """Wire shape of ``POST /api/demo/api/webhook-simulator``."""

    subscription: SubscriptionFact
    event: EventFact
    secret: str
    policy: PolicyCard
    attempts: list[AttemptFact]
    verdict: Literal["delivered", "dead-lettered"]
    delivered_at_offset: int | None
    dead_letter: DeadLetterFact | None
    deliver_by_hand: SignedDelivery
    reasoning: str


def _policy_card(policy: RetryPolicy) -> PolicyCard:
    return PolicyCard(
        max_attempts=policy.max_attempts,
        base_delay_seconds=policy.base_delay_seconds,
        backoff_factor=policy.backoff_factor,
        offsets=policy.attempt_offsets(),
    )


def _event_body(*, event_id: str, event_type: str, fired_at: int, note: str) -> str:
    """The canonical body string: sorted keys, no incidental whitespace.

    The signature covers THESE bytes, so the body is serialized once here
    and everything downstream (attempt signatures, ``deliverByHand``) uses
    this exact string — never a re-serialization of the parsed object.
    """
    payload = {
        "createdAt": datetime.fromtimestamp(fired_at, tz=UTC).isoformat(),
        "data": {"note": note if note else "the event's facts would live here"},
        "id": event_id,
        "type": event_type,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _attempt_fact(
    step: AttemptStep, *, timestamp: int, signature: str, max_attempts: int
) -> AttemptFact:
    outcome: Literal["delivered", "retry-scheduled", "exhausted"]
    if step.delivered:
        outcome = "delivered"
    elif step.attempt < max_attempts:
        outcome = "retry-scheduled"
    else:
        outcome = "exhausted"
    return AttemptFact(
        attempt=step.attempt,
        offset_seconds=step.offset_seconds,
        timestamp=timestamp,
        signature=signature,
        status=step.status,
        outcome=outcome,
    )


def build_webhook_simulator_roster(
    *, secret: str, receive_endpoint: str, policy: RetryPolicy = DEFAULT_RETRY_POLICY
) -> WebhookSimulatorRoster:
    """Shape the roster (pure): scenarios, catalog, secret, endpoint, schedule."""
    cards = [
        ScenarioCard(
            id="immediate-2xx",
            label="Healthy receiver",
            description=(
                "Answers 200 on the first attempt — the happy path: one "
                "delivery, one signature, no retries."
            ),
            success_on_attempt=1,
        ),
        ScenarioCard(
            id="always-500",
            label="Broken receiver",
            description=(
                "Answers 500 on every attempt — the budget runs out and the "
                "event lands in the dead-letter queue."
            ),
            success_on_attempt=None,
        ),
        ScenarioCard(
            id="flaky-then-success",
            label="Flaky receiver",
            description=(
                "Fails twice, then answers 200 on the third attempt — the "
                "backoff curve does its job and the event still lands."
            ),
            success_on_attempt=3,
        ),
    ]
    offsets = policy.attempt_offsets()
    return WebhookSimulatorRoster(
        scenarios=cards,
        event_types=list(WEBHOOK_EVENT_TYPES),
        secret=secret,
        receive_endpoint=receive_endpoint,
        policy=_policy_card(policy),
        reasoning=(
            "Register a subscription by picking a scenario, fire an event, and "
            "the simulator walks every delivery attempt with its real HMAC "
            f"signature. The policy allows {policy.max_attempts} attempts at "
            f"offsets {offsets} seconds — exponential backoff, deliberately "
            "jitter-free so the schedule is exact. The secret below is public "
            "by design (this is the teaching point): recompute the MAC "
            "yourself, or fire deliverByHand at the live receive endpoint."
        ),
    )


def build_webhook_simulator_payload(
    *,
    subscription_id: str,
    event_id: str,
    fired_at: int,
    event_type: str,
    scenario: WebhookScenario,
    note: str,
    secret: str,
    receive_endpoint: str,
    policy: RetryPolicy = DEFAULT_RETRY_POLICY,
) -> WebhookSimulatorPayload:
    """Walk the full simulated lifecycle (pure): attempts, verdict, DLQ, handoff."""
    body = _event_body(event_id=event_id, event_type=event_type, fired_at=fired_at, note=note)
    walk: DeliveryWalk = walk_delivery(
        policy, event_id=event_id, success_on_attempt=_SCENARIO_SUCCESS[scenario]
    )
    attempts = [
        _attempt_fact(
            step,
            timestamp=fired_at + step.offset_seconds,
            signature=sign_payload(
                secret=secret, timestamp=fired_at + step.offset_seconds, payload=body
            ),
            max_attempts=policy.max_attempts,
        )
        for step in walk.steps
    ]
    dead_letter = (
        DeadLetterFact(
            event_id=walk.dead_letter.event_id,
            attempts=walk.dead_letter.attempts,
            last_status=walk.dead_letter.last_status,
            final_offset_seconds=walk.dead_letter.final_offset_seconds,
            reason=walk.dead_letter.reason,
        )
        if walk.dead_letter is not None
        else None
    )
    hand_headers = signed_headers(secret=secret, timestamp=fired_at, payload=body)
    hand = SignedDelivery(
        method="POST",
        url=receive_endpoint,
        headers={"content-type": "application/json", **hand_headers},
        body=body,
    )
    verdict_line = (
        f"Delivered on attempt {walk.attempts_used} (offset +{walk.delivered_at_offset}s)."
        if walk.verdict == "delivered"
        else (
            f"Dead-lettered after {policy.max_attempts} attempts (last at "
            f"+{policy.attempt_offsets()[-1]}s) — the queue entry is in this payload."
        )
    )
    return WebhookSimulatorPayload(
        subscription=SubscriptionFact(
            id=subscription_id,
            url=f"{SIMULATED_TARGET_HOST}/{subscription_id}",
            scenario=scenario,
        ),
        event=EventFact(
            id=event_id,
            type=event_type,
            body=dict(json.loads(body)),
        ),
        secret=secret,
        policy=_policy_card(policy),
        attempts=attempts,
        verdict=walk.verdict,
        delivered_at_offset=walk.delivered_at_offset,
        dead_letter=dead_letter,
        deliver_by_hand=hand,
        reasoning=(
            f"Subscription {subscription_id} ({scenario}) fired {event_type} as "
            f"{event_id}: {len(attempts)} attempt(s) at offsets "
            f"{[fact.offset_seconds for fact in attempts]}s, each signed over "
            "its own timestamp + the exact body bytes. "
            + verdict_line
            + " deliverByHand carries a real signed round — fire it at "
            f"{receive_endpoint} for a 202, tamper with one byte for the 401."
        ),
    )
