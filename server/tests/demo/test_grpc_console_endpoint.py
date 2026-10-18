"""The /api/demo/api/grpc-console endpoints: roster + real rounds over HTTP.

Pinned against the per-test app with the TestClient entered as a context
manager — the app's lifespan runs, so the lazily-started gRPC satellite
is STOPPED at teardown exactly as production shutdown does (asserted in
the last test). Every POST performs a REAL grpc.aio round through the
wired adapter: the payload facts (status, message sequence, elapsed)
come from that run, never from fixtures.
"""

import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

CONSOLE = "/api/demo/api/grpc-console"
_ADDRESS = re.compile(r"^127\.0\.0\.1:\d+$")


def _client(app: FastAPI) -> TestClient:
    """A TestClient whose lifespan runs (start/stop the satellite)."""
    return TestClient(app)


def test_roster_serves_the_live_satellite_and_the_contract(app: FastAPI) -> None:
    with _client(app) as client:
        body = client.get(CONSOLE).json()
    assert _ADDRESS.match(body["serverAddress"])
    assert body["service"] == "guide.PostService"
    assert 'rpc GetPost(GetPostRequest) returns (PostReply);' in body["protoExcerpt"]
    assert "rpc EchoChat(stream ChatNote) returns (stream ChatNote);" in body["protoExcerpt"]
    assert [(m["id"], m["kind"]) for m in body["methods"]] == [
        ("get-post", "unary"),
        ("stream-posts", "server-streaming"),
        ("count-views", "client-streaming"),
        ("echo-chat", "bidirectional"),
    ]
    design = body["methods"][1]
    assert design["streamsIn"] is False and design["streamsOut"] is True
    assert body["streamPauseMs"] == 50
    assert "grpc.aio" in body["reasoning"]


def test_post_round_trip_all_four_methods(app: FastAPI) -> None:
    with _client(app) as client:
        unary = client.post(CONSOLE, json={"method": "get-post"}).json()
        assert unary["statusCode"] == "OK"
        assert unary["sentMessages"] == 1
        assert "deadlineMs" not in unary  # exclude_none: unset stays absent
        assert unary["messages"][0]["fields"]["slug"] == "designing-urls-people-can-read"
        assert unary["method"]["name"] == "GetPost"
        assert unary["method"]["kind"] == "unary"

        stream = client.post(CONSOLE, json={"method": "stream-posts", "tag": "http"}).json()
        assert stream["statusCode"] == "OK"
        assert len(stream["messages"]) == 5  # five seeds carry the http tag

        upload = client.post(
            CONSOLE,
            json={
                "method": "count-views",
                "viewEvents": [
                    {"slug": "idempotency-retold", "viewer": "mak"},
                    {"slug": "idempotency-retold", "viewer": "ada"},
                ],
            },
        ).json()
        assert upload["statusCode"] == "OK"
        assert upload["sentMessages"] == 2
        assert upload["messages"][0]["fields"]["events"] == 2
        # Message field maps keep PROTO names (snake_case) by design.
        assert upload["messages"][0]["fields"]["views_per_post"] == {"idempotency-retold": 2}

        echo = client.post(
            CONSOLE,
            json={
                "method": "echo-chat",
                "chatNotes": [{"sender": "you", "text": "hello"}],
                "deadlineMs": 5000,
            },
        ).json()
        assert echo["statusCode"] == "OK"
        assert echo["deadlineMs"] == 5000
        assert echo["messages"][0]["fields"]["text"] == "hello"

        # All four rounds name the SAME satellite the roster reports.
        roster = client.get(CONSOLE).json()
        addresses = {
            unary["serverAddress"],
            stream["serverAddress"],
            upload["serverAddress"],
            echo["serverAddress"],
            roster["serverAddress"],
        }
        assert len(addresses) == 1


def test_not_found_and_deadline_are_payloads_not_envelopes(app: FastAPI) -> None:
    with _client(app) as client:
        missing = client.post(CONSOLE, json={"method": "get-post", "slug": "nope"}).json()
        assert client.post(CONSOLE, json={"method": "get-post", "slug": "nope"}).status_code == 200
        assert missing["statusCode"] == "NOT_FOUND"
        assert "not found" in missing["statusDetail"]
        assert missing["messages"] == []

        deadline = client.post(
            CONSOLE, json={"method": "stream-posts", "deadlineMs": 100}
        ).json()
        assert deadline["statusCode"] == "DEADLINE_EXCEEDED"
        assert 0 < len(deadline["messages"]) < 12
        assert "DEADLINE_EXCEEDED" in deadline["reasoning"]


def test_invalid_rounds_earn_the_422_envelope(app: FastAPI) -> None:
    with _client(app) as client:
        for body in (
            {"method": "no-such-method"},
            {"method": "get-post", "deadlineMs": 5},  # below the 50ms floor
            {"method": "count-views", "viewEvents": [{"slug": ""}]},
        ):
            response = client.post(CONSOLE, json=body)
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "validation_failed"


def test_lifespan_shutdown_stops_the_satellite(app: FastAPI) -> None:
    with _client(app) as client:
        assert client.post(CONSOLE, json={"method": "get-post"}).json()["statusCode"] == "OK"
        runtime = app.state.grpc_runtime
        assert runtime.address is not None
    # Exiting the context manager ran the lifespan shutdown.
    assert runtime.address is None


def test_both_endpoints_are_declared_in_openapi(app: FastAPI) -> None:
    with _client(app) as client:
        schema = client.get("/openapi.json").json()
        paths = schema["paths"][CONSOLE]
        roster_ref = paths["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        round_ref = paths["post"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        assert roster_ref.endswith("GrpcConsoleRoster")
        assert round_ref.endswith("GrpcConsoleRound")
