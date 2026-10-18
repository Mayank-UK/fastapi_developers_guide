"""The realtime endpoints over the real wiring: the SSE route + the WS route.

SSE: status, the event-stream headers (cache + proxy + the request id the
pure-ASGI middleware stamps on a streamed body), the frame grammar on the
wire, the limit, the Last-Event-ID replay, and the 422 for a forged id.
WS: the join/broadcast/ping round between two real connections, the error
frames for misuse, the 1008 refusals (bad join facts, unreadable frame),
the 1013 ceilings (room full, slow consumer), backfill on ?since=, and
the roster cleanup after a disconnect.
"""

import contextlib
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from guide.domain.realtime.manager import PER_CONNECTION_QUEUE

TICKER_PATH = "/api/realtime/ticker"
PANEL_TICKER_PATH = "/api/demo/realtime/ticker"
PANEL_CHAT_PATH = "/api/demo/realtime/chat"


def stream_frames(client: TestClient, **params: object) -> tuple[list[str], dict[str, str]]:
    """Consume one bounded stream fully: its text blocks and response headers."""
    with client.stream("GET", TICKER_PATH, params=params) as response:
        assert response.status_code == 200
        headers = {key.lower(): value for key, value in response.headers.items()}
        body = "".join(response.iter_text())
    return [block for block in body.split("\n\n") if block], headers


def tick_payloads(blocks: list[str]) -> list[dict[str, object]]:
    ticks = [block for block in blocks if block.startswith("event: tick")]
    return [json.loads(block.rsplit("data: ", 1)[1]) for block in ticks]


def test_stream_serves_the_event_stream_contract(client: TestClient) -> None:
    blocks, headers = stream_frames(client, limit=2, paceMs=50, keepaliveEvery=0)
    assert headers["content-type"].startswith("text/event-stream")
    assert headers["cache-control"] == "no-cache"
    assert headers["x-accel-buffering"] == "no"
    assert headers["x-request-id"]  # the converted middleware stamps streamed bodies too
    assert blocks[0].startswith("event: ready")
    assert "retry: 3000" in blocks[0]
    assert '"simulated": true' in blocks[0]
    assert len(tick_payloads(blocks)) == 2
    assert blocks[-1].startswith("event: end")
    seqs = [payload["seq"] for payload in tick_payloads(blocks)]
    assert seqs == sorted(seqs)  # ids ascend on the wire


def test_stream_multiline_data_dispatches_as_one_event(client: TestClient) -> None:
    blocks, _headers = stream_frames(client, limit=1, paceMs=50, keepaliveEvery=0)
    assert len(tick_payloads(blocks)) == 1  # one event despite the multi-field payload


def test_stream_honors_last_event_id_replay(client: TestClient) -> None:
    first_blocks, _ = stream_frames(client, limit=3, paceMs=50, keepaliveEvery=0)
    seen_ids = [
        block.split("\nid: ", 1)[1].split("\n", 1)[0]
        for block in first_blocks
        if block.startswith("event: tick")
    ]
    resume_from = seen_ids[0]  # replay everything after the FIRST tick

    replay_blocks, _ = stream_frames_header(client, limit=1, paceMs=50, header_id=resume_from)
    assert replay_blocks[0].startswith("event: ready")
    assert f'"replayed": {len(seen_ids) - 1}' in replay_blocks[0]
    all_tick_ids = [
        block.split("\nid: ", 1)[1].split("\n", 1)[0]
        for block in replay_blocks
        if block.startswith("event: tick")
    ]
    # the replay burst arrives first (exactly the missed ticks), then one NEW live tick
    assert all_tick_ids[: len(seen_ids) - 1] == seen_ids[1:]
    assert all_tick_ids[-1] not in seen_ids


def stream_frames_header(
    client: TestClient, *, limit: int, paceMs: int, header_id: str
) -> tuple[list[str], dict[str, str]]:
    """A bounded stream that reconnects with a Last-Event-ID header."""
    with client.stream(
        "GET", TICKER_PATH, params={"limit": limit, "paceMs": paceMs, "keepaliveEvery": 0},
        headers={"Last-Event-ID": header_id},
    ) as response:
        assert response.status_code == 200
        headers = {key.lower(): value for key, value in response.headers.items()}
        body = "".join(response.iter_text())
    return [block for block in body.split("\n\n") if block], headers


def test_stream_rejects_a_forged_last_event_id(client: TestClient) -> None:
    response = client.get(TICKER_PATH, headers={"Last-Event-ID": "not-a-seq"})
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_failed"
    assert "last-event-id" in body["message"]
    assert response.headers["x-request-id"] == body["requestId"]


def test_stream_keepalives_are_visible_on_the_wire(client: TestClient) -> None:
    blocks, _ = stream_frames(client, limit=4, paceMs=50, keepaliveEvery=2)
    keepalives = [block for block in blocks if block.startswith(":")]
    assert len(keepalives) == 1  # after the 2nd live tick
    assert keepalives == [": keepalive"]


def test_ticker_stats_count_the_traffic(client: TestClient) -> None:
    before = client.get(f"{PANEL_TICKER_PATH}/stats").json()["stats"]
    stream_frames(client, limit=2, paceMs=50, keepaliveEvery=0)
    after = client.get(f"{PANEL_TICKER_PATH}/stats").json()["stats"]
    assert after["ticksSent"] == before["ticksSent"] + 2
    assert after["clientsServed"] == before["clientsServed"] + 1


def chat_url(room: str, **params: str) -> str:
    query = "&".join(f"{key}={value}" for key, value in params.items())
    return f"/api/realtime/chat/{room}?{query}"


def receive_until(client_ws: object, wanted_type: str, limit: int = 20) -> dict[str, object]:
    """Read frames until one of ``wanted_type`` arrives (skipping notes/roster)."""
    for _ in range(limit):
        frame = _receive_json(client_ws)
        if isinstance(frame, dict) and frame.get("type") == wanted_type:
            return frame
    raise AssertionError(f"no {wanted_type} frame within {limit} frames")


def _receive_json(client_ws: object) -> object:
    return client_ws.receive_json()  # type: ignore[attr-defined]


def test_chat_round_between_two_members(client: TestClient) -> None:
    with client.websocket_connect(chat_url("lobby", name="ada")) as ada:
        assert ada.receive_json()["type"] == "joined"
        assert ada.receive_json()["members"] == ["ada"]
        with client.websocket_connect(chat_url("lobby", name="grace")) as grace:
            assert grace.receive_json()["type"] == "joined"
            assert grace.receive_json()["members"] == ["ada", "grace"]
            note = ada.receive_json()
            assert note["type"] == "note" and "grace joined" in note["text"]
            assert ada.receive_json()["members"] == ["ada", "grace"]

            ada.send_json({"type": "chat", "text": "hello from ada"})
            chat = receive_until(grace, "chat")
            assert chat["chat"]["sender"] == "ada"
            assert chat["chat"]["text"] == "hello from ada"

            grace.send_json({"type": "ping"})
            assert grace.receive_json() == {"type": "pong"}


def test_chat_sender_does_not_hear_itself_and_errors_are_frames(client: TestClient) -> None:
    with client.websocket_connect(chat_url("solo", name="ada")) as ada:
        ada.receive_json()  # joined
        ada.receive_json()  # roster
        ada.send_json({"type": "chat", "text": "into the void"})
        ada.send_json({"type": "nonsense"})
        error = ada.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "unknown_type"
        ada.send_json({"type": "chat", "text": "   "})
        assert ada.receive_json()["code"] == "empty_text"
        # the connection SURVIVED both misuses
        ada.send_json({"type": "ping"})
        assert ada.receive_json() == {"type": "pong"}


def test_chat_refuses_invalid_join_facts(client: TestClient) -> None:
    for url in (
        chat_url("Not_A_Room", name="ada"),
        chat_url("lobby", name="two words"),
        chat_url("lobby"),  # no name at all
        chat_url("lobby", name="ada", since="abc"),
    ):
        with pytest.raises(WebSocketDisconnect) as raised:
            with client.websocket_connect(url) as socket:
                socket.receive_json()
        assert raised.value.code == 1008


def test_chat_room_full_closes_1013_with_a_frame_first(client: TestClient) -> None:
    stack = contextlib.ExitStack()
    for index in range(8):  # MAX_ROOM_CONNECTIONS
        socket = stack.enter_context(client.websocket_connect(chat_url("packed", name=f"m{index}")))
        socket.receive_json()
        socket.receive_json()
    with stack:
        with pytest.raises(WebSocketDisconnect) as raised:
            with client.websocket_connect(chat_url("packed", name="ninth")) as ninth:
                error = ninth.receive_json()
                assert error["type"] == "error"
                assert error["code"] == "room_full"
                ninth.receive_json()  # then the close arrives
        assert raised.value.code == 1013


def test_chat_unreadable_frame_closes_1008(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as raised:
        with client.websocket_connect(chat_url("lobby", name="ada")) as ada:
            ada.receive_json()
            ada.receive_json()
            ada.send_text("{not json")
            ada.receive_json()
    assert raised.value.code == 1008


def test_chat_reconnect_backfills_the_gap(client: TestClient) -> None:
    with client.websocket_connect(chat_url("backfill", name="ada")) as ada:
        ada.receive_json()
        ada.receive_json()
        ada.send_json({"type": "chat", "text": "before the drop"})
        with client.websocket_connect(chat_url("backfill", name="grace")) as grace:
            grace.receive_json()  # joined
            grace.receive_json()  # roster
            ada.send_json({"type": "chat", "text": "seen live"})
            seen = receive_until(grace, "chat")
            last_seq = seen["chat"]["seq"]
            ada.send_json({"type": "chat", "text": "missed while away"})
        ada.send_json({"type": "chat", "text": "also missed"})
        with client.websocket_connect(
            chat_url("backfill", name="grace", since=str(last_seq))
        ) as grace:
            assert grace.receive_json()["type"] == "joined"
            assert grace.receive_json()["type"] == "roster"
            backfill = grace.receive_json()
            assert backfill["type"] == "backfill"
            assert backfill["gapped"] is False
            texts = [message["text"] for message in backfill["messages"]]
            assert texts == ["missed while away", "also missed"]


def test_chat_slow_consumer_is_retired_with_1013(client: TestClient) -> None:
    with client.websocket_connect(chat_url("flood", name="talker")) as talker:
        talker.receive_json()
        talker.receive_json()
        # The slow member joins and never reads; PER_CONNECTION_QUEUE is 32.
        with client.websocket_connect(chat_url("flood", name="slow")) as slow:
            slow.receive_json()  # joined (roster/note frames for others, not slow)
            with pytest.raises(WebSocketDisconnect) as raised:
                for index in range(PER_CONNECTION_QUEUE + 2):
                    talker.send_json({"type": "chat", "text": f"flood-{index}"})
                # The sentinel closes the slow socket after its queued frames.
                for _ in range(PER_CONNECTION_QUEUE + 2):
                    slow.receive_json()
            assert raised.value.code == 1013
        # The talker survives and sees the retirement announced.
        talker.send_json({"type": "ping"})
        assert receive_until(talker, "pong") == {"type": "pong"}


def test_chat_disconnect_updates_the_roster_and_the_panel(client: TestClient) -> None:
    with client.websocket_connect(chat_url("roster-check", name="ada")) as ada:
        ada.receive_json()
        ada.receive_json()
        with client.websocket_connect(chat_url("roster-check", name="grace")) as grace:
            grace.receive_json()
            grace.receive_json()
        note = ada.receive_json()
        roster = ada.receive_json()
        assert note["type"] == "note" and "grace joined" in note["text"]
        assert roster["members"] == ["ada", "grace"]
    # after ada leaves too: the panel shows the room gone (no ghost roster)
    for _ in range(10):  # the depart broadcast needs a beat to land
        panel = client.get(PANEL_CHAT_PATH, params={"room": "roster-check"}).json()
        if not panel["rooms"]:
            break
    assert panel["rooms"] == []
    assert panel["stats"]["liveConnections"] == 0


def test_chat_panel_serves_ceilings_and_close_codes(client: TestClient) -> None:
    body = client.get(PANEL_CHAT_PATH).json()
    assert body["policy"]["maxRoomConnections"] == 8
    assert body["policy"]["perConnectionQueue"] == 32
    assert body["policy"]["historyCapacity"] == 50
    codes = {row["code"]: row for row in body["closeCodes"]}
    assert set(codes) == {1000, 1008, 1013}
    assert "reconnect" in codes[1013]["when"]
    assert any("process-local" in note for note in body["honestyNotes"])


def test_ticker_panel_serves_policy_and_tour(client: TestClient) -> None:
    body = client.get(PANEL_TICKER_PATH).json()
    assert body["policy"]["symbols"] == ["FDG", "ASY", "PYC"]
    assert body["policy"]["retryMs"] == 3000
    assert body["policy"]["mediaType"] == "text/event-stream"
    assert any(entry["path"] == TICKER_PATH for entry in body["endpoints"])
    assert any("simulated" in note for note in body["honestyNotes"])


def test_chat_scope_carries_the_request_id(client: TestClient, app: FastAPI) -> None:
    """The converted middleware binds ws scopes: one id per connection."""
    from fastapi import WebSocket

    from guide.core.request_context import current_request_id

    @app.websocket("/api/_ws-id")
    async def ws_id(websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_text(current_request_id())
        await websocket.close()

    with client.websocket_connect("/api/_ws-id", headers={"x-request-id": "ws-trace-42"}) as ws:
        assert ws.receive_text() == "ws-trace-42"
    assert current_request_id() == ""  # reset on disconnect, like HTTP
