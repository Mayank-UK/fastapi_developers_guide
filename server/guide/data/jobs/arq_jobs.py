"""The redis/arq adapter: the whole ``JobsStore`` over one decoded pool.

``ArqJobs`` implements every jobs port (broker, attempt trail, dead
letters, mailbox, heartbeat, comparison ledger, reset) over ONE
``ArqRedis`` pool created lazily from a factory — the same
optional-service discipline as the cache and messaging adapters: the
pool is built on the FIRST command (so the app boots with Redis down),
and a store that stops answering degrades to the
``service_unavailable`` envelope instead of hanging a request.

arq's own key layout is part of what this adapter reads, deliberately:
the queue is a sorted set (``arq:queue``) whose SCORE is each job's due
time in epoch ms — which makes the two observability numbers one round
trip each (ZCARD for depth, the lowest score for the oldest job's age)
— and ``arq:in-progress:{id}`` / ``arq:result:{id}`` carry the live
lifecycle. What this adapter never does is READ arq's pickled payloads:
the pool is decoded (``decode_responses=True``, this repo's rule) and
pickle bytes are not valid UTF-8, so the attempt trail — plain JSON
lists this adapter owns — is the readable record, and terminal states
split on the trail's last step rather than the result's bytes.

Two translations carry real semantics and are called out where they
happen: ``replay_dead_letter`` re-enqueues FRESH (a new job id,
attempts reset to one — the parked entry stays as the audit record and
gains ``replayed_as``), and an ``enqueue_job`` answer of ``None`` (the
job id is already queued) cannot happen here because every enqueue
mints a new id — the adapter still refuses to pretend, and raises if
arq ever changes that contract.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from typing import Final, cast

import structlog
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from arq.constants import default_queue_name, in_progress_key_prefix, result_key_prefix
from redis.exceptions import RedisError

from guide.core.config import AppConfig
from guide.core.errors import AppError, FailureKind
from guide.domain.jobs.ports import (
    ATTEMPT_KEY_PREFIX,
    COMPARISON_KEY,
    DLQ_KEY,
    HEARTBEAT_BEATS_KEY,
    HEARTBEAT_LAST_KEY,
    LIST_CAP,
    MAILBOX_KEY,
    AttemptStepRow,
    ComparisonRunRow,
    DeadLetterRow,
    HeartbeatRow,
    JobLifecycleRow,
    JobTicket,
    MailboxRow,
    QueueStatsRow,
    oldest_age_seconds,
)

logger = structlog.get_logger()

PoolFactory = Callable[[], Awaitable[ArqRedis]]
"""How the store gets its pool — the server passes a lazy from-config
factory; the worker passes its already-built pool wrapped in a callable."""

QUEUE_KEY: Final = default_queue_name
"""arq's queue sorted set — score is each job's due time (epoch ms)."""

HEARTBEAT_SCHEDULE: Final = "every minute (arq cron), plus once at worker boot"
"""What the heartbeat row reports about its own schedule."""


@contextmanager
def _map_jobs_failures(operation: str) -> Iterator[None]:
    """Optional-service discipline: redis trouble becomes service_unavailable."""
    try:
        yield
    except AppError:
        raise
    except (RedisError, OSError) as exc:
        logger.warning(
            "jobs_store_unavailable",
            operation=operation,
            error=type(exc).__name__,
            detail=str(exc),
        )
        raise AppError(
            FailureKind.SERVICE_UNAVAILABLE,
            "Redis is unreachable — this demo's queue is the subject, so it "
            "refuses to pretend jobs exist (the app keeps serving everything "
            "else).",
        ) from exc


def create_arq_pool_factory(config: AppConfig) -> PoolFactory:
    """The server-side factory: one lazily-created, memoized arq pool per process.

    ``create_pool`` connects and pings eagerly, so the factory IS the
    lazy seam — constructing this callable connects to nothing, the
    first command pays the connect, and a redis that is down surfaces
    as the 503 envelope fast (arq's one-second connect timeout). The
    memo keeps ONE pool per process; the single-flight lock keeps two
    concurrent first-commands from paying the connect twice.
    """

    memo: list[ArqRedis] = []
    single_flight: asyncio.Lock = asyncio.Lock()

    async def factory() -> ArqRedis:
        if memo:
            return memo[0]
        async with single_flight:
            if not memo:
                settings = RedisSettings.from_dsn(config.redis_url)
                memo.append(await create_pool(settings))
        return memo[0]

    return factory


def _now_ms() -> int:
    return int(time.time() * 1000)


class ArqJobs:
    """The live redis/arq adapter behind the whole jobs console."""

    def __init__(self, pool_factory: PoolFactory) -> None:
        self._pool_factory = pool_factory

    async def _pool(self) -> ArqRedis:
        return await self._pool_factory()

    # ── JobBroker ────────────────────────────────────────────────────────

    async def enqueue(self, function_name: str, payload: str | None) -> JobTicket:
        """Enqueue one job — arq mints the id and the due-time score."""
        with _map_jobs_failures("enqueue"):
            pool = await self._pool()
            args: tuple[str, ...] = () if payload is None else (payload,)
            job = await pool.enqueue_job(function_name, *args)
            if job is None:  # a duplicate _job_id — this adapter never sends one
                raise AppError(
                    FailureKind.CONFLICT,
                    f"arq refused job {function_name!r} — the id is already queued",
                )
            return JobTicket(
                job_id=job.job_id,
                function_name=function_name,
                enqueued_at_ms=_now_ms(),
            )

    async def lifecycle(self, job_id: str) -> JobLifecycleRow:
        """arq's state machine read from the key layout — three probes, no payloads."""
        with _map_jobs_failures("lifecycle"):
            pool = await self._pool()
            has_progress = await pool.exists(f"{in_progress_key_prefix}{job_id}")
            score = await pool.zscore(QUEUE_KEY, job_id)
            if has_progress:
                return JobLifecycleRow(state="in_progress", score_ms=None)
            if score is not None:
                if score > _now_ms():
                    return JobLifecycleRow(state="deferred", score_ms=int(score))
                return JobLifecycleRow(state="queued", score_ms=int(score))
            has_result = await pool.exists(f"{result_key_prefix}{job_id}")
            if has_result:
                return JobLifecycleRow(state="result_present", score_ms=None)
            return JobLifecycleRow(state="gone", score_ms=None)

    async def queue_stats(self) -> QueueStatsRow:
        """The two numbers: ZCARD depth, oldest age from the lowest score."""
        with _map_jobs_failures("queue_stats"):
            pool = await self._pool()
            depth = int(await pool.zcard(QUEUE_KEY))
            oldest = await pool.zrange(QUEUE_KEY, start=0, end=0, withscores=True)
            # zrange's withscores pairs are loosely typed (bytes|str|num); the
            # score is always numeric on a decoded pool — carry it across as one.
            oldest_score = float(oldest[0][1]) if oldest else None
            return QueueStatsRow(
                depth=depth,
                oldest_age_seconds=oldest_age_seconds(_now_ms(), oldest_score),
            )

    # ── AttemptTrail ─────────────────────────────────────────────────────

    async def note(self, job_id: str, step: AttemptStepRow) -> None:
        """Append one outcome to the job's trail (JSON list, capped)."""
        with _map_jobs_failures("note"):
            pool = await self._pool()
            key = f"{ATTEMPT_KEY_PREFIX}{job_id}"
            await pool.rpush(key, step.model_dump_json())
            await pool.ltrim(key, -LIST_CAP, -1)

    async def steps(self, job_id: str) -> list[AttemptStepRow]:
        """The trail in attempt order — RPUSH order IS attempt order."""
        with _map_jobs_failures("steps"):
            pool = await self._pool()
            raw = cast(
                "list[str]", await pool.lrange(f"{ATTEMPT_KEY_PREFIX}{job_id}", 0, -1)
            )
            return [AttemptStepRow.model_validate_json(item) for item in raw]

    # ── DeadLetterQueue ──────────────────────────────────────────────────

    async def record_dead_letter(self, entry: DeadLetterRow) -> None:
        """Park one job — RPUSH + cap keeps the newest LIST_CAP parkings."""
        with _map_jobs_failures("record_dead_letter"):
            pool = await self._pool()
            await pool.rpush(DLQ_KEY, entry.model_dump_json())
            await pool.ltrim(DLQ_KEY, -LIST_CAP, -1)

    async def dead_letters(self, limit: int) -> list[DeadLetterRow]:
        """The parked jobs, newest first (LRANGE from the end, reversed)."""
        with _map_jobs_failures("dead_letters"):
            pool = await self._pool()
            raw = cast("list[str]", await pool.lrange(DLQ_KEY, -limit, -1))
            return [DeadLetterRow.model_validate_json(item) for item in reversed(raw)]

    async def replay_dead_letter(self, entry_id: str) -> JobTicket:
        """Re-enqueue fresh — new id, attempts reset, entry kept as audit.

        The walk reads the WHOLE list so the index handed to LSET counts
        from the list's true head; the parked entry is updated in place,
        gaining ``replayed_as`` — the audit trail grows a link, it never
        loses one.
        """
        with _map_jobs_failures("replay_dead_letter"):
            pool = await self._pool()
            raw = cast("list[str]", await pool.lrange(DLQ_KEY, 0, -1))
            for index, item in enumerate(raw):
                entry = DeadLetterRow.model_validate_json(item)
                if entry.entry_id != entry_id:
                    continue
                ticket = await self.enqueue(entry.function_name, entry.payload or None)
                updated = entry.model_copy(update={"replayed_as": ticket.job_id})
                await pool.lset(DLQ_KEY, index, updated.model_dump_json())
                return ticket
        raise AppError(
            FailureKind.NOT_FOUND,
            f"dead-letter entry {entry_id!r} is not parked (it may have fallen "
            f"off the {LIST_CAP}-entry cap)",
        )

    async def dead_letter_size(self) -> int:
        with _map_jobs_failures("dead_letter_size"):
            pool = await self._pool()
            return int(await pool.llen(DLQ_KEY))

    # ── MailboxRecorder ──────────────────────────────────────────────────

    async def record_message(self, message: MailboxRow) -> None:
        """File one delivered message (the demo's mailbox — no SMTP here)."""
        with _map_jobs_failures("record_message"):
            pool = await self._pool()
            await pool.rpush(MAILBOX_KEY, message.model_dump_json())
            await pool.ltrim(MAILBOX_KEY, -LIST_CAP, -1)

    async def messages(self, limit: int) -> list[MailboxRow]:
        """The mailbox, newest first."""
        with _map_jobs_failures("messages"):
            pool = await self._pool()
            raw = cast("list[str]", await pool.lrange(MAILBOX_KEY, -limit, -1))
            return [MailboxRow.model_validate_json(item) for item in reversed(raw)]

    async def mailbox_size(self) -> int:
        with _map_jobs_failures("mailbox_size"):
            pool = await self._pool()
            return int(await pool.llen(MAILBOX_KEY))

    # ── CronHeartbeat ────────────────────────────────────────────────────

    async def beat(self) -> int:
        """One beat: stamp the last-run ms, bump the counter, answer it."""
        with _map_jobs_failures("beat"):
            pool = await self._pool()
            await pool.set(HEARTBEAT_LAST_KEY, _now_ms())
            return int(await pool.incr(HEARTBEAT_BEATS_KEY))

    async def read(self) -> HeartbeatRow:
        with _map_jobs_failures("heartbeat_read"):
            pool = await self._pool()
            last_raw = await pool.get(HEARTBEAT_LAST_KEY)
            beats_raw = await pool.get(HEARTBEAT_BEATS_KEY)
            return HeartbeatRow(
                last_run_ms=int(last_raw) if last_raw is not None else None,
                beats=int(beats_raw or 0),
                schedule=HEARTBEAT_SCHEDULE,
            )

    # ── ComparisonRuns ───────────────────────────────────────────────────

    async def record(self, run: ComparisonRunRow) -> None:
        """File one side of one comparison run (JSON list, capped)."""
        with _map_jobs_failures("comparison_record"):
            pool = await self._pool()
            await pool.rpush(COMPARISON_KEY, run.model_dump_json())
            await pool.ltrim(COMPARISON_KEY, -LIST_CAP, -1)

    async def recent(self, limit: int) -> list[ComparisonRunRow]:
        """The recent runs, newest first."""
        with _map_jobs_failures("comparison_recent"):
            pool = await self._pool()
            raw = cast("list[str]", await pool.lrange(COMPARISON_KEY, -limit, -1))
            return [ComparisonRunRow.model_validate_json(item) for item in reversed(raw)]

    # ── JobsReset ────────────────────────────────────────────────────────

    async def reset_demo_state(self) -> int:
        """Delete this namespace's demo keys — arq's own keys are untouched.

        The trails are per-job keys, so the sweep SCANs the attempts
        prefix rather than guessing ids; queued jobs (arq's zset and job
        keys) deliberately SURVIVE the reset — they are the broker's,
        not the demo's.
        """
        with _map_jobs_failures("reset_demo_state"):
            pool = await self._pool()
            keys: list[str] = [
                DLQ_KEY,
                MAILBOX_KEY,
                COMPARISON_KEY,
                HEARTBEAT_LAST_KEY,
                HEARTBEAT_BEATS_KEY,
            ]
            async for key in pool.scan_iter(match=f"{ATTEMPT_KEY_PREFIX}*"):
                keys.append(key)
            if not keys:
                return 0
            return int(await pool.delete(*keys))
