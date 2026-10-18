"""The connection manager and chat service: rooms, ceilings, and backfill.

The manager's two ceilings are exercised for real: the join lock makes
the last slot atomic, and a full queue retires its member with the
sentinel. The service tests pin the protocol decisions — say excludes
the sender, announce excludes the joiner, backfill is contiguous-or-
flagged, and departures update the roster without leaking rooms.
"""

import asyncio

import pytest

from guide.domain.realtime.chat import (
    CLOSE_ROOM_FULL,
    HISTORY_CAPACITY,
    ChatRoomService,
    valid_name,
    valid_room,
)
from guide.domain.realtime.manager import (
    MAX_ROOM_CONNECTIONS,
    PER_CONNECTION_QUEUE,
    ConnectionManager,
    RoomFullError,
)


def service_of(
    *, max_room_connections: int = MAX_ROOM_CONNECTIONS, queue_size: int = PER_CONNECTION_QUEUE
) -> ChatRoomService:
    return ChatRoomService(
        ConnectionManager(max_room_connections=max_room_connections, queue_size=queue_size),
        clock=lambda: 42.0,
    )


async def test_join_admits_until_the_ceiling_then_refuses() -> None:
    manager = ConnectionManager(max_room_connections=2, queue_size=4)
    first = await manager.join("lobby", "ada")
    second = await manager.join("lobby", "grace")
    assert manager.roster("lobby") == ["ada", "grace"]
    with pytest.raises(RoomFullError) as raised:
        await manager.join("lobby", "linus")
    assert raised.value.room == "lobby"
    assert raised.value.capacity == 2
    assert manager.roster("lobby") == ["ada", "grace"]  # the refusal changed nothing
    assert first.id != second.id


async def test_concurrent_joins_cannot_both_take_the_last_slot() -> None:
    manager = ConnectionManager(max_room_connections=3, queue_size=4)
    await manager.join("lobby", "ada")
    await manager.join("lobby", "grace")
    outcomes = await asyncio.gather(
        manager.join("lobby", "third"),
        manager.join("lobby", "fourth"),
        manager.join("lobby", "fifth"),
        return_exceptions=True,
    )
    admitted = [outcome for outcome in outcomes if not isinstance(outcome, BaseException)]
    refused = [outcome for outcome in outcomes if isinstance(outcome, RoomFullError)]
    assert len(admitted) == 1
    assert len(refused) == 2
    assert manager.room_size("lobby") == 3


def test_leave_is_idempotent_and_empty_rooms_are_deleted() -> None:
    manager = ConnectionManager(max_room_connections=4, queue_size=4)
    conn = asyncio.run(manager.join("solo", "ada"))
    assert manager.leave(conn) is True
    assert manager.rooms() == []  # the room died with its last member
    assert manager.leave(conn) is False  # second leave: a no-op, not an error
    assert manager.total_connections() == 0


def test_broadcast_reaches_members_but_not_the_excluded_one() -> None:
    manager = ConnectionManager(max_room_connections=4, queue_size=4)
    conn = asyncio.run(manager.join("lobby", "ada"))
    other = asyncio.run(manager.join("lobby", "grace"))
    retired = manager.broadcast("lobby", {"type": "chat"}, exclude_id=conn.id)
    assert retired == []
    assert conn.queue.qsize() == 0
    assert other.queue.qsize() == 1


def test_full_queue_retires_the_member_with_a_sentinel() -> None:
    manager = ConnectionManager(max_room_connections=4, queue_size=2)
    slow = asyncio.run(manager.join("lobby", "slow"))
    fast = asyncio.run(manager.join("lobby", "fast"))
    retired: list[str] = []
    drained = 0
    for index in range(4):  # slow's queue holds 2; the third put must retire it
        retired = retired + manager.broadcast("lobby", {"type": "chat", "seq": index})
        while fast.queue.qsize():  # fast is a live consumer: it keeps draining
            fast.queue.get_nowait()
            drained += 1
    assert retired == ["slow"]
    assert manager.roster("lobby") == ["fast"]  # roster truth, immediately
    assert slow.queue.qsize() == 2  # the discard freed one slot for the sentinel
    assert slow.queue.get_nowait() is not None  # the frame it did manage to queue
    assert slow.queue.get_nowait() is None  # the retire sentinel, after it
    assert drained == 4  # fast received every message, none dropped


def test_valid_room_and_name_patterns() -> None:
    assert valid_room("lobby")
    assert valid_room("terminal-tour")
    assert not valid_room("Lobby")
    assert not valid_room("has space")
    assert not valid_room("")
    assert not valid_room("x" * 25)
    assert valid_name("ada")
    assert valid_name("lob-lawblog")
    assert not valid_name("")
    assert not valid_name("two words")
    assert not valid_name("x" * 25)


async def test_say_records_history_and_excludes_the_sender() -> None:
    service = service_of()
    ada = (await service.join("lobby", "ada", None)).connection
    grace = (await service.join("lobby", "grace", None)).connection
    message = await service.say(ada, "hello")
    assert (message.seq, message.sender, message.text, message.at) == (1, "ada", "hello", 42.0)
    assert ada.queue.qsize() == 0  # senders do not hear themselves
    frame = grace.queue.get_nowait()
    assert frame is not None and frame["type"] == "chat"
    assert frame["chat"]["seq"] == 1
    second = await service.say(grace, "hi back")
    assert second.seq == 2  # one sequence per room, not per member
    assert [message.seq for message in service.recent_messages("lobby")] == [1, 2]


async def test_join_backfill_scrollback_replay_and_gap() -> None:
    service = service_of()
    ada = (await service.join("lobby", "ada", None)).connection
    for index in range(1, 13):  # twelve lines, seq 1..12
        await service.say(ada, f"line-{index}")

    fresh = await service.join("lobby", "newbie", None)
    assert [message.seq for message in fresh.backfill] == [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    assert fresh.gapped is False
    assert fresh.roster == ["ada", "newbie"]

    resumed = await service.join("lobby", "reconnector", since=10)
    assert [message.seq for message in resumed.backfill] == [11, 12]
    assert resumed.gapped is False

    current = await service.join("lobby", "uptodate", since=12)
    assert current.backfill == []
    assert current.gapped is False

    # Beyond the ring: fill history to 59 lines, then ask for an old seq.
    for index in range(13, HISTORY_CAPACITY + 10):
        await service.say(ada, f"line-{index}")
    total = HISTORY_CAPACITY + 9  # 12 + (HISTORY_CAPACITY - 3) lines were said
    gapped_join = await service.join("lobby", "latecomer", since=3)
    assert gapped_join.gapped is True
    assert len(gapped_join.backfill) == HISTORY_CAPACITY
    assert gapped_join.backfill[0].seq == total - HISTORY_CAPACITY + 1
    assert gapped_join.backfill[-1].seq == total


async def test_announce_and_leave_update_the_room_not_the_joiner() -> None:
    service = service_of()
    ada = (await service.join("lobby", "ada", None)).connection
    grace_outcome = await service.join("lobby", "grace", None)
    service.announce("lobby", "grace", except_id=grace_outcome.connection.id)
    ada_note = ada.queue.get_nowait()
    ada_roster = ada.queue.get_nowait()
    assert ada_note is not None and ada_note["type"] == "note"
    assert "grace joined" in ada_note["text"]
    assert ada_roster is not None and ada_roster["members"] == ["ada", "grace"]
    assert grace_outcome.connection.queue.qsize() == 0  # the joiner hears none of it

    service.leave(grace_outcome.connection)
    departure = ada.queue.get_nowait()
    assert departure is not None and departure["type"] == "roster"
    assert departure["members"] == ["ada"]
    service.leave(grace_outcome.connection)  # idempotent: no second roster frame
    assert ada.queue.qsize() == 0


async def test_slow_member_retirement_announces_and_counts() -> None:
    service = service_of(queue_size=2)
    ada = (await service.join("lobby", "ada", None)).connection
    slow = (await service.join("lobby", "slow", None)).connection
    for index in range(3):  # slow (queue 2) is retired by the third line
        await service.say(ada, f"line-{index}")
    stats = service.stats()
    assert stats.slow_retired == 1
    assert stats.messages_sent == 3
    # ada sees the retirement note + updated roster; slow holds the sentinel.
    assert slow.queue.get_nowait() is not None
    assert slow.queue.get_nowait() is None
    kinds = [ada.queue.get_nowait()["type"] for _ in range(ada.queue.qsize())]
    assert "note" in kinds and "roster" in kinds


def test_close_code_vocabulary_is_the_documented_one() -> None:
    assert CLOSE_ROOM_FULL == (1013, "room at capacity — try again later")


async def test_rooms_snapshot_reads_live_facts() -> None:
    service = service_of()
    ada = (await service.join("alpha", "ada", None)).connection
    await service.say(ada, "one")
    snapshots = service.rooms_snapshot()
    assert [snapshot.room for snapshot in snapshots] == ["alpha"]
    assert snapshots[0].members == ["ada"]
    assert snapshots[0].newest_seq == 1
    assert snapshots[0].retained == 1
