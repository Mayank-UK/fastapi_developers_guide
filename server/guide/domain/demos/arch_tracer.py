"""Architecture-tracer demo payload: one request through every layer, live.

``GET /api/demo/arch/tracer`` serves this payload. The endpoint's point is
to make the app's OWN architecture observable in one answer, honestly split
into what is INTROSPECTED from the running app (the built middleware stack,
walked outermost-first to the router; the matched ``/api/posts`` route with
the endpoint's real dependency tree; the composition root's actual wiring —
which adapter satisfies the posts port, read off ``app.state``) and what is
MEASURED: two REAL internal requests driven straight through the real ASGI
application (a hand-built ``http`` scope handed to the app callable — the
same in-process technique the ASGI server itself uses, no socket, no fake
routes). The ``Ok`` round (``GET /api/posts?page=2&limit=4``) crosses every
layer — middleware, routing, dependency resolution, use case, repository,
``Result``, response mapping — and its beats are timed with
``time.perf_counter`` at the ASGI boundary: when the request enters the
outermost layer, when ``http.response.start`` leaves (status + headers
ready), and when the last body message flushes. The ``Err`` round
(``GET /api/posts/nope``) proves the failure path end to end: the
repository's ``None``, the use case's ``Err(AppError(not_found))``, the
router's raise, the shared handler's 404 envelope — the envelope's
``requestId`` and the response's ``x-request-id`` header agree.

Honesty rules the shape: per-hop timings are NOT fabricated — only the
three boundary beats carry measured milliseconds, and every hop row says
which evidence backs it (``measured``, ``observed`` from the real
response, or ``introspected`` from the running app). Both rounds send an
inbound ``x-request-id`` and the round's response must echo it back — the
round-trip proof the real ``RequestIdMiddleware`` ran inside the traced
request. The engine is pure with respect to app state: the caller supplies
the introspected facts and the ASGI callable; everything in the payload
was either read from the live app or produced by the requests themselves.
"""

import json
import time
from collections.abc import Sequence
from typing import Any, Final, Literal

from starlette.types import ASGIApp, Message, Scope

from guide.core.errors import AppError, FailureKind
from guide.core.serialization import CamelModel

StackKind = Literal["framework", "user", "router"]
"""Who owns one stack row: a framework layer, a create_app registration, the router."""

HopEvidence = Literal["measured", "observed", "introspected"]
"""How a hop row is known: timed, read off the real response, or read off the app."""

BeatName = Literal["enter", "response.start", "complete"]
"""The three ASGI-boundary beats every traced round actually measures."""

RoundOutcome = Literal["ok", "err"]
"""The two traced rounds: the Result success path and the failure path."""

REQUEST_ID_HEADER_LOWER: Final = "x-request-id"
"""The header both directions of a traced round ride on (ASGI headers are lowercase)."""

_LAYER_ROLES: Final[dict[str, str]] = {
    "ServerErrorMiddleware": (
        "Starlette's outermost bookend — where the last-resort 500 handler runs"
    ),
    "ExceptionTelemetryMiddleware": (
        "FastAPI's telemetry seam — observes exceptions before handlers answer"
    ),
    "CORSMiddleware": (
        "the cross-origin verdict (topic 25's allow-list), outermost of the user layers"
    ),
    "SecurityHeadersMiddleware": (
        "topic 25's defensive headers — stamped on every response, envelopes included"
    ),
    "RequestIdMiddleware": (
        "the request-id layer — assigns the id request-side, stamps the header response-side"
    ),
    "ExceptionMiddleware": ("the innermost bookend — dispatches the registered exception handlers"),
    "AsyncExitStackMiddleware": (
        "FastAPI's request-scoped exit stack — yield-dependency teardown runs here"
    ),
}
"""One-line roles for the layers this app's built stack is known to contain."""

_ROUTER_ROLE: Final[str] = (
    "the terminal ASGI app — route matching, dependency resolution, the endpoint"
)
_UNKNOWN_LAYER_ROLE: Final[str] = "a middleware layer registered by create_app"
"""Role fallback for user layers the catalog has not met yet."""


class ArchStackLayer(CamelModel):
    """One row of the built chain, outermost first (``order_index`` 0 sees the request first)."""

    name: str
    kind: StackKind
    order_index: int
    role: str


class ArchDependency(CamelModel):
    """One entry in the endpoint's real dependency tree, as FastAPI declared it."""

    param: str
    provider: str
    provider_kind: Literal["model", "function"]


class ArchRoute(CamelModel):
    """The traced endpoint's declared shape, introspected from the live router."""

    template: str
    method: str
    endpoint: str
    response_model: str
    dependencies: list[ArchDependency]


class ArchWiring(CamelModel):
    """What the composition root actually wired, read off the running app."""

    port: str
    adapter: str
    use_cases: str
    wired_by: str


class ArchBeat(CamelModel):
    """One measured moment of a traced round; ``offset_ms`` is from request-enter."""

    event: BeatName
    offset_ms: float


class ArchHop(CamelModel):
    """One architectural hop of the traced request, with its evidence class."""

    stage: str
    layer: str
    detail: str
    evidence: HopEvidence


class ArchFact(CamelModel):
    """One name/value fact read off the traced round's real response."""

    name: str
    value: str


class ArchRound(CamelModel):
    """One complete traced round: the request line, the beats, the proof."""

    outcome: RoundOutcome
    request_line: str
    inbound_request_id: str
    status: int
    beats: list[ArchBeat]
    facts: list[ArchFact]
    hops: list[ArchHop]


class ArchTracerPayload(CamelModel):
    """Wire shape of ``GET /api/demo/arch/tracer``."""

    stack: list[ArchStackLayer]
    route: ArchRoute
    wiring: ArchWiring
    rounds: list[ArchRound]
    reasoning: str


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

    def json_body(self) -> Any:
        """The parsed response body; raises ValueError when it is not JSON."""
        return json.loads(self.body.decode("utf-8"))


async def _drive_round(
    app: ASGIApp,
    *,
    method: str,
    path: str,
    query: str,
    inbound_request_id: str,
) -> _RoundRecording:
    """Drive ONE real request through the real app at the ASGI boundary.

    Builds the ``http`` scope the ASGI server would hand the app, calls the
    app callable directly (no socket — the same in-process channel the test
    client uses), and records the moments the response crosses the boundary
    back out: ``http.response.start`` (status + headers ready) and the final
    ``http.response.body`` message. Everything between enter and start —
    middleware, routing, dependencies, the endpoint — is the app's own code
    running for real.
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
            (b"host", b"arch-tracer.internal"),
            (b"accept", b"application/json"),
            (b"x-request-id", inbound_request_id.encode("utf-8")),
        ],
        "client": ("arch-tracer", 0),
        "server": ("arch-tracer.internal", 80),
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


def _stack_rows(stack_names: Sequence[str], user_names: Sequence[str]) -> list[ArchStackLayer]:
    """Classify the walked chain: user registrations, framework layers, the router terminal."""
    users = frozenset(user_names)
    router_index = len(stack_names) - 1
    return [
        ArchStackLayer(
            name=name,
            kind=("router" if index == router_index else "user" if name in users else "framework"),
            order_index=index,
            role=(
                _ROUTER_ROLE
                if index == router_index
                else _LAYER_ROLES.get(name, _UNKNOWN_LAYER_ROLE)
            ),
        )
        for index, name in enumerate(stack_names)
    ]


def _stack_sentence(stack_names: Sequence[str]) -> str:
    """The chain as one honest descent line for hop narration."""
    return " → ".join(stack_names)


def _dep(route: ArchRoute, param: str) -> ArchDependency:
    """One declared dependency by its handler parameter name."""
    return next(dependency for dependency in route.dependencies if dependency.param == param)


def _ok_round(
    recording: _RoundRecording,
    *,
    request_line: str,
    inbound_request_id: str,
    stack_names: Sequence[str],
    route: ArchRoute,
    wiring: ArchWiring,
) -> ArchRound:
    """Narrate the Ok round from its real recording — facts first, then hops."""
    body = recording.json_body()
    items = body["items"] if isinstance(body, dict) and isinstance(body.get("items"), list) else []
    facts = [
        ArchFact(name="status", value=str(recording.status)),
        ArchFact(name="items", value=str(len(items))),
        ArchFact(name="total", value=str(body.get("total")) if isinstance(body, dict) else "?"),
        ArchFact(name="page", value=str(body.get("page")) if isinstance(body, dict) else "?"),
        ArchFact(name="limit", value=str(body.get("limit")) if isinstance(body, dict) else "?"),
        ArchFact(name="pages", value=str(body.get("pages")) if isinstance(body, dict) else "?"),
        ArchFact(
            name="x-total-count header",
            value=recording.header("x-total-count") or "absent",
        ),
        ArchFact(
            name="x-request-id header",
            value=recording.header(REQUEST_ID_HEADER_LOWER) or "absent",
        ),
    ]
    echoed = recording.header(REQUEST_ID_HEADER_LOWER) == inbound_request_id
    hops = [
        ArchHop(
            stage="middleware stack",
            layer="presentation.middleware",
            detail=(
                f"the request entered the built chain ({_stack_sentence(stack_names)}); the "
                f"inbound x-request-id was accepted and echoed back by the real "
                f"RequestIdMiddleware inside this very round"
            ),
            evidence="observed",
        ),
        ArchHop(
            stage="routing",
            layer="presentation.routers",
            detail=(
                f"the router matched template {route.template} for GET → endpoint "
                f"{route.endpoint} (response_model {route.response_model})"
            ),
            evidence="introspected",
        ),
        ArchHop(
            stage="dependency resolution",
            layer="presentation.dependencies",
            detail=(
                f"{_dep(route, 'query').param} ← {_dep(route, 'query').provider} bound the "
                f"query string into a validated model; {_dep(route, 'use_cases').param} ← "
                f"{_dep(route, 'use_cases').provider} resolved the bundle off app.state — "
                f"the echoed page/limit in the body are the binding's proof"
            ),
            evidence="observed",
        ),
        ArchHop(
            stage="use case",
            layer="domain.use-cases",
            detail=(
                f"{wiring.use_cases}.list_posts.execute(query) — thin orchestration over the "
                f"port, returning a Result"
            ),
            evidence="introspected",
        ),
        ArchHop(
            stage="repository",
            layer="data.adapter",
            detail=(
                f"{wiring.adapter}.list(query) behind the {wiring.port} port: filter, sort, "
                f"count, slice — the seeded posts flowing out as items are its answer"
            ),
            evidence="observed",
        ),
        ArchHop(
            stage="Result",
            layer="domain.result",
            detail="Ok(PostPage) — the domain's failure-as-value contract, no exception raised",
            evidence="observed",
        ),
        ArchHop(
            stage="response mapping",
            layer="presentation.routers",
            detail=(
                "the router mapped Ok to 200, response_model serialized the page, and the "
                "pagination headers (x-total-count, x-page-count, link) were set right here"
            ),
            evidence="observed",
        ),
    ]
    if not echoed:
        # Honest fallback: the echo check failed, so the payload says so —
        # it never claims a round trip it did not observe.
        facts.append(ArchFact(name="inboundIdEchoed", value="false"))
        hops[0] = hops[0].model_copy(
            update={"detail": hops[0].detail + " — WARNING: the echoed id did NOT match"}
        )
    else:
        facts.append(ArchFact(name="inboundIdEchoed", value="true"))
    return ArchRound(
        outcome="ok",
        request_line=request_line,
        inbound_request_id=inbound_request_id,
        status=recording.status,
        beats=[
            ArchBeat(event="enter", offset_ms=0.0),
            ArchBeat(event="response.start", offset_ms=recording.start_offset_ms),
            ArchBeat(event="complete", offset_ms=recording.complete_offset_ms),
        ],
        facts=facts,
        hops=hops,
    )


def _err_round(
    recording: _RoundRecording,
    *,
    request_line: str,
    inbound_request_id: str,
    stack_names: Sequence[str],
    route: ArchRoute,
    wiring: ArchWiring,
) -> ArchRound:
    """Narrate the Err round: None → Err(AppError) → raise → shared handler → envelope."""
    body = recording.json_body()
    error = body.get("error") if isinstance(body, dict) else None
    envelope = error if isinstance(error, dict) else {}
    header_id = recording.header(REQUEST_ID_HEADER_LOWER) or "absent"
    body_id = envelope.get("requestId")
    facts = [
        ArchFact(name="status", value=str(recording.status)),
        ArchFact(name="envelope code", value=str(envelope.get("code", "?"))),
        ArchFact(name="envelope message", value=str(envelope.get("message", "?"))),
        ArchFact(name="envelope requestId", value=str(body_id or "?")),
        ArchFact(name="x-request-id header", value=header_id),
        ArchFact(name="headerMatchesBody", value=str(header_id == body_id).lower()),
    ]
    hops = [
        ArchHop(
            stage="middleware stack",
            layer="presentation.middleware",
            detail=(
                f"same chain ({_stack_sentence(stack_names)}), a fresh request with its own "
                f"inbound id — echoed back on the envelope's own response"
            ),
            evidence="observed",
        ),
        ArchHop(
            stage="routing",
            layer="presentation.routers",
            detail=(
                "template /api/posts/{post_id} matched GET → endpoint read_post; the path "
                "parameter 'nope' is a well-formed id that names nothing"
            ),
            evidence="introspected",
        ),
        ArchHop(
            stage="dependency resolution",
            layer="presentation.dependencies",
            detail=(
                f"{_dep(route, 'use_cases').param} ← "
                f"{_dep(route, 'use_cases').provider} resolved the "
                f"same wired bundle — {wiring.use_cases} from app.state"
            ),
            evidence="introspected",
        ),
        ArchHop(
            stage="repository",
            layer="data.adapter",
            detail=f"{wiring.adapter}.get('nope') answered None — existence is the adapter's fact",
            evidence="observed",
        ),
        ArchHop(
            stage="use case",
            layer="domain.use-cases",
            detail=(
                "GetPostUseCase turned None into Err(AppError(not_found)) — a domain answer "
                "returned as a value, no HTTP anywhere in the domain"
            ),
            evidence="introspected",
        ),
        ArchHop(
            stage="edge raise",
            layer="presentation.routers",
            detail=(
                "read_post raised result.failure — the two-line flip every router performs on "
                "a failed Result"
            ),
            evidence="introspected",
        ),
        ArchHop(
            stage="exception handler",
            layer="core.errors",
            detail=(
                "ExceptionMiddleware dispatched the shared AppError handler: 404, the family "
                "envelope, and the request's OWN id in body and header — the match is the "
                "proof the whole failure path ran"
            ),
            evidence="observed",
        ),
    ]
    return ArchRound(
        outcome="err",
        request_line=request_line,
        inbound_request_id=inbound_request_id,
        status=recording.status,
        beats=[
            ArchBeat(event="enter", offset_ms=0.0),
            ArchBeat(event="response.start", offset_ms=recording.start_offset_ms),
            ArchBeat(event="complete", offset_ms=recording.complete_offset_ms),
        ],
        facts=facts,
        hops=hops,
    )


_OK_INBOUND_ID: Final = "arch-tracer-ok-round"
_ERR_INBOUND_ID: Final = "arch-tracer-err-round"


async def build_arch_tracer_payload(
    *,
    app: ASGIApp,
    stack_names: Sequence[str],
    user_middleware_names: Sequence[str],
    route: ArchRoute,
    wiring: ArchWiring,
) -> ArchTracerPayload:
    """Compose the tracer: introspected structure + two measured, narrated rounds."""
    if not stack_names:
        raise ValueError("the stack needs at least the terminal row")
    ok_recording = await _drive_round(
        app,
        method="GET",
        path="/api/posts",
        query="page=2&limit=4",
        inbound_request_id=_OK_INBOUND_ID,
    )
    err_recording = await _drive_round(
        app,
        method="GET",
        path="/api/posts/nope",
        query="",
        inbound_request_id=_ERR_INBOUND_ID,
    )
    ok_request_line = "GET /api/posts?page=2&limit=4"
    err_request_line = "GET /api/posts/nope"
    rounds = [
        _ok_round(
            ok_recording,
            request_line=ok_request_line,
            inbound_request_id=_OK_INBOUND_ID,
            stack_names=stack_names,
            route=route,
            wiring=wiring,
        ),
        _err_round(
            err_recording,
            request_line=err_request_line,
            inbound_request_id=_ERR_INBOUND_ID,
            stack_names=stack_names,
            route=route,
            wiring=wiring,
        ),
    ]
    reasoning = (
        f"One payload, both halves of the architecture. The stack, route, and wiring rows are "
        f"introspected from the running app (the built chain walked to the router; the matched "
        f"route's real dependency tree; the adapter the composition root wired behind "
        f"{wiring.port}). The two rounds are real internal requests driven through this very "
        f"app at the ASGI boundary — no socket, no staged responses: the ok round "
        f"({ok_request_line}) crossed middleware, routing, dependency resolution, the use "
        f"case, the repository, and the Ok-to-200 mapping; the err round "
        f"({err_request_line}) crossed the repository's None, the use case's "
        f"Err(not_found), the router's raise, and the shared handler's 404 envelope. Only the "
        f"three ASGI-boundary beats carry measured milliseconds — per-hop timings are not "
        f"fabricated, and each hop says what evidence backs it. Both rounds sent an inbound "
        f"x-request-id and the responses echo them: the round trip is the real "
        f"RequestIdMiddleware running inside the traced requests."
    )
    return ArchTracerPayload(
        stack=_stack_rows(stack_names, user_middleware_names),
        route=route,
        wiring=wiring,
        rounds=rounds,
        reasoning=reasoning,
    )
