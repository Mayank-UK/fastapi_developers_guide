"""The gRPC console's domain vocabulary: one call, its answer, its outcome.

The console (topic 15's demo, ``api:grpc-console``) is a caller's seat
over the REAL in-process gRPC server: pick a method, bring arguments, set
an optional deadline, and watch what comes back — message by message for
streams, status code and elapsed time always. These models are that
conversation's domain shape; the data adapter performs the actual
``grpc.aio`` calls (converting protobuf messages to plain field maps at
the boundary) and the demo builder shapes the payload. Constraints live
on the models as usual (topic 10): an invalid call cannot be constructed.

The shapes are deliberately honest about gRPC semantics: ``messages`` is
a SEQUENCE (unary answers one, server-streaming many, bidirectional as
many as came back, client-streaming the one summary), and a failed call
still has a payload — the status code and detail ARE the answer (section
6's whole lesson), with whatever messages arrived before a mid-stream
deadline kept in place.
"""

from typing import Annotated, Literal

from pydantic import Field

from guide.core.serialization import CamelModel

GrpcMethod = Literal["get-post", "stream-posts", "count-views", "echo-chat"]
"""The console's method roster — one per stream kind the contract defines."""

GrpcStreamKind = Literal["unary", "server-streaming", "client-streaming", "bidirectional"]
"""The four shapes an RPC can take — the vocabulary section 3 teaches."""

GrpcStatusCode = Literal[
    "OK",
    "NOT_FOUND",
    "DEADLINE_EXCEEDED",
    "UNAVAILABLE",
    "INVALID_ARGUMENT",
    "UNKNOWN",
]
"""The status codes the console can honestly report (grpc.StatusCode names)."""

STREAM_PAUSE_SECONDS: float = 0.05
"""The deliberate pause between StreamPosts messages (the slow method).

Domain-owned because it is a fact BOTH layers teach: the servicer sleeps
it between streamed posts, and the console's roster reports it so a
caller can reason about deadlines (50ms × N messages is the budget a
deadline must beat)."""

STREAM_PAUSE_MS: int = 50
"""``STREAM_PAUSE_SECONDS`` in milliseconds — the roster's wire spelling."""


class ViewEventFact(CamelModel):
    """One client-streaming view event: a viewer looked at a post."""

    slug: Annotated[str, Field(min_length=1, max_length=120)]
    viewer: Annotated[str, Field(min_length=1, max_length=40)]


class ChatNoteFact(CamelModel):
    """One bidirectional chat note; the service echoes it back."""

    sender: Annotated[str, Field(min_length=1, max_length=40)]
    text: Annotated[str, Field(min_length=1, max_length=200)]


class GrpcConsoleRequest(CamelModel):
    """One console round: the method, its arguments, an optional deadline.

    Every argument has a default so a bare ``{"method": "get-post"}`` is a
    valid round — each method reads only the fields it needs (GetPost the
    slug, StreamPosts the tag, CountViews the view events, EchoChat the
    chat notes). An empty ``view_events``/``chat_notes`` list is a REAL
    edge the contract allows: a client-streaming call with zero messages
    still runs and answers its summary.
    """

    method: GrpcMethod
    slug: Annotated[str, Field(min_length=1, max_length=120)] = (
        "designing-urls-people-can-read"
    )
    tag: Annotated[str, Field(max_length=40)] = ""
    view_events: Annotated[list[ViewEventFact], Field(max_length=12)] = []
    chat_notes: Annotated[list[ChatNoteFact], Field(max_length=12)] = []
    deadline_ms: Annotated[int, Field(ge=50, le=10_000)] | None = None


class GrpcReceivedMessage(CamelModel):
    """One message that came back, in arrival order.

    ``fields`` is the protobuf message as a plain map (proto field names
    preserved): scalars as scalars, ``repeated`` as lists, ``map`` as
    dicts — the honest shape of protobuf's JSON mouth.
    """

    index: int
    fields: dict[str, object]


class GrpcCallOutcome(CamelModel):
    """What one console round actually produced — success OR failure.

    ``status_code`` is grpc's own vocabulary (``OK`` on success); on
    failure the code and detail are the ANSWER, not an exception — the
    router never maps this onto the HTTP error envelope, because the
    console's HTTP call succeeded and the gRPC outcome is its payload.
    """

    status_code: GrpcStatusCode
    status_detail: str
    messages: list[GrpcReceivedMessage]
    elapsed_ms: int
    server_address: str
