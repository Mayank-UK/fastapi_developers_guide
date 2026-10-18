"""The mongo console adapter, against the REAL dev MongoDB.

No HTTP here — these pin the adapter's own contract: the keyed seed is
idempotent (a fresh database and a re-seeded one end in the same six
notes), the find honors filter + projection + sort with honest empties,
the insert/update/delete lifecycle cleans up after itself, the index
exhibit really flips COLLSCAN to IXSCAN, the TTL index really exists
with the configured ``expireAfterSeconds``, and unreachable MongoDB
degrades to ``service_unavailable`` (fast — the client's server-
selection timeout is the bound) instead of hanging or crashing.
"""

import time

import pytest
from mongo_url import COMPOSE_MONGO_URL

from guide.core.config import AppConfig
from guide.core.errors import AppError, FailureKind
from guide.data.mongo import MongoConsoleRepository, create_mongo_client
from guide.domain.db.ports import MongoConsoleRun


@pytest.fixture
async def repository() -> MongoConsoleRepository:
    """Adapter over the dev compose MongoDB; collection dropped for a clean stage."""
    client = create_mongo_client(_config_with(COMPOSE_MONGO_URL))
    try:
        await client["guide_demo"]["console_notes"].drop()
        yield MongoConsoleRepository(client)
    finally:
        client.close()


def _config_with(mongo_url: str) -> AppConfig:
    """An AppConfig speaking only the mongo rail (tests never read the host env)."""
    return AppConfig(mongo_url=mongo_url)


def _find(run: MongoConsoleRun) -> dict:
    return next(op for op in run.operations if op.op == "find")


def _op(run: MongoConsoleRun, op: str) -> dict:
    return next(o for o in run.operations if o.op == op)


async def test_seed_is_idempotent_from_empty_and_on_repeat(
    repository: MongoConsoleRepository,
) -> None:
    """A fresh database and a re-seeded one end in the same six notes."""
    first = await repository.run_console("indexes")
    second = await repository.run_console("indexes")
    assert (first.seed.count_before, first.seed.upserted, first.seed.total_after) == (0, 6, 6)
    assert (second.seed.count_before, second.seed.upserted, second.seed.total_after) == (6, 0, 6)
    assert first.seed.indexes_ensured == ["key_1 (unique)", "created_at_-1"]


async def test_find_honors_filter_projection_and_sort(
    repository: MongoConsoleRepository,
) -> None:
    """Filter on the array field, project the fat fields away, sort desc."""
    run = await repository.run_console("indexes")
    find = _find(run)
    assert [doc["key"] for doc in find.documents] == [
        "mongo-note-ttl",
        "mongo-note-indexes",
        "mongo-note-embedding",
    ]
    assert all(set(doc) == {"key", "title", "author", "created_at"} for doc in find.documents)
    assert all("T" in doc["created_at"] for doc in find.documents)  # ISO datetimes on the wire


async def test_unknown_tag_is_an_honest_empty_not_an_error(
    repository: MongoConsoleRepository,
) -> None:
    run = await repository.run_console("no-such-tag")
    find = _find(run)
    assert find.documents == []
    assert "empty cursor" in find.outcome
    assert _op(run, "count").outcome == "0 document(s)"


async def test_the_refusal_names_every_bad_field_before_any_io(
    repository: MongoConsoleRepository,
) -> None:
    """The pydantic boundary refuses the draft — three field errors, zero writes."""
    run = await repository.run_console("indexes")
    errors = " | ".join(run.refusal.errors)
    assert "title" in errors and "tags" in errors and "status" in errors
    assert run.refusal.attempted["status"] == "embargoed"
    # The refused document never stored: only the ACCEPTED demo insert exists,
    # and the delete step removes it by key — exactly one match.
    assert _op(run, "insert").outcome.startswith("acknowledged")


async def test_the_demo_lifecycle_cleans_up_after_itself(
    repository: MongoConsoleRepository,
) -> None:
    """Insert → update → delete leaves the collection back at its seed."""
    run = await repository.run_console("indexes")
    update = _op(run, "update")
    assert update.outcome == "matched 1, modified 1"
    assert update.documents[0]["key"] == "mongo-demo-insert"
    assert _op(run, "delete").outcome == "deletedCount 1"
    # Provable count agreement: the find and the count share one filter.
    assert _op(run, "count").outcome == f"{len(_find(run).documents)} document(s)"


async def test_index_exhibit_flips_collscan_to_ixscan(
    repository: MongoConsoleRepository,
) -> None:
    """The SAME query explained twice: COLLSCAN over 8 docs, then IXSCAN on 1 key."""
    run = await repository.run_console("indexes")
    collscan, ixscan = run.index_showcase.explains
    assert (collscan.stage, collscan.docs_examined, collscan.keys_examined) == ("COLLSCAN", 8, 0)
    assert collscan.index_name is None
    assert (ixscan.stage, ixscan.index_name) == ("IXSCAN", "title_1")
    assert (ixscan.keys_examined, ixscan.docs_examined) == (1, 1)
    assert run.index_showcase.index_command == "db.explain_stage.createIndex({title: 1})"


async def test_the_ttl_index_really_exists_with_the_configured_expiry(
    repository: MongoConsoleRepository,
) -> None:
    """A real expireAfterSeconds index on the scratch collection.

    Eviction itself runs on mongod's ~60 s TTL monitor — deliberately not
    waited for here; the definition (and its field type) is the proof the
    suite can afford.
    """
    run = await repository.run_console("indexes")
    ttl = run.ttl_showcase
    assert ttl.expire_after_seconds == 10
    assert ttl.index_definition["name"] == "expires_at_1"
    assert ttl.index_definition["expireAfterSeconds"] == "10"
    assert "expires_at" in ttl.index_definition["key"]
    assert [doc["label"] for doc in ttl.scratch_documents] == ["ephemeral", "durable"]
    assert "sweeper" in ttl.eviction_note or "sweeps" in ttl.eviction_note


async def test_unreachable_mongodb_degrades_fast_to_service_unavailable() -> None:
    """The optional-service discipline: port 1 refuses instantly, the adapter maps it."""
    repository = MongoConsoleRepository(
        create_mongo_client(_config_with("mongodb://127.0.0.1:1"))
    )
    started = time.perf_counter()
    with pytest.raises(AppError) as raised:
        await repository.run_console("indexes")
    elapsed = time.perf_counter() - started
    assert raised.value.kind is FailureKind.SERVICE_UNAVAILABLE
    assert elapsed < 6, f"degradation must be fast, took {elapsed:.1f}s"
