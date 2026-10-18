"""Database demos: the schema explorer, the UUID lab, and topic 17's six
live-SQL demos (area ``db``).

Thin routers (family invariant). ``GET /schema-explorer`` introspects
the LIVE database through the ``SchemaReader`` port the composition
root wires (a real PostgreSQL read — information_schema + pg_catalog,
never hard-coded facts) and hands the snapshot to the pure builder;
``?table=posts`` drills into one table, and a table the snapshot does
not contain is the honest 404 envelope. ``GET /uuid`` mints the
uuid4/UUIDv7/bigserial comparison through the pure builder — no
database involved: the lab's whole point is that id strategy is a
SCHEMA decision made before any row exists.

Topic 17 adds six endpoints over the ``GuideRepository`` port, each
seeded first (an idempotent dependency — one count query when the
substrate already exists): ``GET /sql-safety`` runs the parameterized
title filter for real and shows the interpolated statement it refuses
to be; ``GET /migrations`` rehearses a scratch migration sequence that
fails mid-transaction (rollback proves atomicity) then one that
commits; ``GET /sql-lab?exhibit=`` executes the CTE/window/recursive
exhibits; ``GET /search?q=`` ranks full-text matches over the 0002
tsvector column with both EXPLAIN plans; ``GET /race`` choreographs
the lost-update race vs SELECT … FOR UPDATE; ``GET /audit`` commits a
change with its audit row and rolls one back leaving none. Topic 18
adds ``GET /orm-probe`` over the ``OrmProbeRunner`` port: the three
relationship-loading strategies measured with the engine-level SQL
recorder, plus the identity-map and dirty-checking proofs. Topic 19
adds ``GET /mongo-console?tag=`` over the ``MongoConsoleRunner`` port:
the whole scripted document-store console (seed, boundary refusal,
find/update/count/delete, COLLSCAN-vs-IXSCAN explains, a real TTL
index) against the live MongoDB — with mongo down it degrades to the
service_unavailable envelope. The routers only orchestrate: parse
input → one port call → one pure builder.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request

from guide.core.errors import AppError, FailureKind
from guide.domain.db.ids import default_clock
from guide.domain.db.ports import (
    GuideRepository,
    MongoConsoleRunner,
    OrmProbeRunner,
    SchemaReader,
)
from guide.domain.demos.db_audit import AuditPayload, build_audit_payload
from guide.domain.demos.db_migrations import MigrationsPayload, build_migrations_payload
from guide.domain.demos.db_race import RacePayload, build_race_payload
from guide.domain.demos.db_search import SearchPayload, build_search_payload
from guide.domain.demos.mongo_console import (
    MongoConsolePayload,
    build_mongo_console_payload,
)
from guide.domain.demos.orm_probe import OrmProbePayload, build_orm_probe_payload
from guide.domain.demos.schema_explorer import (
    SchemaExplorerPayload,
    build_schema_explorer,
)
from guide.domain.demos.sql_lab import SqlLabPayload, build_sql_lab_payload
from guide.domain.demos.sql_safety import SqlSafetyPayload, build_sql_safety_payload
from guide.domain.demos.uuid_lab import UuidLabPayload, build_uuid_lab_payload

router = APIRouter(prefix="/api/demo/db", tags=["demo:db"])

UUID_SAMPLE_COUNT = 12
"""How many ids each of the lab's three runs mints per request (12 so the
sequence run contains 10/11/12 — the string-sort trap needs them)."""

DEFAULT_FILTER = "'; DROP TABLE posts; --"
"""The safety demo's default input: the canonical injection payload — run
through the REAL query as data, and rendered (never run) interpolated."""

DEFAULT_SEARCH_QUERY = "error envelope"
"""The search demo's default input: matches several seeded posts with
clearly separated ts_rank scores."""


def get_schema_reader(request: Request) -> SchemaReader:
    """FastAPI dependency: the schema reader (wired in create_app)."""
    reader = request.app.state.schema_reader
    if not isinstance(reader, SchemaReader):
        raise AppError(FailureKind.INTERNAL, "Schema reader not wired on app.state")
    return reader


SchemaReaderDep = Annotated[SchemaReader, Depends(get_schema_reader)]


def get_guide_repository(request: Request) -> GuideRepository:
    """FastAPI dependency: the query repository (wired in create_app)."""
    repository = request.app.state.guide_repository
    if not isinstance(repository, GuideRepository):
        raise AppError(FailureKind.INTERNAL, "Guide repository not wired on app.state")
    return repository


async def get_seeded_repository(
    repository: Annotated[GuideRepository, Depends(get_guide_repository)],
) -> GuideRepository:
    """The topic-17 demos' shared dependency: ensure the seed, then serve.

    ``ensure_seed`` is idempotent — one COUNT when the substrate exists,
    the deterministic seed only when posts is empty.
    """
    await repository.ensure_seed()
    return repository


SeededRepositoryDep = Annotated[GuideRepository, Depends(get_seeded_repository)]


def get_orm_probe(request: Request) -> OrmProbeRunner:
    """FastAPI dependency: the ORM probe runner (wired in create_app)."""
    runner = request.app.state.orm_probe
    if not isinstance(runner, OrmProbeRunner):
        raise AppError(FailureKind.INTERNAL, "ORM probe runner not wired on app.state")
    return runner


def get_mongo_console(request: Request) -> MongoConsoleRunner:
    """FastAPI dependency: the mongo console runner (wired in create_app)."""
    runner = request.app.state.mongo_console
    if not isinstance(runner, MongoConsoleRunner):
        raise AppError(FailureKind.INTERNAL, "Mongo console runner not wired on app.state")
    return runner


DEFAULT_MONGO_TAG = "indexes"
"""The console demo's default find filter — a tag three seeded notes carry."""

MONGO_TAG_PATTERN = r"^[a-z0-9-]+$"
"""Tags are lowercase kebab slugs; an unknown tag finds an honest empty."""


DEFAULT_PROBE_POSTS = 5
"""The orm-probe demo's default post count (seeded published posts: nine)."""

PROBE_POSTS_MIN, PROBE_POSTS_MAX = 1, 9


@router.get(
    "/schema-explorer",
    response_model=SchemaExplorerPayload,
    response_model_exclude_none=True,
)
async def read_schema_explorer(
    reader: SchemaReaderDep, table: str | None = None
) -> SchemaExplorerPayload:
    """Introspect the live schema; ``?table=`` drills into one table."""
    snapshot = await reader.read()
    payload = build_schema_explorer(snapshot, focus=table)
    if table is not None and payload.focus is None:
        raise AppError(
            FailureKind.NOT_FOUND,
            f"Table {table!r} does not exist in the live schema.",
        )
    return payload


@router.get("/uuid", response_model=UuidLabPayload, response_model_exclude_none=True)
def read_uuid_lab() -> UuidLabPayload:
    """Mint the uuid4 vs UUIDv7 vs bigserial comparison (pure builder)."""
    return build_uuid_lab_payload(now_ms=default_clock(), sample_count=UUID_SAMPLE_COUNT)


@router.get(
    "/sql-safety",
    response_model=SqlSafetyPayload,
    response_model_exclude_none=True,
)
async def read_sql_safety(
    repository: SeededRepositoryDep,
    value: Annotated[str, Query(alias="filter", max_length=200)] = DEFAULT_FILTER,
) -> SqlSafetyPayload:
    """The same filter two ways: executed with a bind parameter, rendered
    interpolated (shown, never executed)."""
    probe = await repository.filter_posts_by_title(value)
    return build_sql_safety_payload(probe, value)


@router.get(
    "/migrations",
    response_model=MigrationsPayload,
    response_model_exclude_none=True,
)
async def read_migration_rehearsal(
    repository: SeededRepositoryDep,
) -> MigrationsPayload:
    """A scratch migration fails mid-transaction (rollback proves
    atomicity), then the fixed sequence commits."""
    failing, succeeding = await repository.rehearse_migration()
    return build_migrations_payload(failing.scratch_table, failing, succeeding)


@router.get(
    "/sql-lab",
    response_model=SqlLabPayload,
    response_model_exclude_none=True,
)
async def read_sql_lab(
    repository: SeededRepositoryDep,
    exhibit: Literal["ranked", "window", "thread"] = "ranked",
) -> SqlLabPayload:
    """One hand-written SQL exhibit, executed against the seeded data."""
    result = await repository.run_lab_exhibit(exhibit)
    return build_sql_lab_payload(result)


@router.get(
    "/search",
    response_model=SearchPayload,
    response_model_exclude_none=True,
)
async def read_search(
    repository: SeededRepositoryDep,
    q: Annotated[str, Query(max_length=200)] = DEFAULT_SEARCH_QUERY,
) -> SearchPayload:
    """Ranked full-text matches over the generated tsvector, with both
    EXPLAIN plans (indexed vs recomputed)."""
    probe = await repository.search_posts(q)
    return build_search_payload(probe, q)


@router.get("/race", response_model=RacePayload, response_model_exclude_none=True)
async def read_race(repository: SeededRepositoryDep) -> RacePayload:
    """Two concurrent transactions, twice: the lost update, then the
    SELECT … FOR UPDATE serialization."""
    outcome = await repository.run_read_write_race()
    return build_race_payload(outcome)


@router.get("/audit", response_model=AuditPayload, response_model_exclude_none=True)
async def read_audit(repository: SeededRepositoryDep) -> AuditPayload:
    """A committed change WITH its audit row, and a rolled-back change
    leaving NO row — measured, not claimed."""
    proof = await repository.run_audit_proof()
    return build_audit_payload(proof)


@router.get("/orm-probe", response_model=OrmProbePayload, response_model_exclude_none=True)
async def read_orm_probe(
    repository: SeededRepositoryDep,
    probe: Annotated[OrmProbeRunner, Depends(get_orm_probe)],
    posts: Annotated[int, Query(ge=PROBE_POSTS_MIN, le=PROBE_POSTS_MAX)] = DEFAULT_PROBE_POSTS,
) -> OrmProbePayload:
    """The loading strategies measured side by side, plus the session's
    identity-map and dirty-checking proofs (rolled back — repeatable)."""
    loading = await probe.run_loading_probe(posts)
    identity_map = await probe.prove_identity_map()
    dirty_check = await probe.prove_dirty_check()
    return build_orm_probe_payload(loading, identity_map, dirty_check)


@router.get(
    "/mongo-console",
    response_model=MongoConsolePayload,
    response_model_exclude_none=True,
)
async def read_mongo_console(
    runner: Annotated[MongoConsoleRunner, Depends(get_mongo_console)],
    tag: Annotated[
        str, Query(min_length=1, max_length=40, pattern=MONGO_TAG_PATTERN)
    ] = DEFAULT_MONGO_TAG,
) -> MongoConsolePayload:
    """The whole scripted console against the live MongoDB: idempotent
    seed, one pydantic refusal + one acceptance, find (filter +
    projection + sort), update, count, delete, COLLSCAN-vs-IXSCAN
    explains, and a real TTL index."""
    run = await runner.run_console(tag)
    return build_mongo_console_payload(run, tag)
