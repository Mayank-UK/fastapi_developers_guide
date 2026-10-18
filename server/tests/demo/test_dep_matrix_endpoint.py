"""GET /api/demo/dep/matrix: the dependency-cache semantics, measured live.

The endpoint resolves every flavor in ONE request, so these tests pin the
framework's actual behavior through the real app: cached dependencies asked
twice resolve to the SAME instance (equal id()-tokens), use_cache=False
re-runs the provider (distinct tokens), the depth-3 chain shares its middle
layer with the handler's direct request, and a sync provider inside an
async endpoint runs on a threadpool worker — not the handler's thread.
"""

from fastapi.testclient import TestClient

MATRIX_PATH = "/api/demo/dep/matrix"


def _rows(client: TestClient) -> dict[str, dict[str, object]]:
    response = client.get(MATRIX_PATH)
    assert response.status_code == 200
    return {row["flavor"]: row for row in response.json()["rows"]}


def test_matrix_serves_six_flavors_in_order(client: TestClient) -> None:
    response = client.get(MATRIX_PATH)
    assert response.status_code == 200
    assert [row["flavor"] for row in response.json()["rows"]] == [
        "function",
        "callable-class",
        "cached-x2",
        "uncached-x2",
        "chain-depth-3",
        "sync-in-async",
    ]


def test_cached_dependency_asked_twice_is_one_instance(client: TestClient) -> None:
    row = _rows(client)["cached-x2"]
    tokens = row["tokens"]
    assert isinstance(tokens, list)
    assert tokens[0] == tokens[1]
    assert str(tokens[0]).startswith("RateBudget#")
    assert row["verdict"] == "same-instance"


def test_uncached_dependency_asked_twice_is_two_instances(client: TestClient) -> None:
    row = _rows(client)["uncached-x2"]
    tokens = row["tokens"]
    assert isinstance(tokens, list)
    assert tokens[0] != tokens[1]
    assert all(str(token).startswith("Cursor#") for token in tokens)
    assert row["verdict"] == "distinct-instances"


def test_function_flavor_reports_its_single_instance(client: TestClient) -> None:
    row = _rows(client)["function"]
    tokens = row["tokens"]
    assert isinstance(tokens, list) and len(tokens) == 1
    assert str(tokens[0]).startswith("Correlation#")
    assert row["verdict"] == "single"


def test_callable_class_shows_provider_and_minted_key(client: TestClient) -> None:
    row = _rows(client)["callable-class"]
    tokens = row["tokens"]
    assert isinstance(tokens, list)
    assert str(tokens[0]).startswith("ApiKeyIssuer#")
    assert str(tokens[1]).startswith("matrix-")
    assert row["verdict"] == "single"


def test_chain_shares_its_middle_with_the_direct_request(client: TestClient) -> None:
    row = _rows(client)["chain-depth-3"]
    tokens = row["tokens"]
    assert isinstance(tokens, list)
    top, middle, base, middle_direct = (str(token) for token in tokens)
    assert top.startswith("VerifiedRequest#")
    assert middle.startswith("AuthenticatedActor#")
    assert base.startswith("ParsedToken#")
    # The handler's direct Depends(get_authenticated_actor) hit the request
    # cache: it received the SAME actor the chain resolved through.
    assert middle_direct == middle
    assert len({top, middle, base}) == 3
    assert row["verdict"] == "shared-middle"


def test_sync_provider_runs_in_the_threadpool_inside_an_async_endpoint(
    client: TestClient,
) -> None:
    row = _rows(client)["sync-in-async"]
    tokens = row["tokens"]
    assert isinstance(tokens, list)
    dep_thread, handler_thread = (str(token) for token in tokens)
    assert dep_thread.startswith("dep-thread:")
    assert handler_thread.startswith("handler-thread:")
    # The framework fact, measured: the sync provider did NOT run on the
    # event-loop thread the handler runs on.
    assert dep_thread != handler_thread
    assert row["verdict"] == "threadpool"


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    ref = paths[MATRIX_PATH]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert ref.endswith("DepMatrixPayload")
