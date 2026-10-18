"""The chat protocol and room service: join, say, backfill, close codes.

Where every HTTP failure in this app is ONE envelope, a websocket cannot
send one after the handshake — the protocol's failure vocabulary is CLOSE
CODES plus documented protocol messages, and this module owns both. The
close-code choices, on record:

- ``1000`` — a clean leave (the client disconnected, or asked to).
- ``1008`` — policy violation: an unreadable frame or an invalid
  room/name — the stream can no longer be trusted to carry meaning.
- ``1013`` — try again later: the room was full at join, or the member
  fell a full queue behind (both are "reconnect soon" conditions, not
  errors anyone did wrong).

The message protocol is deliberately tiny and total: clients send
``{"type": "chat", "text": …}`` and ``{"type": "ping"}``; servers send
``joined`` / ``roster`` / ``backfill`` / ``chat`` / ``note`` / ``error``
frames. Unknown-but-well-formed types get an ``error`` frame and the
connection SURVIVES (tolerant reader); a frame that is not JSON at all
earns the 1008 close (a stream you cannot parse is a stream you cannot
trust). Reconnection rides ``?since=<seq>``: the service replays the
room's ring after that seq when it can, and serves the recent window
with ``gapped=true`` when it cannot — the same honest choice the SSE
side makes with Last-Event-ID.
"""

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Final

from guide.core.serialization import CamelModel
from guide.domain.realtime.log import BoundedEventLog
from guide.domain.realtime.manager import (
    ConnectionManager,
    ManagedConnection,
    WireMessage,
)
from guide.domain.realtime.ticker import Clock

ROOM_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9][a-z0-9-]{0,23}$")
"""Room ids: lowercase kebab, 1–24 chars — same family as demo ids."""

NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[^\s]{1,24}$")
"""Member names: 1–24 chars, no whitespace (chat lines stay one line)."""

MAX_TEXT_LENGTH: Final[int] = 500
"""One chat line's ceiling — long essays belong to the posts resource."""

HISTORY_CAPACITY: Final[int] = 50
"""Backfill window: how many messages each room's ring retains."""

SCROLLBACK_COUNT: Final[int] = 10
"""What a fresh join sees as context (a reconnect may see the full ring)."""

CLOSE_OK: Final[tuple[int, str]] = (1000, "left the room")
CLOSE_PROTOCOL: Final[tuple[int, str]] = (1008, "unreadable frame or invalid join — closing")
CLOSE_ROOM_FULL: Final[tuple[int, str]] = (1013, "room at capacity — try again later")
CLOSE_SLOW_CONSUMER: Final[tuple[int, str]] = (
    1013,
    "fell a full queue behind — reconnect with ?since=<seq>",
)


class ChatMessage(CamelModel):
    """One chat line; the wire shape inside ``backfill`` and ``chat`` frames."""

    seq: int
    sender: str
    text: str
    at: float


@dataclass(frozen=True, slots=True)
class JoinOutcome:
    """Everything a joining member receives before live traffic starts."""

    connection: ManagedConnection
    backfill: list[ChatMessage]
    gapped: bool
    roster: list[str]


@dataclass(frozen=True, slots=True)
class RoomSnapshot:
    """One room as the demo panel sees it (read-only, no connections)."""

    room: str
    members: list[str]
    newest_seq: int | None
    retained: int


def valid_room(room: str) -> bool:
    """Room ids are lowercase kebab — the pattern, not the mood, decides."""
    return bool(ROOM_PATTERN.fullmatch(room))


def valid_name(name: str) -> bool:
    """Names are single-token, 1–24 chars — no whitespace, no empty string."""
    return bool(NAME_PATTERN.fullmatch(name))


@dataclass(frozen=True, slots=True)
class ChatStats:
    """The firehose counters the demo panel serves."""

    messages_sent: int
    slow_retired: int
    live_connections: int


class ChatRoomService:
    """Rooms over the manager: history, sequences, and the protocol frames."""

    def __init__(
        self,
        manager: ConnectionManager,
        *,
        clock: Clock | None = None,
        history_capacity: int = HISTORY_CAPACITY,
        scrollback: int = SCROLLBACK_COUNT,
    ) -> None:
        self._manager = manager
        self._clock: Clock = clock or time.time
        self._history_capacity = history_capacity
        self._scrollback = scrollback
        self._histories: dict[str, BoundedEventLog[ChatMessage]] = {}
        self._next_seq: dict[str, int] = {}
        self._messages_sent = 0
        self._slow_retired = 0

    @property
    def manager(self) -> ConnectionManager:
        """The rooms/queues/ceilings half — the panel reads its facts."""
        return self._manager

    def stats(self) -> ChatStats:
        """The counters (process-local by design, like the caching lab)."""
        return ChatStats(
            messages_sent=self._messages_sent,
            slow_retired=self._slow_retired,
            live_connections=self._manager.total_connections(),
        )

    def _history(self, room: str) -> BoundedEventLog[ChatMessage]:
        """The room's ring, created on first touch (rooms are born empty)."""
        history = self._histories.get(room)
        if history is None:
            history = BoundedEventLog[ChatMessage](self._history_capacity)
            self._histories[room] = history
        return history

    def _backfill(self, room: str, since: int | None) -> tuple[list[ChatMessage], bool]:
        """The reconnect window: contiguous replay, or the tail marked gapped."""
        history = self._histories.get(room)
        if history is None or not len(history):
            return [], False
        if since is None:
            return history.tail(self._scrollback), False
        replay = history.events_after(since)
        if replay:
            return replay, False
        if (history.newest_seq or 0) <= since:
            return [], False  # already current: nothing missed, nothing to send
        tail = history.tail(self._history_capacity)
        return tail, True  # the ring cannot reach back to `since` — best effort

    async def join(self, room: str, name: str, since: int | None) -> JoinOutcome:
        """Admit a member and shape everything it receives on entry.

        Raises ``RoomFullError`` (the manager's ceiling) for the caller to
        translate into the 1013 close; the room announcement follows from
        the caller once the socket has actually accepted.
        """
        connection = await self._manager.join(room, name)
        backfill, gapped = self._backfill(room, since)
        return JoinOutcome(
            connection=connection,
            backfill=backfill,
            gapped=gapped,
            roster=self._manager.roster(room),
        )

    async def say(self, connection: ManagedConnection, text: str) -> ChatMessage:
        """Record and broadcast one chat line (the sender is excluded)."""
        room = connection.room
        self._next_seq[room] = self._next_seq.get(room, 0) + 1
        message = ChatMessage(
            seq=self._next_seq[room], sender=connection.name, text=text, at=self._clock()
        )
        self._history(room).append(message.seq, message)
        self._messages_sent += 1
        retired = self._manager.broadcast(
            room, chat_frame(message), exclude_id=connection.id
        )
        if retired:
            self._slow_retired += len(retired)
            self.broadcast_note(room, f"{' and '.join(retired)} fell behind and was retired")
            self.broadcast_roster(room)
        return message

    def leave(self, connection: ManagedConnection) -> None:
        """Depart a member (idempotent) and tell the room its new roster."""
        if self._manager.leave(connection):
            self.broadcast_roster(connection.room)

    def deliver(self, connection: ManagedConnection, frame: WireMessage) -> bool:
        """Enqueue a personal frame (pong, error) on the member's own queue.

        Replies ride the SAME queue as room traffic so the member observes
        one strict order; False means the member's queue is full — it is
        already a retirement candidate, so the reply is dropped and logged
        by the caller.
        """
        try:
            connection.queue.put_nowait(frame)
            return True
        except asyncio.QueueFull:
            return False

    def broadcast_roster(self, room: str, *, exclude_id: str | None = None) -> None:
        """The room's current membership to every member (minus one)."""
        self._manager.broadcast(
            room,
            {"type": "roster", "members": self._manager.roster(room)},
            exclude_id=exclude_id,
        )

    def broadcast_note(self, room: str, text: str, *, exclude_id: str | None = None) -> None:
        """A system note the room sees but the history does not keep."""
        self._manager.broadcast(room, {"type": "note", "text": text}, exclude_id=exclude_id)

    def announce(self, room: str, name: str, *, except_id: str) -> None:
        """Tell the room — minus its newest member — who just joined."""
        self.broadcast_note(room, f"{name} joined", exclude_id=except_id)
        self.broadcast_roster(room, exclude_id=except_id)

    def rooms_snapshot(self) -> list[RoomSnapshot]:
        """Every live room with roster and history facts — the demo panel."""
        snapshots: list[RoomSnapshot] = []
        for room in self._manager.rooms():
            history = self._histories.get(room)
            snapshots.append(
                RoomSnapshot(
                    room=room,
                    members=self._manager.roster(room),
                    newest_seq=history.newest_seq if history else None,
                    retained=len(history) if history else 0,
                )
            )
        return snapshots

    def recent_messages(self, room: str, count: int = SCROLLBACK_COUNT) -> list[ChatMessage]:
        """The last messages of a room's history (the panel's transcript)."""
        history = self._histories.get(room)
        return history.tail(count) if history else []


def chat_frame(message: ChatMessage) -> WireMessage:
    """The live ``chat`` wire frame (camelCase, the family's wire rule)."""
    return {"type": "chat", "chat": message.model_dump(by_alias=True)}
