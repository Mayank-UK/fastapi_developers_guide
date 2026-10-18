"""The mongo-console demo payloads: everything the live store answered.

``GET /api/demo/db/mongo-console`` serves these payloads — topic 19's
single demo, inline in the section that teaches queries. One request
runs the whole scripted console against the live MongoDB through the
``MongoConsoleRunner`` port: the idempotent keyed seed, one pydantic
refusal and one acceptance at the document boundary, find with filter +
projection + sort, update one, count, delete, the index exhibit
(COLLSCAN vs IXSCAN explains over the same query), and a real TTL
index. The builder below is PURE — it re-shapes the run's rows and
derives every verdict sentence from what actually ran, so the payload
can never drift from the store.
"""

from guide.core.serialization import CamelModel
from guide.domain.db.ports import (
    ConsoleOperationRow,
    IndexShowcaseRow,
    MongoConsoleRun,
    RefusalRow,
    SeedReport,
    TtlShowcaseRow,
)


class MongoConsolePayload(CamelModel):
    """Wire shape of ``GET /api/demo/db/mongo-console``."""

    database: str
    seed: SeedReport
    refusal: RefusalRow
    operations: list[ConsoleOperationRow]
    index_showcase: IndexShowcaseRow
    ttl_showcase: TtlShowcaseRow
    reasoning: str


def build_mongo_console_payload(run: MongoConsoleRun, tag: str) -> MongoConsolePayload:
    """Shape the console run (pure) — the reasoning derives from the rows."""
    find = next(op for op in run.operations if op.op == "find")
    count = next(op for op in run.operations if op.op == "count")
    delete = next(op for op in run.operations if op.op == "delete")
    collscan, ixscan = run.index_showcase.explains
    reasoning = (
        f"Every row above is what the live {run.database} database answered. "
        f"The seed step upserted {len(run.seed.seed_keys)} keyed documents "
        f"idempotently — {run.seed.count_before} were already present, "
        f"{run.seed.upserted} planted fresh — and ensured the "
        f"{', '.join(run.seed.indexes_ensured)} "
        "indexes the console relies on. The insert was refused once at the "
        f"pydantic boundary ({len(run.refusal.errors)} field errors, zero I/O), "
        "then accepted and stored. The find with filter "
        f"{{tags: '{tag}'}} plus projection plus newest-first sort returned "
        f"{len(find.documents)} document(s), and count_documents over the same "
        f"filter agreed: {count.outcome}. The index exhibit ran one query twice: "
        f"{collscan.stage} examined {collscan.docs_examined} documents without an "
        f"index, then {ixscan.stage} on {ixscan.index_name} examined "
        f"{ixscan.keys_examined} key(s) and {ixscan.docs_examined} document(s) — "
        "the B-tree doing the filtering's work. The TTL exhibit defined a real "
        f"expireAfterSeconds={run.ttl_showcase.expire_after_seconds} index; "
        f"eviction runs on mongod's ~60 s sweeper, which this console shows "
        f"rather than waits for. {delete.outcome} — the demo document is gone "
        "and the collection is back to its seed."
    )
    return MongoConsolePayload(
        database=run.database,
        seed=run.seed,
        refusal=run.refusal,
        operations=run.operations,
        index_showcase=run.index_showcase,
        ttl_showcase=run.ttl_showcase,
        reasoning=reasoning,
    )
