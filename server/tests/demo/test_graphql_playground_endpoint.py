"""The /api/demo/api/graphql-playground endpoint: the live schema, packaged.

Pinned against the per-test app: the payload's SDL is EXACTLY the running
schema's (schema.as_str(), byte for byte — the drift net), the endpoint
names the real mount, and the five curated examples are the tour — a
page, the batched author projection, a real mutation, introspection, and
the deliberate not-found error — each carrying the operation text the
terminal companion sends.
"""

from fastapi.testclient import TestClient

from guide.presentation.routers.graphql import schema as graphql_schema

PLAYGROUND = "/api/demo/api/graphql-playground"


def test_serves_the_endpoint_and_the_live_sdl(client: TestClient) -> None:
    body = client.get(PLAYGROUND).json()
    assert body["endpoint"] == "/api/graphql"
    # The drift net: the served SDL IS the running schema's, byte for byte.
    assert body["sdl"] == graphql_schema.as_str()
    assert "type Query" in body["sdl"]
    assert "createPost(input: CreatePostInput!)" in body["sdl"]


def test_examples_are_the_five_stop_tour_in_order(client: TestClient) -> None:
    body = client.get(PLAYGROUND).json()
    examples = body["examples"]
    assert [example["id"] for example in examples] == [
        "page",
        "authors",
        "mutation",
        "introspection",
        "error",
    ]
    for example in examples:
        assert example["label"]
        assert example["description"]
        assert "query" in example["query"] or "mutation" in example["query"]


def test_example_queries_run_cleanly_against_the_live_endpoint(client: TestClient) -> None:
    """Every curated example is a real operation — the tour cannot lie."""
    body = client.get(PLAYGROUND).json()
    for example in body["examples"]:
        response = client.post(
            "/api/graphql", json={"query": example["query"]}
        )
        assert response.status_code == 200
        result = response.json()
        # The error example is the deliberate not_found; the rest succeed.
        if example["id"] == "error":
            assert result["errors"][0]["extensions"]["code"] == "not_found"
        else:
            assert result.get("errors") is None
            assert result["data"] is not None


def test_reasoning_names_the_endpoint_and_the_live_sdl(client: TestClient) -> None:
    body = client.get(PLAYGROUND).json()
    assert "/api/graphql" in body["reasoning"]
    assert "schema.as_str()" in body["reasoning"]
    assert "genuinely stores" in body["reasoning"]


def test_the_endpoint_is_itself_documented_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    playground = schema["paths"][PLAYGROUND]
    assert (
        playground["get"]["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("GraphqlPlaygroundPayload")
    )
    assert client.get(PLAYGROUND).status_code == 200
