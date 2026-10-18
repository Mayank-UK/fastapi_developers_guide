"""The realtime endpoints (topic 28): the SSE ticker and the WS chat rooms.

Two protocols, one thinness rule. The SSE route is an ordinary FastAPI
handler that returns a ``StreamingResponse`` — media type, cache, and
proxy headers stated explicitly (``no-cache`` because a cached event
stream is a dead one; ``X-Accel-Buffering: no`` because nginx otherwise
buffers the whole body before forwarding a single tick) — with the body
generator the domain owns and the disconnect probe the Request owns.

The websocket route is the one place a router legitimately holds a loop:
the socket IS the transport. Everything decidable lives in the domain
service (join, ceilings, history, fanout); this file shuttles frames —
accept, the entry frames, then a forwarding task that drains the member's
queue to the socket while the receive loop reads client frames, and a
``finally`` that always departs the member (no roster leaks, even on a
crash mid-conversation). Failures speak the protocol's vocabulary, not
the HTTP envelope: close codes for connection-level verdicts, ``error``
frames for message-level misuse — the divergence topic 28 teaches. A
vanished client surfaces as ``WebSocketDisconnect`` out of either loop,
and the finally does the cleanup.

Endpoint map (prefix ``/api/realtime``):

- ``GET  /ticker``      — the SSE stream (``Last-Event-ID`` honored)
- ``WS   /chat/{room}`` — the chat room (``?name=`` required, ``?since=`` optional)
"""

import asyncio
import json
from typing import Annotated, Final

import structlog
from fastapi import APIRouter, Depends, Header, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from guide.core.errors import AppError, FailureKind
from guide.domain.realtime.chat import (
    CLOSE_PROTOCOL,
    CLOSE_ROOM_FULL,
    CLOSE_SLOW_CONSUMER,
    MAX_TEXT_LENGTH,
    ChatRoomService,
    valid_name,
    valid_room,
)
from guide.domain.realtime.frames import SSE_MEDIA_TYPE
from guide.domain.realtime.manager import ManagedConnection, RoomFullError
from guide.domain.realtime.ticker import (
    DEFAULT_RETRY_MS,
    TickerService,
    stream_ticker_frames,
)

router = APIRouter(prefix="/api/realtime", tags=["realtime"])

logger = structlog.get_logger()

TICKER_ROUTE: Final = "/ticker"
CHAT_ROUTE: Final = "/chat/{room}"
"""The router's paths (prefix-relative) — the terminal companion names them."""

STREAM_HEADERS: Final[dict[str, str]] = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}
"""Every event-stream response carries both — a cached or proxy-buffered
stream is precisely the failure this topic exists to avoid."""


def get_ticker_service(request: Request) -> TickerService:
    """FastAPI dependency: the shared ticker service (wired in create_app)."""
    service = request.app.state.ticker_service
    if not isinstance(service, TickerService):
        raise AppError(FailureKind.INTERNAL, "ticker service not wired on app.state")
    return service


def get_chat_service(websocket: WebSocket) -> ChatRoomService:
    """FastAPI dependency: the chat room service (wired in create_app).

    Takes the ``WebSocket`` — websocket-route dependencies resolve from the
    ws scope, where a ``Request`` annotation cannot be satisfied.
    """
    service = websocket.app.state.chat_service
    if not isinstance(service, ChatRoomService):
        raise AppError(FailureKind.INTERNAL, "chat service not wired on app.state")
    return service


TickerDep = Annotated[TickerService, Depends(get_ticker_service)]
ChatDep = Annotated[ChatRoomService, Depends(get_chat_service)]


def _parse_last_event_id(header: str | None) -> int | None:
    """The Last-Event-ID header → its seq, or None for a fresh stream.

    The header is only ever set by an EventSource reconnecting with the id
    this server framed — anything else is a client bug worth the standard
    422 envelope, not a silent ignore (the one-taxonomy discipline holds
    on the SSE route, which is still plain HTTP).
    """
    if header is None:
        return None
    candidate = header.strip()
    if not candidate.isdigit():
        raise AppError(
            FailureKind.VALIDATION_FAILED,
            "last-event-id must be the numeric event id the server framed",
            {"received": candidate[:32]},
        )
    return int(candidate)


@router.get(TICKER_ROUTE)
async def stream_ticker(
    request: Request,
    service: TickerDep,
    limit: Annotated[int, Query(ge=0, le=1000)] = 0,
    pace_ms: Annotated[int, Query(alias="paceMs", ge=50, le=5000)] = 750,
    keepalive_every: Annotated[int, Query(alias="keepaliveEvery", ge=0, le=50)] = 4,
    last_event_id_header: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """The live ticker as ``text/event-stream``: replay, then paced ticks.

    ``limit`` bounds the LIVE ticks (0 = stream until the client leaves) so
    tests and the terminal tour get finite streams; pacing is a labeled
    simulation over the deterministic price walk. The response flows
    through the pure-ASGI request-id middleware unbuffered — x-request-id
    rides the start message and every tick passes the layer untouched.
    """
    last_event_id = _parse_last_event_id(last_event_id_header)
    frames = stream_ticker_frames(
        service,
        last_event_id=last_event_id,
        limit=limit,
        pace_seconds=pace_ms / 1000,
        keepalive_every=keepalive_every,
        retry_ms=DEFAULT_RETRY_MS,
        is_disconnected=request.is_disconnected,
    )
    return StreamingResponse(frames, media_type=SSE_MEDIA_TYPE, headers=STREAM_HEADERS)


async def _drain_member_queue(websocket: WebSocket, connection: ManagedConnection) -> None:
    """Forward one member's queue frames to its socket — its only sender.

    One task per member means writes never interleave. A ``None`` item is
    the manager's verdict that the member fell a full queue behind: close
    1013 (reconnect soon, with ``?since=``) and stop — the handler's
    finally departs the member from the roster. A send onto an already-
    gone socket is logged and ends the loop (nothing left to deliver).
    """
    try:
        while True:
            item = await connection.queue.get()
            if item is None:
                await websocket.close(
                    code=CLOSE_SLOW_CONSUMER[0], reason=CLOSE_SLOW_CONSUMER[1]
                )
                return
            await websocket.send_json(item)
    except asyncio.CancelledError:
        raise
    except (RuntimeError, WebSocketDisconnect) as error:
        logger.warning(
            "chat_forward_stopped",
            room=connection.room,
            member=connection.name,
            reason=repr(error),
        )


@router.websocket(CHAT_ROUTE)
async def chat_socket(
    websocket: WebSocket,
    room: str,
    service: ChatDep,
    name: str = "",
    since: Annotated[str | None, Query()] = None,
) -> None:
    """One chat member's connection: validate, join, then shuttle frames.

    Raw strings for ``name``/``since`` on purpose — a websocket cannot
    answer a 422, so the route validates and refuses the handshake with
    the 1008 close itself.
    """
    since_seq: int | None = None
    if since is not None:
        if not since.strip().isdigit():
            await websocket.close(code=CLOSE_PROTOCOL[0], reason="since must be numeric")
            return
        since_seq = int(since)
    if not valid_room(room) or not valid_name(name):
        # Join facts are wrong before any conversation exists — refuse the
        # handshake outright with the policy close code.
        await websocket.close(code=CLOSE_PROTOCOL[0], reason=CLOSE_PROTOCOL[1])
        return

    await websocket.accept()
    try:
        outcome = await service.join(room, name, since_seq)
    except RoomFullError:
        # The ceiling verdict: a documented error frame, then the 1013 close
        # (browsers see the code only after accept — which is why accept came
        # first).
        await websocket.send_json(
            {"type": "error", "code": "room_full", "message": CLOSE_ROOM_FULL[1]}
        )
        await websocket.close(code=CLOSE_ROOM_FULL[0], reason=CLOSE_ROOM_FULL[1])
        return

    connection = outcome.connection
    forward = asyncio.create_task(_drain_member_queue(websocket, connection))
    try:
        await websocket.send_json(
            {
                "type": "joined",
                "room": room,
                "name": name,
                "gapped": outcome.gapped,
                "historyWindow": len(outcome.backfill),
            }
        )
        await websocket.send_json({"type": "roster", "members": outcome.roster})
        if outcome.backfill:
            await websocket.send_json(
                {
                    "type": "backfill",
                    "messages": [
                        message.model_dump(by_alias=True) for message in outcome.backfill
                    ],
                    "gapped": outcome.gapped,
                }
            )
        service.announce(room, name, except_id=connection.id)

        while True:
            raw = await websocket.receive_text()
            try:
                frame = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.close(code=CLOSE_PROTOCOL[0], reason=CLOSE_PROTOCOL[1])
                return
            verdict = _validate_client_frame(frame)
            if verdict is not None:
                code, message = verdict
                if not service.deliver(
                    connection, {"type": "error", "code": code, "message": message}
                ):
                    logger.warning("chat_reply_dropped", room=room, member=name, code=code)
                continue
            kind = frame["type"]
            if kind == "chat":
                await service.say(connection, frame["text"])
            elif kind == "ping":
                # Replies ride the member's queue so one strict frame order
                # holds on the socket — a pong never jumps queued room traffic.
                if not service.deliver(connection, {"type": "pong"}):
                    logger.warning("chat_reply_dropped", room=room, member=name, code="pong")
            # no else: _validate_client_frame already rejected unknown types
    except WebSocketDisconnect:
        pass  # the client left — the finally departs the member
    finally:
        forward.cancel()
        try:
            await forward
        except asyncio.CancelledError:
            pass
        service.leave(connection)


def _validate_client_frame(frame: object) -> tuple[str, str] | None:
    """Validate (and normalize) one inbound frame: the error verdict, or None.

    A tolerant reader on purpose: unknown-but-well-formed types and bad
    payloads earn an ``error`` frame and the connection SURVIVES; only an
    unparseable frame (closed upstream) is fatal. On success the frame's
    ``text`` is normalized in place (stripped) — validation is this seam's
    one side effect, and callers treat the frame as trusted afterwards.
    """
    if not isinstance(frame, dict) or "type" not in frame:
        return ("malformed", 'frames are {"type": …} objects')
    kind = frame["type"]
    if kind not in ("chat", "ping"):
        return ("unknown_type", f"unknown frame type {kind!r}")
    if kind == "chat":
        text = frame.get("text")
        if not isinstance(text, str) or not text.strip():
            return ("empty_text", "chat text required")
        if len(text) > MAX_TEXT_LENGTH:
            return ("text_too_long", f"chat text capped at {MAX_TEXT_LENGTH} chars")
        frame["text"] = text.strip()
    return None
