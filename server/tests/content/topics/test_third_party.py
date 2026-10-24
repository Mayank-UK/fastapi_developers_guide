"""Topic 42 third-party: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (scaling is the direct sibling): exact
section order (seven sections), unique ids, the ONE demo INLINE in the
section that teaches it (thirdparty:hub in §1 integrating-vs-building),
the terminal companion last, family word depth, and (belt to the global
ratchet) every must-source block verified against its real file. The
honesty rules specific to this topic are also pinned: aiosmtplib,
Stripe, and cloud-storage SDKs are NOT dependencies — their sections
carry concept prose + sourcing-exempt bash recipes only, never a
fabricated live integration to quote.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "third-party"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "integrating-vs-building",
    "email-via-aiosmtplib",
    "email-as-a-job-recap",
    "stripe",
    "cloud-storage",
    "keys-quotas-blast-radius",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_is_the_second_capstone_as_forty_second() -> None:
    topic = _topic()
    assert topic.group == "capstones"
    assert topic.order == 42
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


def test_sections_are_the_seven_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_the_hub_demo_sits_inline_in_the_integrating_section() -> None:
    sections = _topic().sections
    by_id = {section.id: section for section in sections}
    demos = [b for b in by_id["integrating-vs-building"].blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["thirdparty:hub"], "the demo belongs to §1"
    kinds = {b.kind for b in by_id["integrating-vs-building"].blocks}
    assert {"text", "code", "demo"} <= kinds
    # Exactly one demo in the whole topic, inline in its teaching section.
    all_demos = [b for s in sections for b in s.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in all_demos] == ["thirdparty:hub"]


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


def test_the_third_party_story_is_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/pyproject.toml" in sources
    assert "server/guide/domain/webhooks/signing.py" in sources
    assert "server/guide/data/mongo/client.py" in sources
    assert "server/guide/worker.py" in sources
    assert "server/guide/presentation/routers/demo/jobs.py" in sources
    assert "server/guide/domain/messaging/idempotence.py" in sources
    assert "server/guide/domain/files/storage.py" in sources
    assert "server/guide/main.py" in sources
    assert "server/guide/core/config.py" in sources
    assert ".docker/docker-compose.prod.yml" in sources
    assert "server/guide/domain/security/rate_limit.py" in sources
    assert "server/guide/domain/demos/thirdparty_hub.py" in sources
    assert "server/guide/presentation/routers/demo/thirdparty.py" in sources


def test_the_not_installed_vendors_are_taught_by_recipe_only() -> None:
    """aiosmtplib, Stripe, and cloud-storage SDKs are NOT dependencies: concept
    prose + bash recipes, never a fabricated py integration to quote."""
    py_blocks = [
        b
        for section in _topic().sections
        for b in section.blocks
        if isinstance(b, CodeBlock) and b.language == "py"
    ]
    for block in py_blocks:
        assert block.source, f"py block {block.id!r} must quote a real file"
        assert not any(
            token in (block.source or "") for token in ("aiosmtplib", "stripe", "boto")
        ), f"py block {block.id!r} sources a vendor SDK this repo does not install"
    # The recipes themselves are bash blocks, honestly labeled as NOT installed.
    recipe_blocks = {
        b.id: b.snippet
        for section in _topic().sections
        for b in section.blocks
        if isinstance(b, CodeBlock) and b.language == "bash" and b.id.startswith("tp-")
    }
    assert "NOT installed" in recipe_blocks["tp-em-recipe"]
    assert "NOT installed" in recipe_blocks["tp-st-recipe"]
    assert "NOT installed" in recipe_blocks["tp-cs-recipe"]
    # And the honesty is stated in prose too, not only in the recipes.
    email_honesty = " ".join(
        b.text for b in _topic().sections[1].blocks if isinstance(b, TextBlock)
    )
    assert "NOT a dependency" in email_honesty
    stripe_honesty = " ".join(
        b.text for b in _topic().sections[3].blocks if isinstance(b, TextBlock)
    )
    assert "NOT installed" in stripe_honesty


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"]
    assert demos == ["thirdparty:hub"]
