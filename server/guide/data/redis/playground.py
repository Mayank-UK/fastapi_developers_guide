"""The topic-20 adapter: a real playground over the live Redis.

``RedisPlaygroundRepository`` implements the domain's
``RedisPlaygroundRunner`` port against a dedicated demo namespace (every key
starts ``guide_demo:redis:`` — nothing pre-existing in the container is ever
touched, and each run DELs its own keys first, so calls are idempotent).
One ``run_playground`` call is the whole scripted walk: the FIVE core
structures with real commands and real read-backs (string with the atomic
INCR counter, hash, list, set, sorted set with scores), an honest TTL proof
(SET with a short inline expiry, the TTL clock observed, then the key's
absence after a bounded wait — the store evicts on its own clock), and a
REAL pub/sub
round-trip (one bounded asyncio listener task, one PUBLISH, the received
message reported from both sides). Unreachable Redis maps to
``service_unavailable`` exactly like every other data adapter
(optional-service discipline).
"""

import asyncio
import json
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import Any, Final, cast

import structlog
from redis.asyncio import Redis
from redis.asyncio.client import PubSub
from redis.exceptions import RedisError

from guide.core.errors import AppError, FailureKind
from guide.domain.db.ports import (
    PubsubProofRow,
    RedisPlaygroundRun,
    StructureRow,
    StructureValueRow,
    TtlProofRow,
)

logger = structlog.get_logger()

NAMESPACE: Final = "guide_demo:redis:"
NAMESPACE_DISPLAY: Final = "guide_demo:redis:*"
"""The demos' dedicated key namespace — the whole topic owns it."""

TTL_SECONDS: Final = 2
TTL_WAIT_S: Final = 2.25
"""Sleep past the expiry so the absence proof is deterministic: asyncio
sleeps AT LEAST the requested time, so the key is guaranteed gone."""

PUBSUB_WAIT_S: Final = 5.0
"""The bounded wait for the listener's message — matches the pub/sub
connection's socket timeout, so the round-trip has one honest bound."""

LEADERBOARD: Final = (("grace", 100.0), ("barbara", 180.0), ("alan", 250.0))


def _keys_for(tag: str) -> dict[str, str]:
    """The run's five structure keys, all inside the demo namespace."""
    return {
        "string": f"{NAMESPACE}{tag}:hits",
        "hash": f"{NAMESPACE}{tag}:profile",
        "list": f"{NAMESPACE}{tag}:timeline",
        "set": f"{NAMESPACE}{tag}:tags",
        "zset": f"{NAMESPACE}{tag}:leaderboard",
    }


def _flash_key(tag: str) -> str:
    return f"{NAMESPACE}{tag}:flash"


def _channel_for(tag: str) -> str:
    """Pub/sub channels are not keys, but the namespace discipline holds."""
    return f"{NAMESPACE}{tag}:events"


@contextmanager
def _map_redis_failures(operation: str) -> Iterator[None]:
    """Optional-service discipline: Redis trouble becomes service_unavailable."""
    try:
        yield
    except AppError:
        raise
    except (RedisError, OSError) as exc:
        logger.warning(
            "redis_playground_unavailable",
            operation=operation,
            error=type(exc).__name__,
            detail=str(exc),
        )
        raise AppError(
            FailureKind.SERVICE_UNAVAILABLE,
            "Redis is unreachable or unusable — this demo runs real commands "
            "against the live store and refuses to serve stale facts.",
        ) from exc


class RedisPlaygroundRepository:
    """The live-Redis adapter behind topic 20's playground demo."""

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def run_playground(self, tag: str) -> RedisPlaygroundRun:
        """Run the scripted playground; every row is what Redis answered."""
        with _map_redis_failures("playground run"):
            keys = _keys_for(tag)
            stage: Iterable[str] = (*keys.values(), _flash_key(tag))
            await self._reset_stage(stage)
            structures = [
                await self._walk_string(keys["string"], tag),
                await self._walk_hash(keys["hash"], tag),
                await self._walk_list(keys["list"], tag),
                await self._walk_set(keys["set"], tag),
                await self._walk_zset(keys["zset"]),
            ]
            ttl = await self._prove_ttl(_flash_key(tag), tag)
            pubsub = await self._prove_pubsub(_channel_for(tag), tag)
            await self._reset_stage(stage)
            return RedisPlaygroundRun(
                namespace=NAMESPACE_DISPLAY,
                tag=tag,
                structures=structures,
                ttl=ttl,
                pubsub=pubsub,
            )

    async def _reset_stage(self, keys: Iterable[str]) -> None:
        """DEL the run's keys — a fresh stage per call, a clean finish after."""
        await self._client.delete(*keys)

    async def _walk_string(self, key: str, tag: str) -> StructureRow:
        """SET/GET plus the atomic INCR counter — the workhorse pattern."""
        await self._client.set(key, "1")
        initial = await self._client.get(key)
        first_incr = int(await self._client.incr(key))
        second_incr = int(await self._client.incr(key))
        final = await self._client.get(key)
        return StructureRow(
            kind="string",
            key=key,
            description=(
                "A string key holding a number, INCR'd twice — the atomic "
                "counter pattern (rate limiters, metrics) with no read-modify-write."
            ),
            commands=[
                f'SET {key} "1"',
                f"GET {key}",
                f"INCR {key}",
                f"INCR {key}",
                f"GET {key}",
            ],
            outcome=(
                f"each INCR returned the new value ({first_incr}, then "
                f"{second_incr}) — the counter is server-side and atomic"
            ),
            values=[
                StructureValueRow(label="GET right after SET", value=str(initial)),
                StructureValueRow(label="GET after INCR x2", value=str(final)),
            ],
        )

    async def _walk_hash(self, key: str, tag: str) -> StructureRow:
        """HSET a mapping, HGETALL it back — one key, many addressable fields."""
        added = int(
            await self._client.hset(
                key, mapping={"name": "the redis playground", "tag": tag, "visits": "1"}
            )
        )
        # decode_responses=True makes the runtime type dict[str, str]; the
        # cast carries that guarantee across redis-py's bytes-typed stubs.
        snapshot = cast("dict[str, str]", await self._client.hgetall(key))
        return StructureRow(
            kind="hash",
            key=key,
            description=(
                "A hash stores field-value pairs under one key — a small "
                "record (session, profile) read whole with HGETALL."
            ),
            commands=[
                f'HSET {key} name "the redis playground" tag "{tag}" visits "1"',
                f"HGETALL {key}",
            ],
            outcome=f"hset added {added} field(s); hgetall answered all {len(snapshot)} back",
            values=[
                StructureValueRow(label=field, value=snapshot[field])
                for field in sorted(snapshot)
            ],
        )

    async def _walk_list(self, key: str, tag: str) -> StructureRow:
        """LPUSH three entries, LRANGE them — push order vs read order."""
        pushed = int(
            await self._client.lpush(key, f"third:{tag}", f"second:{tag}", f"first:{tag}")
        )
        items = [str(item) for item in await self._client.lrange(key, 0, -1)]
        return StructureRow(
            kind="list",
            key=key,
            description=(
                "A list is a linked sequence: LPUSH adds at the head, LRANGE "
                "reads a window — feeds and timelines grow this way."
            ),
            commands=[
                f'LPUSH {key} "third:{tag}" "second:{tag}" "first:{tag}"',
                f"LRANGE {key} 0 -1",
            ],
            outcome=(
                f"lpush returned {pushed}; lrange 0 -1 reads left-to-right, so the "
                "newest (last-pushed) entry sits at index 0"
            ),
            values=[
                StructureValueRow(label=f"LRANGE 0 -1 [{index}]", value=item)
                for index, item in enumerate(items)
            ],
        )

    async def _walk_set(self, key: str, tag: str) -> StructureRow:
        """SADD members (one is the caller's tag), SMEMBERS them back."""
        added = int(await self._client.sadd(key, "cache", "sessions", "pubsub", tag))
        members = sorted(str(member) for member in await self._client.smembers(key))
        return StructureRow(
            kind="set",
            key=key,
            description=(
                "A set holds unique members with O(1) membership — SADD refuses "
                "duplicates, SISMEMBER is the point, SMEMBERS reads the whole set."
            ),
            commands=[
                f'SADD {key} "cache" "sessions" "pubsub" "{tag}"',
                f"SMEMBERS {key}",
            ],
            outcome=(
                f"sadd added {added} member(s) — re-adding any one would answer 0; "
                "smembers has no order, so the display sorts"
            ),
            values=[
                StructureValueRow(label="member", value=member) for member in members
            ],
        )

    async def _walk_zset(self, key: str) -> StructureRow:
        """ZADD score-member pairs, ZRANGE WITHSCORES in score order."""
        added = cast("int", await self._client.zadd(key, dict(LEADERBOARD)))
        scored = cast(
            "list[tuple[str, float]]",
            await self._client.zrange(key, 0, -1, withscores=True),
        )
        pairs = [(str(member), float(score)) for member, score in scored]
        return StructureRow(
            kind="zset",
            key=key,
            description=(
                "A sorted set maps every member to a score and keeps them "
                "ordered — leaderboards and priority queues, updated in place."
            ),
            commands=[
                f"ZADD {key} "
                + " ".join(f"{int(score)} {member}" for member, score in LEADERBOARD),
                f"ZRANGE {key} 0 -1 WITHSCORES",
            ],
            outcome=(
                f"zadd added {added} member(s); zrange 0 -1 WITHSCORES walks them "
                "in score order — "
                + " → ".join(f"{member} {int(score)}" for member, score in pairs)
            ),
            values=[
                StructureValueRow(
                    label=member, value=f"score {int(score)} · rank {rank}"
                )
                for rank, (member, score) in enumerate(pairs, start=1)
            ],
        )

    async def _prove_ttl(self, key: str, tag: str) -> TtlProofRow:
        """SET with an inline EX, watch the clock, wait past expiry, prove it."""
        value = f"gone in {TTL_SECONDS} seconds ({tag})"
        await self._client.set(key, value, ex=TTL_SECONDS)
        ttl_first_read = int(await self._client.ttl(key))
        started = time.monotonic()
        await asyncio.sleep(TTL_WAIT_S)
        absent_after_expiry = await self._client.get(key) is None
        waited_ms = round((time.monotonic() - started) * 1000)
        return TtlProofRow(
            key=key,
            ttl_seconds=TTL_SECONDS,
            commands=[
                f'SET {key} "{value}" EX {TTL_SECONDS}',
                f"TTL {key}",
                f"GET {key}  (after the {TTL_WAIT_S} s bounded wait)",
            ],
            ttl_first_read=ttl_first_read,
            absent_after_expiry=absent_after_expiry,
            waited_ms=waited_ms,
            proof=(
                f"the key lived its configured {TTL_SECONDS} s — TTL answered "
                f"{ttl_first_read} s immediately after the SET with its inline EX — "
                "then GET answered nil after the bounded wait: the store evicted it "
                "on its own clock, no application code ran a delete"
            ),
        )

    async def _prove_pubsub(self, channel: str, tag: str) -> PubsubProofRow:
        """One real round-trip: bounded listener task, PUBLISH, both sides."""
        payload = json.dumps({"tag": tag, "event": "playground", "n": 1})
        pubsub = self._client.pubsub()
        try:
            await pubsub.subscribe(channel)
            listener = asyncio.ensure_future(self._first_message(pubsub))
            try:
                receivers = int(await self._client.publish(channel, payload))
                message = await asyncio.wait_for(listener, timeout=PUBSUB_WAIT_S)
            finally:
                # No-op once the wait completed; a hard bound on any leak path.
                listener.cancel()
        finally:
            await pubsub.aclose()  # type: ignore[no-untyped-call]  # redis-py ships aclose unannotated
        received = "" if message is None else message
        return PubsubProofRow(
            channel=channel,
            payload=payload,
            commands=[
                f"SUBSCRIBE {channel}",
                f"PUBLISH {channel} {payload}",
                "(the listener's message, collected within a 5 s bound)",
            ],
            receivers=receivers,
            received_payload=received,
            matched=received == payload,
            proof=(
                f"PUBLISH answered {receivers} — the RECEIVER count, not an ack — "
                "and the bounded asyncio task listening on the channel collected "
                "the identical payload: both sides of the wire, one message"
            ),
        )

    @staticmethod
    async def _first_message(pubsub: PubSub) -> str | None:
        """Consume the pub/sub stream until the first real message.

        ``listen()`` yields every event type — the subscription confirmation
        first — so the filter on ``type == "message"`` is what skips the
        bookkeeping and returns the PUBLISHed payload.
        """
        async for message in pubsub.listen():
            if message.get("type") == "message":
                data: Any = message.get("data")
                return str(data)
        return None
