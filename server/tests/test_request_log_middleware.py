"""The access-log middleware (``presentation/middleware/request_log.py``).

One structured ``http_request`` event per HTTP exchange — the layer the
middleware topic recorded as arriving with observability. These tests pin
it at both levels: against the real app (one row per request, carrying the
SAME request id the response header echoes, with method/path/status among
the field rows) and at the bare ASGI boundary (a raising inner app still
gets its row, with status 0 — the honest marker that no response.start
ever crossed this layer).
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from guide.core.logging import recent_log
from guide.presentation.middleware.request_log import RequestLogMiddleware

# asyncio_mode=auto: async tests run on the event loop without markers.


def _fields(event: Any) -> dict[str, str]:
    return dict(event.fields)


def test_every_request_leaves_exactly_one_http_request_row(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    request_id = response.headers["x-request-id"]

    rows = recent_log().by_request_id(request_id)
    assert [row.event for row in rows] == ["http_request"]
    row = rows[0]
    assert row.level == "info"
    fields = _fields(row)
    assert fields["method"] == "GET"
    assert fields["path"] == "/api/health"
    assert fields["status"] == "200"
    assert float(fields["duration_ms"]) >= 0.0


def test_failed_requests_share_the_id_access_log_and_failure_rows(
    client: TestClient,
) -> None:
    response = client.get("/api/posts/nope", headers={"x-request-id": "access-log-404"})
    assert response.status_code == 404

    rows = recent_log().by_request_id("access-log-404")
    # One failure row (the shared handler's warning) + the access-log line.
    assert [row.event for row in rows] == ["app_error", "http_request"]
    assert rows[0].level == "warning"
    assert _fields(rows[1])["status"] == "404"
    # The envelope body carries the same id the rows do.
    assert response.json()["error"]["requestId"] == "access-log-404"


async def test_a_raising_inner_app_still_logs_with_status_zero() -> None:
    async def broken_app(scope: Scope, receive: Receive, send: Send) -> None:
        raise RuntimeError("boom")

    async def receive() -> Message:
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:  # pragma: no cover - never reached
        raise AssertionError("no response crosses this boundary")

    recent_log().clear()
    with pytest.raises(RuntimeError, match="boom"):
        await RequestLogMiddleware(broken_app)(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "method": "GET",
                "path": "/broken",
                "headers": [],
            },
            receive,
            send,
        )

    [row] = recent_log().tail()
    assert row.event == "http_request"
    fields = _fields(row)
    assert fields["status"] == "0"  # no http.response.start ever passed
    assert fields["path"] == "/broken"
