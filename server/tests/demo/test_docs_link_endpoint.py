"""The /api/demo/api/docs-link endpoint: the running app's docs, served live.

Pinned against the per-test app: the payload's facts come from the SAME
schema /openapi.json serves (counts match it exactly), the docs links are
the app's real mounts, the posts resource's generated operations carry
their generated operationIds and documented responses, the showcase slice
is POST /api/posts exactly as generated (docstring → description,
status_code → the 201 response, response_model → the $ref names), and the
endpoint itself is documented in the schema it introspects.
"""

from fastapi.testclient import TestClient

DOCS_LINK = "/api/demo/api/docs-link"


def test_serves_the_real_docs_locations_and_info(client: TestClient) -> None:
    body = client.get(DOCS_LINK).json()
    assert body["docs"] == {"swaggerUi": "/docs", "redoc": "/redoc", "openapiJson": "/openapi.json"}
    assert body["infoTitle"] == "FastAPI Developers Guide"
    assert body["infoVersion"]
    assert body["openapiVersion"].startswith("3.")


def test_counts_match_the_live_openapi_document(client: TestClient) -> None:
    body = client.get(DOCS_LINK).json()
    schema = client.get("/openapi.json").json()
    assert body["pathCount"] == len(schema["paths"])
    assert body["schemaCount"] == len(schema["components"]["schemas"])
    assert body["operationCount"] == sum(
        1
        for item in schema["paths"].values()
        for key in item
        if key in {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
    )
    assert body["areaCount"] == len(body["areas"])
    assert body["pathCount"] > 0 and body["operationCount"] > 0


def test_posts_area_and_operations_come_from_the_generated_schema(client: TestClient) -> None:
    body = client.get(DOCS_LINK).json()
    posts_area = next(area for area in body["areas"] if area["tag"] == "posts")
    assert posts_area["methods"] == ["GET", "POST", "PUT"]
    assert posts_area["operations"] == 4
    assert [(op["method"], op["path"]) for op in body["postsOperations"]] == [
        ("GET", "/api/posts"),
        ("POST", "/api/posts"),
        ("GET", "/api/posts/{post_id}"),
        ("PUT", "/api/posts/{post_id}"),
    ]
    create = body["postsOperations"][1]
    assert create["operationId"] == "create_post_api_posts_post"
    assert create["responses"] == ["201", "422"]
    # Documented errors are part of the contract: every posts op carries 422.
    assert all("422" in op["responses"] for op in body["postsOperations"])


def test_showcase_slices_the_generated_create_operation(client: TestClient) -> None:
    body = client.get(DOCS_LINK).json()
    showcase = body["showcase"]
    assert showcase["method"] == "POST"
    assert showcase["path"] == "/api/posts"
    # The handler's docstring became the description; the summary is derived.
    assert (
        showcase["description"]
        == "Create from the validated body: 201 + Location names the resource."
    )
    assert showcase["requestSchema"] == "PostCreate"
    assert showcase["successStatus"] == "201"
    assert showcase["successSchema"] == "Post"
    assert showcase["validationSchema"] == "HTTPValidationError"


def test_schema_names_name_the_posts_contract_models(client: TestClient) -> None:
    body = client.get(DOCS_LINK).json()
    for name in ("Post", "PostCreate", "PostPage"):
        assert name in body["schemaNames"]
    assert body["schemaNames"] == sorted(body["schemaNames"])


def test_reasoning_names_the_contract_and_both_renderers(client: TestClient) -> None:
    reasoning = client.get(DOCS_LINK).json()["reasoning"]
    assert "/openapi.json" in reasoning
    assert "/docs" in reasoning
    assert "/redoc" in reasoning
    assert "was written by hand" in reasoning


def test_the_endpoint_is_itself_documented_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    docs_link = schema["paths"][DOCS_LINK]
    assert docs_link["get"]["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("DocsLinkPayload")
    assert client.get(DOCS_LINK).status_code == 200
