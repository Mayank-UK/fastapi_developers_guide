"""The GraphQL API at /api/graphql: real queries through the posts substrate.

Pinned against the per-test app: the collection query answers a typed
page off the SAME use cases the REST router serves, the nested author
projection resolves through the dataloader in ONE batched round (a spy
asserts it — a loader that resolves one-by-one is the bug section 5
teaches against), the mutation genuinely stores (proven cross-protocol
through GET /api/posts), errors ride 200 responses with the family codes
in extensions, arguments beyond the model's bounds fail validation at
the edge, introspection answers, GraphiQL serves on GET, and the mount
stays out of the OpenAPI document by construction.
"""

from typing import Any

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from guide.presentation.routers.graphql import AuthorLoader

GRAPHQL = "/api/graphql"

NESTED_AUTHORS_QUERY = (
    "{ posts(limit: 6) { items { title author { id postCount } } } }"
)


def run_query(client: TestClient, query: str) -> dict[str, Any]:
    """POST one operation; GraphQL answers 200 even when it carries errors."""
    response = client.post(GRAPHQL, json={"query": query})
    assert response.status_code == 200
    return response.json()


def test_posts_query_serves_a_typed_page(client: TestClient) -> None:
    body = run_query(
        client,
        "{ posts(limit: 3, sort: OLDEST) { total pages page limit "
        "items { id title status authorName createdAt } } }",
    )
    assert body.get("errors") is None
    page = body["data"]["posts"]
    assert page["total"] == 12
    assert page["pages"] == 4
    assert page["page"] == 1
    assert page["limit"] == 3
    # OLDEST orders by created_at: the first seed post leads.
    assert page["items"][0]["id"] == "designing-urls-people-can-read"
    assert page["items"][0]["authorName"] == "grace"
    assert page["items"][0]["createdAt"].startswith("2026-09-01")
    assert page["items"][0]["status"] == "PUBLISHED"


def test_posts_filter_and_sort_mirror_the_rest_surface(client: TestClient) -> None:
    body = run_query(
        client,
        '{ posts(limit: 100, sort: TITLE, filter: { author: "grace" }) '
        "{ items { title } total } }",
    )
    page = body["data"]["posts"]
    titles = [item["title"] for item in page["items"]]
    assert page["total"] == 4
    assert titles == sorted(titles)


def test_nested_authors_resolve_in_one_batched_loader_round(
    client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    batches: list[list[str]] = []
    original = AuthorLoader._load_authors

    async def spy(self: AuthorLoader, names: list[str]) -> list[Any]:
        batches.append(list(names))
        return await original(self, names)

    monkeypatch.setattr(AuthorLoader, "_load_authors", spy)

    body = run_query(client, NESTED_AUTHORS_QUERY)

    items = body["data"]["posts"]["items"]
    assert len(items) == 6
    # Live author facts: the seed gives each byline exactly four posts.
    assert {item["author"]["id"] for item in items} == {"grace", "alan", "barbara"}
    assert all(item["author"]["postCount"] == 4 for item in items)
    # THE point: six posts → six load() calls → ONE deduplicated batch.
    assert len(batches) == 1
    assert sorted(batches[0]) == ["alan", "barbara", "grace"]


def test_post_query_serves_one_seed_post(client: TestClient) -> None:
    body = run_query(client, '{ post(slug: "idempotency-retold") { id title tags } }')
    assert body["data"]["post"]["title"] == "Idempotency, retold"
    assert body["data"]["post"]["tags"] == ["http"]


def test_unknown_slug_is_a_typed_graphql_error(client: TestClient) -> None:
    body = run_query(client, '{ post(slug: "nope") { id } }')
    assert body["data"] is None
    (error,) = body["errors"]
    assert error["message"] == "Post 'nope' not found"
    assert error["locations"] == [{"line": 1, "column": 3}]
    assert error["path"] == ["post"]
    # The family code vocabulary survives the transport change.
    assert error["extensions"]["code"] == "not_found"
    assert error["extensions"]["slug"] == "nope"


def test_create_post_mutation_stores_through_the_real_pipeline(client: TestClient) -> None:
    body = run_query(
        client,
        "mutation { createPost(input: { title: \"A post from the GraphQL test\", "
        'author: "grace", tags: ["graphql"], status: PUBLISHED }) { id title '
        "status authorName } }",
    )
    created = body["data"]["createPost"]
    assert created["id"] == "a-post-from-the-graphql-test"
    assert created["status"] == "PUBLISHED"
    # Cross-protocol proof: the REST surface serves what the mutation stored.
    rest = client.get(f"/api/posts/{created['id']}")
    assert rest.status_code == 200
    assert rest.json()["title"] == "A post from the GraphQL test"


def test_invalid_arguments_fail_validation_with_details(client: TestClient) -> None:
    body = run_query(client, "{ posts(limit: 500) { total } }")
    (error,) = body["errors"]
    assert error["extensions"]["code"] == "validation_failed"
    assert any("limit" in detail for detail in error["extensions"]["details"])


def test_invalid_mutation_input_fails_validation_with_details(client: TestClient) -> None:
    body = run_query(
        client, 'mutation { createPost(input: { title: "", author: "x" }) { id } }'
    )
    (error,) = body["errors"]
    assert error["extensions"]["code"] == "validation_failed"
    assert any("title" in detail for detail in error["extensions"]["details"])


def test_broken_query_is_a_syntax_error_never_a_crash(client: TestClient) -> None:
    body = run_query(client, "   ")
    (error,) = body["errors"]
    assert "Syntax Error" in error["message"]
    assert error["locations"]


def test_introspection_names_the_entry_points_and_one_type(client: TestClient) -> None:
    body = run_query(
        client,
        "{ __schema { queryType { name } mutationType { name } } }",
    )
    assert body["data"]["__schema"] == {
        "queryType": {"name": "Query"},
        "mutationType": {"name": "Mutation"},
    }
    type_body = run_query(client, '{ __type(name: "Post") { fields { name } } }')
    field_names = [field["name"] for field in type_body["data"]["__type"]["fields"]]
    assert "authorName" in field_names
    assert "author" in field_names


def test_graphiql_serves_on_get_html(client: TestClient) -> None:
    response = client.get(GRAPHQL, headers={"accept": "text/html"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "GraphiQL" in response.text


def test_the_mount_stays_out_of_the_openapi_document(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert GRAPHQL not in schema["paths"]
    # …while the REST surface it mirrors stays documented.
    assert "/api/posts" in schema["paths"]


def test_unresolvable_byline_answers_null_author_not_an_invented_one(
    client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    """A byline the loader cannot resolve becomes a null author — honestly."""

    async def nothing_resolves(self: AuthorLoader, names: list[str]) -> list[Any]:
        return [None for _name in names]

    monkeypatch.setattr(AuthorLoader, "_load_authors", nothing_resolves)
    body = run_query(
        client, '{ post(slug: "idempotency-retold") { authorName author { id } } }'
    )
    assert body.get("errors") is None
    # The stored string is present; the derived object is honestly null.
    assert body["data"]["post"]["authorName"] == "alan"
    assert body["data"]["post"]["author"] is None
