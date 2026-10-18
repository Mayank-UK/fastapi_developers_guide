"""Topic 17 databases-sql: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (sql_schema is the direct sibling):
exact section order (ten sections), unique ids, all SIX demo blocks
INLINE in the sections that teach them (§2 safety, §3 migrations, §5
lab, §7 search, §8 race, §9 audit), the terminal companion last, family
word depth, and (belt to the global ratchet) every must-source block
verified against its real file.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "databases-sql"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "drivers-and-layers",
    "dao-and-parameterized-queries",
    "transactions",
    "orm-comparison",
    "sql-by-hand",
    "explain-analyze",
    "full-text-search",
    "isolation-locking-races",
    "audit-in-the-transaction",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_joins_the_data_group_as_seventeenth() -> None:
    topic = _topic()
    assert topic.group == "data"
    assert topic.order == 17
    summary = next(s for s in production_registry.summaries() if s.id == TOPIC_ID)
    assert summary.section_count == len(EXPECTED_SECTION_IDS)


def test_sections_are_the_ten_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_all_six_demos_sit_inline_in_their_teaching_sections() -> None:
    for index, demo_id in (
        (1, "db:sql-safety"),
        (2, "db:migrations"),
        (4, "db:sql-lab"),
        (6, "db:search"),
        (7, "db:race"),
        (8, "db:audit"),
    ):
        section = _topic().sections[index]
        demos = [b for b in section.blocks if isinstance(b, DemoBlock)]
        assert [d.id for d in demos] == [demo_id], section.id
        # Inline means beside the teaching: text and code carry it too.
        kinds = {b.kind for b in section.blocks}
        assert {"text", "code", "demo"} <= kinds, section.id


def test_last_section_is_the_bash_terminal_companion() -> None:
    last = _topic().sections[-1]
    assert last.id == "terminal-companion"
    code_blocks = [b for b in last.blocks if isinstance(b, CodeBlock)]
    assert code_blocks, "terminal companion needs its curl tour"
    assert all(b.language == "bash" and b.source is None for b in code_blocks)


def test_prose_depth_meets_the_family_floor() -> None:
    words = sum(
        len(block.text.split())
        for section in _topic().sections
        for block in section.blocks
        if isinstance(block, TextBlock)
    )
    assert words >= MIN_PROSE_WORDS


def test_the_repository_sql_and_migration_are_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/guide/data/db/repository.py" in sources
    assert "server/alembic/versions/0002_posts_search_vector.py" in sources
    assert "server/guide/data/db/engine.py" in sources
    assert "server/guide/domain/demos/sql_safety.py" in sources
    # The SQL blocks are real queries quoted from the repository.
    sql_blocks = [b for b in code_blocks if b.language == "sql"]
    assert len(sql_blocks) >= 4
    assert all(b.source == "server/guide/data/db/repository.py" for b in sql_blocks)
    # The EXPLAIN outputs are transcripts — text blocks, honestly exempt.
    plan_blocks = [
        b for b in code_blocks if b.id.startswith("explain-") and b.id.endswith("output")
    ]
    assert {b.language for b in plan_blocks} == {"text"}
    assert all(b.source is None for b in plan_blocks)


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [
        b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"
    ]
    assert demos == [
        "db:sql-safety",
        "db:migrations",
        "db:sql-lab",
        "db:search",
        "db:race",
        "db:audit",
    ]
