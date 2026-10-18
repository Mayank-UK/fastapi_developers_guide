"""The gRPC console adapter: one real ``grpc.aio`` call, reported honestly.

``InProcessGrpcConsole`` implements the domain port over the runtime's
shared channel: the caller picks a method and arguments (plus an
optional deadline in milliseconds), the adapter performs the REAL call —
a stub over ``grpc.aio``, protobuf messages on the wire to the
in-process satellite — and reports the outcome as a domain value:
response messages in arrival order (protobuf field names preserved,
no-presence defaults included), the status code in grpc's own
vocabulary, elapsed milliseconds, and the satellite's address.

Failure mapping is the section-6 lesson as code: a failed RPC does NOT
raise out of ``call`` — ``AioRpcError`` becomes ``NOT_FOUND`` /
``DEADLINE_EXCEEDED`` / … with its detail string, and whatever messages
a mid-stream deadline already delivered stay in ``messages``. Only
errors grpc itself cannot phrase as a status (a broken channel setup, an
async misuse) collapse to ``UNKNOWN`` carrying the exception's text —
honest payload, never a crash, never a swallow.
"""

import time
from collections.abc import AsyncIterator
from typing import Any, Final, cast

import grpc
from google.protobuf.json_format import MessageToDict

from guide.data.grpc.runtime import GrpcRuntime
from guide.domain.grpc.entities import (
    ChatNoteFact,
    GrpcCallOutcome,
    GrpcConsoleRequest,
    GrpcReceivedMessage,
    GrpcStatusCode,
    ViewEventFact,
)
from guide.grpcapi import guide_pb2, guide_pb2_grpc

_KNOWN_STATUS_CODES: Final[frozenset[str]] = frozenset(
    {"OK", "NOT_FOUND", "DEADLINE_EXCEEDED", "UNAVAILABLE", "INVALID_ARGUMENT"}
)
"""The outcome Literal's vocabulary — anything else maps to UNKNOWN."""


def _received(index: int, message: Any) -> GrpcReceivedMessage:
    """One protobuf message as a plain field map (proto names, defaults on)."""
    return GrpcReceivedMessage(
        index=index,
        fields=MessageToDict(
            message,
            preserving_proto_field_name=True,
            always_print_fields_with_no_presence=True,
        ),
    )


async def _view_events(events: list[ViewEventFact]) -> AsyncIterator[Any]:
    """The client-streaming upload: one ViewEvent message per fact."""
    for event in events:
        yield guide_pb2.ViewEvent(slug=event.slug, viewer=event.viewer)


async def _chat_notes(notes: list[ChatNoteFact]) -> AsyncIterator[Any]:
    """The bidirectional upload: one ChatNote message per fact."""
    for note in notes:
        yield guide_pb2.ChatNote(sender=note.sender, text=note.text)


class InProcessGrpcConsole:
    """The domain port's adapter over the shared channel (outbound)."""

    def __init__(self, runtime: GrpcRuntime) -> None:
        self._runtime = runtime

    async def ensure_ready(self) -> str:
        """Delegate to the runtime: start on first use, return the address."""
        return await self._runtime.ensure_started()

    async def call(self, request: GrpcConsoleRequest) -> GrpcCallOutcome:
        """Perform one real round; the outcome is the answer, never a raise."""
        address = await self._runtime.ensure_started()
        stub = guide_pb2_grpc.PostServiceStub(self._runtime.channel)
        timeout = request.deadline_ms / 1000 if request.deadline_ms is not None else None
        started = time.perf_counter()
        messages: list[GrpcReceivedMessage] = []
        status_code: GrpcStatusCode = "OK"
        status_detail = ""
        try:
            if request.method == "get-post":
                reply = await stub.GetPost(
                    guide_pb2.GetPostRequest(slug=request.slug), timeout=timeout
                )
                messages.append(_received(0, reply))
            elif request.method == "stream-posts":
                stream = stub.StreamPosts(
                    guide_pb2.StreamPostsRequest(tag=request.tag), timeout=timeout
                )
                index = 0
                async for reply in stream:
                    messages.append(_received(index, reply))
                    index += 1
            elif request.method == "count-views":
                summary = await stub.CountViews(
                    _view_events(request.view_events), timeout=timeout
                )
                messages.append(_received(0, summary))
            else:  # request.method == "echo-chat"
                stream = stub.EchoChat(_chat_notes(request.chat_notes), timeout=timeout)
                index = 0
                async for echo in stream:
                    messages.append(_received(index, echo))
                    index += 1
        except grpc.aio.AioRpcError as exc:
            name = exc.code().name
            status_code = (
                cast(GrpcStatusCode, name)
                if name in _KNOWN_STATUS_CODES
                else "UNKNOWN"
            )
            status_detail = exc.details() or ""
        except Exception as exc:
            # Reported in the payload (status + detail), never swallowed.
            status_code = "UNKNOWN"
            status_detail = f"gRPC call failed outside RPC status vocabulary: {exc}"
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return GrpcCallOutcome(
            status_code=status_code,
            status_detail=status_detail,
            messages=messages,
            elapsed_ms=elapsed_ms,
            server_address=address,
        )
