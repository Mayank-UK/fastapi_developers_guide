"""Rooms, fanout, and the ceiling: the in-process connection manager.

One manager per app owns every live chat connection. Rooms are plain
dictionaries (this is a single process; a multi-worker deployment would
put a pub/sub bus where the fanout loop sits — topic 22's streams are
that seam). Each member holds its OWN bounded ``asyncio.Queue``: senders
never block on a slow receiver, because the queue is the backpressure
decision point, and it has already made it — a member whose queue is
full has fallen behind by the whole queue depth, so the manager retires
it on the spot (roster removal plus a sentinel that unblocks its send
loop to close the socket). Two ceilings, both enforced here: at most
``max_room_connections`` members per room, checked under the join lock
so concurrent joins cannot both claim the last slot; and the per-
connection queue depth above.

The domain stays transport-free: a ``ManagedConnection`` is a queue plus
identity, and the presentation layer owns the actual ``WebSocket``. The
sentinel is ``None`` — queue items are wire dicts, so ``None`` is an
unambiguous "retire now" instruction to the socket's forwarding loop.
"""

import asyncio
from typing import Any, Final
from uuid import uuid4

MAX_ROOM_CONNECTIONS: Final[int] = 8
"""Members per room — the full-room ceiling (rejection close code 1013)."""

PER_CONNECTION_QUEUE: Final[int] = 32
"""Queued wire messages per connection — the slow-consumer ceiling."""

WireMessage = dict[str, Any]
"""One server-to-client protocol message, sent as the ws JSON frame."""

RETIRE_SENTINEL: Final[None] = None
"""Enqueued to a fallen-behind member: its loop closes the socket (1013)."""


class ManagedConnection:
    """One live member: identity plus its bounded inbound queue."""

    __slots__ = ("id", "name", "queue", "room")

    def __init__(self, *, id: str, room: str, name: str, queue_size: int) -> None:
        """Build a member with its own bounded queue (``queue_size`` deep)."""
        self.id = id
        self.room = room
        self.name = name
        self.queue: asyncio.Queue[WireMessage | None] = asyncio.Queue(maxsize=queue_size)


class RoomFullError(Exception):
    """A join exceeded the room's connection ceiling; reject with 1013."""

    def __init__(self, room: str, capacity: int) -> None:
        super().__init__(f"room {room!r} is at its ceiling of {capacity} connections")
        self.room = room
        self.capacity = capacity


class ConnectionManager:
    """Rooms of bounded-queue members, with ceiling-aware join and fanout."""

    def __init__(
        self,
        *,
        max_room_connections: int = MAX_ROOM_CONNECTIONS,
        queue_size: int = PER_CONNECTION_QUEUE,
    ) -> None:
        self._rooms: dict[str, dict[str, ManagedConnection]] = {}
        self._join_lock = asyncio.Lock()
        self._max_room_connections = max_room_connections
        self._queue_size = queue_size

    @property
    def max_room_connections(self) -> int:
        """The per-room ceiling the demo panel reports."""
        return self._max_room_connections

    @property
    def queue_size(self) -> int:
        """The per-connection queue depth the demo panel reports."""
        return self._queue_size

    async def join(self, room: str, name: str) -> ManagedConnection:
        """Admit one member, or raise ``RoomFullError`` — atomically.

        The lock is what makes the ceiling honest: two joins racing for the
        last slot serialize, and only the first wins.
        """
        async with self._join_lock:
            members = self._rooms.setdefault(room, {})
            if len(members) >= self._max_room_connections:
                raise RoomFullError(room, self._max_room_connections)
            connection = ManagedConnection(
                id=uuid4().hex[:8], room=room, name=name, queue_size=self._queue_size
            )
            members[connection.id] = connection
            return connection

    def leave(self, connection: ManagedConnection) -> bool:
        """Remove one member (idempotent); empty rooms are deleted, not leaked."""
        members = self._rooms.get(connection.room)
        if not members or members.get(connection.id) is not connection:
            return False
        del members[connection.id]
        if not members:
            del self._rooms[connection.room]
        return True

    def roster(self, room: str) -> list[str]:
        """Member names in join order — the panel and the roster frames."""
        return [member.name for member in self._rooms.get(room, {}).values()]

    def room_size(self, room: str) -> int:
        """How many members one room currently holds."""
        return len(self._rooms.get(room, {}))

    def rooms(self) -> list[str]:
        """Every room with at least one member, sorted for stable payloads."""
        return sorted(self._rooms)

    def total_connections(self) -> int:
        """Every live member across all rooms."""
        return sum(len(members) for members in self._rooms.values())

    def broadcast(
        self, room: str, message: WireMessage, *, exclude_id: str | None = None
    ) -> list[str]:
        """Fan one message out to a room's members; retire the fallen-behind.

        ``put_nowait`` is the entire backpressure story: senders never await
        receivers. A full queue means the member is a whole queue-depth
        behind — it is removed from the roster immediately (truth for every
        later broadcast) and handed the retire sentinel so its own loop
        closes the socket. Returns the NAMES of retired members so the
        caller can announce the departure.
        """
        retired: list[str] = []
        for member in tuple(self._rooms.get(room, {}).values()):
            if member.id == exclude_id:
                continue
            try:
                member.queue.put_nowait(message)
            except asyncio.QueueFull:
                self.leave(member)
                self._retire(member)
                retired.append(member.name)
        return retired

    def _retire(self, member: ManagedConnection) -> None:
        """Unblock one queue slot, then enqueue the retire sentinel."""
        try:
            member.queue.get_nowait()
        except asyncio.QueueEmpty:  # pragma: no cover - full queue drained this instant
            pass
        member.queue.put_nowait(RETIRE_SENTINEL)
