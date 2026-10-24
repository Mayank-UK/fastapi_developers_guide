"""Topic 04 fastapi-fundamentals: registered shape + the sourcing belt.

Mirrors the exemplar topic tests (python-language, python-runtime,
http-web): exact section order, unique ids, the demo block INLINE in the
section that teaches it, the terminal companion last, family word depth,
and (belt to the global ratchet) every must-source block verified
against its real file.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "fastapi-fundamentals"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "setup",
    "the-app",
    "anatomy-of-a-router",
    "asgi-pipeline",
    "life-of-a-request",
    "error-handling-first-steps",
    "starlette-underneath",
    "what-it-leaves-out",
    "static-and-docs-mounts",
    "dev-workflow",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_is_registered_in_framework_group() -> None:
    topic = _topic()
    assert topic.group == "framework"
    assert topic.order == 4
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


def test_sections_are_the_eleven_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_app_info_demo_sits_inline_in_the_docs_mounts_section() -> None:
    section = next(s for s in _topic().sections if s.id == "static-and-docs-mounts")
    demos = [b for b in section.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["fastapi:app-info"]
    # Inline means beside the teaching: the section still carries text + code.
    kinds = {b.kind for b in section.blocks}
    assert kinds == {"text", "code", "demo"}


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


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
