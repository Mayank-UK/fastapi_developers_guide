"""Request spans: the repo's real ``yield`` dependency (setup → yield → teardown).

``open_request_span`` is a request-lifecycle instrument, not an exhibit: an
async generator dependency that opens a span before the handler runs, yields
the span into it, and closes it in a ``finally`` AFTER the response has been
sent — the ordering FastAPI guarantees by entering yield dependencies into
the request-scoped ``AsyncExitStack`` and awaiting the response inside it.
Because the response is already gone when teardown runs, a handler can never
report its own teardown; the shared ``SpanLog`` (a bounded ring wired on
``app.state.span_log``) records all four events, and the sibling
``GET /api/demo/dep/lifecycle/log`` endpoint serves them back — the log's
sequence numbers are the ordering proof.

``SpanResponse`` is the other half of the instrument: a Response object is
an ASGI app whose ``__call__`` IS the send step, so it stamps a ``response``
event at the exact moment the bytes leave. One request through
``GET /api/demo/dep/lifecycle`` therefore appends, in order:
setup → handler → response → teardown.
"""

import threading
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Final, Literal
from uuid import uuid4

from fastapi import Depends, Request
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from guide.core.errors import AppError, FailureKind
from guide.core.serialization import CamelModel

SpanEventName = Literal["setup", "handler", "response", "teardown"]
"""The four beats of one request through the span dependency."""

SPAN_LOG_CAPACITY: Final = 20
"""Events kept per app: the ring holds the LAST one, oldest evicted first."""


class SpanEvent(CamelModel):
    """One timestamped beat of one request span; wire is camelCase."""

    sequence: int
    """Log-wide, strictly increasing — the append order, i.e. the truth."""

    span_id: str
    event: SpanEventName
    at: str
    offset_ms: int
    """Milliseconds from this span's setup — the timeline within a request."""


class SpanLog:
    """Append-only ring buffer of span events, bounded to the last ``capacity``.

    A lock guards mutation out of honesty rather than need: the span
    instrument is async-only (the event loop is single-threaded), but sync
    dependencies run in the threadpool — the ring stays safe even if a
    threadpool context ever records. Sequence numbers are allocated under
    the same lock, so they can never contradict append order.
    """

    def __init__(self, capacity: int = SPAN_LOG_CAPACITY) -> None:
        """Hold the last ``capacity`` events (at least one)."""
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._capacity = capacity
        self._events: list[SpanEvent] = []
        self._lock = threading.Lock()
        self._next_sequence = 0

    @property
    def capacity(self) -> int:
        """The ring's bound (events held never exceed it)."""
        return self._capacity

    def append(
        self, span_id: str, event: SpanEventName, at: str, offset_ms: int
    ) -> SpanEvent:
        """Record one beat; returns the event with its allocated sequence."""
        with self._lock:
            span_event = SpanEvent(
                sequence=self._next_sequence,
                span_id=span_id,
                event=event,
                at=at,
                offset_ms=offset_ms,
            )
            self._next_sequence += 1
            self._events.append(span_event)
            if len(self._events) > self._capacity:
                del self._events[: len(self._events) - self._capacity]
        return span_event

    def tail(self) -> list[SpanEvent]:
        """A copy of the held events, oldest first (never the live list)."""
        with self._lock:
            return list(self._events)


class RequestSpan:
    """The per-request span a handler receives from the yield dependency."""

    def __init__(self, log: SpanLog) -> None:
        """Open a span: mint the id, remember the clock origin and log."""
        self.span_id: Final[str] = uuid4().hex[:12]
        self.opened_at: Final[str] = datetime.now(UTC).isoformat(timespec="milliseconds")
        self._log = log
        self._opened_clock: Final[float] = time.perf_counter()

    def record(self, event: SpanEventName) -> None:
        """Append one beat of this span, timestamped and offset from setup."""
        offset_ms = round((time.perf_counter() - self._opened_clock) * 1000)
        self._log.append(
            span_id=self.span_id,
            event=event,
            at=datetime.now(UTC).isoformat(timespec="milliseconds"),
            offset_ms=offset_ms,
        )

    def elapsed_ms(self) -> int:
        """Milliseconds since this span opened (how the handler reports itself)."""
        return round((time.perf_counter() - self._opened_clock) * 1000)


def get_span_log(request: Request) -> SpanLog:
    """FastAPI dependency: the app's span log (wired in create_app)."""
    log = request.app.state.span_log
    if not isinstance(log, SpanLog):
        raise AppError(FailureKind.INTERNAL, "Span log not wired on app.state")
    return log


SpanLogDep = Annotated[SpanLog, Depends(get_span_log)]


async def open_request_span(log: SpanLogDep) -> AsyncIterator[RequestSpan]:
    """FastAPI yield dependency: setup, yield the span, teardown after send.

    Everything before ``yield`` runs during dependency resolution (before
    the handler); the ``finally`` runs when FastAPI closes the request's
    ``AsyncExitStack`` — for a regular response, after the bytes have been
    sent. The dependency's own sub-dependency (``get_span_log``) is how the
    demo's override test swaps the log for a fake.
    """
    span = RequestSpan(log)
    span.record("setup")
    try:
        yield span
    finally:
        span.record("teardown")


RequestSpanDep = Annotated[RequestSpan, Depends(open_request_span)]


class SpanLogSnapshot(CamelModel):
    """Wire shape of ``GET /api/demo/dep/lifecycle/log``: the ring, as data."""

    capacity: int
    events: list[SpanEvent]


class SpanResponse(JSONResponse):
    """A JSON response that stamps its span's ``response`` event at the send moment.

    FastAPI awaits the response object (an ASGI app) to send the bytes, and
    closes the request's ``AsyncExitStack`` — running yield-dependency
    teardown — only after that await completes. Recording inside
    ``__call__`` therefore timestamps the flush itself, which is what makes
    the log's ordering (… → response → teardown) a measurement, not a claim.

    The body is built from a payload model exactly as FastAPI would
    (camelCase aliases, JSON-safe, nulls omitted), because a directly
    returned Response bypasses ``response_model`` serialization.
    """

    def __init__(self, span: RequestSpan, content: CamelModel) -> None:
        """Serialize ``content`` now; stamp the span when this is awaited."""
        super().__init__(
            content=content.model_dump(mode="json", by_alias=True, exclude_none=True)
        )
        self._span = span

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """The send step itself: record, then let the JSON bytes leave."""
        self._span.record("response")
        await super().__call__(scope, receive, send)
