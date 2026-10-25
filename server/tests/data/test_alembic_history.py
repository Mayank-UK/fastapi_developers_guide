"""Alembic history tests: the chain resolves, and head applies idempotently.

Pins the migration setup this topic establishes for the whole guide:
the revision chain (0001 schema → 0002 search_vector → 0003 posts
version counter; later data topics append), config/version locations
resolve from the repo layout (with the production image's WORKDIR
fallback), ``upgrade head`` is safe to run twice (the lifespan does it
at every boot), the live dev database sits AT head, and the applied
schema matches the Core metadata (``alembic check`` finds no drift).
"""

import asyncio
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory
from pg_url import COMPOSE_PG_URL
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from guide.data.db import lifecycle
from guide.data.db.lifecycle import build_alembic_config, upgrade_database_to_head

EXPECTED_HEAD = "0004"
EXPECTED_REVISIONS = ("0004", "0003", "0002", "0001")


def test_script_directory_resolves_the_revision_chain() -> None:
    script = ScriptDirectory.from_config(build_alembic_config(COMPOSE_PG_URL))
    revisions = list(script.walk_revisions())
    assert [rev.revision for rev in revisions] == list(EXPECTED_REVISIONS)
    assert revisions[-1].down_revision is None
    assert revisions[2].down_revision == "0001"
    assert revisions[1].down_revision == "0002"
    assert revisions[0].down_revision == "0003"
    assert script.get_current_head() == EXPECTED_HEAD


def test_config_prefers_the_repo_checkout_over_a_cwd_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dev, CI, and tests run from the checkout: even when the cwd carries
    an image-style asset copy, the module-resolved server/ root wins."""
    (tmp_path / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    config = build_alembic_config("postgresql+asyncpg://user:pass@host:5432/db")

    assert config.config_file_name == str(lifecycle._SERVER_ROOT / "alembic.ini")
    assert config.get_main_option("script_location") == str(lifecycle._SERVER_ROOT / "alembic")


def test_config_falls_back_to_the_image_workdir_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Production image: the module sits in site-packages with no alembic
    tree beside it (simulate by repointing the module root at an empty
    directory), so the WORKDIR copy Dockerfile.prod ships serves the
    migration instead — the fix for prod boots skipping migrations."""
    workdir = tmp_path / "app"
    workdir.mkdir()
    (workdir / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    (workdir / "alembic").mkdir()
    monkeypatch.chdir(workdir)
    monkeypatch.setattr(lifecycle, "_SERVER_ROOT", tmp_path / "site-packages")

    config = build_alembic_config("postgresql+asyncpg://user:pass@host:5432/db")

    assert config.config_file_name == str(workdir / "alembic.ini")
    assert config.get_main_option("script_location") == str(workdir / "alembic")


def test_config_without_any_assets_still_targets_the_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Neither candidate carries the assets (a bare site-packages install):
    the checkout path is returned and the best-effort boot skip reports
    the miss — resolution never invents a third location."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lifecycle, "_SERVER_ROOT", tmp_path / "site-packages")

    config = build_alembic_config("postgresql+asyncpg://user:pass@host:5432/db")

    assert config.config_file_name == str(tmp_path / "site-packages" / "alembic.ini")
    assert config.get_main_option("script_location") == str(tmp_path / "site-packages" / "alembic")


async def test_upgrade_head_is_idempotent_on_the_live_dev_database() -> None:
    # The lifespan runs this at every boot; twice in a row must be a no-op.
    await asyncio.to_thread(upgrade_database_to_head, COMPOSE_PG_URL)
    await asyncio.to_thread(upgrade_database_to_head, COMPOSE_PG_URL)

    engine = create_async_engine(COMPOSE_PG_URL)
    try:
        async with engine.connect() as connection:
            current = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            assert current == EXPECTED_HEAD
            tables = {
                row[0]
                for row in await connection.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                    )
                )
            }
            assert {"authors", "posts", "comments", "audit_log", "outbox"} <= tables
            # 0004 landed: the transactional outbox (UUIDv7 event ids, the
            # unpublished partial index the relay's poll walks).
            outbox_columns = {
                row[0]
                for row in await connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'outbox'"
                    )
                )
            }
            assert outbox_columns == {
                "id",
                "event_id",
                "event_type",
                "aggregate",
                "payload",
                "created_at",
                "published_at",
            }
            outbox_indexes = {
                row[0]
                for row in await connection.execute(
                    text(
                        "SELECT indexname FROM pg_indexes WHERE tablename = 'outbox'"
                    )
                )
            }
            assert outbox_indexes == {
                "pk_outbox",
                "uq_outbox_event_id",
                "ix_outbox_unpublished",
            }
            # 0002 landed: the generated tsvector column and its GIN index.
            vector_columns = {
                row[0]
                for row in await connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'posts' AND column_name = 'search_vector'"
                    )
                )
            }
            assert vector_columns == {"search_vector"}
            # 0003 landed: the optimistic-versioning counter (server default 1).
            version_rows = (
                await connection.execute(
                    text(
                        "SELECT column_name, column_default FROM information_schema.columns "
                        "WHERE table_name = 'posts' AND column_name = 'version'"
                    )
                )
            ).all()
            assert version_rows == [("version", "1")]
            gin_indexes = {
                row[0]
                for row in await connection.execute(
                    text(
                        "SELECT ic.relname FROM pg_index ix "
                        "JOIN pg_class ic ON ic.oid = ix.indexrelid "
                        "JOIN pg_am am ON am.oid = ic.relam "
                        "WHERE ic.relname = 'ix_posts_search_vector' "
                        "AND am.amname = 'gin'"
                    )
                )
            }
            assert gin_indexes == {"ix_posts_search_vector"}
    finally:
        await engine.dispose()


async def test_applied_schema_matches_the_core_metadata_no_drift() -> None:
    """``alembic check``: autogenerate against the live database would
    propose NOTHING — the migration and guide/data/db/schema.py agree."""
    await asyncio.to_thread(command.check, build_alembic_config(COMPOSE_PG_URL))
