"""Topic 43 advanced-architecture: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (third-party is the direct sibling):
exact section order (nine sections), unique ids, BOTH demos INLINE in
the sections that teach them (arch:saga in §5 sagas, arch:eventstore
in §7 event-sourcing), the terminal companion last, family word depth,
and (belt to the global ratchet) every must-source block verified
against its real file. The topic's honesty rules are also pinned: the
sagas and event-sourcing sections quote the REAL patterns substrate
(guide/domain/patterns/ + its data adapter), and the CQRS section is
honest that the repo is not full CQRS.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "advanced-architecture"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "consistency-map",
    "ddd-vocabulary",
    "monolith-first",
    "between-services",
    "sagas",
    "cqrs",
    "event-sourcing",
    "tracing-across-boundaries",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_is_the_final_capstone_as_forty_third() -> None:
    topic = _topic()
    assert topic.group == "capstones"
    assert topic.order == 43
    assert len(production_registry.summaries()) == 43, "the curriculum is complete: 43 topics"
    summary = next(s for s in production_registry.summaries() if s.id == TOPIC_ID)
    assert summary.section_count == len(EXPECTED_SECTION_IDS)


def test_sections_are_the_nine_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_the_saga_demo_sits_inline_in_the_sagas_section() -> None:
    sections = _topic().sections
    by_id = {section.id: section for section in sections}
    demos = [b for b in by_id["sagas"].blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["arch:saga"], "the saga demo belongs to §5"
    kinds = {b.kind for b in by_id["sagas"].blocks}
    assert {"text", "code", "demo"} <= kinds


def test_the_eventstore_demo_sits_inline_in_the_event_sourcing_section() -> None:
    sections = _topic().sections
    by_id = {section.id: section for section in sections}
    demos = [b for b in by_id["event-sourcing"].blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["arch:eventstore"], "the eventstore demo belongs to §7"
    kinds = {b.kind for b in by_id["event-sourcing"].blocks}
    assert {"text", "code", "demo"} <= kinds


def test_exactly_two_demos_in_the_whole_topic() -> None:
    all_demos = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, DemoBlock)
    ]
    assert [d.id for d in all_demos] == ["arch:saga", "arch:eventstore"]


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


def test_the_architecture_story_is_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    # The patterns substrate is the PRIMARY quote target (both halves + adapter).
    assert "server/guide/domain/patterns/saga.py" in sources
    assert "server/guide/domain/patterns/event_store.py" in sources
    assert "server/guide/data/patterns/memory_event_store.py" in sources
    # The consistency map quotes the real DDL and the real relay.
    assert "server/alembic/versions/0001_guide_schema.py" in sources
    assert "server/guide/domain/messaging/outbox_service.py" in sources
    assert "server/guide/domain/messaging/ports.py" in sources
    # DDD vocabulary + CQRS quote the posts area the words map onto.
    assert "server/guide/domain/posts/entities.py" in sources
    assert "server/guide/domain/posts/ports.py" in sources
    assert "server/guide/domain/posts/use_cases.py" in sources
    # Monolith-first quotes the composition root + the deploy surface.
    assert "server/guide/main.py" in sources
    assert ".docker/docker-compose.prod.yml" in sources
    # Tracing quotes the real request-id middleware.
    assert "server/guide/core/request_context.py" in sources
    # The demo plumbing is quoted like every topic since the exemplar.
    assert "server/guide/domain/demos/arch_saga.py" in sources
    assert "server/guide/presentation/routers/demo/arch.py" in sources


def test_the_cqrs_section_stays_honest_about_scope() -> None:
    """The repo is NOT full CQRS — the section must say so in prose."""
    cqrs_text = " ".join(
        b.text
        for b in next(s for s in _topic().sections if s.id == "cqrs").blocks
        if isinstance(b, TextBlock)
    )
    assert "NOT full CQRS" in cqrs_text


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert body["version"] == 1
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"]
    assert demos == ["arch:saga", "arch:eventstore"]
