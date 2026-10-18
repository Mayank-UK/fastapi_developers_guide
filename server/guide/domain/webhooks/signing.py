"""HMAC signing for webhook deliveries — the shared-secret proof of sender.

Anyone who discovers a webhook URL can POST to it, so a delivery needs a
credential that rides ON the request: the sender and the receiver share a
secret, and every delivery carries ``x-webhook-timestamp`` plus
``x-webhook-signature`` — an HMAC-SHA256, keyed by the secret, computed
over ``"{timestamp}.{payload}"`` (the timestamp is INSIDE the signed
message, so a captured delivery cannot be re-signed with a fresh clock:
replaying it verbatim trips the freshness window, and re-dating it breaks
the signature).

Two properties matter more than the arithmetic. The signature covers the
EXACT payload bytes the sender put on the wire — a receiver that parses
first and re-serializes later verifies nothing, which is why the receive
endpoint reads the raw body before anything else. And the comparison on
the receiver's side uses :func:`hmac.compare_digest`, the standard
library's constant-time equality: ``==`` on strings returns False at the
first differing byte, so a patient attacker who can measure response
times can harvest a valid signature one byte position at a time — the
constant-time compare closes that timing side channel.

Both halves live here so they cannot drift: ``signed_headers`` builds a
delivery's headers, ``verify_payload`` re-derives and checks them. The
functions are pure — ``now`` is a parameter, not a clock read — so tests
pin exact windows instead of sleeping.
"""

import hashlib
import hmac
from dataclasses import dataclass
from typing import Final

from guide.core.errors import AppError, FailureKind
from guide.core.result import Err, Ok, Result

SIGNATURE_HEADER: Final[str] = "x-webhook-signature"
"""Carries the hex HMAC-SHA256, prefixed with the scheme (``v1=<hex>``)."""

TIMESTAMP_HEADER: Final[str] = "x-webhook-timestamp"
"""Carries the unix seconds the sender signed; freshness is checked at verify."""

SIGNATURE_SCHEME: Final[str] = "v1"
"""Scheme prefix — a version tag, so a rotation to another MAC fits the header."""

DEFAULT_MAX_SKEW_SECONDS: Final[int] = 300
"""The freshness window: five minutes each side of ``now``, the family default."""

DEMO_SHARED_SECRET: Final[str] = "whsec_guide_demo_do_not_rotate"
"""This repo's teaching secret — PUBLIC BY DESIGN so the tour can verify by hand.

A real deployment never does this: secrets live per subscription in config
or a secret manager, are rotated, and are never committed. This one signs
demo deliveries whose whole lesson is that you can recompute the HMAC
yourself, so it is deliberately printed in the simulator's payload.
"""


@dataclass(frozen=True, slots=True)
class WebhookReceipt:
    """What a verified delivery proves: when it was signed, how old it arrived."""

    timestamp: int
    age_seconds: int


def _mac(*, secret: str, message: str) -> str:
    """Hex HMAC-SHA256 of ``message`` keyed by ``secret`` (the single derivation)."""
    digest = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()


def sign_payload(*, secret: str, timestamp: int, payload: str) -> str:
    """Sign one delivery: ``v1=`` + hex HMAC-SHA256 over ``"{timestamp}.{payload}"``."""
    return f"{SIGNATURE_SCHEME}={_mac(secret=secret, message=f'{timestamp}.{payload}')}"


def signed_headers(*, secret: str, timestamp: int, payload: str) -> dict[str, str]:
    """The two headers a signed delivery carries — timestamp plain, MAC prefixed."""
    return {
        TIMESTAMP_HEADER: str(timestamp),
        SIGNATURE_HEADER: sign_payload(secret=secret, timestamp=timestamp, payload=payload),
    }


def verify_payload(
    *,
    secret: str,
    timestamp: int,
    signature: str,
    payload: str,
    now: int,
    max_skew_seconds: int = DEFAULT_MAX_SKEW_SECONDS,
) -> Result[WebhookReceipt]:
    """Check one delivery against the secret; ``Ok(receipt)`` or ``Err(unauthorized)``.

    Two gates, cheapest first. Freshness: the signed timestamp must sit
    within ``max_skew_seconds`` of ``now`` on either side — a delivery
    older than the window is a replay candidate and a future-dated one is
    a clock-skew candidate, and both are refused before any cryptography
    runs. Authenticity: the expected signature is re-derived over the
    exact ``payload`` bytes and compared with :func:`hmac.compare_digest`
    on UTF-8 bytes (the byte form never raises on hostile header values,
    where the two-``str`` form requires pure ASCII).

    The two failure reasons are distinct here for teaching; production
    receivers often collapse them into one generic ``invalid signature``
    so the answer itself leaks nothing about which gate fired.
    """
    age_seconds = now - timestamp
    if abs(age_seconds) > max_skew_seconds:
        return Err(
            AppError(
                FailureKind.UNAUTHORIZED,
                f"Webhook timestamp {timestamp} is outside the ±{max_skew_seconds}s "
                f"freshness window of {now}.",
            )
        )
    expected = sign_payload(secret=secret, timestamp=timestamp, payload=payload)
    if not hmac.compare_digest(expected.encode("utf-8"), signature.encode("utf-8")):
        return Err(
            AppError(
                FailureKind.UNAUTHORIZED,
                "Webhook signature mismatch: the payload does not match the "
                "shared secret.",
            )
        )
    return Ok(WebhookReceipt(timestamp=timestamp, age_seconds=abs(age_seconds)))
