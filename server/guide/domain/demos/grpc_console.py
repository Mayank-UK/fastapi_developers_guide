"""gRPC console demo payloads: the roster and one real round, shaped.

``GET /api/demo/api/grpc-console`` and ``POST /api/demo/api/grpc-console``
serve these payloads — topic 15's demo. The GET roster names the REAL
in-process satellite (its bound address, started on first use), carries
the service stanza of the real ``guide.proto`` verbatim (a test pins the
excerpt against the file, so the two cannot drift), and lists the four
methods with their stream kinds. The POST payload is one REAL round as
the console adapter reported it: what went out (method, arguments,
message count, optional deadline), what came back (the message sequence,
protobuf field maps), the status code in grpc's own vocabulary, elapsed
milliseconds, and the address the call really went to.

The builder is PURE: the roster takes the address and the stream pause
as parameters (the router asks the adapter), the round takes the request
plus the adapter's outcome — no I/O, no grpc import, nothing but shaping
(the same discipline as every builder in this package).
"""

from typing import Final

from guide.core.serialization import CamelModel
from guide.domain.grpc.entities import (
    GrpcCallOutcome,
    GrpcConsoleRequest,
    GrpcMethod,
    GrpcStreamKind,
)

SERVICE_EXCERPT: Final[str] = (
    "service PostService {\n"
    "  rpc GetPost(GetPostRequest) returns (PostReply);\n"
    "  rpc StreamPosts(StreamPostsRequest) returns (stream PostReply);\n"
    "  rpc CountViews(stream ViewEvent) returns (ViewsSummary);\n"
    "  rpc EchoChat(stream ChatNote) returns (stream ChatNote);\n"
    "}"
)
"""The service stanza, verbatim from guide/grpcapi/guide.proto (test-pinned)."""


class GrpcMethodCard(CamelModel):
    """One method as the roster offers it: name, stream kind, message types."""

    id: GrpcMethod
    name: str
    kind: GrpcStreamKind
    input: str
    output: str
    streams_in: bool
    streams_out: bool
    description: str


class GrpcConsoleRoster(CamelModel):
    """Wire shape of ``GET /api/demo/api/grpc-console``."""

    server_address: str
    service: str
    proto_excerpt: str
    methods: list[GrpcMethodCard]
    stream_pause_ms: int
    reasoning: str


class GrpcConsoleRound(CamelModel):
    """Wire shape of ``POST /api/demo/api/grpc-console`` — one real round."""

    method: GrpcMethodCard
    slug: str
    tag: str
    view_events: int
    chat_notes: int
    deadline_ms: int | None
    sent_messages: int
    status_code: str
    status_detail: str
    messages: list[dict[str, object]]
    elapsed_ms: int
    server_address: str
    reasoning: str


_METHOD_CARDS: Final[tuple[GrpcMethodCard, ...]] = (
    GrpcMethodCard(
        id="get-post",
        name="GetPost",
        kind="unary",
        input="GetPostRequest",
        output="PostReply",
        streams_in=False,
        streams_out=False,
        description=(
            "One request, one answer: a post by slug, or NOT_FOUND — the "
            "shape REST's GET /api/posts/{slug} serves."
        ),
    ),
    GrpcMethodCard(
        id="stream-posts",
        name="StreamPosts",
        kind="server-streaming",
        input="StreamPostsRequest",
        output="stream PostReply",
        streams_in=False,
        streams_out=True,
        description=(
            "One request, a sequence of answers: every post matching the tag, "
            "one message each, 50ms apart — deadlines land mid-stream here."
        ),
    ),
    GrpcMethodCard(
        id="count-views",
        name="CountViews",
        kind="client-streaming",
        input="stream ViewEvent",
        output="ViewsSummary",
        streams_in=True,
        streams_out=False,
        description=(
            "A sequence of requests, one answer: the client uploads view "
            "events and receives a single tally back."
        ),
    ),
    GrpcMethodCard(
        id="echo-chat",
        name="EchoChat",
        kind="bidirectional",
        input="stream ChatNote",
        output="stream ChatNote",
        streams_in=True,
        streams_out=True,
        description=(
            "Streams both ways: notes flow in, echoes flow back, in real "
            "time, over one long-lived call."
        ),
    ),
)


def method_card(method: GrpcMethod) -> GrpcMethodCard:
    """The roster card for one console method (KeyError-free by construction)."""
    return next(card for card in _METHOD_CARDS if card.id == method)


def build_grpc_console_roster(*, server_address: str, stream_pause_ms: int) -> GrpcConsoleRoster:
    """Shape the roster (pure): the address, the contract, the four methods."""
    return GrpcConsoleRoster(
        server_address=server_address,
        service="guide.PostService",
        proto_excerpt=SERVICE_EXCERPT,
        methods=list(_METHOD_CARDS),
        stream_pause_ms=stream_pause_ms,
        reasoning=(
            f"A real grpc.aio server is live in-process at {server_address}, hosting "
            "guide.PostService over the same posts use cases as /api/posts and "
            "/api/graphql; every console round is a real call — protobuf frames over "
            "loopback TCP, status codes and deadlines included."
        ),
    )


def _sent_messages(request: GrpcConsoleRequest) -> int:
    """How many protobuf messages the round uploaded (per its stream kind)."""
    if request.method in ("get-post", "stream-posts"):
        return 1
    if request.method == "count-views":
        return len(request.view_events)
    return len(request.chat_notes)


def build_grpc_console_round(
    *, request: GrpcConsoleRequest, outcome: GrpcCallOutcome
) -> GrpcConsoleRound:
    """Shape one finished round (pure): request echo + the adapter's outcome."""
    ok = outcome.status_code == "OK"
    deadline_note = (
        f"deadline {outcome.elapsed_ms}ms into the call"
        if request.deadline_ms is not None
        else "no deadline set — the call ran to completion"
    )
    return GrpcConsoleRound(
        method=method_card(request.method),
        slug=request.slug,
        tag=request.tag,
        view_events=len(request.view_events),
        chat_notes=len(request.chat_notes),
        deadline_ms=request.deadline_ms,
        sent_messages=_sent_messages(request),
        status_code=outcome.status_code,
        status_detail=outcome.status_detail,
        messages=[{"index": m.index, "fields": m.fields} for m in outcome.messages],
        elapsed_ms=outcome.elapsed_ms,
        server_address=outcome.server_address,
        reasoning=(
            f"A real grpc.aio call to {outcome.server_address} answered "
            f"{outcome.status_code} ({len(outcome.messages)} message(s), "
            f"{outcome.elapsed_ms}ms elapsed, {deadline_note})"
            + ("." if ok else f" — {outcome.status_detail}")
        ),
    )
