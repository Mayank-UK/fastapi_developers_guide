"""The redis-backed messaging adapter: streams, groups, dedupe set.

``RedisStreams`` implements the ``StreamProducer``, ``StreamConsumer``
and ``ProcessedEventStore`` ports over the SHARED redis.asyncio client
built by ``guide.data.redis.client`` (same 2-second socket timeouts,
same ``decode_responses=True`` str guarantee — the casts below carry
that across redis-py's bytes-typed stubs, exactly like the cache store).
Every method is one awaited redis command wrapped in the optional-service
context manager: unreachable Redis degrades the messaging demos to the
``service_unavailable`` envelope fast, and the app keeps serving.

Two translations carry real semantics and are called out where they
happen: ``ensure_group`` treats BUSYGROUP as success (idempotent group
creation — the group already existing is the common case, not an error),
and ``claim`` drops XAUTOCLAIM's third reply element (ids it CLEARED
from the pending list because the stream entries were trimmed away —
with this guide's no-trimming streams that list is always empty, but
the adapter still speaks the honest shape rather than assuming it).

The demo creates its group at ``0-0`` so a group born after appends
still sees the whole log — the replay property section two teaches;
production usually births groups at ``$`` (only future entries) because
a NEW group rarely wants history.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Final, cast

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError, ResponseError

from guide.core.errors import AppError, FailureKind
from guide.domain.messaging.ports import (
    EventDraft,
    PendingRow,
    StreamEntryRow,
)

logger = structlog.get_logger()

FIELD_EVENT_ID: Final = "event_id"
FIELD_EVENT_TYPE: Final = "type"
FIELD_PAYLOAD: Final = "payload"
"""The wire field names inside every stream entry this guide appends."""

GROUP_START_ID: Final = "0-0"
"""Where a new consumer group starts reading: the beginning of the log."""

type StreamField = bytes | bytearray | memoryview[int] | str | int | float
"""redis-py's stream field type — keys and values may be any of these;
this guide only ever sends str, but the stub speaks the full union. The
``type`` statement keeps the union LAZY (memoryview is not subscriptable
at runtime), so the alias is a mypy-only spelling."""

type ReplyPair = tuple[str, dict[str, str]]
"""One (entry-id, fields) reply pair, post-decode_responses: plain str."""


@contextmanager
def _map_messaging_failures(operation: str) -> Iterator[None]:
    """Optional-service discipline: Redis trouble becomes service_unavailable."""
    try:
        yield
    except AppError:
        raise
    except (RedisError, OSError) as exc:
        logger.warning(
            "messaging_store_unavailable",
            operation=operation,
            error=type(exc).__name__,
            detail=str(exc),
        )
        raise AppError(
            FailureKind.SERVICE_UNAVAILABLE,
            "Redis is unreachable — this demo's streams are the subject, so it "
            "refuses to pretend delivery happened (the app keeps serving "
            "everything else).",
        ) from exc


def _encode(draft: EventDraft) -> dict[StreamField, StreamField]:
    """The entry's wire fields — flat strings; the stream never interprets them.

    Typed as the stub's full field union (dict values are invariant, so a
    narrower ``dict[str, str]`` would not satisfy it) — every VALUE this
    guide writes is a str.
    """
    return {
        FIELD_EVENT_ID: draft.event_id,
        FIELD_EVENT_TYPE: draft.event_type,
        FIELD_PAYLOAD: draft.payload,
    }


def _decode(entry_id: str, fields: dict[str, str]) -> StreamEntryRow:
    """One (id, fields) reply pair into the domain's entry row."""
    return StreamEntryRow(
        id=entry_id,
        event_id=fields[FIELD_EVENT_ID],
        event_type=fields[FIELD_EVENT_TYPE],
        payload=fields[FIELD_PAYLOAD],
    )


class RedisStreams:
    """The live-Redis adapter behind both messaging demos."""

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def append(self, stream: str, draft: EventDraft) -> str:
        """XADD — the broker answers the entry id it minted (ms-seq)."""
        with _map_messaging_failures("append"):
            return cast("str", await self._client.xadd(stream, _encode(draft)))

    async def ensure_group(self, stream: str, group: str) -> None:
        """XGROUP CREATE with MKSTREAM — BUSYGROUP means already done."""
        with _map_messaging_failures("ensure_group"):
            try:
                await self._client.xgroup_create(
                    stream, group, id=GROUP_START_ID, mkstream=True
                )
            except ResponseError as exc:
                # redis-py 8 carries BUSYGROUP as a plain ResponseError; the
                # group existing is the common case, so it is success here.
                if "BUSYGROUP" not in str(exc):
                    raise

    async def read_new(
        self, stream: str, group: str, consumer: str, count: int
    ) -> list[StreamEntryRow]:
        """XREADGROUP '>' as one consumer — entries never delivered to the group."""
        with _map_messaging_failures("read_new"):
            # decode_responses=True keeps every id/field a str; redis-py answers
            # XREADGROUP as a list of [stream, entries] pairs (even for one
            # stream), so the cast carries both guarantees across the stub.
            reply = cast(
                "list[tuple[str, list[ReplyPair]]] | None",
                await self._client.xreadgroup(group, consumer, {stream: ">"}, count=count),
            )
            pairs: list[ReplyPair] = []
            for reply_stream, reply_entries in reply or []:
                if reply_stream == stream:
                    pairs = reply_entries
            return [_decode(str(entry_id), fields) for entry_id, fields in pairs]

    async def ack(self, stream: str, group: str, entry_ids: Sequence[str]) -> int:
        """XACK — how many entries left the group's pending list (the PEL)."""
        with _map_messaging_failures("ack"):
            return int(await self._client.xack(stream, group, *entry_ids))

    async def pending(self, stream: str, group: str, count: int) -> list[PendingRow]:
        """XPENDING's range form — owner, idle milliseconds, delivery count."""
        with _map_messaging_failures("pending"):
            raw = await self._client.xpending_range(
                stream, group, min="-", max="+", count=count
            )
            return [
                PendingRow(
                    entry_id=str(row["message_id"]),
                    consumer=str(row["consumer"]),
                    idle_ms=int(row["time_since_delivered"]),
                    deliveries=int(row["times_delivered"]),
                )
                for row in raw
            ]

    async def claim(
        self, stream: str, group: str, consumer: str, min_idle_ms: int, count: int
    ) -> list[StreamEntryRow]:
        """XAUTOCLAIM — pending entries idle past the threshold change owner."""
        with _map_messaging_failures("claim"):
            reply = await self._client.xautoclaim(
                stream, group, consumer, min_idle_time=min_idle_ms, count=count
            )
            pairs = cast("list[ReplyPair]", reply[1])
            # reply[2] (ids XAUTOCLAIM cleared because their entries were
            # trimmed) is dropped: this guide never trims its demo streams.
            return [_decode(entry_id, fields) for entry_id, fields in pairs]

    async def entries(self, stream: str) -> list[StreamEntryRow]:
        """XRANGE over the whole log — id order, replay included."""
        with _map_messaging_failures("entries"):
            pairs = cast(
                "list[tuple[str, dict[str, str]]]", await self._client.xrange(stream)
            )
            return [_decode(entry_id, fields) for entry_id, fields in pairs]

    async def seen(self, set_key: str, event_id: str) -> bool:
        """SISMEMBER — has this event id been processed already?"""
        with _map_messaging_failures("seen"):
            return bool(await self._client.sismember(set_key, event_id))

    async def remember(self, set_key: str, event_id: str) -> None:
        """SADD — record the event id AFTER its work completed."""
        with _map_messaging_failures("remember"):
            await self._client.sadd(set_key, event_id)
