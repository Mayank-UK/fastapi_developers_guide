"""Topic 18 sqlalchemy-orm: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (databases_sql is the direct sibling):
exact section order (ten sections), unique ids, the ONE demo block
INLINE in the section that teaches relationship loading (§3), the
terminal companion last, family word depth, and (belt to the global
ratchet) every must-source block verified against its real file.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "sqlalchemy-orm"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "what-an-orm-does",
    "session-identity-map-dirty-checking",
    "relationship-loading",
    "the-n-plus-one-problem",
    "projections-and-dtos",
    "async-sessions",
    "optimistic-versioning",
    "pagination",
    "testcontainers",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_joins_the_data_group_as_eighteenth() -> None:
    topic = _topic()
    assert topic.group == "data"
    assert topic.order == 18
    summary = next(s for s in production_registry.summaries() if s.id == TOPIC_ID)
    assert summary.section_count == len(EXPECTED_SECTION_IDS)


def test_sections_are_the_ten_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_the_demo_sits_inline_in_the_loading_section() -> None:
    section = _topic().sections[2]
    demos = [b for b in section.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["db:orm-probe"], section.id
    # Inline means beside the teaching: text and code carry it too.
    kinds = {b.kind for b in section.blocks}
    assert {"text", "code", "demo"} <= kinds, section.id
    # Exactly one demo in the whole topic.
    all_demos = [
        b for s in _topic().sections for b in s.blocks if isinstance(b, DemoBlock)
    ]
    assert [d.id for d in all_demos] == ["db:orm-probe"]


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


def test_the_orm_stack_and_testcontainers_are_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/guide/data/db/orm/models.py" in sources
    assert "server/guide/data/db/orm/sessions.py" in sources
    assert "server/guide/data/db/orm/query_counter.py" in sources
    assert "server/guide/data/db/orm/probe.py" in sources
    assert "server/alembic/versions/0003_posts_version_counter.py" in sources
    assert "server/tests/data/test_orm_testcontainers.py" in sources
    assert "server/guide/main.py" in sources
    # The captured statements (N+1 transcript, the guarded UPDATE, the two
    # pagination queries) are runtime output — text blocks, honestly exempt.
    transcripts = [
        b for b in code_blocks if b.language == "text" and b.source is None
    ]
    assert len(transcripts) == 4


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [
        b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"
    ]
    assert demos == ["db:orm-probe"]
