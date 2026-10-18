"""Topic 22 messaging: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (caching is the direct sibling): exact
section order (eight sections), unique ids, the TWO demo blocks INLINE in
the sections that teach them (msg:stream in §2 logs-vs-queues, msg:outbox
in §5 transactional-outbox), the terminal companion last, family word
depth, and (belt to the global ratchet) every must-source block verified
against its real file.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "messaging"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "why-asynchronous-work",
    "logs-vs-queues",
    "delivery-guarantees",
    "pending-entries-and-xautoclaim",
    "transactional-outbox",
    "idempotent-consumers",
    "kafka-and-rabbitmq",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_joins_the_state_auth_group_as_twenty_second() -> None:
    topic = _topic()
    assert topic.group == "state-auth"
    assert topic.order == 22
    summary = next(s for s in production_registry.summaries() if s.id == TOPIC_ID)
    assert summary.section_count == len(EXPECTED_SECTION_IDS)


def test_sections_are_the_eight_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_the_demos_sit_inline_in_their_teaching_sections() -> None:
    sections = _topic().sections
    stream_section, outbox_section = sections[1], sections[4]
    assert [d.id for d in stream_section.blocks if isinstance(d, DemoBlock)] == ["msg:stream"]
    assert [d.id for d in outbox_section.blocks if isinstance(d, DemoBlock)] == ["msg:outbox"]
    # Inline means beside the teaching: text and code carry each demo too.
    for section in (stream_section, outbox_section):
        kinds = {b.kind for b in section.blocks}
        assert {"text", "code", "demo"} <= kinds, section.id
    # Exactly two demos in the whole topic, in curriculum order.
    all_demos = [b for s in sections for b in s.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in all_demos] == ["msg:stream", "msg:outbox"]


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


def test_the_messaging_stack_is_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/guide/domain/messaging/ports.py" in sources
    assert "server/guide/domain/messaging/stream_service.py" in sources
    assert "server/guide/domain/messaging/outbox_service.py" in sources
    assert "server/guide/domain/messaging/idempotence.py" in sources
    assert "server/guide/data/messaging/redis_streams.py" in sources
    assert "server/guide/data/messaging/outbox_store.py" in sources
    assert "server/alembic/versions/0004_outbox.py" in sources


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [
        b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"
    ]
    assert demos == ["msg:stream", "msg:outbox"]
