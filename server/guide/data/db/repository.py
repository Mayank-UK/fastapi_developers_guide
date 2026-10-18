"""The topic-17 query adapter: every demo's SQL, one repository.

``PgGuideRepository`` implements the domain's ``GuideRepository`` port
against the live PostgreSQL. Everything the six database demos teach
lives here as REAL, runnable SQL: the parameterized title filter (and
the interpolation it refuses to be), the transactional migration
rehearsal over a scratch table, the three sql-lab exhibits (a ranking
window, a running-total window, a recursive CTE walking one post's
comment thread), the full-text search over the 0002 generated tsvector
with both EXPLAIN plans, the deterministic two-transaction race, and the
audit proof that commits and rolls back through the topic-16 audit
writer.

The seed is idempotent: ``ensure_seed`` inserts the deterministic
authors, posts, and comments ONLY when the posts table is empty, so
every demo endpoint can depend on data existing without ever
duplicating it. Unreachable/unusable PostgreSQL maps to the taxonomy's
``service_unavailable`` envelope (optional-service discipline), exactly
like the schema reader.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from typing import Final

import sqlalchemy as sa
import structlog
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from guide.core.errors import AppError, FailureKind
from guide.data.db.audit import record_audit
from guide.data.db.schema import comments, posts
from guide.domain.db.audit import AuditEvent
from guide.domain.db.ports import (
    AuditEventRow,
    AuditProof,
    CommittedChangeRow,
    FilterProbe,
    LabQueryResult,
    MigrationRunRow,
    MigrationStepRow,
    PostBriefRow,
    RaceOutcome,
    RaceRunRow,
    RaceSlotRow,
    RolledBackChangeRow,
    SearchMatchRow,
    SearchProbe,
)

logger = structlog.get_logger()


# ── The seed: deterministic, mirroring the posts substrate's flavor ─────────

GRACE_ID: Final = uuid.UUID("0192b0c0-0000-7000-8000-000000000001")
ALAN_ID: Final = uuid.UUID("0192b0c0-0000-7000-8000-000000000002")
BARBARA_ID: Final = uuid.UUID("0192b0c0-0000-7000-8000-000000000003")

SEED_AUTHORS: Final = (
    {
        "id": GRACE_ID,
        "name": "Grace Hopper",
        "email": "grace@guide.dev",
        "bio": "Writes the API chapters; believes every status code is a promise.",
    },
    {
        "id": ALAN_ID,
        "name": "Alan Kay",
        "email": "alan@guide.dev",
        "bio": "Covers messaging and versioning; keeps a deprecation calendar.",
    },
    {
        "id": BARBARA_ID,
        "name": "Barbara Liskov",
        "email": "barbara@guide.dev",
        "bio": "Owns pagination and error modeling; substitutes for nobody.",
    },
)


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    """One deterministic timestamp: September 2026, fixed clock."""
    return datetime(2026, 9, day, hour, minute, tzinfo=UTC)


SEED_POSTS: Final = (
    {
        "author_id": GRACE_ID,
        "slug": "designing-urls-people-can-read",
        "title": "Designing URLs people can read",
        "body": "A URL is part of the interface: resource nouns, kebab-case "
        "slugs, no verbs hiding in paths. A reader should guess what a "
        "collection holds from its name alone, and a slug should "
        "survive being read aloud in a meeting.",
        "tags": ["api", "design"],
        "status": "published",
        "created_at": _at(1, 9),
    },
    {
        "author_id": GRACE_ID,
        "slug": "status-codes-are-a-contract",
        "title": "Status codes are a contract",
        "body": "Every status code is a promise about what happened and what "
        "the client should do next. 2xx means the error envelope was "
        "never needed, 4xx means the client owns the mistake, 5xx "
        "means the server does. Treat redirects and retries as part "
        "of the contract, not decoration.",
        "tags": ["http", "errors"],
        "status": "published",
        "created_at": _at(2, 10),
    },
    {
        "author_id": ALAN_ID,
        "slug": "idempotency-retold",
        "title": "Idempotency, retold",
        "body": "An idempotent endpoint promises that doing it twice looks "
        "like doing it once. That promise is what makes retries safe: "
        "a client that times out can re-send with the same key and "
        "sleep at night. DELETE and PUT earn it naturally; POST needs "
        "an idempotency key.",
        "tags": ["http"],
        "status": "published",
        "created_at": _at(3, 9),
    },
    {
        "author_id": ALAN_ID,
        "slug": "content-negotiation-in-practice",
        "title": "Content negotiation in practice",
        "body": "The Accept header is a negotiation, not a wish list. Quality "
        "values rank what the client actually prefers, and a server "
        "that cannot speak any of them must answer 406 honestly "
        "rather than silently defaulting. Versioning through profiles "
        "beats inventing custom media types.",
        "tags": ["http"],
        "status": "published",
        "created_at": _at(4, 9),
    },
    {
        "author_id": BARBARA_ID,
        "slug": "why-pagination-is-a-resource-problem",
        "title": "Why pagination is a resource problem",
        "body": "Pagination is not a query detail, it is part of the "
        "resource's identity. Offset windows drift under writes; "
        "cursors pin the reader to a stable position in the ordering. "
        "Choose the cursor column as carefully as a primary key, "
        "because that is the job it is doing.",
        "tags": ["api"],
        "status": "published",
        "created_at": _at(5, 9),
    },
    {
        "author_id": BARBARA_ID,
        "slug": "filtering-without-surprises",
        "title": "Filtering without surprises",
        "body": "Filters belong in the query string, validation belongs at "
        "the edge, and surprises belong nowhere. An unknown filter "
        "parameter should be rejected, not ignored, because a silent "
        "no-op filter reads exactly like an empty result set until "
        "the day it costs an outage.",
        "tags": ["api"],
        "status": "published",
        "created_at": _at(6, 9),
    },
    {
        "author_id": GRACE_ID,
        "slug": "the-envelope-is-the-error-model",
        "title": "The envelope is the error model",
        "body": "Every failure answers with one shape: code, message, request "
        "id, optional details. The envelope is a contract like any "
        "other response model. Clients log the request id, humans "
        "correlate it to the trace, and nobody parses prose to find "
        "out what went wrong.",
        "tags": ["errors"],
        "status": "draft",
        "created_at": _at(7, 9),
    },
    {
        "author_id": ALAN_ID,
        "slug": "versioning-an-api-you-already-shipped",
        "title": "Versioning an API you already shipped",
        "body": "Versioning decisions arrive late by definition: the API is "
        "already in the wild. Additive changes need no new version. "
        "Breaking ones get a new path prefix, a migration window, and "
        "a deprecation header — never a silent change that rewrites "
        "responses under running clients.",
        "tags": ["api"],
        "status": "published",
        "created_at": _at(8, 9),
    },
    {
        "author_id": BARBARA_ID,
        "slug": "notes-on-rfc-9457",
        "title": "Notes on RFC 9457",
        "body": "Problem Details borrows the shape we already serve: type, "
        "title, status, detail, instance. Keep the family envelope "
        "for machine parsing and add problem fields where a standard "
        "client expects them. The standard is a vocabulary, not a "
        "replacement for your error taxonomy.",
        "tags": ["errors", "http"],
        "status": "published",
        "created_at": _at(9, 9),
    },
    {
        "author_id": GRACE_ID,
        "slug": "drafting-the-webhooks-chapter",
        "title": "Drafting the webhooks chapter",
        "body": "Draft notes: reversed APIs, HMAC signatures over the raw "
        "body, retries with backoff until the dead letter queue. The "
        "receiver must answer 2xx fast and do the work elsewhere.",
        "tags": ["drafts"],
        "status": "draft",
        "created_at": _at(10, 9),
    },
    {
        "author_id": ALAN_ID,
        "slug": "drafting-the-graphql-chapter",
        "title": "Drafting the GraphQL chapter",
        "body": "Draft notes: one endpoint, a typed schema, resolvers over "
        "the same use cases the REST routes serve, and dataloaders to "
        "keep the N+1 problem in the room where it is solved.",
        "tags": ["drafts"],
        "status": "draft",
        "created_at": _at(11, 9),
    },
    {
        "author_id": BARBARA_ID,
        "slug": "drafting-the-grpc-chapter",
        "title": "Drafting the gRPC chapter",
        "body": "Draft notes: contracts in protobuf, four streaming shapes, "
        "deadlines that actually fire, and status codes that travel "
        "with the method rather than the transport.",
        "tags": ["drafts"],
        "status": "draft",
        "created_at": _at(12, 9),
    },
)
"""Twelve deterministic posts — the same roster the in-memory substrate
of topic 11 serves, now with bodies worth full-text searching."""

_SEED_COMMENT: Final[tuple[dict[str, object], ...]] = (
    {
        "slug": "designing-urls-people-can-read",
        "author": "lin",
        "body": "Slugs that read aloud in meetings — the best naming test I have heard.",
        "created_at": _at(1, 12),
    },
    {
        "slug": "designing-urls-people-can-read",
        "author": "maya",
        "body": "Nested collections still trip me: /authors/{id}/posts "
        "versus a flat /posts?author=.",
        "created_at": _at(1, 13),
    },
    {
        "slug": "status-codes-are-a-contract",
        "author": "maya",
        "body": "The 429 chapter should link here — Retry-After is part of the contract too.",
        "created_at": _at(2, 10, 30),
    },
    {
        "slug": "status-codes-are-a-contract",
        "author": "tom",
        "body": "Would add: 409 for lost updates, since two clients raced on the same row.",
        "created_at": _at(2, 11),
    },
    {
        "slug": "status-codes-are-a-contract",
        "author": "lin",
        "body": "That race example is exactly what SELECT FOR UPDATE is for.",
        "created_at": _at(2, 11, 30),
    },
    {
        "slug": "status-codes-are-a-contract",
        "author": "maya",
        "body": "Or an optimistic version column, when holding locks is too costly.",
        "created_at": _at(2, 12),
    },
    {
        "slug": "status-codes-are-a-contract",
        "author": "tom",
        "body": "Draft: a table mapping every code to the promise it makes.",
        "created_at": _at(2, 12, 30),
    },
    {
        "slug": "idempotency-retold",
        "author": "lin",
        "body": "Idempotency keys belong in the header, not the body — the body is the payload.",
        "created_at": _at(3, 10),
    },
    {
        "slug": "content-negotiation-in-practice",
        "author": "lin",
        "body": "406 over silent defaults — honesty beats convenience.",
        "created_at": _at(4, 10),
    },
    {
        "slug": "why-pagination-is-a-resource-problem",
        "author": "tom",
        "body": "Cursor pagination saved our feed; offset windows drifted under writes.",
        "created_at": _at(5, 10),
    },
    {
        "slug": "why-pagination-is-a-resource-problem",
        "author": "lin",
        "body": "created_at ties are real — the cursor needs the id as tiebreaker.",
        "created_at": _at(5, 11),
    },
    {
        "slug": "filtering-without-surprises",
        "author": "tom",
        "body": "Rejecting unknown filters caught three bugs in our client last quarter.",
        "created_at": _at(6, 10),
    },
    {
        "slug": "the-envelope-is-the-error-model",
        "author": "maya",
        "body": "The request id in the envelope is the support ticket's best friend.",
        "created_at": _at(7, 10),
    },
    {
        "slug": "the-envelope-is-the-error-model",
        "author": "tom",
        "body": "Clients should branch on the code field, never on message prose.",
        "created_at": _at(7, 11),
    },
    {
        "slug": "versioning-an-api-you-already-shipped",
        "author": "maya",
        "body": "Deprecation headers first, sunset dates second, removal last. In that order.",
        "created_at": _at(8, 10),
    },
    {
        "slug": "notes-on-rfc-9457",
        "author": "tom",
        "body": "instance pointing at the request id is a nice touch.",
        "created_at": _at(9, 10),
    },
)
"""Sixteen deterministic comments; the status-codes thread (five, in
created_at order) is the recursive-CTE exhibit's walking ground."""

AUDIT_TARGET_SLUG: Final = "the-envelope-is-the-error-model"
"""The audit demo's post: seeded draft, so the first committed proof run
flips it to published (and every later run flips it back)."""

RACE_AUTHOR_A: Final = "race-runner-a"
RACE_AUTHOR_B: Final = "race-runner-b"
RACE_AUTHORS: Final = (RACE_AUTHOR_A, RACE_AUTHOR_B)


# ── The SQL every demo runs (the topic quotes these verbatim) ───────────────

TITLE_FILTER_SQL = """
SELECT p.id, p.slug, p.title, p.status
FROM posts AS p
WHERE p.title ILIKE :pattern
ORDER BY p.id
"""
"""The safety demo's filter query — :pattern is a BIND PARAMETER, so the
caller's text can only ever be data."""

SCRATCH_TABLE: Final = "migration_lab_scratch"

FAILING_STEPS: Final = (
    (
        "create the scratch table",
        f"CREATE TABLE {SCRATCH_TABLE} (id bigint PRIMARY KEY, label text NOT NULL)",
    ),
    ("seed one row", f"INSERT INTO {SCRATCH_TABLE} (id, label) VALUES (1, 'seeded by step two')"),
    (
        "add a NOT NULL column to a non-empty table — fails",
        f"ALTER TABLE {SCRATCH_TABLE} ADD COLUMN size integer NOT NULL",
    ),
)
"""The failing rehearsal: PostgreSQL refuses the third step (a NOT NULL
column with no default on a table that already has rows), and the whole
transaction — CREATE TABLE and INSERT included — rolls back."""

SUCCEEDING_STEPS: Final = (
    FAILING_STEPS[0],
    FAILING_STEPS[1],
    (
        "the fixed step: a DEFAULT makes the column addable",
        f"ALTER TABLE {SCRATCH_TABLE} ADD COLUMN size integer NOT NULL DEFAULT 0",
    ),
    ("backfill the existing rows", f"UPDATE {SCRATCH_TABLE} SET size = 42 WHERE id = 1"),
)

RANKED_EXHIBIT_SQL = """
WITH per_author AS (
    SELECT a.name AS author,
           p.id AS post_id,
           p.title AS title,
           p.created_at AS created_at,
           COUNT(c.id) AS comment_count
    FROM posts AS p
    JOIN authors AS a ON a.id = p.author_id
    LEFT JOIN comments AS c ON c.post_id = p.id
    GROUP BY a.name, p.id, p.title, p.created_at
)
SELECT author,
       post_id,
       title,
       comment_count,
       ROW_NUMBER() OVER (
           PARTITION BY author ORDER BY created_at
       ) AS nth_post,
       RANK() OVER (ORDER BY comment_count DESC) AS by_comments
FROM per_author
ORDER BY author, nth_post
"""
"""Exhibit 'ranked': two windows over one CTE — each author's posts
numbered oldest-first, and every post's rank by comment count."""

RUNNING_TOTAL_EXHIBIT_SQL = """
SELECT p.id AS post_id,
       p.title AS title,
       p.created_at AS created_at,
       COUNT(c.id) AS comments,
       SUM(COUNT(c.id)) OVER (
           ORDER BY p.created_at
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS running_comments,
       ROUND(
           AVG(COUNT(c.id)) OVER (
               ORDER BY p.created_at
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           ), 2
       ) AS avg_comments_so_far
FROM posts AS p
LEFT JOIN comments AS c ON c.post_id = p.id
GROUP BY p.id, p.title, p.created_at
ORDER BY p.created_at
"""
"""Exhibit 'window': a running total AND a running average of comments
across the whole post timeline — aggregates computed per row, in one
pass, without a self-join."""

THREAD_EXHIBIT_SQL = """
WITH RECURSIVE thread AS (
    SELECT c.id AS id, c.author AS author, c.body AS body, 1 AS depth
    FROM comments AS c
    WHERE c.post_id = :post_id
      AND c.id = (SELECT MIN(c2.id) FROM comments AS c2
                  WHERE c2.post_id = :post_id)
    UNION ALL
    SELECT nxt.id, nxt.author, nxt.body, thread.depth + 1
    FROM thread
    JOIN LATERAL (
        SELECT c3.id, c3.author, c3.body
        FROM comments AS c3
        WHERE c3.post_id = :post_id AND c3.id > thread.id
        ORDER BY c3.id
        LIMIT 1
    ) AS nxt ON TRUE
)
SELECT depth, id, author, body
FROM thread
ORDER BY depth
"""
"""Exhibit 'thread': the recursive CTE walks one post's comment thread
link by link — anchor on the first comment, then each step joins
LATERAL to the NEXT comment by id, depth counting as it goes."""

SEARCH_SQL = """
SELECT p.id, p.slug, p.title,
       ts_rank(p.search_vector, query) AS rank,
       ts_headline('english', p.title || ': ' || p.body, query,
                   'StartSel=<b>, StopSel=</b>, MaxFragments=2') AS headline
FROM posts AS p, plainto_tsquery('english', :query) AS query
WHERE p.search_vector @@ query
ORDER BY rank DESC, p.id
"""
"""The search demo's ranked query: the @@ match walks the GIN index,
ts_rank orders the hits, and ts_headline renders the match context."""

INDEXED_PLAN_SQL = """
EXPLAIN (ANALYZE, COSTS OFF)
SELECT p.id
FROM posts AS p, plainto_tsquery('english', :query) AS query
WHERE p.search_vector @@ query
"""
"""The index-side plan: search_vector @@ query is exactly what the GIN
index answers. Run with seq scans disabled for this session so a
12-row table still shows the index path the planner picks at scale."""

NAIVE_PLAN_SQL = """
EXPLAIN (ANALYZE, COSTS OFF)
SELECT p.id
FROM posts AS p, plainto_tsquery('english', :query) AS query
WHERE to_tsvector('english', coalesce(p.title, '') || ' ' || coalesce(p.body, ''))
      @@ query
"""
"""The no-index plan: recomputing to_tsvector per ROW (a seq scan that
pays the stemming cost 12 times — and N times on a real table)."""


def _cell(value: object) -> str:
    """One result cell as display text: dates ISO, NULL empty, rest str."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


@contextmanager
def _map_db_failures(operation: str) -> Iterator[None]:
    """Optional-service discipline: DB trouble becomes service_unavailable."""
    try:
        yield
    except AppError:
        raise
    except (sa.exc.SQLAlchemyError, OSError) as exc:
        logger.warning(
            "guide_repository_unavailable",
            operation=operation,
            error=type(exc).__name__,
            detail=str(exc),
        )
        raise AppError(
            FailureKind.SERVICE_UNAVAILABLE,
            "PostgreSQL is unreachable or unusable — this demo runs real "
            "SQL against the live database and refuses to serve stale facts.",
        ) from exc


@asynccontextmanager
async def _two_connections(
    engine: AsyncEngine,
) -> AsyncIterator[tuple[AsyncConnection, AsyncConnection]]:
    """Two independent connections for the race (each its own transaction)."""
    connection_a = await engine.connect()
    connection_b = await engine.connect()
    try:
        yield connection_a, connection_b
    finally:
        await connection_a.close()
        await connection_b.close()


class PgGuideRepository:
    """The live-PostgreSQL adapter behind every topic-17 demo."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def ensure_seed(self) -> None:
        """Seed the demo substrate if (and only if) posts is empty."""
        with _map_db_failures("ensure_seed"):
            async with self._engine.begin() as connection:
                count = await connection.scalar(sa.select(sa.func.count()).select_from(posts))
                if count:
                    return
                for author in SEED_AUTHORS:
                    await connection.execute(
                        sa.text(
                            "INSERT INTO authors (id, name, email, bio) "
                            "VALUES (:id, :name, :email, :bio)"
                        ),
                        dict(author),
                    )
                for post in SEED_POSTS:
                    await connection.execute(
                        sa.insert(posts).values(updated_at=post["created_at"], **post)
                    )
                slug_ids = dict(
                    (await connection.execute(sa.select(posts.c.slug, posts.c.id))).all()
                )
                for comment in _SEED_COMMENT:
                    await connection.execute(
                        sa.insert(comments).values(
                            post_id=slug_ids[str(comment["slug"])],
                            author=str(comment["author"]),
                            body=str(comment["body"]),
                            created_at=comment["created_at"],
                        )
                    )

    async def filter_posts_by_title(self, filter_value: str) -> FilterProbe:
        """Run the parameterized title filter and return what it matched."""
        with _map_db_failures("filter_posts_by_title"):
            pattern = f"%{filter_value}%"
            async with self._engine.connect() as connection:
                result = await connection.execute(sa.text(TITLE_FILTER_SQL), {"pattern": pattern})
                rows = [
                    PostBriefRow(id=row.id, slug=row.slug, title=row.title, status=row.status)
                    for row in result.mappings()
                ]
            return FilterProbe(
                sql=TITLE_FILTER_SQL,
                parameter_name="pattern",
                parameter_value=pattern,
                rows=rows,
            )

    async def rehearse_migration(self) -> tuple[MigrationRunRow, MigrationRunRow]:
        """Run the failing rehearsal, then the succeeding one; verify each."""
        with _map_db_failures("rehearse_migration"):
            failing = await self._rehearse_one("failing", FAILING_STEPS)
            succeeding = await self._rehearse_one("succeeding", SUCCEEDING_STEPS)
            # Cleanup: the scratch table is dropped again (committed), so
            # the demo can repeat — the payload already recorded its proof.
            async with self._engine.begin() as connection:
                await connection.execute(sa.text(f"DROP TABLE IF EXISTS {SCRATCH_TABLE}"))
            return failing, succeeding

    async def _rehearse_one(
        self, scenario: str, steps: tuple[tuple[str, str], ...]
    ) -> MigrationRunRow:
        """Run one migration rehearsal inside ONE transaction; verify after."""
        async with self._engine.begin() as connection:
            await connection.execute(sa.text(f"DROP TABLE IF EXISTS {SCRATCH_TABLE}"))

        failure: str | None = None
        applied = 0
        try:
            async with self._engine.begin() as connection:
                for _, sql in steps:
                    await connection.execute(sa.text(sql))
                    applied += 1
        except sa.exc.DBAPIError as exc:
            failure = str(exc.orig) if exc.orig is not None else str(exc)

        step_rows = [
            MigrationStepRow(
                description=description,
                sql=sql,
                outcome=(
                    "applied"
                    if index < applied
                    else (
                        f"failed: {failure}"
                        if failure is not None and index == applied
                        else "rolled back with the transaction"
                    )
                ),
            )
            for index, (description, sql) in enumerate(steps)
        ]
        async with self._engine.connect() as connection:
            exists = bool(
                await connection.scalar(
                    sa.text("SELECT to_regclass(:table_name) IS NOT NULL"),
                    {"table_name": SCRATCH_TABLE},
                )
            )
            row_count = (
                await connection.scalar(sa.text(f"SELECT COUNT(*) FROM {SCRATCH_TABLE}"))
                if exists
                else None
            )
        return MigrationRunRow(
            scenario=scenario,
            scratch_table=SCRATCH_TABLE,
            steps=step_rows,
            failure=failure,
            committed=failure is None,
            table_exists_after=exists,
            row_count_after=row_count,
        )

    async def run_lab_exhibit(self, exhibit: str) -> LabQueryResult:
        """Execute one sql-lab exhibit (ranked · window · thread)."""
        with _map_db_failures("run_lab_exhibit"):
            async with self._engine.connect() as connection:
                params: dict[str, object] = {}
                if exhibit == "ranked":
                    sql = RANKED_EXHIBIT_SQL
                elif exhibit == "window":
                    sql = RUNNING_TOTAL_EXHIBIT_SQL
                elif exhibit == "thread":
                    thread_post = await connection.scalar(
                        sa.text(
                            "SELECT post_id FROM comments "
                            "GROUP BY post_id ORDER BY COUNT(*) DESC, post_id LIMIT 1"
                        )
                    )
                    if thread_post is None:
                        return LabQueryResult(
                            exhibit=exhibit,
                            sql=THREAD_EXHIBIT_SQL,
                            columns=["depth", "id", "author", "body"],
                            rows=[],
                        )
                    sql = THREAD_EXHIBIT_SQL
                    params = {"post_id": thread_post}
                else:
                    raise ValueError(f"unknown exhibit: {exhibit!r}")
                result = await connection.execute(sa.text(sql), params)
                columns = list(result.keys())
                rows = [
                    {key: _cell(value) for key, value in row.items()} for row in result.mappings()
                ]
            return LabQueryResult(exhibit=exhibit, sql=sql, columns=columns, rows=rows)

    async def search_posts(self, query: str) -> SearchProbe:
        """Rank full-text matches and capture both EXPLAIN plans."""
        with _map_db_failures("search_posts"):
            async with self._engine.connect() as connection:
                parsed_query = str(
                    await connection.scalar(
                        sa.text("SELECT plainto_tsquery('english', :query)::text"),
                        {"query": query},
                    )
                )
                result = await connection.execute(sa.text(SEARCH_SQL), {"query": query})
                matches = [
                    SearchMatchRow(
                        id=row.id,
                        slug=row.slug,
                        title=row.title,
                        rank=float(row.rank),
                        headline=row.headline,
                    )
                    for row in result.mappings()
                ]
                # The index path: seq scans disabled FOR THIS TRANSACTION
                # only (SET LOCAL), so a 12-row table still shows the GIN
                # bitmap the planner picks once the table is real-sized.
                # (The reads above left an implicit transaction open — an
                # explicit begin() needs it committed first.)
                await connection.commit()
                async with connection.begin():
                    await connection.execute(sa.text("SET LOCAL enable_seqscan = off"))
                    indexed_plan = [
                        row[0]
                        for row in (
                            await connection.execute(sa.text(INDEXED_PLAN_SQL), {"query": query})
                        ).all()
                    ]
                await connection.commit()
                naive_plan = [
                    row[0]
                    for row in (
                        await connection.execute(sa.text(NAIVE_PLAN_SQL), {"query": query})
                    ).all()
                ]
            return SearchProbe(
                parsed_query=parsed_query,
                sql=SEARCH_SQL,
                matches=matches,
                indexed_plan=indexed_plan,
                naive_plan=naive_plan,
            )

    async def run_read_write_race(self) -> RaceOutcome:
        """Race two transactions twice: unlocked, then FOR UPDATE locked."""
        with _map_db_failures("run_read_write_race"):
            async with self._engine.begin() as connection:
                await connection.execute(
                    sa.delete(comments).where(comments.c.author.in_(RACE_AUTHORS))
                )
                first = (
                    await connection.execute(
                        sa.select(posts.c.id, posts.c.title).order_by(posts.c.id).limit(1)
                    )
                ).one()
                post_id, post_title = int(first.id), str(first.title)
                baseline = int(
                    await connection.scalar(
                        sa.select(sa.func.count())
                        .select_from(comments)
                        .where(comments.c.post_id == post_id),
                    )
                    or 0
                )
            unlocked = await self._race_unlocked(post_id, baseline)
            locked = await self._race_locked(post_id, baseline)
            async with self._engine.begin() as connection:
                await connection.execute(
                    sa.delete(comments).where(comments.c.author.in_(RACE_AUTHORS))
                )
            return RaceOutcome(
                post_id=post_id,
                post_title=post_title,
                baseline_comments=baseline,
                unlocked=unlocked,
                locked=locked,
            )

    async def _comment_count(self, connection: AsyncConnection, post_id: int) -> int:
        """SELECT COUNT(*) for one post — the read in read-modify-write."""
        return int(
            await connection.scalar(
                sa.select(sa.func.count())
                .select_from(comments)
                .where(comments.c.post_id == post_id),
            )
            or 0
        )

    async def _insert_slot(
        self, connection: AsyncConnection, post_id: int, author: str, slot: int, tag: str
    ) -> None:
        """INSERT the computed comment — the write in read-modify-write."""
        await connection.execute(
            sa.insert(comments).values(
                post_id=post_id,
                author=author,
                body=f"slot #{slot} ({tag} run) — comment number {slot}",
            )
        )

    async def _final_slots(self, post_id: int) -> list[RaceSlotRow]:
        """Read the race's residue back, then CLEAN it for the next run.

        The payload keeps the evidence; the database returns to its seed
        state so the two runs (and the next request) never contaminate
        each other's counts.
        """
        async with self._engine.begin() as connection:
            rows = (
                await connection.execute(
                    sa.select(comments.c.author, comments.c.body)
                    .where(comments.c.post_id == post_id)
                    .where(comments.c.author.in_(RACE_AUTHORS))
                    .order_by(comments.c.id)
                )
            ).all()
            await connection.execute(
                sa.delete(comments).where(comments.c.author.in_(RACE_AUTHORS))
            )
        return [RaceSlotRow(author=row.author, body=row.body) for row in rows]

    async def _race_unlocked(self, post_id: int, baseline: int) -> RaceRunRow:
        """Two READ COMMITTED transactions: both read, then both write.

        The interleave is deterministic (no sleeps): every statement is
        awaited in a fixed order — both counts complete before either
        insert starts, so both compute the SAME slot number and the
        second write silently overwrites the first's intent.
        """
        async with _two_connections(self._engine) as (conn_a, conn_b):
            tx_a = await conn_a.begin()
            tx_b = await conn_b.begin()
            try:
                count_a = await self._comment_count(conn_a, post_id)
                count_b = await self._comment_count(conn_b, post_id)
                await self._insert_slot(conn_a, post_id, RACE_AUTHOR_A, count_a + 1, "unlocked")
                await self._insert_slot(conn_b, post_id, RACE_AUTHOR_B, count_b + 1, "unlocked")
                await tx_a.commit()
                await tx_b.commit()
            except BaseException:
                await tx_a.rollback()
                await tx_b.rollback()
                raise
        slots = await self._final_slots(post_id)
        return RaceRunRow(
            mode="read-modify-write",
            timeline=[
                "A BEGIN · B BEGIN (READ COMMITTED)",
                f"A reads COUNT(*) = {count_a}",
                f"B reads COUNT(*) = {count_b} — same snapshot territory, neither write has landed",
                f"A inserts 'slot #{count_a + 1}' (its comment number {count_a + 1})",
                f"B inserts 'slot #{count_b + 1}' — computed from the SAME stale read",
                "A COMMIT · B COMMIT — both slot numbers survive, one "
                "comment number was never assigned",
            ],
            final_slots=slots,
        )

    async def _race_locked(self, post_id: int, baseline: int) -> RaceRunRow:
        """Same race, but both transactions take SELECT ... FOR UPDATE first.

        A locks the post row; B's lock request BLOCKS (deterministically —
        it is started as a task and only awaited after A commits), so B's
        COUNT runs AFTER A's insert is committed and visible: the writes
        serialize on the row lock and every slot number is unique.
        """
        async with _two_connections(self._engine) as (conn_a, conn_b):
            tx_a = await conn_a.begin()
            tx_b = await conn_b.begin()
            try:
                await conn_a.execute(
                    sa.text("SELECT id FROM posts WHERE id = :post_id FOR UPDATE"),
                    {"post_id": post_id},
                )
                lock_b = asyncio.create_task(
                    conn_b.execute(
                        sa.text("SELECT id FROM posts WHERE id = :post_id FOR UPDATE"),
                        {"post_id": post_id},
                    )
                )
                count_a = await self._comment_count(conn_a, post_id)
                await self._insert_slot(conn_a, post_id, RACE_AUTHOR_A, count_a + 1, "locked")
                await tx_a.commit()  # releases the row lock; B unblocks
                await lock_b
                count_b = await self._comment_count(conn_b, post_id)
                await self._insert_slot(conn_b, post_id, RACE_AUTHOR_B, count_b + 1, "locked")
                await tx_b.commit()
            except BaseException:
                if not lock_b.done():
                    lock_b.cancel()
                await tx_a.rollback()
                await tx_b.rollback()
                raise
        slots = await self._final_slots(post_id)
        return RaceRunRow(
            mode="select-for-update",
            timeline=[
                "A BEGIN · B BEGIN (READ COMMITTED)",
                "A locks the post row: SELECT id FROM posts WHERE id = … FOR UPDATE",
                "B requests the same lock and BLOCKS",
                f"A reads COUNT(*) = {count_a}",
                f"A inserts 'slot #{count_a + 1}'",
                "A COMMITs — the row lock releases and B's query returns",
                f"B reads COUNT(*) = {count_b} — A's insert is committed and visible",
                f"B inserts 'slot #{count_b + 1}' — computed from a FRESH read",
                "B COMMITs — both comment numbers were really assigned",
            ],
            final_slots=slots,
        )

    async def run_audit_proof(self) -> AuditProof:
        """Commit a change with its audit row; roll one back; read history."""
        with _map_db_failures("run_audit_proof"):
            async with self._engine.connect() as connection:
                target = (
                    await connection.execute(
                        sa.select(posts.c.id, posts.c.title, posts.c.status).where(
                            posts.c.slug == AUDIT_TARGET_SLUG
                        )
                    )
                ).one()
                post_id, post_title = int(target.id), str(target.title)
                status_before = str(target.status)

            # The committed half: change + audit row, one transaction.
            status_after = "published" if status_before == "draft" else "draft"
            change_note = f"status: {status_before} -> {status_after}"
            async with self._engine.begin() as connection:
                await connection.execute(
                    sa.update(posts).where(posts.c.id == post_id).values(status=status_after)
                )
                await record_audit(
                    connection,
                    AuditEvent(
                        actor="demo:db-audit",
                        action="update",
                        table_name="posts",
                        row_pk=str(post_id),
                        changes={"status": change_note},
                    ),
                )

            # Snapshot AFTER the committed half: whatever the rolled-back
            # attempt adds on top of this count is what survived it (zero).
            async with self._engine.connect() as connection:
                history_before = int(
                    await connection.scalar(
                        sa.text("SELECT COUNT(*) FROM audit_log WHERE row_pk = :pk"),
                        {"pk": str(post_id)},
                    )
                )

            # The rolled-back half: audit written, then the SAME
            # transaction trips the title CHECK — both rows vanish.
            attempted_title = "this title is deliberately far too long " * 6
            rollback_failure: str | None = None
            try:
                async with self._engine.begin() as connection:
                    await connection.execute(
                        sa.update(posts).where(posts.c.id == post_id).values(title=attempted_title)
                    )
                    await record_audit(
                        connection,
                        AuditEvent(
                            actor="demo:db-audit",
                            action="update",
                            table_name="posts",
                            row_pk=str(post_id),
                            changes={"title": "… -> 204 characters of regret"},
                        ),
                    )
            except sa.exc.DBAPIError as exc:
                rollback_failure = str(exc.orig) if exc.orig is not None else str(exc)

            async with self._engine.connect() as connection:
                visible = (
                    await connection.execute(
                        sa.select(posts.c.status, posts.c.title).where(posts.c.id == post_id)
                    )
                ).one()
                latest_audit = (
                    await connection.execute(
                        sa.text(
                            "SELECT id, occurred_at, actor, action, changes "
                            "FROM audit_log WHERE row_pk = :pk "
                            "ORDER BY id DESC LIMIT 1"
                        ),
                        {"pk": str(post_id)},
                    )
                ).one()
                history_rows = (
                    await connection.execute(
                        sa.text(
                            "SELECT id, occurred_at, actor, action, changes "
                            "FROM audit_log WHERE row_pk = :pk ORDER BY id"
                        ),
                        {"pk": str(post_id)},
                    )
                ).all()
                history_after = len(history_rows)

            committed = CommittedChangeRow(
                status_before=status_before,
                status_after=status_after,
                change_visible=str(visible.status) == status_after,
                audit_row=AuditEventRow(
                    id=int(latest_audit.id),
                    occurred_at=_cell(latest_audit.occurred_at),
                    actor=str(latest_audit.actor),
                    action=str(latest_audit.action),
                    changes=str(dict(latest_audit.changes)),
                ),
            )
            rolled_back = RolledBackChangeRow(
                attempted_title=attempted_title,
                failure=rollback_failure or "no failure — the proof is broken",
                change_visible=str(visible.title) == attempted_title,
                audit_rows_after=history_after - history_before,
            )
            history = [
                AuditEventRow(
                    id=int(row.id),
                    occurred_at=_cell(row.occurred_at),
                    actor=str(row.actor),
                    action=str(row.action),
                    changes=str(dict(row.changes)),
                )
                for row in history_rows
            ]
            return AuditProof(
                post_id=post_id,
                post_title=post_title,
                committed=committed,
                rolled_back=rolled_back,
                history=history,
            )
