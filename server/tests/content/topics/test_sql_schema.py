"""Topic 16 sql-schema: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (grpc, webhooks): exact section
order, unique ids, both demo blocks INLINE in the sections that teach
them (§5 explorer, §7 uuid lab), the terminal companion last, family
word depth, and (belt to the global ratchet) every must-source block
verified against its real file.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "sql-schema"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "relational-thinking",
    "pg-types-and-constraints",
    "primary-and-foreign-keys",
    "normalization-to-denormalization",
    "indexes",
    "alembic-history",
    "uuid7-vs-sequential",
    "audit-logging-pattern",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_opens_the_data_group_as_sixteenth() -> None:
    topic = _topic()
    assert topic.group == "data"
    assert topic.order == 16
    assert [group.id for group in production_registry.groups()] == [
        "foundations",
        "framework",
        "request-handling",
        "apis",
        "data",
        "state-auth",
        "media-realtime",
        "platform",
        "ship",
        "capstones",
    ]
    summary = next(s for s in production_registry.summaries() if s.id == TOPIC_ID)
    assert summary.section_count == len(EXPECTED_SECTION_IDS)


def test_sections_are_the_nine_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_explorer_demo_sits_inline_in_the_indexes_section() -> None:
    section = _topic().sections[4]
    assert section.id == "indexes"
    demos = [b for b in section.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["db:schema-explorer"]
    # Inline means beside the teaching: the section still carries text + code.
    kinds = {b.kind for b in section.blocks}
    assert kinds == {"text", "code", "demo"}


def test_uuid_demo_sits_inline_in_the_seventh_section() -> None:
    section = _topic().sections[6]
    assert section.id == "uuid7-vs-sequential"
    demos = [b for b in section.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["db:uuid"]
    # Inline means beside the teaching: text + code carry it; the three
    # strategies also form a list block here.
    kinds = {b.kind for b in section.blocks}
    assert {"text", "code", "demo"} <= kinds


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


def test_the_schema_and_migration_are_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/guide/data/db/schema.py" in sources
    assert "server/alembic/versions/0001_guide_schema.py" in sources
    assert "server/guide/domain/db/ids.py" in sources
    assert "server/guide/data/db/introspection.py" in sources
    # The introspection SQL block must be language sql — real queries, quoted.
    sql_blocks = [b for b in code_blocks if b.language == "sql"]
    assert len(sql_blocks) >= 1
    assert all(b.source == "server/guide/data/db/introspection.py" for b in sql_blocks)


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
