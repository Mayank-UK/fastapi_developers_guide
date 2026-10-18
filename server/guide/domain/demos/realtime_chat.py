"""The realtime chat demo payload: the panel over the live rooms.

Demo ``realtime:chat`` (topic 28, INLINE in the WebSockets section): the
panel shows the rooms that exist RIGHT NOW — rosters, retained history,
the ceiling facts (members per room, queue depth, the close codes) — and
the recent transcript, while the live conversation happens over the
websocket the panel points at. Pure shaping over the chat service; no
state lives here.
"""

from typing import Final

from guide.core.serialization import CamelModel
from guide.domain.realtime.chat import (
    HISTORY_CAPACITY,
    SCROLLBACK_COUNT,
    ChatMessage,
    ChatRoomService,
)
from guide.domain.realtime.manager import (
    MAX_ROOM_CONNECTIONS,
    PER_CONNECTION_QUEUE,
)

SOCKET_PATH_TEMPLATE: Final = "/api/realtime/chat/{room}"
"""The live websocket the panel points clients at (plus ?name= and ?since=)."""


class EndpointRow(CamelModel):
    """One demo endpoint: the path and what trying it teaches."""

    path: str
    method: str
    teaches: str


class CloseCodeRow(CamelModel):
    """One documented close code: the number and when the server sends it."""

    code: int
    reason: str
    when: str


class RoomRow(CamelModel):
    """One live room: roster, history facts, and the recent transcript."""

    room: str
    members: list[str]
    newest_seq: int | None
    retained: int


class MessageRow(CamelModel):
    """One recent chat line (the panel's transcript slice)."""

    seq: int
    sender: str
    text: str
    at: float


class ChatPolicyRow(CamelModel):
    """The room's fixed facts: ceilings, windows, validation rules."""

    max_room_connections: int
    per_connection_queue: int
    history_capacity: int
    scrollback: int
    room_pattern: str
    name_pattern: str


class ChatStatsRow(CamelModel):
    """The firehose counters, live from the service."""

    messages_sent: int
    slow_retired: int
    live_connections: int


class ChatPanel(CamelModel):
    """Wire shape of ``GET /api/demo/realtime/chat`` — the panel's contract."""

    policy: ChatPolicyRow
    close_codes: list[CloseCodeRow]
    rooms: list[RoomRow]
    recent_messages: list[MessageRow]
    stats: ChatStatsRow
    endpoints: list[EndpointRow]
    honesty_notes: list[str]
    reasoning: str


def _message_row(message: ChatMessage) -> MessageRow:
    return MessageRow(
        seq=message.seq, sender=message.sender, text=message.text, at=message.at
    )


def build_chat_panel(service: ChatRoomService, *, room: str | None = None) -> ChatPanel:
    """The panel: ceiling facts, close-code table, live rooms, transcript.

    ``room`` selects whose transcript and roster lead the panel (the demo
    client passes the room it is about to join); without it the most
    recently active room — or none — serves.
    """
    snapshots = service.rooms_snapshot()
    selected = next((s for s in snapshots if s.room == room), snapshots[-1] if snapshots else None)
    stats = service.stats()
    return ChatPanel(
        policy=ChatPolicyRow(
            max_room_connections=MAX_ROOM_CONNECTIONS,
            per_connection_queue=PER_CONNECTION_QUEUE,
            history_capacity=HISTORY_CAPACITY,
            scrollback=SCROLLBACK_COUNT,
            room_pattern="^[a-z0-9][a-z0-9-]{0,23}$",
            name_pattern="1-24 chars, no whitespace",
        ),
        close_codes=[
            CloseCodeRow(code=1000, reason="left the room", when="the client disconnects cleanly"),
            CloseCodeRow(
                code=1008,
                reason="unreadable frame or invalid join",
                when="the stream can no longer be trusted to carry meaning",
            ),
            CloseCodeRow(
                code=1013,
                reason="room full, or queue overflow",
                when="reconnect soon — the ceilings, not an error anyone made",
            ),
        ],
        rooms=[
            RoomRow(room=s.room, members=s.members, newest_seq=s.newest_seq, retained=s.retained)
            for s in snapshots
        ],
        recent_messages=(
            [_message_row(message) for message in service.recent_messages(selected.room)]
            if selected
            else []
        ),
        stats=ChatStatsRow(
            messages_sent=stats.messages_sent,
            slow_retired=stats.slow_retired,
            live_connections=stats.live_connections,
        ),
        endpoints=[
            EndpointRow(
                path=SOCKET_PATH_TEMPLATE,
                method="WS",
                teaches="join with ?name=, chat, ping — reconnect with ?since=<seq>",
            ),
        ],
        honesty_notes=[
            "rooms and history are process-local (one uvicorn worker) — a second "
            "worker would need the pub/sub seam topic 22 teaches",
            "the sender does not receive its own message echoed back",
            "name and room are validated before the handshake is accepted",
        ],
        reasoning=(
            "Fanout over bounded per-connection queues: senders never wait for "
            "slow receivers, and a member a full queue behind is retired with a "
            "close code that says reconnect, not a crash that says broken."
        ),
    )
