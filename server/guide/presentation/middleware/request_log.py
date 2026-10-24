"""Access-log middleware: one structured ``http_request`` line per request.

Topic 33's request-logging layer — the half the middleware topic recorded
as missing ("it arrives with observability"). Pure ASGI by design (the
topic-28 lesson: no BaseHTTPMiddleware, no body buffering — the send
wrapper only observes messages as they pass, so streaming responses stay
unbuffered through this layer too). The timing is the promised
``perf_counter`` pair around the whole inner call: started at request-enter,
read in the ``finally`` after the last message flushed, so ``duration_ms``
covers the entire onion beneath this layer — middleware, routing,
dependencies, the handler, response serialization, and every body chunk.

The request id on every line is read from the response's own
``x-request-id`` header, stamped by ``RequestIdMiddleware`` on the inside:
the access log, the error envelopes, and the client all see the SAME id
without this layer knowing anything about contextvars. A response that
never produced ``http.response.start`` (the last-resort 500 path answers
from OUTSIDE the user stack) is logged with status 0 — the honest marker
that this layer saw the request leave but never saw a response return.

Every event this layer writes flows through the real structlog pipeline,
so it is also snapshotted into the recent-events ring the structured-log
viewer serves: one request, one ``http_request`` row, correlated by id.
"""

import time

import structlog
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from guide.core.request_context import REQUEST_ID_HEADER

logger = structlog.get_logger()


class RequestLogMiddleware:
    """Log one ``http_request`` event per HTTP exchange, at completion."""

    def __init__(self, app: ASGIApp) -> None:
        """Wrap ``app``, the next ASGI application (add_middleware supplies it)."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Time the whole inner call; log method, path, status, duration, id."""
        if scope["type"] != "http":
            # Websocket exchanges carry their id in the bound log context; the
            # access log is the HTTP-only layer (no response to summarize).
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "?")
        path = scope.get("path", "?")
        started = time.perf_counter()
        status: list[int] = []
        request_id: list[str] = []

        async def send_observing(message: Message) -> None:
            # The response side: headers ride exactly one message — read the
            # status and the stamped id there, let every body chunk pass.
            if message["type"] == "http.response.start":
                status.append(int(message["status"]))
                request_id.append(Headers(scope=message).get(REQUEST_ID_HEADER, ""))
            await send(message)

        try:
            await self.app(scope, receive, send_observing)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 1)
            logger.info(
                "http_request",
                method=method,
                path=path,
                status=status[0] if status else 0,
                duration_ms=duration_ms,
                request_id=request_id[0] if request_id else "",
            )
