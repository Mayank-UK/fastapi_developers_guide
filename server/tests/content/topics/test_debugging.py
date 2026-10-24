"""Topic 35 debugging: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (observability is the direct sibling in
this group): exact section order (eight sections), unique ids, the ONE
demo INLINE in the section that teaches it (debug:stall in §4 py-spy),
the terminal companion last, family word depth, and (belt to the global
ratchet) every must-source block verified against its real file. The
honesty rules are pinned too: py-spy and pyinstrument are NOT
dependencies, so their sections carry sourcing-exempt bash recipes only —
no fabricated integrations to quote.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "debugging"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "mindset",
    "print-limits",
    "pdb-debugger",
    "py-spy",
    "tracemalloc-heap",
    "pyinstrument-profiling",
    "production",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_joins_the_platform_group_as_thirty_fifth() -> None:
    topic = _topic()
    assert topic.group == "platform"
    assert topic.order == 35
    summary = next(s for s in production_registry.summaries() if s.id == TOPIC_ID)
    assert summary.section_count == len(EXPECTED_SECTION_IDS)
    assert any(group.id == "platform" for group in production_registry.groups())


def test_sections_are_the_eight_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_the_stall_demo_sits_inline_in_the_py_spy_section() -> None:
    sections = _topic().sections
    by_id = {section.id: section for section in sections}
    demos = [b for b in by_id["py-spy"].blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["debug:stall"], "the stall demo belongs to §4"
    kinds = {b.kind for b in by_id["py-spy"].blocks}
    assert {"text", "code", "demo"} <= kinds
    # Exactly one demo in the whole topic, inline in its teaching section.
    all_demos = [b for s in sections for b in s.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in all_demos] == ["debug:stall"]


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


def test_the_debugging_story_is_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/guide/core/errors.py" in sources
    assert "server/guide/core/logging.py" in sources
    assert "server/guide/presentation/middleware/request_log.py" in sources
    assert "server/guide/domain/demos/debug_stall.py" in sources
    assert "server/guide/presentation/routers/demo/debug.py" in sources
    assert "server/tests/demo/test_debug_stall_endpoint.py" in sources
    assert "server/guide/data/jobs/arq_jobs.py" in sources


def test_the_not_installed_tools_are_taught_by_recipe_only() -> None:
    """py-spy + pyinstrument are NOT dependencies: concept prose + bash recipes,
    never a fabricated py integration to quote."""
    py_blocks = [
        b
        for section in _topic().sections
        for b in section.blocks
        if isinstance(b, CodeBlock) and b.language == "py"
    ]
    for block in py_blocks:
        assert block.source, f"py block {block.id!r} must quote a real file"
        assert "py_spy" not in block.source and "pyinstrument" not in block.source
    # The recipes themselves are bash blocks, honestly labeled.
    recipes = [
        b.id
        for b in _topic().sections[3].blocks
        if isinstance(b, CodeBlock) and b.language == "bash"
    ]
    assert "dbg-pyspy-recipe" in recipes
    assert "NOT installed" in next(
        b.snippet for b in _topic().sections[5].blocks
        if isinstance(b, CodeBlock) and b.language == "bash"
    )


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"]
    assert demos == ["debug:stall"]
