"""Topic 23 authentication: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (messaging is the direct sibling): exact
section order (ten sections), unique ids, the SIX demo blocks INLINE in
the sections that teach them (auth:sessions in §2 login-flow-and-cookies,
auth:api-keys in §3 api-keys, auth:jwt in §5 jwt, auth:oauth in §6
oauth2-flows, auth:hashing in §8 password-hashing, auth:refresh in §9
refresh-rotation), the terminal companion last, family word depth, and
(belt to the global ratchet) every must-source block verified against its
real file.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "authentication"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "what-authentication-is",
    "login-flow-and-cookies",
    "api-keys",
    "sessions-vs-keys-vs-tokens",
    "jwt",
    "oauth2-flows",
    "deciding",
    "password-hashing",
    "refresh-rotation",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_joins_the_state_auth_group_as_twenty_third() -> None:
    topic = _topic()
    assert topic.group == "state-auth"
    assert topic.order == 23
    summary = next(s for s in production_registry.summaries() if s.id == TOPIC_ID)
    assert summary.section_count == len(EXPECTED_SECTION_IDS)


def test_sections_are_the_ten_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_the_demos_sit_inline_in_their_teaching_sections() -> None:
    sections = _topic().sections
    by_id = {section.id: section for section in sections}
    placements = {
        "auth:sessions": "login-flow-and-cookies",
        "auth:api-keys": "api-keys",
        "auth:jwt": "jwt",
        "auth:oauth": "oauth2-flows",
        "auth:hashing": "password-hashing",
        "auth:refresh": "refresh-rotation",
    }
    for demo_id, section_id in placements.items():
        demos = [b.id for b in by_id[section_id].blocks if isinstance(b, DemoBlock)]
        assert demos == [demo_id], (section_id, demos)
    # Inline means beside the teaching: text and code carry each demo too.
    for section_id in placements.values():
        kinds = {b.kind for b in by_id[section_id].blocks}
        assert {"text", "code", "demo"} <= kinds, section_id
    # Exactly six demos in the whole topic, in curriculum order.
    all_demos = [b for s in sections for b in s.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in all_demos] == list(placements)


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


def test_the_auth_stack_is_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/guide/domain/auth/ports.py" in sources
    assert "server/guide/domain/auth/session_service.py" in sources
    assert "server/guide/domain/auth/api_key_service.py" in sources
    assert "server/guide/domain/auth/jwt_service.py" in sources
    assert "server/guide/domain/auth/oauth_service.py" in sources
    assert "server/guide/domain/auth/password_service.py" in sources
    assert "server/guide/domain/auth/refresh_service.py" in sources
    assert "server/guide/presentation/routers/demo/auth.py" in sources


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [
        b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"
    ]
    assert demos == [
        "auth:sessions",
        "auth:api-keys",
        "auth:jwt",
        "auth:oauth",
        "auth:hashing",
        "auth:refresh",
    ]
