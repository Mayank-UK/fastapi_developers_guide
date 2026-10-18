"""The /api/demo/api/workbench endpoints: roster facets + traced rounds.

Pinned against the per-test app: the roster serves the live substrate's
facets through the real list use case; a GET round reports the page, the
pagination block, and the layer stack; a 404 round carries the real
envelope with the CURRENT request's id (matching the x-request-id header);
a create round really mutates the store; a replace round preserves
identity; and DELETE — plus a POST against the item template — resolves to
the honest 405 whose envelope mirrors Starlette's own. Bogus combinations
(item template without a postId, a body on GET) die as the edge's own 422,
part of the lesson.
"""

from fastapi.testclient import TestClient

WORKBENCH = "/api/demo/api/workbench"


def test_roster_serves_live_facets_from_the_real_substrate(client: TestClient) -> None:
    body = client.get(WORKBENCH).json()
    assert body["authors"] == ["alan", "barbara", "grace"]
    assert "design" in body["tags"] and "drafts" in body["tags"]
    assert body["statuses"] == ["draft", "published"]
    assert body["sorts"] == ["newest", "oldest", "title"]
    assert body["totalPosts"] == 12
    assert "12 posts" in body["reasoning"]


def test_list_round_reports_page_pagination_and_layers(client: TestClient) -> None:
    response = client.post(
        WORKBENCH,
        json={
            "method": "GET",
            "template": "/api/posts",
            "query": {"page": 2, "limit": 4, "author": "grace"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["operation"] == "list"
    assert body["status"] == 200
    assert body["statusReason"] == "200 OK"
    assert body["kind"] == "page"
    assert body["request"]["path"] == "/api/posts?page=2&limit=4&author=grace"
    assert body["page"]["total"] == 4
    assert body["page"]["items"] == []  # page 2 of 4 items at limit 4 is empty
    assert body["pagination"]["pages"] == 1
    assert body["pagination"]["prev"] == "/api/posts?limit=4&author=grace"
    # exclude_none drops absent neighbors — there is no next on the last page.
    assert "next" not in body["pagination"]
    assert [layer["name"] for layer in body["layers"]] == [
        "routing",
        "validation",
        "use case",
        "repository",
        "response",
    ]
    assert "author=grace" in body["layers"][3]["detail"]


def test_default_list_round_omits_default_query_parts(client: TestClient) -> None:
    body = client.post(
        WORKBENCH, json={"method": "GET", "template": "/api/posts"}
    ).json()
    assert body["request"]["path"] == "/api/posts"
    assert body["pagination"]["next"] == "/api/posts?page=2"
    assert body["page"]["limit"] == 6


def test_get_round_serves_one_post(client: TestClient) -> None:
    body = client.post(
        WORKBENCH,
        json={"method": "GET", "template": "/api/posts/{postId}", "postId": "idempotency-retold"},
    ).json()
    assert body["operation"] == "get"
    assert body["status"] == 200
    assert body["kind"] == "post"
    assert body["post"]["author"] == "alan"
    assert body["request"]["path"] == "/api/posts/idempotency-retold"
    assert body["layers"][2]["name"] == "use case"


def test_get_round_for_a_missing_id_carries_the_real_envelope_with_this_rounds_id(
    client: TestClient,
) -> None:
    response = client.post(
        WORKBENCH,
        json={"method": "GET", "template": "/api/posts/{postId}", "postId": "nope"},
    )
    body = response.json()
    assert body["status"] == 404
    assert body["statusReason"] == "404 Not Found"
    assert body["kind"] == "envelope"
    envelope = body["envelope"]
    assert envelope["code"] == "not_found"
    assert "nope" in envelope["message"]
    # The envelope's requestId IS this workbench round's id.
    assert envelope["requestId"] == response.headers["x-request-id"]


def test_create_round_runs_the_real_use_case_and_mutates_the_store(
    client: TestClient,
) -> None:
    response = client.post(
        WORKBENCH,
        json={
            "method": "POST",
            "template": "/api/posts",
            "body": {"title": "Workbench made this", "author": "tester", "tags": ["api"]},
        },
    )
    body = response.json()
    assert body["operation"] == "create"
    assert body["status"] == 201
    assert body["statusReason"] == "201 Created"
    assert body["kind"] == "post"
    assert body["post"]["id"] == "workbench-made-this"
    assert body["layers"][3]["name"] == "repository"
    assert "Location: /api/posts/workbench-made-this" in body["layers"][4]["detail"]
    # The real collection sees it.
    assert client.get("/api/posts/workbench-made-this").status_code == 200


def test_replace_round_preserves_identity(client: TestClient) -> None:
    body = client.post(
        WORKBENCH,
        json={
            "method": "PUT",
            "template": "/api/posts/{postId}",
            "postId": "drafting-the-webhooks-chapter",
            "body": {
                "title": "Drafting the webhooks chapter, done",
                "author": "grace",
                "tags": ["drafts"],
                "status": "published",
            },
        },
    ).json()
    assert body["status"] == 200
    assert body["post"]["status"] == "published"
    assert body["post"]["createdAt"] == "2026-09-10T08:00:00.000+00:00"
    assert body["post"]["updatedAt"] >= body["post"]["createdAt"]


def test_delete_round_answers_the_honest_405(client: TestClient) -> None:
    body = client.post(WORKBENCH, json={"method": "DELETE", "template": "/api/posts"}).json()
    assert body["operation"] == "method-not-allowed"
    assert body["status"] == 405
    assert body["statusReason"] == "405 Method Not Allowed"
    assert body["envelope"]["code"] == "not_found"
    assert body["envelope"]["message"] == "Method Not Allowed"
    # The stack stops at routing: no use-case or repository layer ran.
    assert [layer["name"] for layer in body["layers"]] == ["routing", "response"]


def test_workbench_405_matches_the_real_routes_405(client: TestClient) -> None:
    simulated = client.post(
        WORKBENCH, json={"method": "DELETE", "template": "/api/posts"}
    ).json()["envelope"]
    real = client.delete("/api/posts").json()["error"]
    assert simulated["code"] == real["code"]
    assert simulated["message"] == real["message"]


def test_post_against_the_item_template_is_also_405(client: TestClient) -> None:
    body = client.post(
        WORKBENCH,
        json={
            "method": "POST",
            "template": "/api/posts/{postId}",
            "postId": "notes-on-rfc-9457",
            "body": {"title": "t", "author": "a"},
        },
    ).json()
    assert body["operation"] == "method-not-allowed"
    assert body["status"] == 405


def test_item_template_without_post_id_is_the_edges_own_422(client: TestClient) -> None:
    response = client.post(WORKBENCH, json={"method": "GET", "template": "/api/posts/{postId}"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["details"][0]["loc"] == ["body"]
    assert "post_id is required" in error["details"][0]["msg"]


def test_query_on_a_non_get_round_is_the_edges_own_422(client: TestClient) -> None:
    response = client.post(
        WORKBENCH,
        json={
            "method": "POST",
            "template": "/api/posts",
            "query": {"page": 1},
            "body": {"title": "t", "author": "a"},
        },
    )
    assert response.status_code == 422
    assert "query applies only" in response.json()["error"]["details"][0]["msg"]


def test_response_models_are_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    workbench = schema["paths"][WORKBENCH]
    assert workbench["get"]["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("WorkbenchRosterPayload")
    post = workbench["post"]
    assert post["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("WorkbenchPayload")
    assert post["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "WorkbenchRequest"
    )
