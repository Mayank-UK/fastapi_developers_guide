"""Request-id middleware + contextvar access for logging and error envelopes.

Every request gets exactly one id: the inbound ``x-request-id`` header when
the client supplies one (accepted as-is, capped at 200 chars so hostile
headers cannot bloat every log line and response), otherwise a fresh uuid4.
The id is echoed on every response's ``x-request-id`` header, bound to a
``ContextVar`` so structlog can pick it up anywhere in the call stack, and
mirrored onto the ASGI scope's state so even the outermost
ServerErrorMiddleware handler — which runs *outside* this middleware — can
recover it after the contextvar has been reset during unwinding. Topic 33
made the structlog pickup real: the id is also BOUND as a structlog
contextvar for the duration of the exchange, so every log line any code in
the request writes carries ``request_id`` without passing it at each call
site (the pipeline's ``merge_contextvars`` processor merges it in).

Implementation history, on record: this layer began life as a
``BaseHTTPMiddleware`` subclass (readability first — the middleware topic
teaches that idiom with the security-headers layer). The caveat recorded
then came due in topic 28: ``BaseHTTPMiddleware`` bridges its friendly
``Request``/``Response`` objects through a per-request task, which buffers
the body and breaks streaming backpressure — server-sent events must flow
UNBUFFERED — and its http-only ``dispatch`` never sees websocket scopes at
all. Topic 28 rewrote it as the pure ASGI layer below: the request side
reads the raw scope, the response side stamps the header on the one
``http.response.start`` message as it passes (every body chunk flows
through untouched), and websocket scopes get the same contextvar + state
mirror — a websocket carries no response headers to stamp, so there the
id serves logging only.
"""

from contextvars import ContextVar
from uuid import uuid4

import structlog
from fastapi import Request
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER: str = "x-request-id"
_MAX_INBOUND_ID_LENGTH: int = 200

_request_id: ContextVar[str] = ContextVar("fdg_request_id", default="")


def current_request_id() -> str:
    """Return the ambient request id ("" outside a request)."""
    return _request_id.get()


def reset_request_context() -> None:
    """Clear the ambient request id; test isolation between requests/tests."""
    _request_id.set("")


def resolve_request_id(request: Request) -> str:
    """Best-effort lookup: contextvar first, then the request's scope state.

    Handlers running inside this middleware see the contextvar; the
    unhandled-exception handler runs outside it (ServerErrorMiddleware wraps
    user middleware) and reads the scope mirror instead.
    """
    ambient = _request_id.get()
    if ambient:
        return ambient
    state_id = request.scope.get("state", {}).get("request_id")
    return state_id if isinstance(state_id, str) else ""


def _assign_request_id(inbound: str | None) -> str:
    """Normalize the inbound header: strip, cap at 200, default to uuid4 hex."""
    candidate = (inbound or "").strip()[:_MAX_INBOUND_ID_LENGTH]
    return candidate or uuid4().hex


def _inbound_id(scope: Scope) -> str | None:
    """The inbound header from the raw scope (case-insensitive, decoded)."""
    return Headers(scope=scope).get(REQUEST_ID_HEADER)


def _mirror_into_scope(scope: Scope, request_id: str) -> None:
    """Set ``scope.state.request_id`` — the lookup that survives unwinding."""
    scope.setdefault("state", {})["request_id"] = request_id


def _bind_log_context(request_id: str) -> None:
    """Bind the id as a structlog contextvar: every log line the request's
    code writes (handler, dependencies, adapters) carries ``request_id``
    automatically, merged in by the pipeline's first processor."""
    structlog.contextvars.bind_contextvars(request_id=request_id)


def _unbind_log_context() -> None:
    """Remove the bound id — the ``finally`` that resets the contextvar calls
    this, so no log line outside a request inherits a stale id."""
    structlog.contextvars.unbind_contextvars("request_id")


class RequestIdMiddleware:
    """Assign/expose the request id for every HTTP and websocket scope."""

    def __init__(self, app: ASGIApp) -> None:
        """Wrap ``app``, the next ASGI application (add_middleware supplies it)."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Bind the id for the duration of the exchange; stamp the response."""
        if scope["type"] not in ("http", "websocket"):
            # lifespan (and any future scope type) has no request to identify.
            await self.app(scope, receive, send)
            return

        request_id = _assign_request_id(_inbound_id(scope))
        token = _request_id.set(request_id)
        # Mirror into the shared ASGI scope so handlers outside this
        # middleware (ServerErrorMiddleware's 500 path) still see the id.
        _mirror_into_scope(scope, request_id)
        # Bind into structlog's context so every log line this request's
        # code writes carries the id without passing it at each call site.
        _bind_log_context(request_id)

        if scope["type"] == "websocket":
            # A websocket has no response headers to stamp — the id binds so
            # every log line the handler writes correlates to the connection.
            try:
                await self.app(scope, receive, send)
            finally:
                _unbind_log_context()
                _request_id.reset(token)
            return

        async def send_with_request_id(message: Message) -> None:
            # The response side at the wire level: headers ride exactly one
            # message (http.response.start) — stamp it there and let every
            # body chunk flow past untouched, which is what keeps streaming
            # responses (topic 28's SSE) unbuffered through this layer.
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            _unbind_log_context()
            _request_id.reset(token)
