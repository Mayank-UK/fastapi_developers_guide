"""The security middleware stack on the wire: headers, CSP split, CORS, HSTS.

Every case runs against the real per-test app: the defensive headers must
be on the 200, on the 404 envelope, AND on the 429 the limiter raises —
the error paths are the ones an attacker actually probes. The CSP is
path-aware (strict on the API, CDN-aware on the docs pages), HSTS appears
only over https, and CORS answers both origins plus both preflight
verdicts from the SAME allow-list the composition root wires.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Headers

from guide.presentation.middleware.security_headers import API_CSP, DOCS_CSP

ALLOWED_ORIGIN = "http://localhost:5174"
EVIL_ORIGIN = "http://evil.example"
BURN_PATH = "/api/demo/security/rate-limit/burn"


def _assert_static_headers(headers: Headers) -> None:
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["content-security-policy"] == API_CSP


def test_security_headers_are_on_the_success_path(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    _assert_static_headers(response.headers)


def test_security_headers_are_on_the_404_envelope(client: TestClient) -> None:
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    _assert_static_headers(response.headers)


def test_security_headers_are_on_the_429_envelope(client: TestClient) -> None:
    for _ in range(5):
        assert client.post(BURN_PATH).status_code == 200
    throttled = client.post(BURN_PATH)
    assert throttled.status_code == 429
    assert throttled.headers["retry-after"].isdigit()
    _assert_static_headers(throttled.headers)


def test_csp_is_strict_on_the_api_and_docs_aware_on_the_docs_pages(
    client: TestClient,
) -> None:
    assert client.get("/api/health").headers["content-security-policy"] == API_CSP
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert docs.headers["content-security-policy"] == DOCS_CSP
    assert "cdn.jsdelivr.net" in docs.headers["content-security-policy"]
    redoc = client.get("/redoc")
    assert redoc.status_code == 200
    assert redoc.headers["content-security-policy"] == DOCS_CSP


def test_hsts_is_absent_over_http_and_present_over_https(
    app: FastAPI, client: TestClient
) -> None:
    assert "strict-transport-security" not in client.get("/api/health").headers
    https_client = TestClient(app, base_url="https://example.test")
    https_response = https_client.get("/api/health")
    assert https_response.status_code == 200
    assert https_response.headers["strict-transport-security"] == (
        "max-age=31536000; includeSubDomains"
    )


def test_cors_allows_the_listed_origin_with_credentials(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": ALLOWED_ORIGIN})
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    # The security headers stack with the CORS verdict — both middlewares ran.
    _assert_static_headers(response.headers)


def test_cors_is_silent_for_a_disallowed_origin(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": EVIL_ORIGIN})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_preflight_is_answered_for_allowed_and_refused_for_disallowed(
    client: TestClient,
) -> None:
    allowed = client.options(
        BURN_PATH,
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "POST" in allowed.headers["access-control-allow-methods"]

    refused = client.options(
        BURN_PATH,
        headers={
            "Origin": EVIL_ORIGIN,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert refused.status_code == 400
    assert "access-control-allow-origin" not in refused.headers
