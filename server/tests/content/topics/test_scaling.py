"""Topic 40 scaling: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (reliability is the direct sibling):
exact section order (nine sections), unique ids, the ONE demo INLINE in
the section that teaches it (scaling:stateless in §2 statelessness), the
terminal companion last, family word depth, and (belt to the global
ratchet) every must-source block verified against its real file. The
honesty rule specific to this topic is also pinned: the state-placement
inventory's rows name the REAL holders wired on app.state (main.py) and
the externalized/client-side stores the earlier topics built — no
fabricated infrastructure.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "scaling"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "what-scaling-means",
    "statelessness",
    "load-balancing",
    "replicas",
    "data-at-scale",
    "cdn-edge",
    "backpressure",
    "capacity",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_is_the_fourth_ship_topic_as_fortieth() -> None:
    topic = _topic()
    assert topic.group == "ship"
    assert topic.order == 40
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


def test_sections_are_the_nine_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_the_stateless_demo_sits_inline_in_the_statelessness_section() -> None:
    sections = _topic().sections
    by_id = {section.id: section for section in sections}
    demos = [b for b in by_id["statelessness"].blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["scaling:stateless"], "the demo belongs to §2"
    kinds = {b.kind for b in by_id["statelessness"].blocks}
    assert {"text", "code", "demo"} <= kinds
    # Exactly one demo in the whole topic, inline in its teaching section.
    all_demos = [b for s in sections for b in s.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in all_demos] == ["scaling:stateless"]


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


def test_the_scaling_story_is_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/guide/main.py" in sources
    assert "server/guide/core/scenario.py" in sources
    assert "server/guide/domain/demos/scaling_stateless.py" in sources
    assert "server/guide/presentation/routers/demo/scaling.py" in sources
    assert ".docker/docker-compose-platform.yml" in sources
    assert ".docker/docker-compose.yml" in sources
    assert ".docker/docker-compose.prod.yml" in sources
    assert "server/alembic/versions/0001_guide_schema.py" in sources
    assert "server/guide/data/db/engine.py" in sources
    assert ".docker/client/nginx.conf" in sources
    assert "server/guide/domain/realtime/manager.py" in sources
    assert "server/guide/domain/security/rate_limit.py" in sources
    assert "server/guide/data/jobs/arq_jobs.py" in sources


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"]
    assert demos == ["scaling:stateless"]
