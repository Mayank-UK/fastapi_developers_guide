"""Topic 27 internationalization: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (files-media is the direct sibling):
exact section order (seven sections), unique ids, the ONE demo block
INLINE in the section that teaches it (i18n:negotiator in §2
accept-language-negotiation), the terminal companion last, family word
depth, and (belt to the global ratchet) every must-source block verified
against its real file.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "internationalization"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "global-by-default",
    "accept-language-negotiation",
    "gettext-and-catalogs",
    "formatting-and-plurals",
    "timezones-versus-locales",
    "translation-workflow",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_joins_the_media_realtime_group_as_twenty_seventh() -> None:
    topic = _topic()
    assert topic.group == "media-realtime"
    assert topic.order == 27
    summary = next(s for s in production_registry.summaries() if s.id == TOPIC_ID)
    assert summary.section_count == len(EXPECTED_SECTION_IDS)


def test_sections_are_the_seven_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_the_one_demo_sits_inline_in_its_teaching_section() -> None:
    sections = _topic().sections
    by_id = {section.id: section for section in sections}
    demos = [b for b in by_id["accept-language-negotiation"].blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["i18n:negotiator"], "the negotiator belongs to §2"
    kinds = {b.kind for b in by_id["accept-language-negotiation"].blocks}
    assert {"text", "code", "demo"} <= kinds, "inline means text and code beside it"
    all_demos = [b for s in sections for b in s.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in all_demos] == ["i18n:negotiator"]  # exactly one demo


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


def test_the_i18n_substrate_is_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/guide/domain/i18n/negotiation.py" in sources
    assert "server/guide/presentation/routers/demo/i18n.py" in sources
    assert "server/guide/domain/i18n/catalog.py" in sources
    assert "server/guide/domain/i18n/formatting.py" in sources
    assert "server/guide/domain/i18n/timezones.py" in sources
    assert (
        "server/guide/domain/i18n/locales/pl/LC_MESSAGES/messages.po" in sources
    ), "the topic quotes the repo's real Polish catalog"
    assert (
        "server/guide/domain/i18n/locales/de/LC_MESSAGES/messages.po" in sources
    ), "the topic quotes the repo's real German catalog"


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [
        b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"
    ]
    assert demos == ["i18n:negotiator"]
