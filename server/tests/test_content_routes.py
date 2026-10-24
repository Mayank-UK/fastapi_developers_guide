"""GET /api/content and /api/content/{topic_id}: exact wire contract."""

from content_builders import a_code_block, a_demo_block, a_group, a_section, a_text_block, a_topic
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guide.content.registry import ContentRegistry

CONTENT_PATH = "/api/content"


def build_fixture_app(app: FastAPI) -> None:
    """Give the factory app a two-topic fixture registry, authored unordered."""
    app.state.content_registry = ContentRegistry(
        groups=[a_group(id="framework", order=2), a_group(id="foundations", order=1)],
        topics=[
            a_topic(
                id="second-topic",
                order=2,
                group="framework",
                sections=[
                    a_section(id="only", blocks=[a_text_block(), a_code_block(id="c2")]),
                    a_section(
                        id="terminal",
                        blocks=[
                            a_text_block(id="t2"),
                            a_code_block(
                                id="bash",
                                language="bash",
                                source=None,
                                snippet="curl localhost:8000/api/content",
                            ),
                        ],
                    ),
                ],
            ),
            a_topic(id="first-topic", order=1, group="foundations"),
        ],
    )


def test_production_list_serves_the_registered_curriculum(client: TestClient) -> None:
    """The production registry (not a fixture) is what the live app serves."""
    response = client.get(CONTENT_PATH)
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    assert [group["id"] for group in body["groups"]] == [
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
    assert [topic["id"] for topic in body["topics"]] == [
        "python-language",
        "python-runtime",
        "http-web",
        "fastapi-fundamentals",
        "pydantic",
        "fastapi-dependencies",
        "routing",
        "middleware",
        "request-response",
        "validation",
        "api-design",
        "api-documentation",
        "graphql",
        "webhooks",
        "grpc",
        "sql-schema",
        "databases-sql",
        "sqlalchemy-orm",
        "mongodb",
        "redis",
        "caching",
        "messaging",
        "authentication",
        "authorization",
        "security",
        "files-media",
        "internationalization",
        "realtime",
        "background-jobs",
        "exception-handling",
        "dependency-management",
        "architecture",
        "observability",
        "testing",
        "debugging",
        "environments",
        "deployment",
        "performance",
        "reliability",
        "scaling",
        "best-practices",
        "third-party",
        "advanced-architecture",
    ]
    assert body["topics"][0]["sectionCount"] == 11
    assert body["topics"][1]["sectionCount"] == 9
    assert body["topics"][2]["sectionCount"] == 9
    assert body["topics"][3]["sectionCount"] == 11
    assert body["topics"][4]["sectionCount"] == 10
    assert body["topics"][5]["sectionCount"] == 9
    assert body["topics"][6]["sectionCount"] == 8
    assert body["topics"][7]["sectionCount"] == 8
    assert body["topics"][8]["sectionCount"] == 8
    assert body["topics"][9]["sectionCount"] == 8
    assert body["topics"][10]["sectionCount"] == 8
    assert body["topics"][11]["sectionCount"] == 7
    assert body["topics"][12]["sectionCount"] == 7
    assert body["topics"][13]["sectionCount"] == 7
    assert body["topics"][14]["sectionCount"] == 8
    assert body["topics"][15]["sectionCount"] == 9
    assert body["topics"][16]["sectionCount"] == 10
    assert body["topics"][17]["sectionCount"] == 10
    assert body["topics"][18]["sectionCount"] == 10
    assert body["topics"][19]["sectionCount"] == 7
    assert body["topics"][20]["sectionCount"] == 8
    assert body["topics"][21]["sectionCount"] == 8
    assert body["topics"][22]["sectionCount"] == 10
    assert body["topics"][23]["sectionCount"] == 8
    assert body["topics"][24]["sectionCount"] == 10
    assert body["topics"][25]["sectionCount"] == 8
    assert body["topics"][26]["sectionCount"] == 7
    assert body["topics"][27]["sectionCount"] == 7
    assert body["topics"][28]["sectionCount"] == 9
    assert body["topics"][29]["sectionCount"] == 9
    assert body["topics"][30]["sectionCount"] == 7
    assert body["topics"][31]["sectionCount"] == 9
    assert body["topics"][32]["sectionCount"] == 10
    assert body["topics"][33]["sectionCount"] == 10
    assert body["topics"][34]["sectionCount"] == 8
    assert body["topics"][35]["sectionCount"] == 7
    assert body["topics"][36]["sectionCount"] == 12
    assert body["topics"][37]["sectionCount"] == 8
    assert body["topics"][38]["sectionCount"] == 9
    assert body["topics"][39]["sectionCount"] == 9
    assert body["topics"][40]["sectionCount"] == 12
    assert body["topics"][41]["sectionCount"] == 7
    assert body["topics"][42]["sectionCount"] == 9


def test_fixture_list_is_sorted_by_order_with_section_count(
    app: FastAPI, client: TestClient
) -> None:
    build_fixture_app(app)
    body = client.get(CONTENT_PATH).json()

    assert body["version"] == 1
    assert [group["id"] for group in body["groups"]] == ["foundations", "framework"]
    assert [topic["id"] for topic in body["topics"]] == ["first-topic", "second-topic"]

    summary = body["topics"][1]
    assert summary == {
        "id": "second-topic",
        "title": "Topic One",
        "group": "framework",
        "order": 2,
        "sectionCount": 2,
    }


def test_fixture_detail_returns_the_full_topic(app: FastAPI, client: TestClient) -> None:
    build_fixture_app(app)
    body = client.get(f"{CONTENT_PATH}/second-topic").json()

    assert body["version"] == 1
    assert body["id"] == "second-topic"
    assert [section["id"] for section in body["sections"]] == ["only", "terminal"]
    kinds = [block["kind"] for block in body["sections"][0]["blocks"]]
    assert kinds == ["text", "code"]
    code_block = body["sections"][0]["blocks"][1]
    assert code_block["language"] == "py"
    assert code_block["source"] == "server/pyproject.toml"
    assert code_block["snippet"] == "x = 1"


def test_demo_block_serializes_in_detail(app: FastAPI, client: TestClient) -> None:
    app.state.content_registry = ContentRegistry(
        groups=[a_group()],
        topics=[
            a_topic(
                sections=[a_section(blocks=[a_text_block(), a_demo_block(id="runtime:async")])]
            )
        ],
    )
    blocks = client.get(f"{CONTENT_PATH}/topic-one").json()["sections"][0]["blocks"]
    assert blocks[1] == {
        "kind": "demo",
        "id": "runtime:async",
        "title": "Sample demo",
    }


def test_unknown_topic_id_is_404_envelope(app: FastAPI, client: TestClient) -> None:
    build_fixture_app(app)
    response = client.get(f"{CONTENT_PATH}/nope")
    assert response.status_code == 404
    body = response.json()["error"]
    assert body["code"] == "not_found"
    assert "nope" in body["message"]
    assert body["requestId"]
    assert response.headers["x-request-id"] == body["requestId"]


def test_response_models_are_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    list_ref = schema["paths"][CONTENT_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    detail_ref = schema["paths"][f"{CONTENT_PATH}/{{topic_id}}"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]["$ref"]
    assert list_ref.endswith("ContentListResponse")
    assert detail_ref.endswith("ContentDetail")
