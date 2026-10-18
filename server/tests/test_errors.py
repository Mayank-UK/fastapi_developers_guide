"""Error taxonomy end to end: kind→status map, envelope shape, request ids.

Every case goes through the real wiring (factory app + middleware +
handlers) using test-only routes that raise; behavior, not implementation.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException

from guide.core.errors import (
    AppError,
    FailureKind,
    http_status_for,
    kind_for_http_status,
)

RECORDED_STATUS_CONTRACT = {
    FailureKind.VALIDATION_FAILED: 422,
    FailureKind.UNAUTHORIZED: 401,
    FailureKind.FORBIDDEN: 403,
    FailureKind.NOT_FOUND: 404,
    FailureKind.CONFLICT: 409,
    FailureKind.RATE_LIMITED: 429,
    FailureKind.SERVICE_UNAVAILABLE: 503,
    FailureKind.INTERNAL: 500,
}


@pytest.fixture
def raiser_client(app: FastAPI) -> TestClient:
    """Client over the factory app plus test-only routes that raise on demand."""

    @app.get("/api/_boom/{kind}")
    def boom(kind: str) -> dict[str, str]:
        raise AppError(FailureKind(kind), "boom message", {"hint": "x"})

    @app.get("/api/_starlette/{status}")
    def starlette_raise(status: int) -> dict[str, str]:
        raise HTTPException(status_code=status, detail="custom detail")

    @app.get("/api/_crash")
    def crash() -> dict[str, str]:
        raise RuntimeError("secret internals must not leak")

    return TestClient(app)


def test_status_map_is_the_recorded_family_contract() -> None:
    for kind, status in RECORDED_STATUS_CONTRACT.items():
        assert http_status_for(kind) == status


def test_every_kind_reaches_the_client_as_its_envelope(raiser_client: TestClient) -> None:
    for kind in FailureKind:
        response = raiser_client.get(f"/api/_boom/{kind.value}")
        body = response.json()
        assert response.status_code == RECORDED_STATUS_CONTRACT[kind]
        assert body["error"]["code"] == kind.value
        assert body["error"]["message"] == "boom message"
        assert body["error"]["requestId"]
        assert body["error"]["details"] == {"hint": "x"}


def test_unnamed_statuses_take_closest_kind_but_keep_truthful_status() -> None:
    assert kind_for_http_status(405) is FailureKind.NOT_FOUND
    assert kind_for_http_status(400) is FailureKind.NOT_FOUND
    assert kind_for_http_status(501) is FailureKind.INTERNAL


def test_method_not_allowed_keeps_405_with_not_found_kind(raiser_client: TestClient) -> None:
    response = raiser_client.patch("/api/health")  # health only allows GET
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "not_found"
    assert "allow" in {key.lower() for key in response.headers}


def test_starlette_http_exception_maps_by_status(raiser_client: TestClient) -> None:
    for status, code in ((401, "unauthorized"), (404, "not_found"), (409, "conflict")):
        response = raiser_client.get(f"/api/_starlette/{status}")
        assert response.status_code == status
        assert response.json()["error"]["code"] == code
        assert response.json()["error"]["message"] == "custom detail"


def test_unknown_path_is_404_envelope(raiser_client: TestClient) -> None:
    response = raiser_client.get("/api/definitely-not-a-route")
    assert response.status_code == 404
    body = response.json()["error"]
    assert body["code"] == "not_found"
    assert body["requestId"]


def test_request_validation_failure_is_422_envelope(client: TestClient) -> None:
    response = client.patch("/api/demo/scenario", json={"injectFailure": "bogus"})
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_failed"
    assert body["requestId"]
    detail = body["details"][0]
    assert set(detail) == {"loc", "msg", "type"}
    assert "injectFailure" in detail["loc"]


def test_unhandled_exception_is_500_generic_envelope_with_request_id(
    app: FastAPI, capsys: pytest.CaptureFixture[str]
) -> None:
    client = TestClient(app, raise_server_exceptions=False)

    @app.get("/api/_crash")
    def crash() -> dict[str, str]:
        raise RuntimeError("secret internals must not leak")

    response = client.get("/api/_crash")
    assert response.status_code == 500
    body = response.json()["error"]
    assert body["code"] == "internal"
    assert body["message"] == "Internal server error."
    assert "secret internals" not in response.text
    assert body["requestId"]
    assert response.headers["x-request-id"] == body["requestId"]
    # The failure is logged with the request id, traceback included.
    captured = capsys.readouterr().out
    assert "unhandled_exception" in captured
    assert body["requestId"] in captured


def test_request_id_generated_and_inbound_honored(client: TestClient) -> None:
    generated = client.get("/api/health")
    assert generated.headers["x-request-id"]

    honored = client.get("/api/health", headers={"x-request-id": "trace-abc-123"})
    assert honored.headers["x-request-id"] == "trace-abc-123"

    on_error = client.get(
        "/api/definitely-not-a-route", headers={"x-request-id": "err-trace"}
    )
    assert on_error.headers["x-request-id"] == "err-trace"


def test_inbound_request_id_capped_at_200_chars(client: TestClient) -> None:
    huge = "r" * 300
    response = client.get("/api/health", headers={"x-request-id": huge})
    assert response.headers["x-request-id"] == huge[:200]
