"""GET/POST /api/demo/reqres/inspector: the live Request object's contract.

The endpoints reflect the REAL request that fetched them, so these tests
pin reflection against the request TestClient actually sends: query
collection with repeated keys, selected headers including custom x-*
probes, the POST body contract (content type, length, parsed message),
the client address, and the request-id round trip through the response
header.
"""

from fastapi.testclient import TestClient

INSPECTOR_PATH = "/api/demo/reqres/inspector"


def test_get_reflects_the_request_line_and_query(client: TestClient) -> None:
    body = client.get(f"{INSPECTOR_PATH}?zoom=2").json()
    assert body["method"] == "GET"
    assert body["path"] == INSPECTOR_PATH
    assert body["rawQuery"] == "zoom=2"
    assert body["queryParams"] == [{"name": "zoom", "values": ["2"], "isRepeated": False}]


def test_repeated_query_keys_collect_every_value(client: TestClient) -> None:
    body = client.get(f"{INSPECTOR_PATH}?tag=a&tag=b&zoom=1&tag=c").json()
    by_name = {param["name"]: param for param in body["queryParams"]}
    assert by_name["tag"]["values"] == ["a", "b", "c"]
    assert by_name["tag"]["isRepeated"] is True


def test_custom_x_headers_are_reflected_and_unselected_ones_are_not(client: TestClient) -> None:
    body = client.get(INSPECTOR_PATH, headers={"X-Probe": "hello", "Referer": "https://x"}).json()
    names = [header["name"] for header in body["headers"]]
    assert "x-probe" in names
    assert "referer" not in names
    assert body["headers"][names.index("x-probe")]["value"] == "hello"


def test_post_reports_body_contract_and_parsed_message(client: TestClient) -> None:
    response = client.post(INSPECTOR_PATH, json={"message": "hi"})
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "POST"
    assert body["contentType"] == "application/json"
    assert isinstance(body["contentLength"], int)
    assert body["contentLength"] > 0
    assert body["bodyMessage"] == "hi"


def test_get_without_body_omits_the_body_facts(client: TestClient) -> None:
    body = client.get(INSPECTOR_PATH).json()
    assert "contentType" not in body
    assert "contentLength" not in body
    assert "bodyMessage" not in body


def test_client_address_is_reported_when_the_transport_provides_one(client: TestClient) -> None:
    body = client.get(INSPECTOR_PATH).json()
    assert body["client"]["host"] == "testclient"
    assert isinstance(body["client"]["port"], int)


def test_request_id_round_trip_payload_matches_header(client: TestClient) -> None:
    response = client.get(INSPECTOR_PATH, headers={"x-request-id": "inspector-probe"})
    body = response.json()
    assert body["requestId"] == "inspector-probe"
    assert response.headers["x-request-id"] == "inspector-probe"
    assert body["requestIdHeader"] == "x-request-id"


def test_response_models_are_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    for method in ("get", "post"):
        ref = schema["paths"][INSPECTOR_PATH][method]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        assert ref.endswith("RequestInspectorPayload")
