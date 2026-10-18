"""The PostgreSQL side of the transactional outbox.

``PgOutboxStore`` implements the ``OutboxAccess`` port over the shared
async engine: the one-transaction business write (a post AND its outbox
event committing together in ``engine.begin()`` — the pattern's entire
reason to exist), the relay's poll (unpublished rows in insertion order,
walking the partial index migration 0004 added), the mark (stamping
``published_at`` on delivered events), and the panel's read-backs.

Identifier strategy is adapter-owned, like every repository in this
guide: the post's slug is the title slugified plus a UUIDv7 hex suffix
(unique by construction), and the EVENT id is a fresh UUIDv7 from
``guide.domain.db.ids`` — the stable logical id consumers dedupe on,
minted once at write time and never regenerated, so a redelivered event
carries the same id as its first delivery.

``trip_crash_point`` is the atomicity proof, mirroring the audit demo's
deliberate rollback: AFTER both inserts, the same transaction trips the
posts title CHECK (a 200-plus-character title), the commit never
happens, and PostgreSQL's rollback takes BOTH halves out — no post, no
event, nothing dangling. Without the flag, any failure is an honest one
and degrades through the optional-service mapper like every adapter.
"""

import json
import re
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from typing import Final, cast
from uuid import UUID

import sqlalchemy as sa
import structlog
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncEngine

from guide.core.errors import AppError, FailureKind
from guide.data.db.repository import ALAN_ID
from guide.data.db.schema import authors, outbox, posts
from guide.domain.db.ids import Uuid7Mint
from guide.domain.messaging.ports import (
    OutboxPostDraft,
    OutboxPostRow,
    OutboxRow,
    OutboxStatsRow,
    OutboxWriteRow,
)

logger = structlog.get_logger()

EVENT_TYPE: Final = "post.created"
"""The one event this outbox mints: a post became durable."""

DEMO_AUTHOR_ID: Final = ALAN_ID
"""The seeded author whose posts the demo writes — Alan covers messaging."""

CRASH_POINT_TITLE: Final = "deliberately past the title CHECK to prove the rollback " * 4
"""The failing statement's payload: over 120 characters, so the posts
CHECK refuses it and the WHOLE transaction (post + outbox row) rolls back."""

_SLUG_STRIP: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9]+")

SEED_MISSING_MESSAGE: Final = (
    "the demo substrate is not seeded — the outbox writes posts as a seeded "
    "author; open any database demo once (it seeds idempotently) and retry"
)


def _slugify(title: str) -> str:
    """Title → kebab-case slug; empty results fall back to a bare 'post'."""
    slug = _SLUG_STRIP.sub("-", title.lower()).strip("-")
    return slug or "post"


def _payload_json(payload: object) -> str:
    """The JSONB payload as canonical text (sorted keys) for display rows."""
    return json.dumps(payload, sort_keys=True) if isinstance(payload, dict) else str(payload)


@contextmanager
def _map_outbox_failures(operation: str) -> Iterator[None]:
    """Optional-service discipline: PostgreSQL trouble becomes service_unavailable."""
    try:
        yield
    except AppError:
        raise
    except (sa.exc.SQLAlchemyError, OSError) as exc:
        logger.warning(
            "outbox_store_unavailable",
            operation=operation,
            error=type(exc).__name__,
            detail=str(exc),
        )
        raise AppError(
            FailureKind.SERVICE_UNAVAILABLE,
            "PostgreSQL is unreachable or unusable — the outbox's atomicity lives "
            "in a PostgreSQL transaction, so this demo refuses to pretend.",
        ) from exc


def _as_outbox_row(row: RowMapping) -> OutboxRow:
    """One outbox table row into the domain's display row."""
    published_at = row["published_at"]
    return OutboxRow(
        event_id=str(cast("UUID", row["event_id"])),
        event_type=str(row["event_type"]),
        aggregate=str(row["aggregate"]),
        payload=_payload_json(row["payload"]),
        created_at=cast("datetime", row["created_at"]).isoformat(),
        published_at=(
            None
            if published_at is None
            else cast("datetime", published_at).isoformat()
        ),
    )


class PgOutboxStore:
    """The live-PostgreSQL adapter behind the outbox demo."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._mint = Uuid7Mint()

    async def create_post_with_event(
        self, draft: OutboxPostDraft, *, trip_crash_point: bool = False
    ) -> OutboxWriteRow:
        """Insert post + outbox event in ONE transaction — both halves or neither."""
        with _map_outbox_failures("create_post_with_event"):
            event_id = self._mint.mint()
            slug = f"{_slugify(draft.title)}-{event_id.hex[:8]}"
            payload: dict[str, object] = {"postId": None, "slug": slug, "title": draft.title}
            failure: str | None = None
            post_row: tuple[int, str] | None = None
            created_at: str | None = None
            try:
                async with self._engine.begin() as connection:
                    author_name = await connection.scalar(
                        sa.select(authors.c.name).where(authors.c.id == DEMO_AUTHOR_ID)
                    )
                    if author_name is None:
                        raise AppError(FailureKind.SERVICE_UNAVAILABLE, SEED_MISSING_MESSAGE)

                    inserted = await connection.execute(
                        sa.insert(posts)
                        .values(
                            author_id=DEMO_AUTHOR_ID,
                            slug=slug,
                            title=draft.title,
                            body=draft.body,
                            status="published",
                        )
                        .returning(posts.c.id, posts.c.created_at)
                    )
                    post = inserted.one()
                    post_row = (int(post.id), str(author_name))
                    payload["postId"] = int(post.id)

                    stamped = await connection.execute(
                        sa.insert(outbox)
                        .values(
                            event_id=event_id,
                            event_type=EVENT_TYPE,
                            aggregate=f"posts:{post.id}",
                            payload=payload,
                        )
                        .returning(outbox.c.created_at)
                    )
                    created_at = cast("datetime", stamped.one().created_at).isoformat()

                    if trip_crash_point:
                        # The crash point: this UPDATE cannot succeed (the title
                        # CHECK refuses it), so the COMMIT never happens and the
                        # rollback takes the post AND the outbox row with it.
                        await connection.execute(
                            sa.update(posts)
                            .where(posts.c.id == post.id)
                            .values(title=CRASH_POINT_TITLE)
                        )
            except sa.exc.DBAPIError as exc:
                if not trip_crash_point:
                    raise  # an honest failure — the mapper degrades it
                failure = str(exc.orig) if exc.orig is not None else str(exc)

            if failure is not None:
                return OutboxWriteRow(
                    committed=False,
                    post=None,
                    event=None,
                    failure=failure,
                    detail=(
                        "the crash point tripped AFTER both inserts — the whole "
                        "transaction rolled back: no post, no outbox row, nothing "
                        "dangling (the dual-write problem cannot happen inside one tx)"
                    ),
                )
            assert post_row is not None and created_at is not None  # committed path
            post_id, author_name = post_row
            return OutboxWriteRow(
                committed=True,
                post=OutboxPostRow(
                    id=post_id,
                    slug=slug,
                    title=draft.title,
                    author=author_name,
                    created_at=created_at,
                ),
                event=OutboxRow(
                    event_id=str(event_id),
                    event_type=EVENT_TYPE,
                    aggregate=f"posts:{post_id}",
                    payload=json.dumps(payload, sort_keys=True),
                    created_at=created_at,
                    published_at=None,
                ),
                failure=None,
                detail=(
                    f"post {post_id} and event {event_id} committed in ONE transaction "
                    f"— both durable now; the relay can publish the event whenever "
                    f"it runs, and until it does the row waits in the outbox"
                ),
            )

    async def unpublished(self, limit: int) -> list[OutboxRow]:
        """The relay's work queue: unpublished rows, in insertion order."""
        with _map_outbox_failures("unpublished"):
            async with self._engine.connect() as connection:
                result = await connection.execute(
                    sa.select(outbox)
                    .where(outbox.c.published_at.is_(None))
                    .order_by(outbox.c.id)
                    .limit(limit)
                )
                return [_as_outbox_row(row) for row in result.mappings()]

    async def mark_published(self, event_ids: Sequence[str]) -> int:
        """Stamp published_at on the named events; answer how many were stamped."""
        if not event_ids:
            return 0
        with _map_outbox_failures("mark_published"):
            async with self._engine.begin() as connection:
                result = await connection.execute(
                    sa.update(outbox)
                    .where(
                        outbox.c.event_id.in_([uuid.UUID(value) for value in event_ids]),
                        outbox.c.published_at.is_(None),
                    )
                    .values(published_at=sa.func.now())
                )
                return int(result.rowcount or 0)

    async def recent(self, limit: int) -> list[OutboxRow]:
        """The newest outbox rows, oldest-first for display."""
        with _map_outbox_failures("recent"):
            async with self._engine.connect() as connection:
                result = await connection.execute(
                    sa.select(outbox).order_by(outbox.c.id.desc()).limit(limit)
                )
                return [_as_outbox_row(row) for row in reversed(result.mappings().all())]

    async def stats(self) -> OutboxStatsRow:
        """total / published over the whole table; unpublished is the difference."""
        with _map_outbox_failures("stats"):
            async with self._engine.connect() as connection:
                row = (
                    await connection.execute(
                        sa.select(
                            sa.func.count(),
                            sa.func.count().filter(outbox.c.published_at.is_not(None)),
                        )
                    )
                ).one()
                total, published = int(row[0]), int(row[1])
                return OutboxStatsRow(
                    total=total, published=published, unpublished=total - published
                )
