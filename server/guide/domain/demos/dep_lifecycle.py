"""Dep-lifecycle demo payloads: what a handler CAN know about its own span.

``GET /api/demo/dep/lifecycle`` answers with these payloads — the span
facts that exist BEFORE the response leaves (span id, setup timestamp, how
far into the span the handler ran) plus the honest confession of what has
NOT happened yet: the teardown, which only runs after these bytes are gone.
The sibling ``/lifecycle/log`` endpoint (serving the span instrument's
``SpanLogSnapshot``) is where the full ordering shows up.

The builder is pure: facts in, payload out — no I/O, no state.
"""

from typing import Final

from guide.core.serialization import CamelModel

PENDING_AFTER_RESPONSE: Final[tuple[str, ...]] = ("teardown",)
"""What cannot be in this body: it happens after the body is on the wire."""


class DepLifecyclePayload(CamelModel):
    """Wire shape of ``GET /api/demo/dep/lifecycle`` (camelCase)."""

    span_id: str
    setup_at: str
    """ISO-8601 UTC timestamp the dependency's setup recorded."""

    handler_offset_ms: int
    """How far into the span the handler ran (ms after setup)."""

    pending_events: list[str]
    """Span beats that had NOT run when this body was built: the teardown."""


def build_lifecycle_payload(
    span_id: str, setup_at: str, handler_offset_ms: int
) -> DepLifecyclePayload:
    """Assemble the span facts a handler can honestly report about itself."""
    return DepLifecyclePayload(
        span_id=span_id,
        setup_at=setup_at,
        handler_offset_ms=handler_offset_ms,
        pending_events=list(PENDING_AFTER_RESPONSE),
    )
