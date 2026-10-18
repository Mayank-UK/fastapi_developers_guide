"""GET/POST /api/demo/http/headers: the echo endpoint's wire contract.

The endpoints run the real builder against a real request, so these tests
send KNOWN headers through TestClient and assert they come back classified
— plus the request-fact echoes (method, path, raw query, content type, the
POST's parsed body), absent-fact omission, the request-id round trip, and
the declared response models in OpenAPI.
"""

from typing import Any

from fastapi.testclient import TestClient

DEMO_PATH = "/api/demo/http/headers"


def _by_name(body: dict[str, Any]) -> dict[str, Any]:
    """The echoed headers, keyed by name (names are unique on the wire)."""
    return {header["name"]: header for header in body["headers"]}


def test_get_echoes_known_headers_classified_end_to_end(client: TestClient) -> None:
    response = client.get(
        DEMO_PATH,
        headers={
            "user-agent": "echo-probe/1.0",
            "accept": "application/json",
            "x-demo-trace": "hello-http",
        },
    )
    assert response.status_code == 200
    echoed = _by_name(response.json())

    assert echoed["user-agent"]["value"] == "echo-probe/1.0"
    assert echoed["user-agent"]["scope"] == "end-to-end"
    assert echoed["accept"]["value"] == "application/json"
    assert echoed["x-demo-trace"]["value"] == "hello-http"
    assert echoed["x-demo-trace"]["scope"] == "end-to-end"
    assert echoed["x-demo-trace"]["note"] == (
        "extension header: the x- prefix is convention, not standard"
    )


def test_get_reports_the_request_line_and_raw_query(client: TestClient) -> None:
    body = client.get(f"{DEMO_PATH}?from=client-demo").json()
    assert body["method"] == "GET"
    assert body["path"] == DEMO_PATH
    assert body["query"] == "from=client-demo"


def test_get_omits_absent_facts_entirely(client: TestClient) -> None:
    body = client.get(DEMO_PATH).json()
    assert set(body) == {"method", "path", "headers", "hopByHop"}
    assert "content-type" not in _by_name(body)


def test_hop_by_hop_reference_list_rides_along(client: TestClient) -> None:
    body = client.get(DEMO_PATH).json()
    assert body["hopByHop"] == [
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    ]


def test_inbound_request_id_is_echoed_and_stamped_on_the_response(client: TestClient) -> None:
    response = client.get(DEMO_PATH, headers={"x-request-id": "probe-42"})
    assert response.headers["x-request-id"] == "probe-42"
    echoed = _by_name(response.json())
    assert echoed["x-request-id"]["value"] == "probe-42"


def test_post_carries_body_content_type_and_parsed_message(client: TestClient) -> None:
    response = client.post(
        DEMO_PATH, json={"message": "via testclient"}, headers={"x-demo-trace": "post"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "POST"
    assert body["contentType"] == "application/json"
    assert body["bodyMessage"] == "via testclient"
    echoed = _by_name(body)
    assert echoed["content-type"]["value"] == "application/json"
    assert echoed["x-demo-trace"]["value"] == "post"


def test_post_without_body_still_answers_and_omits_body_facts(client: TestClient) -> None:
    body = client.post(DEMO_PATH).json()
    assert body["method"] == "POST"
    assert "bodyMessage" not in body
    assert "contentType" not in body


def test_post_with_invalid_body_is_the_422_validation_envelope(client: TestClient) -> None:
    response = client.post(
        DEMO_PATH,
        content='{"message": 42}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert response.headers["x-request-id"]


def test_response_models_are_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    for verb in ("get", "post"):
        ref = schema["paths"][DEMO_PATH][verb]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        assert ref.endswith("HttpHeadersEchoPayload")
