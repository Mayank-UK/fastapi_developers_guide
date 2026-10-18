"""The schema-introspection port: rows in, no driver types out.

The schema explorer demo needs FACTS about the live database — tables,
columns, foreign keys, checks, indexes — and the domain must not know
PostgreSQL. So the port speaks plain row models: an adapter (see
``guide.data.db.introspection``) reads them out of information_schema
and pg_catalog, and the demo builder shapes them. ``SchemaReader`` is
the Protocol the composition root wires; ``SchemaSnapshot`` is one
consistent, ordered harvest of the public schema.

Topic 17 adds the query port on the same discipline: ``GuideRepository``
is the Protocol the six database demos resolve, and the row models below
(one per demo operation) carry RESULTS, never driver types — connections,
cursors, and asyncpg row objects stay behind the adapter. The pure demo
builders in ``guide.domain.demos`` shape these results into payloads; the
adapter in ``guide.data.db.repository`` produces them against the live
PostgreSQL. Topic 18 extends the same shape to the ORM: ``OrmProbeRunner``
is the Protocol behind the orm-probe demo, and its rows carry measured
SQL counts, captured statements, and proofs — never sessions or mapped
objects. Topic 19 keeps the discipline for the document store:
``MongoConsoleRunner`` is the Protocol behind the mongo-console demo,
its rows carry what the live MongoDB actually answered (documents,
plans, index definitions — rendered to display strings, ``ObjectId``
never on the wire), and ``ConsoleNoteDraft`` is the pydantic boundary
every insert passes through — MongoDB enforces no schema, so the
application layer owns that job. Topic 20 closes the data phase with
the in-memory store: ``RedisPlaygroundRunner`` is the Protocol behind
the redis playground demo, its rows carry what the live Redis actually
answered (structure values, TTL facts, both sides of a real pub/sub
round-trip — display strings only, driver types stay behind the
adapter).
"""

from datetime import datetime
from typing import Annotated, Literal, Protocol, runtime_checkable

from pydantic import ConfigDict, Field

from guide.core.serialization import CamelModel


class ColumnRow(CamelModel):
    """One column exactly as information_schema.columns reports it."""

    table_name: str
    column_name: str
    data_type: str
    udt_name: str
    is_nullable: bool
    column_default: str | None


class ForeignKeyRow(CamelModel):
    """One foreign key constraint: local columns → referenced columns."""

    constraint_name: str
    table_name: str
    columns: list[str]
    referenced_table: str
    referenced_columns: list[str]
    on_delete: str


class CheckRow(CamelModel):
    """One CHECK constraint with its definition as PostgreSQL renders it."""

    constraint_name: str
    table_name: str
    definition: str


class IndexRow(CamelModel):
    """One index: which columns, what kind, and whether it is partial."""

    index_name: str
    table_name: str
    columns: list[str]
    kind: str
    is_unique: bool
    is_primary: bool
    where: str | None


class SchemaSnapshot(CamelModel):
    """Every introspected fact about the public schema, one harvest."""

    database_name: str
    tables: list[str]
    columns: list[ColumnRow]
    foreign_keys: list[ForeignKeyRow]
    checks: list[CheckRow]
    indexes: list[IndexRow]


@runtime_checkable
class SchemaReader(Protocol):
    """What every schema-introspection adapter must provide."""

    async def read(self) -> SchemaSnapshot:
        """Harvest the live public schema; failures raise, never lie."""
        ...


# ── Topic 17: the query port and its result rows ────────────────────────────


class PostBriefRow(CamelModel):
    """One post as the safety demo's filter query returns it."""

    id: int
    slug: str
    title: str
    status: str


class FilterProbe(CamelModel):
    """The executed parameterized filter: the SQL, the bind value, the rows."""

    sql: str
    parameter_name: str
    parameter_value: str
    rows: list[PostBriefRow]


class MigrationStepRow(CamelModel):
    """One step of a rehearsed migration sequence and what became of it."""

    description: str
    sql: str
    outcome: str
    """``applied`` · ``failed: <reason>`` · ``rolled back with the transaction``."""


class MigrationRunRow(CamelModel):
    """One full migration rehearsal: the steps, the ending, the verification."""

    scenario: str
    scratch_table: str
    steps: list[MigrationStepRow]
    failure: str | None
    committed: bool
    table_exists_after: bool
    row_count_after: int | None


class LabQueryResult(CamelModel):
    """One sql-lab exhibit's raw answer: the SQL, the columns, the rows.

    Cells are display-formatted strings (dates ISO, numerals as PostgreSQL
    rendered them) so the pure builder needs no type knowledge.
    """

    exhibit: str
    sql: str
    columns: list[str]
    rows: list[dict[str, str]]


class SearchMatchRow(CamelModel):
    """One ranked full-text hit with its highlighted headline."""

    id: int
    slug: str
    title: str
    rank: float
    headline: str


class SearchProbe(CamelModel):
    """The search demo's harvest: parsed query, ranked rows, both plans."""

    parsed_query: str
    sql: str
    matches: list[SearchMatchRow]
    indexed_plan: list[str]
    naive_plan: list[str]


class RaceSlotRow(CamelModel):
    """One comment the race wrote, as the final state shows it."""

    author: str
    body: str


class RaceRunRow(CamelModel):
    """One race run: the choreography timeline and the final comment slots."""

    mode: str
    timeline: list[str]
    final_slots: list[RaceSlotRow]


class RaceOutcome(CamelModel):
    """Both runs over the same row: unlocked vs locked, side by side."""

    post_id: int
    post_title: str
    baseline_comments: int
    unlocked: RaceRunRow
    locked: RaceRunRow


class AuditEventRow(CamelModel):
    """One audit_log row exactly as the history query reads it back."""

    id: int
    occurred_at: str
    actor: str
    action: str
    changes: str


class CommittedChangeRow(CamelModel):
    """The committed half of the audit proof: change + its audit row."""

    status_before: str
    status_after: str
    change_visible: bool
    audit_row: AuditEventRow


class RolledBackChangeRow(CamelModel):
    """The rolled-back half: what was attempted, what survived (nothing)."""

    attempted_title: str
    failure: str
    change_visible: bool
    audit_rows_after: int


class AuditProof(CamelModel):
    """The audit demo's full evidence: both halves + the post's history."""

    post_id: int
    post_title: str
    committed: CommittedChangeRow
    rolled_back: RolledBackChangeRow
    history: list[AuditEventRow]


@runtime_checkable
class GuideRepository(Protocol):
    """What every topic-17 query adapter must provide.

    ``ensure_seed`` is idempotent — it seeds the deterministic authors,
    posts, and comments ONLY when the posts table is empty, so every demo
    can depend on data being present without ever duplicating it.
    """

    async def ensure_seed(self) -> None:
        """Seed the demo substrate if (and only if) posts is empty."""
        ...

    async def filter_posts_by_title(self, filter_value: str) -> FilterProbe:
        """Run the parameterized title filter and return what it matched."""
        ...

    async def rehearse_migration(self) -> tuple[MigrationRunRow, MigrationRunRow]:
        """Run the failing rehearsal then the succeeding one; verify each."""
        ...

    async def run_lab_exhibit(self, exhibit: str) -> LabQueryResult:
        """Execute one sql-lab exhibit (ranked · window · thread)."""
        ...

    async def search_posts(self, query: str) -> SearchProbe:
        """Rank full-text matches and capture both EXPLAIN plans."""
        ...

    async def run_read_write_race(self) -> RaceOutcome:
        """Race two transactions twice: unlocked, then FOR UPDATE locked."""
        ...

    async def run_audit_proof(self) -> AuditProof:
        """Commit a change with its audit row; roll one back; read history."""
        ...


# ── Topic 18: the ORM probe port and its result rows ───────────────────────


class StrategyRow(CamelModel):
    """One loading strategy's measured run: SQL count, statements, results."""

    strategy: str
    """``lazy`` · ``joinedload`` · ``selectinload``."""

    sql_count: int
    statements: list[str]
    elapsed_ms: float
    authors: list[str]
    """The touched posts' author names, in post order — the comparison key."""

    comment_total: int


class LoadingProbe(CamelModel):
    """The same access pattern under every strategy, side by side."""

    post_count: int
    first_post_title: str
    strategies: list[StrategyRow]
    results_match: bool


class IdentityMapProof(CamelModel):
    """Two ``get`` calls, ONE SELECT, one object — measured, not claimed."""

    post_id: int
    select_count: int
    same_object: bool
    statements: list[str]


class DirtyCheckProof(CamelModel):
    """One mutated field → flush emits exactly one UPDATE (then rollback)."""

    post_id: int
    field: str
    before: str
    after: str
    update_count: int
    update_sql: str
    committed: bool


class VersionConflictProof(CamelModel):
    """Two sessions racing one row: the winner commits, the loser fails."""

    post_title: str
    stale_version: int
    committed_version: int
    winner_status: str
    loser_error: str


class PageEntry(CamelModel):
    """One projected page row: just the id and title the client needs."""

    id: int
    title: str


class PaginationProbe(CamelModel):
    """Limit/offset vs keyset pagination over the same ordering, compared."""

    page_size: int
    total: int
    offset_pages: list[list[PageEntry]]
    keyset_pages: list[list[PageEntry]]
    offset_sql: str
    keyset_sql: str
    agree: bool


@runtime_checkable
class OrmProbeRunner(Protocol):
    """What every topic-18 ORM adapter must provide.

    Every method runs REAL sessions against the live database through
    the shared engine/factory the composition root wires, with SQL
    captured by the engine-level recorder — results are measurements.
    Mutating proofs (dirty check, version conflict) roll back or clean
    up after themselves so the seed stays stable across runs.
    """

    async def run_loading_probe(self, post_count: int) -> LoadingProbe:
        """Run the touch-author-and-comments pattern under all strategies."""
        ...

    async def prove_identity_map(self) -> IdentityMapProof:
        """Two ``get`` calls for one id; count the SELECTs; compare objects."""
        ...

    async def prove_dirty_check(self) -> DirtyCheckProof:
        """Mutate one field, flush (one UPDATE), roll back."""
        ...

    async def run_version_conflict(self) -> VersionConflictProof:
        """Commit over a stale version and catch the loser's failure."""
        ...

    async def paginate(self, page_size: int) -> PaginationProbe:
        """Walk the same pages two ways: offset windows vs id keyset."""
        ...


# ── Topic 19: the MongoDB console port and its result rows ──────────────────


class ConsoleNoteDraft(CamelModel):
    """The pydantic boundary every console insert passes through.

    MongoDB enforces no schema — this model IS the gate between untrusted
    input and the collection. ``extra="forbid"`` turns an unknown field
    into a refusal instead of a silent write, and every constraint below
    is application-layer policy the store cannot supply.
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9-]+$")
    author: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=3, max_length=120)
    body: str = Field(min_length=1, max_length=2000)
    tags: list[Annotated[str, Field(min_length=1, max_length=40)]] = Field(
        min_length=1, max_length=8
    )
    status: Literal["draft", "published", "archived"]
    created_at: datetime


class SeedReport(CamelModel):
    """One console run's seed step — keyed upserts, so repeats are idempotent."""

    collection: str
    seed_keys: list[str]
    count_before: int
    upserted: int
    total_after: int
    indexes_ensured: list[str]


class RefusalRow(CamelModel):
    """The boundary's refusal: what was attempted and why it never ran."""

    attempted: dict[str, str]
    errors: list[str]


class ConsoleOperationRow(CamelModel):
    """One console operation and what the live MongoDB answered.

    ``documents`` rows are display strings (dates ISO, ``ObjectId`` as
    ``str``) so the pure payload builder needs no BSON knowledge.
    """

    op: str
    """``insert`` · ``find`` · ``update`` · ``count`` · ``delete``."""

    description: str
    command: str
    """The mongosh-shaped rendering of what actually ran."""

    outcome: str
    documents: list[dict[str, str]]


class ExplainStageRow(CamelModel):
    """One explain(): the winning plan's access stage with its exam counts."""

    label: str
    query: str
    stage: str
    """The access stage that satisfied the scan — ``COLLSCAN`` or ``IXSCAN``."""

    index_name: str | None
    keys_examined: int
    docs_examined: int


class IndexShowcaseRow(CamelModel):
    """The index exhibit: one query, explained before and after createIndex."""

    collection: str
    document_count: int
    index_command: str
    explains: list[ExplainStageRow]


class TtlShowcaseRow(CamelModel):
    """The TTL exhibit: a real ``expireAfterSeconds`` index, definition shown."""

    collection: str
    index_definition: dict[str, str]
    expire_after_seconds: int
    scratch_documents: list[dict[str, str]]
    eviction_note: str


class MongoConsoleRun(CamelModel):
    """Everything one console run really did, database name included."""

    database: str
    seed: SeedReport
    refusal: RefusalRow
    operations: list[ConsoleOperationRow]
    index_showcase: IndexShowcaseRow
    ttl_showcase: TtlShowcaseRow


@runtime_checkable
class MongoConsoleRunner(Protocol):
    """What every topic-19 MongoDB adapter must provide.

    The whole console is ONE call: an idempotent keyed seed, one refusal
    and one acceptance through ``ConsoleNoteDraft``, then find (filter +
    projection + sort), update, count, and delete over the live store,
    plus the index exhibit (COLLSCAN vs IXSCAN explains) and a real TTL
    index on a scratch collection. Every row carries what MongoDB
    actually answered; unreachable MongoDB is the adapter's problem to
    translate (service_unavailable), never the port's.
    """

    async def run_console(self, tag: str) -> MongoConsoleRun:
        """Run the scripted console; ``tag`` is the find filter's value."""
        ...


# ── Topic 20: the Redis playground port and its result rows ─────────────────


class StructureValueRow(CamelModel):
    """One value a structure read returned, as a display string."""

    label: str
    value: str


class StructureRow(CamelModel):
    """One Redis structure walked with real commands and real results.

    ``kind`` names the structure type; ``key`` is the full key including
    the demo namespace; ``commands`` are redis-cli-shaped renderings of
    what actually ran; ``outcome`` summarizes what the store answered;
    ``values`` carries the read-back values in read order.
    """

    kind: Literal["string", "hash", "list", "set", "zset"]
    key: str
    description: str
    commands: list[str]
    outcome: str
    values: list[StructureValueRow]


class TtlProofRow(CamelModel):
    """The TTL exhibit: set, watch the clock run out, prove the absence."""

    key: str
    ttl_seconds: int
    """The expiry the exhibit configured (SET's inline EX seconds)."""

    commands: list[str]
    ttl_first_read: int
    """TTL immediately after the SET — the live clock, within [1, ttl_seconds]."""

    absent_after_expiry: bool
    waited_ms: int
    proof: str


class PubsubProofRow(CamelModel):
    """The pub/sub exhibit: one real message, both sides of the wire."""

    channel: str
    payload: str
    commands: list[str]
    receivers: int
    """What PUBLISH answered — how many subscribers received the message."""

    received_payload: str
    matched: bool
    proof: str


class RedisPlaygroundRun(CamelModel):
    """Everything one playground run really did, namespace included."""

    namespace: str
    tag: str
    structures: list[StructureRow]
    ttl: TtlProofRow
    pubsub: PubsubProofRow


@runtime_checkable
class RedisPlaygroundRunner(Protocol):
    """What every topic-20 Redis adapter must provide.

    One call walks the FIVE core structures on the live store (string
    with SET/GET/INCR, hash, list, set, sorted set — each with its real
    read-back), proves TTL expiry honestly (SET with a short inline
    expiry, the TTL clock observed, then the key's absence after the
    bounded wait), and performs a REAL pub/sub round-trip (a bounded
    listener task, one PUBLISH, the received message reported from both
    sides).
    Keys live under the dedicated ``guide_demo:redis:*`` namespace; every
    row carries what Redis actually answered, and unreachable Redis is
    the adapter's problem to translate (service_unavailable), never the
    port's.
    """

    async def run_playground(self, tag: str) -> RedisPlaygroundRun:
        """Run the playground; ``tag`` is woven into the keys and values."""
        ...
