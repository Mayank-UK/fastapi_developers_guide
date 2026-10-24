"""Trace-correlation payload: one fan-out, three real rounds, one ring.

``GET /api/demo/obs/trace`` serves this payload INLINE in topic 33's
OTel-tracing section. The point is request-id/trace correlation on REAL
data, in the architecture tracer's footsteps: the engine drives three REAL
internal requests through the live app at the ASGI boundary (a hand-built
``http`` scope handed to the app callable — no socket, no staged
responses), each round carrying an inbound ``x-request-id`` DERIVED from
this panel's own request id (the trace root): shared prefix, per-round
suffix — a miniature of how real trace context propagates (one trace id,
per-span ids).

Each round's id is then looked for in three places, and the payload pins
the agreement: the ``x-request-id`` header the round's response echoes,
the ``requestId`` inside the error envelope a failed round produced, and
the log rows the ring holds for that id — with topic 33's access-log layer
in the stack, every round leaves an ``http_request`` row, and the two
failed rounds leave their failure row beside it. Two rows, one id: that
IS correlation. The healthy round deliberately demonstrates the opposite
signal — success is not logged in this app, so its lone access-log row
with no failure row beside it is the good-news shape.

Honesty rules the shape (the arch-tracer posture): only the round's two
ASGI-boundary beats are measured (request-enter to response-start, and to
the final body flush); no per-hop timings are invented; and OTel itself is
NOT a dependency of this repo — the request-id mechanism is what really
runs here. What the OpenTelemetry SDK would add is the section's subject,
not this payload's claim.
"""

import json
import time
from typing import Any, Final

from starlette.types import ASGIApp, Message, Scope

from guide.core.errors import AppError, FailureKind
from guide.core.logging import recent_log
from guide.core.serialization import CamelModel
from guide.domain.demos.obs_viewer import CapturedEvent, captured_event

ROOT_ID_PREFIX_LIMIT: Final[int] = 24
"""The root id's slice child ids derive from — bounded so a hostile
200-char inbound id cannot overflow the 200-char header cap downstream."""

REQUEST_ID_HEADER_LOWER: Final = "x-request-id"
"""The header both directions of a traced round ride on (ASGI: lowercase)."""

DERIVED_ID_CONVENTION: Final = (
    "child ids are '<root-prefix>-<label>': the shared prefix is this panel's "
    "own request id (the trace root), the suffix names the round — one trace, "
    "one id per span, the same shape W3C trace context standardizes"
)


class TraceRound(CamelModel):
    """One real internal request, its outcome, and its correlated log rows."""

    label: str
    request_line: str
    inbound_request_id: str
    status: int
    first_byte_ms: float
    """Request-enter to http.response.start — status + headers ready."""

    duration_ms: float
    """Request-enter to the final body flush, measured at the ASGI boundary."""

    header_echoed: bool
    """The response's x-request-id equals the inbound id (the round trip)."""

    envelope_code: str | None
    """The error envelope's code (None on 2xx — no envelope to correlate)."""

    envelope_request_id: str | None
    """The error envelope's requestId; must equal the inbound id when set."""

    log_events: list[CapturedEvent]
    """The ring's real rows carrying this round's id, oldest first."""

    note: str


class TraceFanout(CamelModel):
    """Wire shape of ``GET /api/demo/obs/trace`` — the fan-out's contract."""

    root_request_id: str
    derived_id_convention: str
    rounds: list[TraceRound]
    correlation_note: str
    honesty_note: str


CORRELATION_NOTE: Final = (
    "Read one failed round top to bottom: the SAME id appears in the "
    "response header it echoed, the error envelope's requestId, and every "
    "log row it produced (the access-log line and the failure line). Three "
    "places, one id — that is what correlation means: any one of them "
    "retrieves the others."
)

HONESTY_NOTE: Final = (
    "The rounds are real internal requests driven through this very app at "
    "the ASGI boundary; only the two boundary beats carry measured "
    "milliseconds. OpenTelemetry is NOT a dependency here — the request-id "
    "mechanism you see running is the repo's real one, and it is the same "
    "idea OTel's trace context implements (shared trace id, per-span ids, "
    "header propagation); what the SDK would add is automatic span trees "
    "and exporters, taught in the section above."
)

_OK_NOTE: Final = (
    "A healthy round leaves exactly one row — the access-log line — and no "
    "failure row: success is not logged by design, so the absence of a "
    "second row is the signal that nothing needed a human. The echoed "
    "header proves the round ran; the quiet log stream is the good news."
)

_FAILED_NOTE: Final = (
    "One id, three correlations: the echoed response header, the error "
    "envelope's requestId, and this round's log rows — the access-log line "
    "and the failure line the shared id ties together."
)


class _RoundRecording:
    """What one real internal request actually did (raw, pre-narration)."""

    def __init__(
        self,
        *,
        status: int,
        headers: dict[str, str],
        body: bytes,
        start_offset_ms: float,
        complete_offset_ms: float,
    ) -> None:
        self.status = status
        self.headers = headers
        self.body = body
        self.start_offset_ms = start_offset_ms
        self.complete_offset_ms = complete_offset_ms

    def header(self, name: str) -> str | None:
        """One response header (lowercase name), or None when absent."""
        return self.headers.get(name)

    def envelope(self) -> dict[str, Any]:
        """The parsed error envelope, or {} when the body is not one."""
        try:
            body = json.loads(self.body.decode("utf-8"))
        except ValueError:
            return {}
        if not isinstance(body, dict):
            return {}
        error = body.get("error")
        return error if isinstance(error, dict) else {}


async def _drive_round(
    app: ASGIApp, *, method: str, path: str, query: str, inbound_request_id: str
) -> _RoundRecording:
    """Drive ONE real request through the real app at the ASGI boundary.

    Builds the ``http`` scope the ASGI server would hand the app, calls the
    app callable directly (no socket — the same in-process channel the test
    client uses), and records the moments the response crosses the boundary
    back out. Everything between enter and flush is the app's own code.
    """
    entered = time.perf_counter()
    start_offset: list[float] = []
    complete_offset: list[float] = []
    status: list[int] = []
    headers: dict[str, str] = {}
    body_chunks: list[bytes] = []

    async def receive() -> Message:
        """The GET rounds carry no body; an honest disconnect if anything asks."""
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        """Collect the response as it leaves — the measurable boundary."""
        if message["type"] == "http.response.start":
            start_offset.append((time.perf_counter() - entered) * 1000)
            status.append(int(message["status"]))
            for key, value in message.get("headers", []):
                headers[key.decode("latin-1").lower()] = value.decode("latin-1")
        elif message["type"] == "http.response.body":
            body_chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                complete_offset.append((time.perf_counter() - entered) * 1000)

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query.encode("utf-8"),
        "root_path": "",
        "headers": [
            (b"host", b"obs-trace.internal"),
            (b"accept", b"application/json"),
            (b"x-request-id", inbound_request_id.encode("utf-8")),
        ],
        "client": ("obs-trace", 0),
        "server": ("obs-trace.internal", 80),
    }
    await app(scope, receive, send)
    if not status or not start_offset or not complete_offset:
        raise AppError(
            FailureKind.INTERNAL,
            f"the traced round {method} {path} never flushed a complete response",
        )
    return _RoundRecording(
        status=status[0],
        headers=headers,
        body=b"".join(body_chunks),
        start_offset_ms=round(start_offset[0], 1),
        complete_offset_ms=round(complete_offset[0], 1),
    )


async def build_trace_fanout_payload(
    *, app: ASGIApp, root_request_id: str
) -> TraceFanout:
    """Drive the three-round fan-out and correlate every id end to end.

    The rounds are fixed by design — one per outcome class this app's
    failure paths produce: a clean 200 (silent in the logs), the 404 the
    posts resource's missing id raises, and the 422 FastAPI's query
    validation answers — so every correlation claim in the payload has a
    deterministic, testable counterpart.
    """
    root_prefix = root_request_id[:ROOT_ID_PREFIX_LIMIT]
    rounds_spec: list[tuple[str, str, str, str]] = [
        ("ok", "GET /api/health", "/api/health", ""),
        ("not-found", "GET /api/posts/nope", "/api/posts/nope", ""),
        (
            "validation",
            "GET /api/posts?page=notanumber",
            "/api/posts",
            "page=notanumber",
        ),
    ]
    rounds: list[TraceRound] = []
    for label, request_line, path, query in rounds_spec:
        inbound_request_id = f"{root_prefix}-{label}"
        recording = await _drive_round(
            app,
            method="GET",
            path=path,
            query=query,
            inbound_request_id=inbound_request_id,
        )
        envelope = recording.envelope()
        failed = recording.status >= 400
        rounds.append(
            TraceRound(
                label=label,
                request_line=request_line,
                inbound_request_id=inbound_request_id,
                status=recording.status,
                first_byte_ms=recording.start_offset_ms,
                duration_ms=recording.complete_offset_ms,
                header_echoed=recording.header(REQUEST_ID_HEADER_LOWER)
                == inbound_request_id,
                envelope_code=str(envelope.get("code")) if failed else None,
                envelope_request_id=(
                    str(envelope.get("requestId")) if failed else None
                ),
                log_events=[
                    captured_event(event)
                    for event in recent_log().by_request_id(inbound_request_id)
                ],
                note=_FAILED_NOTE if failed else _OK_NOTE,
            )
        )
    return TraceFanout(
        root_request_id=root_request_id,
        derived_id_convention=DERIVED_ID_CONVENTION,
        rounds=rounds,
        correlation_note=CORRELATION_NOTE,
        honesty_note=HONESTY_NOTE,
    )
