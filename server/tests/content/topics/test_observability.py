"""Topic 33 observability: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (dependency-management is the direct
sibling in this group): exact section order (ten sections), unique ids,
BOTH demos INLINE in the sections that teach them (obs:viewer in §2
structlog-json, obs:trace in §7 otel-tracing), the terminal companion
last, family word depth, and (belt to the global ratchet) every
must-source block verified against its real file.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "observability"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "three-questions",
    "structlog-json",
    "request-logging-middleware",
    "levels",
    "health-liveness-readiness",
    "prometheus-metrics",
    "otel-tracing",
    "alerting",
    "process-nets",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_joins_the_platform_group_as_thirty_third() -> None:
    topic = _topic()
    assert topic.group == "platform"
    assert topic.order == 33
    summary = next(s for s in production_registry.summaries() if s.id == TOPIC_ID)
    assert summary.section_count == len(EXPECTED_SECTION_IDS)
    assert any(group.id == "platform" for group in production_registry.groups())


def test_sections_are_the_ten_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_the_viewer_demo_sits_inline_in_the_structlog_json_section() -> None:
    sections = _topic().sections
    by_id = {section.id: section for section in sections}
    demos = [b for b in by_id["structlog-json"].blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["obs:viewer"], "the viewer belongs to §2"
    kinds = {b.kind for b in by_id["structlog-json"].blocks}
    assert {"text", "code", "demo"} <= kinds


def test_the_trace_demo_sits_inline_in_the_otel_tracing_section() -> None:
    sections = _topic().sections
    by_id = {section.id: section for section in sections}
    demos = [b for b in by_id["otel-tracing"].blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["obs:trace"], "the trace belongs to §7"
    kinds = {b.kind for b in by_id["otel-tracing"].blocks}
    assert {"text", "code", "demo"} <= kinds
    # Exactly two demos in the whole topic, each inline in its teaching section.
    all_demos = [b for s in sections for b in s.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in all_demos] == ["obs:viewer", "obs:trace"]


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


def test_the_observability_story_is_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/guide/core/logging.py" in sources
    assert "server/guide/core/request_context.py" in sources
    assert "server/guide/core/errors.py" in sources
    assert "server/guide/core/config.py" in sources
    assert "server/guide/presentation/routers/health.py" in sources
    assert ".docker/docker-compose.prod.yml" in sources
    assert "server/guide/data/redis/playground.py" in sources
    assert "server/guide/data/jobs/arq_jobs.py" in sources
    assert "server/guide/domain/demos/obs_viewer.py" in sources
    assert "server/guide/domain/demos/obs_trace.py" in sources
    assert "server/guide/presentation/routers/demo/obs.py" in sources
    assert "server/guide/presentation/middleware/request_log.py" in sources
    assert "server/guide/presentation/dependencies/request_span.py" in sources
    assert "server/tests/demo/test_obs_trace_endpoint.py" in sources
    assert "server/uv.lock" in sources


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"]
    assert demos == ["obs:viewer", "obs:trace"]
