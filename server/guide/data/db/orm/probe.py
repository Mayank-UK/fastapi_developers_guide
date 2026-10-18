"""The topic-18 adapter: ORM proofs against the live PostgreSQL.

``OrmProbeRepository`` implements the domain's ``OrmProbeRunner`` port
over the shared engine and the session factory from ``sessions``. Every
method opens FRESH sessions per proof (no state leaks between requests),
captures emitted SQL through the engine-level recorder, and leaves the
seed stable: the dirty-check proof rolls back, and the version-conflict
probe creates and removes its own throwaway post. Unreachable
PostgreSQL maps to ``service_unavailable`` exactly like every other
data adapter (optional-service discipline).
"""

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

import sqlalchemy as sa
import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.exc import StaleDataError

from guide.core.errors import AppError, FailureKind
from guide.data.db.orm.models import Post
from guide.data.db.orm.query_counter import record_sql
from guide.data.db.repository import GRACE_ID
from guide.domain.db.ports import (
    DirtyCheckProof,
    IdentityMapProof,
    LoadingProbe,
    PageEntry,
    PaginationProbe,
    StrategyRow,
    VersionConflictProof,
)

logger = structlog.get_logger()

STRATEGIES: Final[tuple[str, ...]] = ("lazy", "joinedload", "selectinload")
"""The three loading shapes §3 of the topic teaches, in payload order."""

PROBE_SLUG: Final = "orm-optimistic-versioning-probe"
"""The version-conflict proof's throwaway post (created, fought over,
deleted — every run starts and ends clean)."""


@contextmanager
def _map_db_failures(operation: str) -> Iterator[None]:
    """Optional-service discipline: DB trouble becomes service_unavailable."""
    try:
        yield
    except AppError:
        raise
    except (SQLAlchemyError, OSError) as exc:
        logger.warning(
            "orm_probe_unavailable",
            operation=operation,
            error=type(exc).__name__,
            detail=str(exc),
        )
        raise AppError(
            FailureKind.SERVICE_UNAVAILABLE,
            "PostgreSQL is unreachable or unusable — this demo runs real "
            "ORM sessions against the live database and refuses to serve "
            "stale facts.",
        ) from exc


class OrmProbeRepository:
    """The live-PostgreSQL adapter behind topic 18's probe."""

    def __init__(
        self,
        engine: AsyncEngine,
        sessions: async_sessionmaker[AsyncSession],
    ) -> None:
        self._engine = engine
        self._sessions = sessions

    # ── §3/§4: the loading strategies and the N+1 they expose ──────────────

    async def run_loading_probe(self, post_count: int) -> LoadingProbe:
        """One access pattern, three load strategies, measured side by side.

        The pattern is the canonical ORM read: load N posts, then touch
        each post's author AND comments — the exact shape that turns
        into N+1 queries under lazy loading. Each strategy gets a FRESH
        session and its own recorder window, so the counts are
        attributable. ``awaitable_attrs`` is the async-honest way to
        touch a possibly-unloaded attribute: already-loaded (eager
        strategies) resolves immediately, lazy loads emit the awaited
        SELECT.
        """
        with _map_db_failures("run_loading_probe"):
            rows: list[StrategyRow] = []
            for strategy in STRATEGIES:
                async with self._sessions() as session:
                    with record_sql(self._engine) as recorder:
                        started = time.perf_counter()
                        statement = (
                            select(Post)
                            .where(Post.status == "published")
                            .order_by(Post.id)
                            .limit(post_count)
                        )
                        if strategy == "joinedload":
                            statement = statement.options(
                                joinedload(Post.author), joinedload(Post.comments)
                            )
                        elif strategy == "selectinload":
                            statement = statement.options(
                                selectinload(Post.author), selectinload(Post.comments)
                            )
                        posts = (await session.scalars(statement)).unique().all()
                        authors: list[str] = []
                        comment_total = 0
                        for post in posts:
                            author = await post.awaitable_attrs.author
                            comments = await post.awaitable_attrs.comments
                            authors.append(author.name)
                            comment_total += len(comments)
                        elapsed_ms = (time.perf_counter() - started) * 1000.0
                rows.append(
                    StrategyRow(
                        strategy=strategy,
                        sql_count=recorder.count(),
                        statements=list(recorder.statements),
                        elapsed_ms=round(elapsed_ms, 3),
                        authors=authors,
                        comment_total=comment_total,
                    )
                )
            by_strategy = {row.strategy: row for row in rows}
            reference = by_strategy["lazy"]
            results_match = all(
                row.authors == reference.authors and row.comment_total == reference.comment_total
                for row in rows
            )
            return LoadingProbe(
                post_count=post_count,
                first_post_title=(await self._first_post_title()),
                strategies=rows,
                results_match=results_match,
            )

    async def _first_post_title(self) -> str:
        """The probe's anchor post title (id-ordered first published)."""
        async with self._sessions() as session:
            title = await session.scalar(
                select(Post.title)
                .where(Post.status == "published")
                .order_by(Post.id)
                .limit(1)
            )
            return title if title is not None else ""

    # ── §2: the identity map and dirty checking ────────────────────────────

    async def prove_identity_map(self) -> IdentityMapProof:
        """Two ``get`` calls for one id: one SELECT, one Python object.

        The second ``get`` is answered from the session's identity map
        (the session IS a cache keyed by primary key), so no SQL runs
        and the returned object is the SAME instance — ``is``, not ``==``.
        """
        with _map_db_failures("prove_identity_map"):
            post_id = await self._anchor_post_id()
            async with self._sessions() as session:
                with record_sql(self._engine) as recorder:
                    first = await session.get(Post, post_id)
                    second = await session.get(Post, post_id)
                    same_object = first is not None and first is second
                return IdentityMapProof(
                    post_id=post_id,
                    select_count=recorder.count("SELECT"),
                    same_object=same_object,
                    statements=list(recorder.statements),
                )

    async def prove_dirty_check(self) -> DirtyCheckProof:
        """Mutate ONE field; flush emits exactly ONE UPDATE; roll back.

        The session diffs each mapped object against its loaded state
        (dirty checking) and flushes the minimal change set: one column,
        one row — plus the version counter migration 0003 added, visible
        in the captured WHERE clause. The rollback keeps the seed stable
        so the proof repeats identically.
        """
        with _map_db_failures("prove_dirty_check"):
            post_id = await self._anchor_post_id()
            async with self._sessions() as session:
                post = await session.get(Post, post_id)
                assert post is not None
                before = post.status
                after = "published" if before == "draft" else "draft"
                post.status = after
                with record_sql(self._engine) as recorder:
                    await session.flush()
                await session.rollback()
                updates = recorder.with_verb("UPDATE")
                return DirtyCheckProof(
                    post_id=post_id,
                    field="status",
                    before=before,
                    after=after,
                    update_count=len(updates),
                    update_sql=updates[0] if updates else "no UPDATE emitted",
                    committed=False,
                )

    # ── §7: optimistic versioning ──────────────────────────────────────────

    async def run_version_conflict(self) -> VersionConflictProof:
        """Two sessions, one row: the winner commits, the loser is refused.

        Both sessions load the throwaway post at version 1; the winner
        commits a status flip (version becomes 2); the loser then tries
        to commit its own edit and the flush's ``WHERE version = 1``
        matches zero rows — SQLAlchemy raises ``StaleDataError`` and the
        row keeps the winner's state. The post is deleted afterwards so
        the proof repeats from scratch.
        """
        with _map_db_failures("run_version_conflict"):
            post_id = await self._create_probe_post()
            try:
                return await self._fight_over(post_id)
            finally:
                await self._drop_probe_post()

    async def _fight_over(self, post_id: int) -> VersionConflictProof:
        """Load one row into two sessions; the winner commits, the loser fails."""
        async with self._sessions() as winner:
            winner_post = await winner.get(Post, post_id)
            assert winner_post is not None
            stale_version = winner_post.version
            async with self._sessions() as loser:
                loser_post = await loser.get(Post, post_id)
                assert loser_post is not None
                # The winner commits first: version 1 -> 2.
                winner_post.status = "published"
                await winner.commit()
                committed_version = winner_post.version
                # The loser edits its STALE copy and tries to commit.
                loser_post.body = loser_post.body + " (the loser's edit)"
                try:
                    await loser.commit()
                except StaleDataError as exc:
                    return VersionConflictProof(
                        post_title=winner_post.title,
                        stale_version=stale_version,
                        committed_version=committed_version,
                        winner_status=winner_post.status,
                        loser_error=f"{type(exc).__name__}: {exc}",
                    )
                raise AppError(
                    FailureKind.INTERNAL,
                    "The version conflict did not fire — the loser's "
                    "stale write was allowed to commit.",
                )

    async def _create_probe_post(self) -> int:
        """Insert the throwaway post (version starts at 1 via server default)."""
        async with self._sessions() as session:
            post = Post(
                author_id=GRACE_ID,
                slug=f"{PROBE_SLUG}-{uuid.uuid4().hex[:8]}",
                title="The optimistic versioning probe",
                body="Two sessions will fight over this row; only one can win.",
                tags=["orm"],
                status="draft",
            )
            session.add(post)
            await session.commit()
            return int(post.id)

    async def _drop_probe_post(self) -> None:
        """Delete the throwaway post by slug prefix — every run cleans up."""
        async with self._sessions() as session:
            await session.execute(
                sa.delete(Post).where(Post.slug.like(f"{PROBE_SLUG}-%"))
            )
            await session.commit()

    # ── §8: pagination (and §5's projection, by construction) ──────────────

    async def paginate(self, page_size: int) -> PaginationProbe:
        """Walk the published posts two ways: offset windows vs id keyset.

        Both paths project to ``(id, title)`` — an ORM entity carries
        every column; a page rarely needs more than two. Offset windows
        ask for rows k..k+n (the database still walks the first k);
        keyset asks for ``WHERE id > last_seen`` (an indexed seek). With
        the seed's nine published posts and page_size three, both
        produce the same three pages — the agreement is checked, and
        the two captured statements show the differing WHERE shapes.
        """
        with _map_db_failures("paginate"):
            async with self._sessions() as session:
                total = int(
                    await session.scalar(
                        select(sa.func.count())
                        .select_from(Post)
                        .where(Post.status == "published")
                    )
                    or 0
                )
                offset_pages: list[list[PageEntry]] = []
                keyset_pages: list[list[PageEntry]] = []
                last_seen_id: int | None = None
                offset_sql = keyset_sql = ""
                for page_index in range((total + page_size - 1) // page_size):
                    with record_sql(self._engine) as recorder:
                        offset_statement = (
                            select(Post.id, Post.title)
                            .where(Post.status == "published")
                            .order_by(Post.id)
                            .offset(page_index * page_size)
                            .limit(page_size)
                        )
                        offset_rows = [
                            PageEntry(id=int(row.id), title=str(row.title))
                            for row in (await session.execute(offset_statement)).all()
                        ]
                    if page_index == 1:
                        offset_sql = recorder.statements[0]
                    offset_pages.append(offset_rows)

                    with record_sql(self._engine) as recorder:
                        keyset_statement = (
                            select(Post.id, Post.title)
                            .where(Post.status == "published")
                            .where(Post.id > (last_seen_id or 0))
                            .order_by(Post.id)
                            .limit(page_size)
                        )
                        keyset_rows = [
                            PageEntry(id=int(row.id), title=str(row.title))
                            for row in (await session.execute(keyset_statement)).all()
                        ]
                    if page_index == 1:
                        keyset_sql = recorder.statements[0]
                    keyset_pages.append(keyset_rows)
                    if keyset_rows:
                        last_seen_id = keyset_rows[-1].id
            return PaginationProbe(
                page_size=page_size,
                total=total,
                offset_pages=offset_pages,
                keyset_pages=keyset_pages,
                offset_sql=offset_sql,
                keyset_sql=keyset_sql,
                agree=offset_pages == keyset_pages,
            )

    async def _anchor_post_id(self) -> int:
        """The proofs' anchor post: id-ordered first published (seeded #1)."""
        async with self._sessions() as session:
            post_id = await session.scalar(
                select(Post.id)
                .where(Post.status == "published")
                .order_by(Post.id)
                .limit(1)
            )
            return int(post_id or 0)
