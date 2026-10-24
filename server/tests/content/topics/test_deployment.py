"""Topic 37 deployment: registered shape + the sourcing belt.

Mirrors the per-topic topic tests (debugging is the direct sibling in
this family): exact section order (twelve sections), unique ids, the ONE
demo INLINE in the section that teaches it (deploy:stack in §3 compose),
the terminal companion last, family word depth, and (belt to the global
ratchet) every must-source block verified against its real file. The
honesty rules are pinned too: Kubernetes ships NO manifests in this repo
(deploy/k8s/ does not exist), so its section carries prose + a
sourcing-exempt bash recipe only — no fabricated yaml; gunicorn,
kubectl, and terraform likewise appear only as clearly-marked recipes.
"""

from typing import Final

from fastapi.testclient import TestClient
from test_snippet_ratchet import violations

from guide.content.models import CodeBlock, DemoBlock, TextBlock, Topic
from guide.content.registry import production_registry

TOPIC_ID: Final = "deployment"

EXPECTED_SECTION_IDS: Final[tuple[str, ...]] = (
    "ship-vs-run",
    "docker-multi-stage",
    "compose-trio",
    "reverse-proxy-tls",
    "workers-graceful-shutdown",
    "ci-cd",
    "parity-secrets",
    "kubernetes",
    "rollouts",
    "iac",
    "linux-survival",
    "terminal-companion",
)

MIN_PROSE_WORDS: Final = 2500
"""Family depth mandate: ~3k words per topic; the floor catches thin topics."""


def _topic() -> Topic:
    topic = production_registry.topic_by_id(TOPIC_ID)
    assert topic is not None
    return topic


def test_topic_opens_the_ship_group_as_thirty_seventh() -> None:
    topic = _topic()
    assert topic.group == "ship"
    assert topic.order == 37
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
    ship = next(group for group in production_registry.groups() if group.id == "ship")
    assert ship.order == 9, "the client's planned map reads ship between platform and capstones"
    summary = next(s for s in production_registry.summaries() if s.id == TOPIC_ID)
    assert summary.section_count == len(EXPECTED_SECTION_IDS)


def test_sections_are_the_twelve_in_order() -> None:
    assert tuple(section.id for section in _topic().sections) == EXPECTED_SECTION_IDS


def test_block_ids_are_unique_across_the_topic() -> None:
    ids = [block.id for section in _topic().sections for block in section.blocks]
    assert len(ids) == len(set(ids))


def test_the_stack_demo_sits_inline_in_the_compose_section() -> None:
    sections = _topic().sections
    by_id = {section.id: section for section in sections}
    demos = [b for b in by_id["compose-trio"].blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in demos] == ["deploy:stack"], "the stack demo belongs to §3"
    kinds = {b.kind for b in by_id["compose-trio"].blocks}
    assert {"text", "code", "demo"} <= kinds
    # Exactly one demo in the whole topic, inline in its teaching section.
    all_demos = [b for s in sections for b in s.blocks if isinstance(b, DemoBlock)]
    assert [d.id for d in all_demos] == ["deploy:stack"]


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


def test_the_deployment_story_is_quoted_from_real_files() -> None:
    code_blocks = [
        b for section in _topic().sections for b in section.blocks if isinstance(b, CodeBlock)
    ]
    sources = {b.source for b in code_blocks if b.source}
    assert "server/guide/presentation/routers/health.py" in sources
    assert ".docker/server/Dockerfile.prod" in sources
    assert ".docker/server/Dockerfile" in sources
    assert ".docker/docker-compose-platform.yml" in sources
    assert ".docker/docker-compose.prod.yml" in sources
    assert ".docker/client/nginx.conf" in sources
    assert "server/guide/main.py" in sources
    assert ".github/workflows/ci.yml" in sources
    assert ".github/workflows/deploy-production.yml" in sources
    assert "server/.env.production.example" in sources
    assert "server/guide/core/config.py" in sources
    assert "server/guide/presentation/routers/demo/deploy.py" in sources
    assert "server/tests/demo/test_deploy_stack_endpoint.py" in sources


def test_the_kubernetes_section_teaches_honestly_no_fabricated_manifests() -> None:
    """deploy/k8s/ does not exist in this repo: prose + bash recipe only,
    never an invented yaml manifest (a yaml block would need a real source)."""
    k8s = next(s for s in _topic().sections if s.id == "kubernetes")
    for block in k8s.blocks:
        if isinstance(block, CodeBlock):
            assert block.language == "bash" and block.source is None, block.id
            assert "NOT deployed here" in block.snippet
    # And the pipeline's tools-not-run appear only as marked recipes.
    recipe_blocks = [
        b
        for s in _topic().sections
        for b in s.blocks
        if isinstance(b, CodeBlock) and b.language == "bash" and b.source is None
    ]
    snippets = "\n".join(b.snippet for b in recipe_blocks)
    assert snippets.count("honest recipe") >= 3, "gunicorn, kubectl, terraform marked honestly"


def test_every_must_source_block_passes_the_ratchet_belt() -> None:
    assert violations(production_registry) == []


def test_detail_route_serves_the_topic(client: TestClient) -> None:
    body = client.get(f"/api/content/{TOPIC_ID}").json()
    assert body["id"] == TOPIC_ID
    assert [s["id"] for s in body["sections"]] == list(EXPECTED_SECTION_IDS)
    demos = [b["id"] for s in body["sections"] for b in s["blocks"] if b["kind"] == "demo"]
    assert demos == ["deploy:stack"]
