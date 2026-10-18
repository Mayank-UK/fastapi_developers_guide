"""The real /api/posts endpoints: the posts resource's wire contract.

Pinned against the per-test app (fresh twelve-post seed each time): the
collection's page shape and pagination headers, filters and sorts, the
edge's own 422 for a bad query, item reads with the shared 404 envelope,
201 + Location on create (slug minted from the title), full-replace
semantics, the 405 the undefined DELETE earns, and the OpenAPI contract
declared for every route.
"""

from fastapi.testclient import TestClient

POSTS = "/api/posts"


def test_collection_serves_the_default_page_with_pagination_headers(
    client: TestClient,
) -> None:
    response = client.get(POSTS)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 12
    assert body["page"] == 1
    assert body["limit"] == 6
    assert body["pages"] == 2
    assert len(body["items"]) == 6
    # Newest first: the last seed (2026-09-12) leads.
    assert body["items"][0]["id"] == "drafting-the-grpc-chapter"
    assert response.headers["x-total-count"] == "12"
    assert response.headers["x-page-count"] == "2"
    assert response.headers["link"] == '</api/posts?page=2>; rel="next"'


def test_page_two_carries_prev_and_next_links(client: TestClient) -> None:
    response = client.get(POSTS, params={"page": 2, "limit": 4})
    body = response.json()
    assert body["pages"] == 3
    assert response.headers["link"] == (
        '</api/posts?page=3&limit=4>; rel="next", '
        '</api/posts?limit=4>; rel="prev"'
    )


def test_single_page_has_no_link_header(client: TestClient) -> None:
    response = client.get(POSTS, params={"limit": 100})
    assert response.json()["pages"] == 1
    assert "link" not in response.headers


def test_filters_narrow_totals_and_links_preserve_the_lens(client: TestClient) -> None:
    response = client.get(
        POSTS,
        params={"author": "grace", "tag": "design", "sort": "oldest", "limit": 2},
    )
    body = response.json()
    # grace × design: seeds 1, 2, and 7.
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == [
        "designing-urls-people-can-read",
        "status-codes-are-a-contract",
    ]
    # The next link keeps the filters and the non-default sort, omits page=1.
    assert response.headers["link"] == (
        '</api/posts?page=2&limit=2&author=grace&tag=design&sort=oldest>; rel="next"'
    )


def test_status_filter_and_title_sort(client: TestClient) -> None:
    drafts = client.get(POSTS, params={"status": "draft"}).json()
    assert drafts["total"] == 3
    assert all(item["status"] == "draft" for item in drafts["items"])

    by_title = client.get(POSTS, params={"sort": "title", "limit": 3}).json()
    assert [item["title"] for item in by_title["items"]] == [
        "Content negotiation in practice",
        "Designing URLs people can read",
        "Drafting the GraphQL chapter",
    ]


def test_page_past_the_end_is_an_empty_page_not_an_error(client: TestClient) -> None:
    body = client.get(POSTS, params={"page": 99}).json()
    assert body["items"] == []
    assert body["total"] == 12
    assert body["page"] == 99


def test_bad_query_is_the_edges_own_422(client: TestClient) -> None:
    response = client.get(POSTS, params={"page": 0})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["details"][0]["loc"] == ["query", "page"]

    bogus_status = client.get(POSTS, params={"status": "loud"})
    assert bogus_status.status_code == 422
    assert bogus_status.json()["error"]["details"][0]["loc"] == ["query", "status"]


def test_item_read_serves_one_post(client: TestClient) -> None:
    response = client.get(f"{POSTS}/idempotency-retold")
    assert response.status_code == 200
    post = response.json()
    assert post["author"] == "alan"
    assert post["status"] == "published"
    assert post["createdAt"] == "2026-09-03T08:00:00.000+00:00"


def test_unknown_item_is_the_shared_404_envelope(client: TestClient) -> None:
    response = client.get(f"{POSTS}/does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert "does-not-exist" in error["message"]
    assert error["requestId"]
    assert response.headers["x-request-id"] == error["requestId"]


def test_create_answers_201_with_location_and_minted_slug(client: TestClient) -> None:
    response = client.post(
        POSTS,
        json={
            "title": "A post from a test",
            "author": "tester",
            "tags": ["api"],
            "status": "published",
        },
    )
    assert response.status_code == 201
    post = response.json()
    assert post["id"] == "a-post-from-a-test"
    assert post["createdAt"] == post["updatedAt"]
    assert response.headers["location"] == "/api/posts/a-post-from-a-test"
    # The store really grew.
    assert client.get(POSTS).json()["total"] == 13


def test_create_with_a_colliding_title_mints_a_uniquified_slug(
    client: TestClient,
) -> None:
    body = {"title": "Idempotency, retold", "author": "tester"}
    first = client.post(POSTS, json=body).json()
    second = client.post(POSTS, json=body).json()
    assert first["id"] == "idempotency-retold-2"
    assert second["id"] == "idempotency-retold-3"


def test_create_with_a_punctuation_only_title_falls_back_to_post(
    client: TestClient,
) -> None:
    response = client.post(POSTS, json={"title": "??? !!!", "author": "tester"})
    assert response.status_code == 201
    assert response.json()["id"] == "post"


def test_invalid_create_body_is_the_422_envelope(client: TestClient) -> None:
    response = client.post(POSTS, json={"author": "tester"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["details"][0]["loc"] == ["body", "title"]
    assert error["details"][0]["type"] == "missing"


def test_replace_keeps_identity_and_bumps_updated_at(client: TestClient) -> None:
    before = client.get(f"{POSTS}/notes-on-rfc-9457").json()
    response = client.put(
        f"{POSTS}/notes-on-rfc-9457",
        json={
            "title": "Notes on RFC 9457, revised",
            "body": "Updated by PUT.",
            "author": "barbara",
            "tags": ["http"],
            "status": "draft",
        },
    )
    assert response.status_code == 200
    after = response.json()
    assert after["title"] == "Notes on RFC 9457, revised"
    assert after["status"] == "draft"
    assert after["createdAt"] == before["createdAt"]
    assert after["updatedAt"] >= before["updatedAt"]


def test_replace_unknown_item_is_404(client: TestClient) -> None:
    response = client.put(
        f"{POSTS}/nope", json={"title": "t", "author": "a"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_delete_is_not_defined_and_answers_405_envelope(client: TestClient) -> None:
    response = client.delete(f"{POSTS}/notes-on-rfc-9457")
    assert response.status_code == 405
    error = response.json()["error"]
    # Truthful status, closest-kind code: the taxonomy's rule for unnamed 4xx.
    assert error["code"] == "not_found"
    assert error["message"] == "Method Not Allowed"
    assert error["requestId"]
    # And the post survived.
    assert client.get(f"{POSTS}/notes-on-rfc-9457").status_code == 200


def test_response_models_are_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    posts = schema["paths"][POSTS]
    assert posts["get"]["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("PostPage")
    assert posts["post"]["responses"]["201"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("Post")
    item = schema["paths"][f"{POSTS}/{{post_id}}"]
    assert item["get"]["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("Post")
    assert item["put"]["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("PostCreate")
    # The surface is honest: no DELETE operation is declared.
    assert "delete" not in item
    assert "delete" not in posts
