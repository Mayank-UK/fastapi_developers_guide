"""GET /api/demo/arch/tracer: the live architecture trace's contract.

The endpoint runs against the REAL app (the test fixture's own
create_app), so these tests pin the payload against the app serving it:
the introspected structure (the built stack walk, the traced route's real
dependency tree, the composition wiring read off app.state), and the two
measured rounds driven through the app at the ASGI boundary — the ok
round's beats, facts, and request-id round trip; the err round's 404
envelope with header/body id agreement. Honesty is pinned too: every hop
labels its evidence, and no hop invents a timing (only the three boundary
beats carry offsets).
"""

from fastapi.testclient import TestClient

DEMO_PATH = "/api/demo/arch/tracer"

EXPECTED_STACK = [
    "ServerErrorMiddleware",
    "ExceptionTelemetryMiddleware",
    "CORSMiddleware",
    "SecurityHeadersMiddleware",
    "RequestIdMiddleware",
    "ExceptionMiddleware",
    "AsyncExitStackMiddleware",
    "APIRouter",
]
"""The built chain, outermost first (same walk the middleware demo proves)."""

EXPECTED_DEPS = [
    {"param": "query", "provider": "PostListQuery", "providerKind": "model"},
    {"param": "use_cases", "provider": "get_post_use_cases", "providerKind": "function"},
]


def test_serves_the_live_stack_in_request_order(client: TestClient) -> None:
    body = client.get(DEMO_PATH).json()
    assert [layer["name"] for layer in body["stack"]] == EXPECTED_STACK
    assert [layer["orderIndex"] for layer in body["stack"]] == list(range(len(EXPECTED_STACK)))
    kinds = {layer["name"]: layer["kind"] for layer in body["stack"]}
    assert kinds["RequestIdMiddleware"] == "user"
    assert kinds["CORSMiddleware"] == "user"
    assert kinds["SecurityHeadersMiddleware"] == "user"
    assert kinds["APIRouter"] == "router"
    assert kinds["ServerErrorMiddleware"] == "framework"
    assert all(layer["role"] for layer in body["stack"])


def test_route_facts_come_from_the_real_posts_router(client: TestClient) -> None:
    body = client.get(DEMO_PATH).json()
    route = body["route"]
    assert route["template"] == "/api/posts"
    assert route["method"] == "GET"
    assert route["endpoint"] == "list_posts"
    assert route["responseModel"] == "PostPage"
    assert route["dependencies"] == EXPECTED_DEPS


def test_wiring_facts_come_off_the_live_app_state(client: TestClient) -> None:
    body = client.get(DEMO_PATH).json()
    assert body["wiring"] == {
        "port": "PostRepository",
        "adapter": "InMemoryPostRepository",
        "useCases": "PostUseCases",
        "wiredBy": "create_app()",
    }


def test_the_ok_round_crossed_every_layer_for_real(client: TestClient) -> None:
    body = client.get(DEMO_PATH).json()
    ok = next(round_ for round_ in body["rounds"] if round_["outcome"] == "ok")
    assert ok["requestLine"] == "GET /api/posts?page=2&limit=4"
    assert ok["inboundRequestId"] == "arch-tracer-ok-round"
    assert ok["status"] == 200
    # The three measured boundary beats, in order, non-decreasing.
    beats = ok["beats"]
    assert [beat["event"] for beat in beats] == ["enter", "response.start", "complete"]
    assert beats[0]["offsetMs"] == 0.0
    assert beats[1]["offsetMs"] >= beats[0]["offsetMs"]
    assert beats[2]["offsetMs"] >= beats[1]["offsetMs"]
    facts = {fact["name"]: fact["value"] for fact in ok["facts"]}
    assert facts["status"] == "200"
    assert facts["page"] == "2"
    assert facts["limit"] == "4"
    assert facts["total"] == facts["x-total-count header"]
    assert int(facts["items"]) == 4
    # The round trip is the real middleware running: inbound id echoed back.
    assert facts["x-request-id header"] == "arch-tracer-ok-round"
    assert facts["inboundIdEchoed"] == "true"


def test_the_err_round_proves_the_failure_path_end_to_end(client: TestClient) -> None:
    body = client.get(DEMO_PATH).json()
    err = next(round_ for round_ in body["rounds"] if round_["outcome"] == "err")
    assert err["requestLine"] == "GET /api/posts/nope"
    assert err["inboundRequestId"] == "arch-tracer-err-round"
    assert err["status"] == 404
    facts = {fact["name"]: fact["value"] for fact in err["facts"]}
    assert facts["envelope code"] == "not_found"
    assert "nope" in facts["envelope message"]
    assert facts["envelope requestId"] == "arch-tracer-err-round"
    assert facts["x-request-id header"] == "arch-tracer-err-round"
    assert facts["headerMatchesBody"] == "true"


def test_every_hop_labels_its_evidence_and_none_invents_a_timing(client: TestClient) -> None:
    body = client.get(DEMO_PATH).json()
    allowed = {"measured", "observed", "introspected"}
    for round_ in body["rounds"]:
        for hop in round_["hops"]:
            assert hop["evidence"] in allowed
            assert hop["stage"]
            assert hop["layer"]
            assert hop["detail"]
        # Timings live ONLY on the beats: three events, never more.
        assert len(round_["beats"]) == 3


def test_the_traced_requests_are_isolated_from_the_tracer_request(client: TestClient) -> None:
    """The inner request-id contextvar unwinds cleanly: the tracer's own id survives."""
    response = client.get(DEMO_PATH)
    body = response.json()
    outer_id = response.headers["x-request-id"]
    assert outer_id
    for round_ in body["rounds"]:
        # The internal rounds carried their OWN ids — neither is the outer one.
        assert round_["inboundRequestId"] != outer_id


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][DEMO_PATH]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert ref.endswith("ArchTracerPayload")
