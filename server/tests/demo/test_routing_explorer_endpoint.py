"""GET /api/demo/routing/explorer: the route matcher's live contract.

The endpoint runs the real builder against the REAL app's declared table
(the test fixture's own create_app), so these tests pin outcomes against
the app serving them: defaults, a matched template with its bound
parameter, the 405 with allowed methods, the trailing-slash redirect, the
404 with near misses, the 422 envelopes for an unknown verb and a
non-absolute path, and the declared response model in OpenAPI.
"""

from fastapi.testclient import TestClient

DEMO_PATH = "/api/demo/routing/explorer"


def test_defaults_to_get_api_health_and_matches(client: TestClient) -> None:
    body = client.get(DEMO_PATH).json()
    assert body["request"] == {"method": "GET", "path": "/api/health"}
    assert body["outcome"] == "matched"
    assert body["matchedPath"] == "/api/health"
    assert body["matchedMethods"] == ["GET"]
    assert body["routeCount"] >= 15


def test_matched_path_parameter_is_bound(client: TestClient) -> None:
    body = client.get(
        DEMO_PATH, params={"method": "GET", "path": "/api/content/routing"}
    ).json()
    assert body["outcome"] == "matched"
    assert body["matchedPath"] == "/api/content/{topic_id}"
    assert body["pathParams"] == [{"name": "topic_id", "value": "routing", "source": "path"}]
    assert body["matchedTags"] == ["content"]


def test_query_parameters_of_the_simulated_path_are_parsed(client: TestClient) -> None:
    body = client.get(
        DEMO_PATH, params={"path": "/api/content/routing?extra=1"}
    ).json()
    assert body["outcome"] == "matched"
    assert body["queryParams"] == [{"name": "extra", "value": "1", "source": "query"}]


def test_head_against_a_get_route_is_the_405_outcome(client: TestClient) -> None:
    body = client.get(
        DEMO_PATH, params={"method": "HEAD", "path": "/api/health"}
    ).json()
    assert body["outcome"] == "method_not_allowed"
    assert body["allowedMethods"] == ["GET"]
    assert "no implicit HEAD" in body["reasoning"]


def test_trailing_slash_is_the_redirect_outcome(client: TestClient) -> None:
    body = client.get(DEMO_PATH, params={"path": "/api/content/"}).json()
    assert body["outcome"] == "redirect"
    assert body["redirectTarget"] == "/api/content"


def test_unknown_path_is_the_404_outcome_with_near_misses(client: TestClient) -> None:
    body = client.get(DEMO_PATH, params={"path": "/api/nope"}).json()
    assert body["outcome"] == "not_found"
    near_paths = [miss["path"] for miss in body["nearMisses"]]
    # Every declared path shares the /api prefix, so the closest three lead with it.
    assert len(near_paths) == 3
    assert near_paths[0] == "/api/content"
    assert all(path.startswith("/api/") for path in near_paths)


def test_unknown_method_is_the_422_envelope(client: TestClient) -> None:
    response = client.get(DEMO_PATH, params={"method": "BOGUS", "path": "/api/health"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert response.headers["x-request-id"] == error["requestId"]


def test_non_absolute_path_is_the_422_envelope(client: TestClient) -> None:
    response = client.get(DEMO_PATH, params={"path": "api/health"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][DEMO_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("RoutingExplorerPayload")


def test_request_id_round_trip(client: TestClient) -> None:
    response = client.get(DEMO_PATH, headers={"x-request-id": "routing-probe"})
    assert response.headers["x-request-id"] == "routing-probe"
