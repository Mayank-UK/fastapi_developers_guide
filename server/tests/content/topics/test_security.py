"""Topic 25 security: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (authorization is the direct sibling):
exact section order (ten sections), unique ids, the TWO demo blocks INLINE
in the sections that teach them (security:lab in §2 security-headers,
security:pii in §9 pii-and-gdpr), the terminal companion last, family word
depth, and (belt to the global ratchet) every must-source block verified
against its real file.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "security"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "the-threat-model-habit",
    "security-headers",
    "cors",
    "rate-limiting",
    "the-injection-family",
    "csrf-and-ssrf",
    "secrets",
    "owasp-api-top-ten",
    "pii-and-gdpr",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_closes_the_state_auth_group_as_twenty_fifth() -> None:
    topic = _topic()
    assert topic.group == "state-auth"
    assert topic.order == 25
    summary = next(s for s in production_registry.summaries() if s.id == TOPIC_ID)
    assert summary.section_count == len(EXPECTED_SECTION_IDS)


def test_sections_are_the_ten_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_the_two_demos_sit_inline_in_their_teaching_sections() -> None:
    sections = _topic().sections
    by_id = {section.id: section for section in sections}
    lab_demos = [b for b in by_id["security-headers"].blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in lab_demos] == ["security:lab"], "the lab belongs to §2"
    pii_demos = [b for b in by_id["pii-and-gdpr"].blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in pii_demos] == ["security:pii"], "the PII lab belongs to §9"
    # Inline means beside the teaching: text and code carry each demo too.
    for section_id in ("security-headers", "pii-and-gdpr"):
        kinds = {b.kind for b in by_id[section_id].blocks}
        assert {"text", "code", "demo"} <= kinds, section_id
    # Exactly two demos in the whole topic.
    all_demos = [b for s in sections for b in s.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in all_demos] == ["security:lab", "security:pii"]


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


def test_the_security_stack_is_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/guide/presentation/middleware/security_headers.py" in sources
    assert "server/guide/domain/security/cors.py" in sources
    assert "server/guide/main.py" in sources
    assert "server/guide/domain/security/rate_limit.py" in sources
    assert "server/guide/presentation/dependencies/rate_limit.py" in sources
    assert "server/guide/data/db/repository.py" in sources
    assert "server/guide/domain/auth/session_service.py" in sources
    assert "server/guide/core/config.py" in sources
    assert "server/guide/domain/security/pii.py" in sources
    assert "server/guide/domain/security/records.py" in sources


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [
        b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"
    ]
    assert demos == ["security:lab", "security:pii"]
