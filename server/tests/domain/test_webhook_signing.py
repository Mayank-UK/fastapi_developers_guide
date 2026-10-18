"""The HMAC signer/verifier pair: round trip, tamper, replay-window gates.

Topic 14's §3 machinery, pinned directly against the domain functions:
a delivery signed by ``signed_headers`` verifies; every mutation of the
three signed facts (payload, secret, timestamp) is refused; the freshness
window rejects both stale and future-dated deliveries at exactly its
boundary; and hostile signature strings (non-ASCII, stripped scheme)
answer Err rather than raising — the constant-time byte comparison never
turns an attack into a traceback.
"""

from guide.core.errors import FailureKind, http_status_for
from guide.core.result import Err, Ok
from guide.domain.webhooks.signing import (
    DEFAULT_MAX_SKEW_SECONDS,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    sign_payload,
    signed_headers,
    verify_payload,
)

SECRET = "whsec_test_shared_secret"
PAYLOAD = '{"createdAt":"2026-10-15T10:00:00+00:00","data":{"note":"hi"},"id":"evt_1"}'
NOW = 1_760_000_000


def test_signed_headers_round_trip_verifies() -> None:
    headers = signed_headers(secret=SECRET, timestamp=NOW, payload=PAYLOAD)
    result = verify_payload(
        secret=SECRET,
        timestamp=NOW,
        signature=headers[SIGNATURE_HEADER],
        payload=PAYLOAD,
        now=NOW,
    )
    assert isinstance(result, Ok)
    assert result.value.timestamp == NOW
    assert result.value.age_seconds == 0


def test_signature_scheme_is_v1_prefixed_hex_sha256() -> None:
    signature = sign_payload(secret=SECRET, timestamp=NOW, payload=PAYLOAD)
    scheme, mac = signature.split("=", 1)
    assert scheme == "v1"
    assert len(mac) == 64  # SHA-256 hex digest
    int(mac, 16)  # pure hex, no separators


def test_tampered_payload_is_refused_as_unauthorized() -> None:
    signature = sign_payload(secret=SECRET, timestamp=NOW, payload=PAYLOAD)
    result = verify_payload(
        secret=SECRET,
        timestamp=NOW,
        signature=signature,
        payload=PAYLOAD.replace('"hi"', '"HI"'),
        now=NOW,
    )
    assert isinstance(result, Err)
    assert result.failure.kind is FailureKind.UNAUTHORIZED
    assert "signature" in result.failure.message


def test_wrong_secret_is_refused() -> None:
    signature = sign_payload(secret=SECRET, timestamp=NOW, payload=PAYLOAD)
    result = verify_payload(
        secret="whsec_someone_elses_secret",
        timestamp=NOW,
        signature=signature,
        payload=PAYLOAD,
        now=NOW,
    )
    assert isinstance(result, Err)
    assert result.failure.kind is FailureKind.UNAUTHORIZED


def test_re_dated_delivery_is_refused_the_signature_covers_the_timestamp() -> None:
    """A replay cannot refresh an old delivery's clock: the timestamp is signed."""
    signature = sign_payload(secret=SECRET, timestamp=NOW - 3_600, payload=PAYLOAD)
    result = verify_payload(
        secret=SECRET, timestamp=NOW, signature=signature, payload=PAYLOAD, now=NOW
    )
    assert isinstance(result, Err)
    assert result.failure.kind is FailureKind.UNAUTHORIZED


def test_stale_timestamp_is_refused_at_exactly_the_window_edge() -> None:
    timestamp = NOW - DEFAULT_MAX_SKEW_SECONDS
    signature = sign_payload(secret=SECRET, timestamp=timestamp, payload=PAYLOAD)
    # One second inside the window verifies; one second outside is refused.
    inside = verify_payload(
        secret=SECRET, timestamp=timestamp, signature=signature, payload=PAYLOAD, now=NOW
    )
    assert isinstance(inside, Ok)
    assert inside.value.age_seconds == DEFAULT_MAX_SKEW_SECONDS
    outside = verify_payload(
        secret=SECRET,
        timestamp=timestamp - 1,
        signature=signature,
        payload=PAYLOAD,
        now=NOW,
    )
    assert isinstance(outside, Err)
    assert "freshness window" in outside.failure.message


def test_future_dated_timestamp_beyond_the_window_is_refused() -> None:
    timestamp = NOW + DEFAULT_MAX_SKEW_SECONDS + 1
    signature = sign_payload(secret=SECRET, timestamp=timestamp, payload=PAYLOAD)
    result = verify_payload(
        secret=SECRET, timestamp=timestamp, signature=signature, payload=PAYLOAD, now=NOW
    )
    assert isinstance(result, Err)
    assert "freshness window" in result.failure.message


def test_stripped_scheme_prefix_is_a_mismatch_not_a_parse() -> None:
    signature = sign_payload(secret=SECRET, timestamp=NOW, payload=PAYLOAD)
    result = verify_payload(
        secret=SECRET,
        timestamp=NOW,
        signature=signature.removeprefix("v1="),
        payload=PAYLOAD,
        now=NOW,
    )
    assert isinstance(result, Err)
    assert result.failure.kind is FailureKind.UNAUTHORIZED


def test_hostile_signature_strings_answer_err_never_raise() -> None:
    hostile_signatures = (
        "",
        "v1=",
        "v1=not-hex-at-all",
        "v1=" + "é" * 64,
        "scheme-we-have-never-heard-of",
    )
    for hostile in hostile_signatures:
        result = verify_payload(
            secret=SECRET, timestamp=NOW, signature=hostile, payload=PAYLOAD, now=NOW
        )
        assert isinstance(result, Err)
        assert result.failure.kind is FailureKind.UNAUTHORIZED


def test_custom_window_is_honored() -> None:
    timestamp = NOW - 60
    signature = sign_payload(secret=SECRET, timestamp=timestamp, payload=PAYLOAD)
    strict = verify_payload(
        secret=SECRET,
        timestamp=timestamp,
        signature=signature,
        payload=PAYLOAD,
        now=NOW,
        max_skew_seconds=30,
    )
    loose = verify_payload(
        secret=SECRET,
        timestamp=timestamp,
        signature=signature,
        payload=PAYLOAD,
        now=NOW,
        max_skew_seconds=120,
    )
    assert isinstance(strict, Err)
    assert isinstance(loose, Ok)
    assert loose.value.age_seconds == 60


def test_signing_is_deterministic_and_input_sensitive() -> None:
    base = sign_payload(secret=SECRET, timestamp=NOW, payload=PAYLOAD)
    assert sign_payload(secret=SECRET, timestamp=NOW, payload=PAYLOAD) == base
    assert sign_payload(secret=SECRET, timestamp=NOW + 1, payload=PAYLOAD) != base
    assert sign_payload(secret=SECRET + "x", timestamp=NOW, payload=PAYLOAD) != base


def test_receipt_age_is_absolute_for_future_deliveries_too() -> None:
    timestamp = NOW + 10
    signature = sign_payload(secret=SECRET, timestamp=timestamp, payload=PAYLOAD)
    result = verify_payload(
        secret=SECRET, timestamp=timestamp, signature=signature, payload=PAYLOAD, now=NOW
    )
    assert isinstance(result, Ok)
    assert result.value.age_seconds == 10


def test_app_error_from_verdict_is_envelope_ready() -> None:
    """The Err's AppError is the SAME typed error the handlers map — 401 by kind."""
    result = verify_payload(
        secret=SECRET, timestamp=NOW, signature="v1=bad", payload=PAYLOAD, now=NOW
    )
    assert isinstance(result, Err)
    assert http_status_for(result.failure.kind) == 401


def test_headers_carry_the_documented_names() -> None:
    headers = signed_headers(secret=SECRET, timestamp=NOW, payload=PAYLOAD)
    assert set(headers) == {TIMESTAMP_HEADER, SIGNATURE_HEADER}
    assert headers[TIMESTAMP_HEADER] == str(NOW)
