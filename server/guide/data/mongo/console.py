"""The topic-19 adapter: a real console over the live MongoDB.

``MongoConsoleRepository`` implements the domain's ``MongoConsoleRunner``
port against a dedicated demo namespace (the ``guide_demo`` database —
nothing pre-existing in the container is ever touched). One ``run_console``
call is the whole scripted console: an idempotent keyed seed, one refusal
and one acceptance through the ``ConsoleNoteDraft`` boundary, find with
filter + projection + sort, update one, count, delete, then two exhibits —
the index showcase (the SAME query explained before and after
``createIndex``: COLLSCAN vs IXSCAN with examined counts) and a REAL TTL
index on a scratch collection (definition shown; eviction is mongod's
~60 s background sweeper, which the console deliberately does not wait
for). Unreachable MongoDB maps to ``service_unavailable`` exactly like
every other data adapter (optional-service discipline).
"""

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, Final

import structlog
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pydantic import ValidationError
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from guide.core.errors import AppError, FailureKind
from guide.domain.db.ports import (
    ConsoleNoteDraft,
    ConsoleOperationRow,
    ExplainStageRow,
    IndexShowcaseRow,
    MongoConsoleRun,
    RefusalRow,
    SeedReport,
    TtlShowcaseRow,
)

logger = structlog.get_logger()

ConsoleCollection = AsyncIOMotorCollection[dict[str, Any]]
"""The console collections' shape — plain dicts in and out of motor."""

DemoDatabase = AsyncIOMotorDatabase[dict[str, Any]]
"""The demo database's shape — its collections are plain-dict collections."""

GUIDE_DEMO_DB: Final = "guide_demo"
"""The demos' dedicated database — the whole topic owns this namespace."""

CONSOLE_COLLECTION: Final = "console_notes"
EXPLAIN_COLLECTION: Final = "explain_stage"
TTL_COLLECTION: Final = "ttl_stage"
TTL_EXPIRE_AFTER_SECONDS: Final = 10
"""Short enough to teach, long enough that no run ever races the sweeper."""

DEMO_KEY: Final = "mongo-demo-insert"
"""The insert/update/delete exhibit's key — reset at the start, deleted at
the end, so every run sees exactly the same lifecycle."""

EXPLAIN_DOC_COUNT: Final = 8
EXPLAIN_QUERY_TITLE: Final = "explain stage note 5"

SEED_NOTES: Final[tuple[ConsoleNoteDraft, ...]] = (
    ConsoleNoteDraft(
        key="mongo-note-documents",
        author="Grace Hopper",
        title="A document is the unit",
        body="No rows, no joins over foreign keys — the whole record is one addressable value.",
        tags=["modeling"],
        status="published",
        created_at=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
    ),
    ConsoleNoteDraft(
        key="mongo-note-flexible-fields",
        author="Alan Turing",
        title="Fields may differ per document",
        body="The collection enforces nothing; the application's models are the schema.",
        tags=["modeling"],
        status="published",
        created_at=datetime(2026, 10, 1, 11, 0, tzinfo=UTC),
    ),
    ConsoleNoteDraft(
        key="mongo-note-embedding",
        author="Barbara Liskov",
        title="Embed what you read together",
        body="Arrays and subdocuments travel with the parent — one read, no join.",
        tags=["modeling", "indexes"],
        status="published",
        created_at=datetime(2026, 10, 1, 13, 0, tzinfo=UTC),
    ),
    ConsoleNoteDraft(
        key="mongo-note-indexes",
        author="Grace Hopper",
        title="Indexes are B-trees here too",
        body="createIndex on a field and explain() flips COLLSCAN to IXSCAN.",
        tags=["indexes"],
        status="published",
        created_at=datetime(2026, 10, 1, 15, 0, tzinfo=UTC),
    ),
    ConsoleNoteDraft(
        key="mongo-note-ttl",
        author="Alan Turing",
        title="Expiry belongs in the index layer",
        body="A TTL index deletes expired documents so application code never does.",
        tags=["indexes", "ttl"],
        status="published",
        created_at=datetime(2026, 10, 1, 17, 0, tzinfo=UTC),
    ),
    ConsoleNoteDraft(
        key="mongo-note-motor",
        author="Barbara Liskov",
        title="Motor is pymongo on the event loop",
        body="Same wire protocol, awaited methods, one shared executor thread pool.",
        tags=["motor"],
        status="published",
        created_at=datetime(2026, 10, 1, 19, 0, tzinfo=UTC),
    ),
)

INVALID_DRAFT_PAYLOAD: Final[dict[str, Any]] = {
    "key": DEMO_KEY,
    "author": "Grace Hopper",
    "title": "",
    "body": "The body is fine; three other fields are not.",
    "tags": [],
    "status": "embargoed",
    "created_at": "2026-10-02T09:00:00Z",
}
"""The refusal exhibit: empty title, empty tags, unknown status — pydantic
refuses all three BEFORE any I/O, so MongoDB never sees this document."""

FIND_PROJECTION: Final[dict[str, int]] = {
    "_id": 0,
    "key": 1,
    "title": 1,
    "author": 1,
    "created_at": 1,
}


@contextmanager
def _map_mongo_failures(operation: str) -> Iterator[None]:
    """Optional-service discipline: MongoDB trouble becomes service_unavailable."""
    try:
        yield
    except AppError:
        raise
    except (PyMongoError, OSError) as exc:
        logger.warning(
            "mongo_console_unavailable",
            operation=operation,
            error=type(exc).__name__,
            detail=str(exc),
        )
        raise AppError(
            FailureKind.SERVICE_UNAVAILABLE,
            "MongoDB is unreachable or unusable — this demo runs real operations "
            "against the live document store and refuses to serve stale facts.",
        ) from exc


def _render_document(document: Mapping[str, Any]) -> dict[str, str]:
    """One BSON document as display strings — dates ISO, ObjectId str, lists joined."""
    rendered: dict[str, str] = {}
    for field, value in document.items():
        if isinstance(value, datetime):
            rendered[field] = value.isoformat()
        elif isinstance(value, list):
            rendered[field] = ", ".join(str(item) for item in value)
        else:
            rendered[field] = str(value)
    return rendered


def _mongosh(document: Mapping[str, Any]) -> str:
    """A mongosh-shaped rendering of one command argument."""
    return json.dumps(document, default=str, ensure_ascii=False)


def _access_stage(plan: Mapping[str, Any]) -> tuple[str, str | None]:
    """Walk the winning plan to its access stage: COLLSCAN or IXSCAN (+ name)."""
    stage = plan
    name = str(stage.get("stage", ""))
    while "inputStage" in stage:
        stage = stage["inputStage"]
        name = str(stage.get("stage", name))
    index_name = str(stage["indexName"]) if name == "IXSCAN" and "indexName" in stage else None
    return name, index_name


class MongoConsoleRepository:
    """The live-MongoDB adapter behind topic 19's console demo."""

    def __init__(self, client: AsyncIOMotorClient[dict[str, Any]]) -> None:
        self._client = client

    async def run_console(self, tag: str) -> MongoConsoleRun:
        """Run the scripted console; every row is what MongoDB answered."""
        with _map_mongo_failures("console run"):
            database = self._client[GUIDE_DEMO_DB]
            console = database[CONSOLE_COLLECTION]
            seed = await self._seed(console)
            refusal = _refuse_invalid_draft()
            operations = [
                await self._op_insert(console),
                await self._op_find(console, tag),
                await self._op_update(console),
                await self._op_count(console, tag),
                await self._op_delete(console),
            ]
            index_showcase = await self._index_showcase(database)
            ttl_showcase = await self._ttl_showcase(database)
            return MongoConsoleRun(
                database=GUIDE_DEMO_DB,
                seed=seed,
                refusal=refusal,
                operations=operations,
                index_showcase=index_showcase,
                ttl_showcase=ttl_showcase,
            )

    async def _seed(self, console: ConsoleCollection) -> SeedReport:
        """Keyed upserts: the first run plants six notes, every later run no-ops."""
        keys = [note.key for note in SEED_NOTES]
        count_before = await console.count_documents({"key": {"$in": keys}})
        upserted = 0
        for note in SEED_NOTES:
            result = await console.replace_one({"key": note.key}, note.model_dump(), upsert=True)
            if result.upserted_id is not None:
                upserted += 1
        total_after = await console.count_documents({"key": {"$in": keys}})
        key_index = await console.create_index([("key", ASCENDING)], unique=True)
        sort_index = await console.create_index([("created_at", DESCENDING)])
        return SeedReport(
            collection=CONSOLE_COLLECTION,
            seed_keys=keys,
            count_before=count_before,
            upserted=upserted,
            total_after=total_after,
            indexes_ensured=[f"{key_index} (unique)", sort_index],
        )

    async def _op_insert(self, console: ConsoleCollection) -> ConsoleOperationRow:
        """Reset the demo key, validate a draft, then insert_one the dump."""
        reset = await console.delete_many({"key": DEMO_KEY})
        draft = ConsoleNoteDraft(
            key=DEMO_KEY,
            author="Grace Hopper",
            title="The document boundary",
            body="Validated by ConsoleNoteDraft first; the store trusted the dump.",
            tags=["demo"],
            status="draft",
            created_at=datetime.now(UTC),
        )
        result = await console.insert_one(draft.model_dump())
        stored = {"_id": result.inserted_id, **draft.model_dump()}
        return ConsoleOperationRow(
            op="insert",
            description=(
                f"Reset the demo key first (delete_many removed {reset.deleted_count} "
                "stale copy), validate through ConsoleNoteDraft, then insert_one the dump."
            ),
            command=f"db.{CONSOLE_COLLECTION}.insert_one({_mongosh(draft.model_dump(mode='json'))})",
            outcome=f"acknowledged — insertedId {result.inserted_id}",
            documents=[_render_document(stored)],
        )

    async def _op_find(self, console: ConsoleCollection, tag: str) -> ConsoleOperationRow:
        """Filter + projection + sort: the shape of every document read."""
        query = {"tags": tag}
        cursor = console.find(query, FIND_PROJECTION).sort([("created_at", DESCENDING)])
        found = await cursor.to_list(length=None)
        outcome = (
            f"{len(found)} document(s) match tags={tag!r}"
            + ("" if found else " — an empty cursor is the honest answer, not an error")
        )
        return ConsoleOperationRow(
            op="find",
            description="Filter on an array field, project away the fat fields, sort newest-first.",
            command=(
                f'db.{CONSOLE_COLLECTION}.find({{tags: "{tag}"}}, '
                "{key: 1, title: 1, author: 1, created_at: 1, _id: 0})"
                ".sort({created_at: -1})"
            ),
            outcome=outcome,
            documents=[_render_document(doc) for doc in found],
        )

    async def _op_update(self, console: ConsoleCollection) -> ConsoleOperationRow:
        """Update operators change fields in place; matched/modified are separate facts."""
        result = await console.update_one({"key": DEMO_KEY}, {"$set": {"status": "archived"}})
        after = await console.find_one({"key": DEMO_KEY}, FIND_PROJECTION)
        return ConsoleOperationRow(
            op="update",
            description="One document by key: $set a field, then read it back.",
            command=(
                f'db.{CONSOLE_COLLECTION}.update_one({{key: "{DEMO_KEY}"}}, '
                '{$set: {status: "archived"}})'
            ),
            outcome=f"matched {result.matched_count}, modified {result.modified_count}",
            documents=[_render_document(after)] if after is not None else [],
        )

    async def _op_count(self, console: ConsoleCollection, tag: str) -> ConsoleOperationRow:
        """count_documents with the SAME filter the find used — the totals agree."""
        count = await console.count_documents({"tags": tag})
        return ConsoleOperationRow(
            op="count",
            description="Server-side count over the same filter the find used.",
            command=f'db.{CONSOLE_COLLECTION}.count_documents({{tags: "{tag}"}})',
            outcome=f"{count} document(s)",
            documents=[],
        )

    async def _op_delete(self, console: ConsoleCollection) -> ConsoleOperationRow:
        """Delete the demo document — the collection returns to its seed state."""
        result = await console.delete_one({"key": DEMO_KEY})
        return ConsoleOperationRow(
            op="delete",
            description="Remove the demo document; the seed is all that remains.",
            command=f'db.{CONSOLE_COLLECTION}.delete_one({{key: "{DEMO_KEY}"}})',
            outcome=f"deletedCount {result.deleted_count}",
            documents=[],
        )

    async def _index_showcase(self, database: DemoDatabase) -> IndexShowcaseRow:
        """The same query explained twice: COLLSCAN, then IXSCAN on a real index."""
        stage = database[EXPLAIN_COLLECTION]
        await stage.drop()
        await stage.insert_many(
            [
                {"slot": slot, "title": f"explain stage note {slot}"}
                for slot in range(1, EXPLAIN_DOC_COUNT + 1)
            ]
        )
        query = {"title": EXPLAIN_QUERY_TITLE}
        before = await self._explain(database, EXPLAIN_COLLECTION, query)
        index_name = await stage.create_index([("title", ASCENDING)])
        after = await self._explain(database, EXPLAIN_COLLECTION, query)
        return IndexShowcaseRow(
            collection=EXPLAIN_COLLECTION,
            document_count=EXPLAIN_DOC_COUNT,
            index_command=f"db.{EXPLAIN_COLLECTION}.createIndex({{title: 1}})",
            explains=[
                ExplainStageRow(
                    label="without an index",
                    query=f'{{title: "{EXPLAIN_QUERY_TITLE}"}}',
                    stage=before[0],
                    index_name=before[1],
                    keys_examined=before[2],
                    docs_examined=before[3],
                ),
                ExplainStageRow(
                    label=f"with {index_name}",
                    query=f'{{title: "{EXPLAIN_QUERY_TITLE}"}}',
                    stage=after[0],
                    index_name=after[1],
                    keys_examined=after[2],
                    docs_examined=after[3],
                ),
            ],
        )

    async def _explain(
        self,
        database: DemoDatabase,
        collection: str,
        query: Mapping[str, Any],
    ) -> tuple[str, str | None, int, int]:
        """Run one explain and extract stage, index name, and examined counts."""
        explained = await database.command(
            {"explain": {"find": collection, "filter": dict(query)}, "verbosity": "executionStats"}
        )
        query_planner: dict[str, Any] = explained.get("queryPlanner", {})
        winning_plan: dict[str, Any] = query_planner.get("winningPlan", {})
        stage, index_name = _access_stage(winning_plan)
        execution_stats: dict[str, Any] = explained.get("executionStats", {})
        return (
            stage,
            index_name,
            int(execution_stats.get("totalKeysExamined", 0)),
            int(execution_stats.get("totalDocsExamined", 0)),
        )

    async def _ttl_showcase(self, database: DemoDatabase) -> TtlShowcaseRow:
        """A real TTL index on a scratch collection — definition shown, not waited on."""
        stage = database[TTL_COLLECTION]
        await stage.drop()
        await stage.create_index(
            [("expires_at", ASCENDING)], expireAfterSeconds=TTL_EXPIRE_AFTER_SECONDS
        )
        now = datetime.now(UTC)
        await stage.insert_many(
            [
                {
                    "label": "ephemeral",
                    "expires_at": now + timedelta(seconds=TTL_EXPIRE_AFTER_SECONDS),
                },
                {"label": "durable", "expires_at": now + timedelta(hours=1)},
            ]
        )
        indexes = await stage.list_indexes().to_list(length=None)
        ttl_entry = next(entry for entry in indexes if "expireAfterSeconds" in entry)
        scratch = await stage.find({}, {"_id": 0}).to_list(length=None)
        return TtlShowcaseRow(
            collection=TTL_COLLECTION,
            index_definition={
                field: str(dict(value)) if isinstance(value, Mapping) else str(value)
                for field, value in ttl_entry.items()
            },
            expire_after_seconds=int(ttl_entry["expireAfterSeconds"]),
            scratch_documents=[_render_document(doc) for doc in scratch],
            eviction_note=(
                "mongod's TTL monitor sweeps this collection roughly every 60 s and "
                "deletes documents whose expires_at is older than the index's "
                f"{TTL_EXPIRE_AFTER_SECONDS} s grace; this console shows the real "
                "definition and relies on the sweeper — it does not sit and wait."
            ),
        )


def _refuse_invalid_draft() -> RefusalRow:
    """The boundary proof: pydantic refuses the bad draft before any I/O.

    Pure by design — no motor, no collection; the ValidationError is the
    whole exhibit, which is exactly the point: MongoDB never sees (and
    never could store) the refused document.
    """
    try:
        ConsoleNoteDraft.model_validate(INVALID_DRAFT_PAYLOAD)
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        return RefusalRow(
            attempted={field: str(value) for field, value in INVALID_DRAFT_PAYLOAD.items()},
            errors=errors,
        )
    raise AppError(FailureKind.INTERNAL, "the invalid draft unexpectedly validated")
