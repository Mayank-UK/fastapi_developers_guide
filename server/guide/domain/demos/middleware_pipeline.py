"""Middleware-pipeline demo payload: the live ASGI onion, made observable.

``GET /api/demo/middleware/pipeline`` serves this payload. The endpoint's
point is to make the middleware chain VISIBLE, three ways: the real
COMPOSITION (the built stack walked from the outermost layer down to the
app's own router — collected from the live app by the thin router), a REAL
in-memory ASGI run of that composition — one pure-ASGI ``TracingMiddleware``
per layer wrapping a terminal endpoint app — whose recorded events prove
the wrap order (request events descend the stack, the handler runs once
in the middle, response events unwind in reverse), and the live request
id the REAL ``RequestIdMiddleware`` assigned to the very request fetching
this payload (its ``x-request-id`` header on the response is the
response-side half of the same proof — stamped after this payload was
built, so ``curl -i`` can watch both sides agree).

The engine is pure: names + request id in, payload out — no sockets, no
clock, no randomness; the awaiting is ordinary in-memory coroutine
execution. Sequence numbers come from append order, so the trace is
deterministic and testable.
"""

from collections.abc import Sequence
from typing import Final, Literal

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from guide.core.request_context import REQUEST_ID_HEADER
from guide.core.serialization import CamelModel

StackKind = Literal["framework", "user", "router"]
"""Who owns one stack row: a framework layer, a create_app registration, the router."""

TracePhase = Literal["request", "handler", "response"]
"""Where in the onion one event fired: descending, the terminal app, ascending."""

_LAYER_ROLES: Final[dict[str, str]] = {
    "ServerErrorMiddleware": (
        "Starlette's outermost bookend — the last-resort 500 handler; its "
        "responses never re-enter the stack"
    ),
    "ExceptionTelemetryMiddleware": (
        "FastAPI's telemetry seam — observes exceptions before handlers answer"
    ),
    "CORSMiddleware": (
        "Starlette's CORS layer (topic 25) — outermost of the user layers so "
        "even error envelopes carry the cross-origin verdict"
    ),
    "SecurityHeadersMiddleware": (
        "this app's security-headers layer (topic 25) — defensive headers "
        "stamped on every response, error envelopes included"
    ),
    "RequestIdMiddleware": (
        "this app's request-id layer — assigns the id request-side, stamps "
        "the response header response-side"
    ),
    "ExceptionMiddleware": (
        "Starlette's innermost bookend — runs the registered exception handlers"
    ),
    "AsyncExitStackMiddleware": (
        "FastAPI's request-scoped exit stack — closeable resources unwind "
        "here after the response is sent"
    ),
}
"""One-line roles for the layers this app's stack is known to contain."""

_ROUTER_ROLE: Final[str] = (
    "the terminal ASGI app — route matching (topic 07), dependencies (topic 06), "
    "the endpoint itself"
)
_USER_LAYER_ROLE: Final[str] = "user middleware registered by create_app"
_FRAMEWORK_LAYER_ROLE: Final[str] = "a framework layer mounted by the stack builder"


class StackLayer(CamelModel):
    """One row of the chain, outermost first (``order_index`` 0 sees the request first)."""

    name: str
    kind: StackKind
    order_index: int
    role: str


class TraceEvent(CamelModel):
    """One beat of the traced run; ``sequence`` is the chronological truth."""

    stage: str
    phase: TracePhase
    sequence: int
    note: str


class MiddlewarePipelinePayload(CamelModel):
    """Wire shape of ``GET /api/demo/middleware/pipeline``."""

    stack: list[StackLayer]
    trace: list[TraceEvent]
    request_side_order: list[str]
    """Stack names in request order — outermost first, the router last."""

    response_side_order: list[str]
    """The same names as the response unwinds — innermost first, outermost last."""

    request_id: str
    """The id the REAL RequestIdMiddleware assigned to the request fetching this."""

    request_id_header: str
    reasoning: str


class TraceRecorder:
    """Append-only event log; the sequence number IS the chronological truth."""

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    def record(self, stage: str, phase: TracePhase, note: str) -> None:
        """Append one event with the next sequence number."""
        self._events.append(
            TraceEvent(stage=stage, phase=phase, sequence=len(self._events), note=note)
        )

    def events(self) -> list[TraceEvent]:
        """The recorded events, oldest first (a copy, never the live list)."""
        return list(self._events)


class TracingMiddleware:
    """Pure ASGI middleware: one event entering, one event exiting.

    This is the whole middleware idea in one small class — hold the next
    ASGI app, run code BEFORE awaiting it (the request side), run code
    AFTER (the response side). No ``Request``/``Response`` objects and no
    base class: just the raw ``(scope, receive, send)`` contract every
    ASGI application already speaks.
    """

    def __init__(self, app: ASGIApp, stage: str, recorder: TraceRecorder) -> None:
        """Wrap ``app``; events are recorded under ``stage``'s name."""
        self._app = app
        self._stage = stage
        self._recorder = recorder

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """The ASGI call: descend, then unwind."""
        self._recorder.record(self._stage, "request", f"request descends through {self._stage}")
        await self._app(scope, receive, send)
        self._recorder.record(
            self._stage, "response", f"response ascends back through {self._stage}"
        )


async def run_traced_pipeline(stack_names: Sequence[str]) -> list[TraceEvent]:
    """Run one in-memory request through one tracing layer per stack row.

    Layers wrap in REVERSED row order — the same loop Starlette's
    ``build_middleware_stack`` uses — so the FIRST row (outermost) is
    wrapped last and sees the request first. The terminal app is the last
    row (the router): it records the single ``handler`` event and sends a
    minimal response, which every layer passes outward untouched.
    """
    if not stack_names:
        raise ValueError("the stack needs at least the terminal row")
    recorder = TraceRecorder()
    terminal = stack_names[-1]

    async def endpoint(scope: Scope, receive: Receive, send: Send) -> None:
        """The terminal app: the handler beat, then a minimal response out."""
        recorder.record(terminal, "handler", f"{terminal} matched the route and ran the endpoint")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    app: ASGIApp = endpoint
    for name in reversed(stack_names[:-1]):
        app = TracingMiddleware(app, stage=name, recorder=recorder)

    sent: list[Message] = []

    async def receive() -> Message:
        """No request body is read; an honest disconnect if anything asks."""
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        """Collect what the stack flushes — the proof the response got out."""
        sent.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "method": "GET",
            "path": "/traced",
            "headers": [],
        },
        receive,
        send,
    )
    if len(sent) != 2:
        raise RuntimeError(f"the traced response did not flush (got {len(sent)} messages)")
    return recorder.events()


async def build_middleware_pipeline_payload(
    *,
    stack_names: Sequence[str],
    user_middleware_names: Sequence[str],
    request_id: str,
) -> MiddlewarePipelinePayload:
    """Compose the stack, run the traced pipeline, shape the payload (pure)."""
    if not stack_names:
        raise ValueError("the stack needs at least the terminal row")
    user_names = frozenset(user_middleware_names)
    router_index = len(stack_names) - 1

    def _kind(name: str, index: int) -> StackKind:
        if name in user_names:
            return "user"
        return "router" if index == router_index else "framework"

    stack = [
        StackLayer(
            name=name,
            kind=_kind(name, index),
            order_index=index,
            role=(
                _ROUTER_ROLE
                if index == router_index
                else _LAYER_ROLES.get(
                    name, _USER_LAYER_ROLE if name in user_names else _FRAMEWORK_LAYER_ROLE
                )
            ),
        )
        for index, name in enumerate(stack_names)
    ]
    trace = await run_traced_pipeline(stack_names)
    request_side_order = [layer.name for layer in stack]
    response_side_order = list(reversed(request_side_order))
    reasoning = (
        f"One request, {len(stack) - 1} middleware layers: request events descend the "
        f"stack in wrap order — {' then '.join(request_side_order[:-1])} — the router "
        f"runs the endpoint once in the middle, and response events unwind the same "
        f"layers in reverse, because code after each layer's await runs only once the "
        f"inner app has finished. The trace replays exactly this composition as a real "
        f"in-memory pure-ASGI run. The live proof rides on this very response: its "
        f"{REQUEST_ID_HEADER} header was stamped by RequestIdMiddleware AFTER this "
        f"payload was built, and its value is the requestId field — check it with "
        f"curl -i."
    )
    return MiddlewarePipelinePayload(
        stack=stack,
        trace=trace,
        request_side_order=request_side_order,
        response_side_order=response_side_order,
        request_id=request_id,
        request_id_header=REQUEST_ID_HEADER,
        reasoning=reasoning,
    )
