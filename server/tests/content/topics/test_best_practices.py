"""Topic 41 best-practices: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (environments is the direct sibling):
exact section order (twelve sections), unique ids, the demo block INLINE
in the section that teaches it (best:checklist in §11 the anti-checklist),
the terminal companion last, family word depth, and (belt to the global
ratchet) every must-source block verified against its real file.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "best-practices"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "setup",
    "api-discipline",
    "security",
    "data",
    "reliability",
    "observability",
    "performance",
    "operations",
    "git-and-review",
    "human-practices",
    "anti-checklist",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_opens_the_capstones_group_as_forty_first() -> None:
    topic = _topic()
    assert topic.group == "capstones"
    assert topic.order == 41
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


def test_sections_are_the_twelve_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_the_demo_sits_inline_in_the_anti_checklist_section() -> None:
    sections = _topic().sections
    by_id = {section.id: section for section in sections}
    demos = [b for b in by_id["anti-checklist"].blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["best:checklist"], "the self-audit belongs to §11"
    # Inline means beside the teaching: text and code carry the demo too.
    kinds = {b.kind for b in by_id["anti-checklist"].blocks}
    assert {"text", "code", "demo"} <= kinds
    # Exactly one demo in the whole topic.
    all_demos = [b for s in sections for b in s.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in all_demos] == ["best:checklist"]


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


def test_the_practices_story_is_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/pyproject.toml" in sources
    assert "server/guide/presentation/routers/posts.py" in sources
    assert "server/guide/presentation/middleware/security_headers.py" in sources
    assert "server/guide/domain/auth/password_service.py" in sources
    assert "server/alembic/versions/0001_guide_schema.py" in sources
    assert "server/guide/data/db/repository.py" in sources
    assert "server/guide/data/mongo/client.py" in sources
    assert "server/guide/data/db/lifecycle.py" in sources
    assert "server/guide/core/logging.py" in sources
    assert "server/guide/core/request_context.py" in sources
    assert "server/guide/data/db/engine.py" in sources
    assert "server/guide/domain/demos/testing_runner.py" in sources
    assert ".docker/docker-compose.yml" in sources
    assert "server/tests/test_snippet_ratchet.py" in sources
    assert "server/guide/presentation/routers/demo/best.py" in sources


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"]
    assert demos == ["best:checklist"]
