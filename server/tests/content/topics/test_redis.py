"""Topic 20 redis: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (mongodb is the direct sibling): exact
section order (seven sections), unique ids, the ONE demo block INLINE in
the section that teaches the structures (§3), the terminal companion last,
family word depth, and (belt to the global ratchet) every must-source block
verified against its real file.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "redis"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "what-redis-is",
    "the-optional-service-discipline",
    "redis-asyncio-structures",
    "ttl-and-expiry",
    "pub-sub",
    "when-a-second-store",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_joins_the_data_group_as_twentieth() -> None:
    topic = _topic()
    assert topic.group == "data"
    assert topic.order == 20
    summary = next(s for s in production_registry.summaries() if s.id == TOPIC_ID)
    assert summary.section_count == len(EXPECTED_SECTION_IDS)


def test_sections_are_the_seven_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_the_demo_sits_inline_in_the_structures_section() -> None:
    section = _topic().sections[2]
    demos = [b for b in section.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["redis:playground"], section.id
    # Inline means beside the teaching: text and code carry it too.
    kinds = {b.kind for b in section.blocks}
    assert {"text", "code", "demo"} <= kinds, section.id
    # Exactly one demo in the whole topic.
    all_demos = [
        b for s in _topic().sections for b in s.blocks if isinstance(b, DemoBlock)
    ]
    assert [d.id for d in all_demos] == ["redis:playground"]


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


def test_the_redis_stack_is_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/guide/core/config.py" in sources
    assert "server/guide/data/redis/client.py" in sources
    assert "server/guide/data/redis/playground.py" in sources
    assert "server/guide/domain/db/ports.py" in sources
    assert "server/guide/main.py" in sources
    assert "server/guide/presentation/routers/demo/redis.py" in sources
    assert "server/tests/demo/test_redis_playground_endpoint.py" in sources


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [
        b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"
    ]
    assert demos == ["redis:playground"]
