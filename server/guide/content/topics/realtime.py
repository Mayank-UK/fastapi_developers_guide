"""Topic 28 — Realtime (SSE + WebSockets; the media-realtime group continues).

Everything before this topic answered requests; this one HOLDS connections.
It opens with the four push models and who holds the connection in each,
builds server-sent events over the streaming machinery topics 09 and 26
already laid (with the ticker demo INLINE as the live lesson — and the
middleware conversion its unbuffered flow forced), takes the event-stream
wire format apart line by line (framing, keepalive comments, Last-Event-ID
resume, proxy buffering), upgrades to WebSockets for the two-way chat room
(demo INLINE: lifecycle, message types, close codes), scales that room
into broadcast with rooms, per-connection queues, and the two ceilings,
and closes with what the client sees when the connection DIES — the
reconnection semantics both protocols need to be honest about. Terminal
companion last: a curl -N tour of the live stream, a real websockets
client for the chat round, and the header checks that prove the streamed
responses still carry their request ids.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="realtime",
    title="Realtime: SSE and WebSockets",
    subtitle=(
        "Push models and who holds the connection, server-sent events over "
        "StreamingResponse, the event-stream wire format and Last-Event-ID "
        "resume, WebSockets with rooms, bounded fanout and ceilings, and the "
        "reconnection semantics that make both protocols honest."
    ),
    group="media-realtime",
    order=28,
    sections=[
        # ── 1. Push models ───────────────────────────────────────────────────
        Section(
            id="push-models",
            title="Push models",
            blocks=[
                TextBlock(
                    kind="text",
                    id="push-pitch",
                    text=(
                        "Every interaction so far had the same shape: the client "
                        "asks, the server answers, the connection is done. That "
                        "request/response grammar is HTTP's genius and its "
                        "blind spot — the server cannot START a conversation. "
                        "Yet half of what makes an app feel alive is exactly "
                        "that: prices move, messages arrive, jobs finish, and "
                        "the user should see it without asking again. Bridging "
                        "that gap is a design decision with exactly one "
                        "variable at its center: WHO HOLDS THE CONNECTION. The "
                        "client can keep asking (polling), the server can "
                        "answer late on purpose (long-polling), the server can "
                        "hold one long response open and keep writing to it "
                        "(server-sent events), or both sides can agree to "
                        "leave a switched-up connection open and talk whenever "
                        "they want (WebSockets). Four models, one axis:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="push-models-list",
                    ordered=False,
                    items=[
                        "Polling — the client holds nothing: it re-asks on a "
                        "timer, so freshness is bounded by the interval and "
                        "cost is N clients × requests-per-interval even when "
                        "nothing changed; trivial to build, terrible at scale.",
                        "Long-polling — the server holds the REQUEST: it "
                        "refuses to answer until data exists (or a timeout), "
                        "the client immediately re-asks; freshness without the "
                        "waste, at the price of a permanently hung request per "
                        "client and reconnect churn.",
                        "Server-sent events (SSE) — the server holds ONE LONG "
                        "RESPONSE: a plain HTTP GET whose ``text/event-stream`` "
                        "body never ends, framed as dispatchable events; "
                        "server→client only, but it is just HTTP — proxies, "
                        "auth, and the browser's EventSource reconnect for free.",
                        "WebSockets — BOTH hold a switched-up CONNECTION: one "
                        "TCP, a thin frame protocol, either side sends anytime; "
                        "full duplex for chat and collaboration, at the price "
                        "of leaving HTTP's semantics behind (no statuses, no "
                        "caching, your own error vocabulary).",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="push-choosing",
                    text=(
                        "Choosing is about directionality and failure honesty. "
                        "If the client only LISTENS — tickers, feeds, logs, "
                        "progress, notifications — SSE is almost always right: "
                        "it rides the machinery you already have (one streaming "
                        "GET, topic 26's backpressure included), survives "
                        "proxies better than people expect, and the browser's "
                        "``EventSource`` gives you auto-reconnect and resume as "
                        "a platform feature rather than code you own. If the "
                        "client TALKS BACK while listening — chat, cursors, "
                        "presence, collaborative editing — you need the "
                        "bidirectional channel, and that means WebSockets and "
                        "the work this topic does in its second half: a message "
                        "protocol, close codes instead of status codes, and "
                        "rooms with ceilings. What you should never do is "
                        "reach for the duplex hammer because it sounds more "
                        "powerful: a websocket that only ever streams one way "
                        "paid the protocol's full price for SSE's feature set, "
                        "and gave back HTTP's caching, tooling, and debuggability "
                        "in the process."
                    ),
                ),
            ],
        ),
        # ── 2. SSE via StreamingResponse ─────────────────────────────────────
        Section(
            id="sse-via-streamingresponse",
            title="SSE via StreamingResponse",
            lead="This section carries the topic's first demo — the live ticker.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="sse-pitch",
                    text=(
                        "Mechanically, an SSE endpoint is nothing new: topic 09 "
                        "streamed NDJSON and topic 26 made backpressure visible "
                        "with paced chunks — both were ``StreamingResponse`` "
                        "over an async generator. SSE is that same shape with "
                        "two decisions changed: the media type becomes "
                        "``text/event-stream`` (which tells the browser and "
                        "every proxy that this body is events, not a document), "
                        "and the generator does not stop — it yields as long as "
                        "the client stays connected. The router's whole job "
                        "stays thin: honor the reconnect header if there is "
                        "one, hand the domain's generator to the response, and "
                        "state the cache and buffering headers that keep the "
                        "stream honest:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="sse-endpoint-quote",
                    language="py",
                    caption="The SSE route: one GET, a never-ending generator, honest headers.",
                    source="server/guide/presentation/routers/realtime.py",
                    snippet=(
                        "    last_event_id = _parse_last_event_id(last_event_id_header)\n"
                        "    frames = stream_ticker_frames(\n"
                        "        service,\n"
                        "        last_event_id=last_event_id,\n"
                        "        limit=limit,\n"
                        "        pace_seconds=pace_ms / 1000,\n"
                        "        keepalive_every=keepalive_every,\n"
                        "        retry_ms=DEFAULT_RETRY_MS,\n"
                        "        is_disconnected=request.is_disconnected,\n"
                        "    )\n"
                        "    return StreamingResponse(frames, media_type=SSE_MEDIA_TYPE, headers=STREAM_HEADERS)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="sse-headers-read",
                    text=(
                        "Both headers are load-bearing. ``Cache-Control: "
                        "no-cache`` because a cached event stream is a dead "
                        "one — an intermediary that serves the first second of "
                        "ticks forever has broken the feature while looking "
                        "like an optimization. ``X-Accel-Buffering: no`` is "
                        "the nginx-specific spell that tells the reverse proxy "
                        "to forward each chunk as it arrives instead of "
                        "spooling the body (the generic cure is switching "
                        "``proxy_buffering`` off for the location). The "
                        "disconnect probe rides along as a callable — the same "
                        "dependency-inversion the files topic used for "
                        "``file.read`` — so the domain's loop can poll "
                        "``request.is_disconnected()`` between ticks without "
                        "the domain ever meeting a ``Request``. And ``limit`` "
                        "bounds the LIVE ticks so tests and terminal tours get "
                        "finite streams; production streams simply leave it at "
                        "zero and run until the client leaves."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="sse-generator-pitch",
                    text=(
                        "The generator itself is the domain's: a ready frame "
                        "with the reconnect hint, the replay burst for a "
                        "resuming client, then the paced live loop — mint one "
                        "event into the shared ring, frame it, yield it, sleep "
                        "(the pacing is a labeled simulation over a "
                        "deterministic price walk, and the sleeper is injected "
                        "so tests run instantly):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="sse-generator-quote",
                    language="py",
                    caption="The stream body: ready frame, replay burst, then the paced live loop.",
                    source="server/guide/domain/realtime/ticker.py",
                    snippet=(
                        "    service.open_client()\n"
                        "    replay = service.replay_after(last_event_id) if last_event_id is not None else []\n"
                        "    yield encode_sse_event(\n"
                        "        json.dumps(\n"
                        "            {\n"
                        "                \"replayed\": len(replay),\n"
                        "                \"resumeWindow\": service.log.capacity,\n"
                        "                \"symbols\": list(TICKER_SYMBOLS),\n"
                        "                \"paceMs\": round(pace_seconds * 1000),\n"
                        "                \"simulated\": True,\n"
                        "            }\n"
                        "        ),\n"
                        "        event=READY_EVENT,\n"
                        "        retry_ms=retry_ms,\n"
                        "    )\n"
                        "    for event in replay:\n"
                        "        yield _frame_event(event)\n"
                        "\n"
                        "    live_ticks = 0\n"
                        "    while limit == 0 or live_ticks < limit:\n"
                        "        if keepalive_every and live_ticks and live_ticks % keepalive_every == 0:\n"
                        "            yield encode_keepalive()\n"
                        "        await sleeper(pace_seconds)\n"
                        "        if await is_disconnected():\n"
                        "            return  # the client is gone: stop without an end frame\n"
                        "        event = await service.next_event()\n"
                        "        live_ticks += 1\n"
                        "        yield _frame_event(event)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="sse-middleware-pitch",
                    text=(
                        "One more thing had to change before a single tick "
                        "could flow, and it is this topic's infrastructure "
                        "story: the request-id middleware. Topic 08 recorded "
                        "the caveat on the source file itself — "
                        "``BaseHTTPMiddleware`` bridges its friendly "
                        "``Request``/``Response`` objects through a "
                        "per-request task, which re-assembles the response "
                        "into a buffered view; an event stream wrapped that "
                        "way arrives buffered or, under some servers, not at "
                        "all until the stream ends. The conversion is done, "
                        "and the new response side is four lines at the wire "
                        "level — stamp the header on the one message that "
                        "carries headers, touch nothing else:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="sse-middleware-quote",
                    language="py",
                    caption="The converted layer: the start message is stamped; every body chunk passes untouched.",
                    source="server/guide/core/request_context.py",
                    snippet=(
                        "        async def send_with_request_id(message: Message) -> None:\n"
                        "            # The response side at the wire level: headers ride exactly one\n"
                        "            # message (http.response.start) — stamp it there and let every\n"
                        "            # body chunk flow past untouched, which is what keeps streaming\n"
                        "            # responses (topic 28's SSE) unbuffered through this layer.\n"
                        "            if message[\"type\"] == \"http.response.start\":\n"
                        "                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id\n"
                        "            await send(message)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="sse-middleware-read",
                    text=(
                        "Behavior is identical everywhere the old contract was "
                        "pinned — inbound header honored and capped, the "
                        "contextvar bound and reset, ``x-request-id`` on every "
                        "response including error envelopes (the tests never "
                        "moved) — and it grows one honest capability: the same "
                        "``__call__`` now also binds the id for WEBSOCKET "
                        "scopes, which ``dispatch`` never saw, so chat-handler "
                        "log lines correlate like HTTP ones do (a websocket has "
                        "no response headers to stamp; there the id serves "
                        "logging only). The demo panel's firehose stats make "
                        "the live side observable while you stream — try it:"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="realtime:ticker",
                    title="The realtime ticker",
                    description=(
                        "GET /api/demo/realtime/ticker serves the panel (policy: "
                        "symbols FDG/ASY/PYC, 750ms default pace — SIMULATED and "
                        "labeled, retry hint 3000ms, keepalive every 4th wait, "
                        "replay ring of 120; the endpoint tour; honesty notes) "
                        "and GET /api/demo/realtime/ticker/stats is the firehose "
                        "odometer (ticks sent, clients served, resume replays, "
                        "ring bounds). The LIVE stream is the centerpiece: "
                        "connect with the browser's EventSource (the panel's "
                        "connect button), watch ticks arrive in real time with "
                        "their ids, disconnect, reconnect and watch the "
                        "Last-Event-ID replay land — readyState and the last "
                        "event id are on the panel the whole time. The stream "
                        "runs at GET /api/realtime/ticker (limit=0 streams "
                        "until you leave; paceMs, keepaliveEvery are query "
                        "parameters; Last-Event-ID header honored)."
                    ),
                ),
            ],
        ),
        # ── 3. Event stream mechanics ───────────────────────────────────────
        Section(
            id="event-stream-mechanics",
            title="Event stream mechanics",
            blocks=[
                TextBlock(
                    kind="text",
                    id="mech-pitch",
                    text=(
                        "The event-stream format is a few rules about lines, "
                        "and every one of them is worth knowing cold because "
                        "they are the difference between a stream that "
                        "dispatches and one that buffers forever. An EVENT is "
                        "a block of ``field: value`` lines terminated by ONE "
                        "blank line — and the blank line is not decoration, it "
                        "is the dispatch signal: everything before it is "
                        "buffered, the blank line makes the client fire the "
                        "event. Four fields exist: ``event`` (a type name, so "
                        "one stream can carry several kinds — this ticker uses "
                        "``ready``, ``tick``, ``end``), ``id`` (an opaque "
                        "cursor the client remembers for reconnection — this "
                        "server frames the event's seq), ``retry`` "
                        "(milliseconds; the client's reconnect delay after a "
                        "drop), and ``data`` (the payload). ``data`` may span "
                        "multiple lines — each line repeats the ``data:`` "
                        "prefix and the client joins them with newlines into "
                        "ONE event, which is exactly how you stream a "
                        "multi-line JSON document without breaking framing. "
                        "The serializer is pure and total:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="mech-serializer-quote",
                    language="py",
                    caption="Framing one event: field lines, one data line per newline, the blank line that dispatches.",
                    source="server/guide/domain/realtime/frames.py",
                    snippet=(
                        "    lines: list[str] = []\n"
                        "    if event is not None:\n"
                        "        lines.append(f\"{FIELD_EVENT}: {_single_line_value(event)}\")\n"
                        "    if id is not None:\n"
                        "        lines.append(f\"{FIELD_ID}: {_single_line_value(id)}\")\n"
                        "    if retry_ms is not None:\n"
                        "        lines.append(f\"{FIELD_RETRY}: {retry_ms}\")\n"
                        "    for piece in _single_line_value(data).split(\"\\n\"):\n"
                        "        lines.append(f\"data: {piece}\")\n"
                        "    return \"\\n\".join(lines) + \"\\n\\n\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="mech-keepalive-read",
                    text=(
                        "Two more grammar facts pay rent in production. A line "
                        "starting with a colon is a COMMENT — clients ignore "
                        "it completely, which is precisely why it is the "
                        "keepalive: an idle stream (no events to send, waiting "
                        "on the world) sends ``: keepalive`` every so often so "
                        "every intermediary between you and the client sees "
                        "traffic and keeps the connection open. The keepalive "
                        "is invisible to ``EventSource`` handlers on purpose — "
                        "it talks to the infrastructure, not the application. "
                        "The other fact is line endings: the grammar says "
                        "clients MUST accept CR, LF, or CRLF as line "
                        "terminators, but a server should emit plain LF; this "
                        "serializer normalizes any CRLF in payload data on "
                        "the way in so a hostile ``\\r`` cannot smuggle a "
                        "frame boundary inside a data line."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="mech-replay-pitch",
                    text=(
                        "Reconnection is where the format earns its keep. When "
                        "the connection drops, ``EventSource`` reconnects "
                        "AUTOMATICALLY (after ``retry`` milliseconds if the "
                        "server said so, else a browser-chosen backoff) and — "
                        "the crucial part — sends the last dispatched id back "
                        "as the ``Last-Event-ID`` request header. The server's "
                        "whole obligation is to answer that header honestly, "
                        "and honesty has a hard edge: you can only replay "
                        "what you still retain. This server keeps a bounded "
                        "ring per stream; the replay reads it with the "
                        "gap-check that makes the edge explicit:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="mech-replay-quote",
                    language="py",
                    caption="Gap-aware replay: contiguous run, or nothing — a hole is never papered over.",
                    source="server/guide/domain/realtime/log.py",
                    snippet=(
                        "        if not self._events:\n"
                        "            return []\n"
                        "        oldest_seq = self._events[0][0]\n"
                        "        newest_seq = self._events[-1][0]\n"
                        "        if last_seq >= newest_seq:\n"
                        "            return []\n"
                        "        if last_seq + 1 < oldest_seq:\n"
                        "            return []  # the gap case: retention does not reach the client's position\n"
                        "        return [event for seq, event in self._events if seq > last_seq]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="mech-proxy-read",
                    text=(
                        "The last mechanics are the ones that live between you "
                        "and the client. PROXIES buffer by default — nginx "
                        "spools the response to serve it efficiently, which is "
                        "death to a stream; the cure is the "
                        "``X-Accel-Buffering: no`` header this endpoint sends "
                        "(or ``proxy_buffering off`` on the location), and "
                        "after nginx the same story repeats for every layer "
                        "that might coalesce writes — the response compression "
                        "middlewares of the world buffer too, which is why "
                        "event-stream responses are excluded from gzip in "
                        "every serious deployment. HTTP/2 helps more than it "
                        "hurts (no head-of-line blocking across multiplexed "
                        "streams, so one long SSE response no longer occupies "
                        "the browser's connection budget) but changes nothing "
                        "here: the framing, the keepalive, and the replay "
                        "semantics are identical over both versions. And when "
                        "the stream must cross a browser's connection LIMIT — "
                        "six streams per origin over HTTP/1.1, a real ceiling "
                        "for multi-tab apps — that is the strongest argument "
                        "for consolidating feeds: one event stream carrying "
                        "typed events (the ``event:`` field exists for "
                        "exactly this) beats six parallel ones."
                    ),
                ),
            ],
        ),
        # ── 4. WebSockets ────────────────────────────────────────────────────
        Section(
            id="websockets",
            title="WebSockets",
            lead="This section carries the topic's second demo — the live chat room.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="ws-pitch",
                    text=(
                        "When the client must talk while listening, the "
                        "upgrade happens: an HTTP GET asks to switch protocols "
                        "(``Upgrade: websocket``), the server agrees with "
                        "``101 Switching Protocols``, and from that byte "
                        "forward the connection is NOT HTTP anymore — it is a "
                        "thin frame protocol where either side sends whenever "
                        "it wants. In FastAPI the surface is a decorator on "
                        "the same router: ``@router.websocket(\"/chat/{room}\")`` "
                        "over an ``async def`` taking the ``WebSocket``. The "
                        "lifecycle is explicit and short: ``accept()`` the "
                        "handshake, ``receive``/``send`` frames, ``close(code, "
                        "reason)`` — and the receive side raises "
                        "``WebSocketDisconnect`` the moment the client "
                        "vanishes, which is your cleanup signal. One "
                        "dependency note before anything else: uvicorn only "
                        "SPEAKS websockets if the ``websockets`` library is "
                        "installed — this repo gets it from "
                        "``uvicorn[standard]``, and without it every "
                        "connection dies at the handshake with a 403 the app "
                        "code never sees."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ws-protocol-pitch",
                    text=(
                        "The protocol design is yours to write, and this "
                        "room's is deliberately tiny and total. Clients send "
                        "``{\"type\": \"chat\", \"text\": …}`` and "
                        "``{\"type\": \"ping\"}``; the server answers with "
                        "``joined`` (your identity and the room's state), "
                        "``roster`` (who is here), ``backfill`` (what you "
                        "missed, on a reconnect), ``chat`` (a line, with seq "
                        "and sender), ``note`` (system lines — joins, "
                        "retirements), ``pong``, and ``error`` (a verdict on "
                        "a bad frame). The failure vocabulary is where "
                        "websockets force the divergence this guide must "
                        "teach honestly: there is no status code, no envelope, "
                        "no 422 after the handshake — a websocket that wants "
                        "to say \"bad input\" either sends an ``error`` FRAME "
                        "and keeps talking, or CLOSES with a code:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="ws-closecodes-quote",
                    language="py",
                    caption="The room's close-code vocabulary — the ws counterpart of the HTTP error taxonomy.",
                    source="server/guide/domain/realtime/chat.py",
                    snippet=(
                        "CLOSE_OK: Final[tuple[int, str]] = (1000, \"left the room\")\n"
                        "CLOSE_PROTOCOL: Final[tuple[int, str]] = (1008, \"unreadable frame or invalid join — closing\")\n"
                        "CLOSE_ROOM_FULL: Final[tuple[int, str]] = (1013, \"room at capacity — try again later\")\n"
                        "CLOSE_SLOW_CONSUMER: Final[tuple[int, str]] = (\n"
                        "    1013,\n"
                        "    \"fell a full queue behind — reconnect with ?since=<seq>\",\n"
                        ")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ws-closecodes-read",
                    text=(
                        "The choices, on record: ``1000`` is the normal leave "
                        "(the client's own disconnect); ``1008`` says the "
                        "stream became untrustworthy — a frame that is not "
                        "JSON, or a join with an invalid room or name, "
                        "refused before the handshake is even accepted; "
                        "``1013`` means TRY AGAIN LATER and is the code for "
                        "both ceilings (room full at join, queue overflow in "
                        "flight) — conditions where reconnecting soon is the "
                        "correct client behavior and nobody did anything "
                        "wrong. One rendering fact worth knowing before you "
                        "meet it in production: a close issued BEFORE the "
                        "handshake is accepted reaches a real client as a "
                        "rejected upgrade — uvicorn answers HTTP 403 — so "
                        "the 1008 itself is observable to in-process test "
                        "clients (starlette's TestClient surfaces the code) "
                        "while browsers see a plain refused connection; "
                        "that is the honest trade of refusing early rather "
                        "than accepting a join you already know is invalid. "
                        "That reading — close codes as a small error "
                        "TAXONOMY for connections, error frames for messages "
                        "— is the ws-side mirror of the one-envelope "
                        "discipline the HTTP side has followed since topic "
                        "04, and the two vocabularies do not mix: this repo "
                        "never fakes a status code inside a frame."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ws-handler-pitch",
                    text=(
                        "The handler is the one router in this app that "
                        "legitimately holds a loop — the socket IS the "
                        "transport. Everything decidable lives in the domain "
                        "service; the handler accepts, joins (translating the "
                        "ceiling verdict into its close code), sends the "
                        "entry frames, and then runs two directions at once: "
                        "a forwarding task that drains the member's queue to "
                        "the socket, and a receive loop that validates client "
                        "frames — with a ``finally`` that always departs the "
                        "member, so the roster never leaks a ghost:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="ws-handler-quote",
                    language="py",
                    caption="Join + ceiling verdict + entry frames: the room's front door.",
                    source="server/guide/presentation/routers/realtime.py",
                    snippet=(
                        "    await websocket.accept()\n"
                        "    try:\n"
                        "        outcome = await service.join(room, name, since_seq)\n"
                        "    except RoomFullError:\n"
                        "        # The ceiling verdict: a documented error frame, then the 1013 close\n"
                        "        # (browsers see the code only after accept — which is why accept came\n"
                        "        # first).\n"
                        "        await websocket.send_json(\n"
                        "            {\"type\": \"error\", \"code\": \"room_full\", \"message\": CLOSE_ROOM_FULL[1]}\n"
                        "        )\n"
                        "        await websocket.close(code=CLOSE_ROOM_FULL[0], reason=CLOSE_ROOM_FULL[1])\n"
                        "        return"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="ws-forward-quote",
                    language="py",
                    caption="The forwarding loop: the member's ONLY sender — one strict frame order.",
                    source="server/guide/presentation/routers/realtime.py",
                    snippet=(
                        "    try:\n"
                        "        while True:\n"
                        "            item = await connection.queue.get()\n"
                        "            if item is None:\n"
                        "                await websocket.close(\n"
                        "                    code=CLOSE_SLOW_CONSUMER[0], reason=CLOSE_SLOW_CONSUMER[1]\n"
                        "                )\n"
                        "                return\n"
                        "            await websocket.send_json(item)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ws-ordering-read",
                    text=(
                        "The forwarding task exists for a reason worth stating "
                        "plainly: ONE sender per socket. If the receive loop "
                        "answered pongs directly while room traffic flowed "
                        "through a queue, two tasks would interleave writes "
                        "and a client could observe a pong BEFORE the chat "
                        "line that preceded its ping — a small lie that "
                        "corrodes trust in the stream. So every server-origin "
                        "frame after the entry sequence rides the member's "
                        "queue, replies included, and the socket has one "
                        "strict order. Try the room live — two browser tabs "
                        "are the best demo it has:"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="realtime:chat",
                    title="The chat room",
                    description=(
                        "GET /api/demo/realtime/chat serves the panel: the "
                        "rooms that exist RIGHT NOW with rosters and retained "
                        "history, the recent transcript, the ceiling facts (8 "
                        "members per room, 32-deep per-connection queues, "
                        "50-message backfill window), the documented close-code "
                        "table, and the stats (messages sent, slow members "
                        "retired, live connections). The LIVE room is the "
                        "centerpiece: open the WS at /api/realtime/chat/"
                        "{room}?name=… with the browser's WebSocket API (the "
                        "panel's join button), watch the roster update as "
                        "tabs join and leave, send lines and watch them "
                        "broadcast, ping for a pong, reconnect with ?since= "
                        "and watch the backfill land, and open a second tab "
                        "to see true broadcast (senders do not receive their "
                        "own lines)."
                    ),
                ),
            ],
        ),
        # ── 5. Broadcast, rooms, and the ceiling ─────────────────────────────
        Section(
            id="broadcast-rooms-and-the-ceiling",
            title="Broadcast, rooms, and the ceiling",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rooms-pitch",
                    text=(
                        "One connection was plumbing; a ROOM is a system. The "
                        "in-process connection manager this topic builds is "
                        "four decisions in a dictionary: rooms map to members "
                        "(a room exists exactly while it has members — an "
                        "empty room is deleted, never leaked); every member "
                        "holds its OWN bounded ``asyncio.Queue``; fanout is "
                        "``put_nowait`` over the room, which means senders "
                        "NEVER block on slow receivers — the queue is where "
                        "backpressure gets decided, and it has already decided "
                        "it; and the two ceilings are enforced at their exact "
                        "seams. The fanout loop, whole:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rooms-broadcast-quote",
                    language="py",
                    caption="Fanout: non-blocking puts, and the fallen-behind member retired on the spot.",
                    source="server/guide/domain/realtime/manager.py",
                    snippet=(
                        "        retired: list[str] = []\n"
                        "        for member in tuple(self._rooms.get(room, {}).values()):\n"
                        "            if member.id == exclude_id:\n"
                        "                continue\n"
                        "            try:\n"
                        "                member.queue.put_nowait(message)\n"
                        "            except asyncio.QueueFull:\n"
                        "                self.leave(member)\n"
                        "                self._retire(member)\n"
                        "                retired.append(member.name)\n"
                        "        return retired"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rooms-slow-read",
                    text=(
                        "Read the ``QueueFull`` arm as policy, not error "
                        "handling: a member whose 32-deep queue is full has "
                        "ignored a full queue-depth of chat — it is not "
                        "catching up, it is gone-in-spirit, and the honest "
                        "move is to stop pretending. Retirement is three "
                        "steps with one meaning: leave the roster immediately "
                        "(every later broadcast already excludes it — truth "
                        "for the room), free one queue slot and push the "
                        "retire sentinel (its forwarding loop unblocks, "
                        "closes the socket with 1013, and says so), and "
                        "return the NAME so the caller announces the "
                        "departure. The room then broadcasts a note — "
                        "``grace fell behind and was retired`` — and the "
                        "updated roster, because a ceiling that fires "
                        "silently is a ceiling nobody learns from."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rooms-join-pitch",
                    text=(
                        "The OTHER ceiling guards the join, and its honesty "
                        "is concurrency: two members racing for the last slot "
                        "must not both win. The lock makes the check-and-take "
                        "atomic — this is the same single-flight discipline "
                        "topic 21 used for cache misses, applied to admission:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rooms-join-quote",
                    language="py",
                    caption="Atomic admission: the ceiling check and the take share one lock.",
                    source="server/guide/domain/realtime/manager.py",
                    snippet=(
                        "        async with self._join_lock:\n"
                        "            members = self._rooms.setdefault(room, {})\n"
                        "            if len(members) >= self._max_room_connections:\n"
                        "                raise RoomFullError(room, self._max_room_connections)\n"
                        "            connection = ManagedConnection(\n"
                        "                id=uuid4().hex[:8], room=room, name=name, queue_size=self._queue_size\n"
                        "            )\n"
                        "            members[connection.id] = connection\n"
                        "            return connection"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rooms-scale-read",
                    text=(
                        "Two scope notes keep the design honest about what it "
                        "is. This manager is IN-PROCESS: one uvicorn worker "
                        "means one manager means one truth — but the day a "
                        "second worker joins, member A on worker one and "
                        "member B on worker two share a room the dictionary "
                        "cannot see, and the fix is not more dictionaries: it "
                        "is the pub/sub seam topic 22 already taught (Redis "
                        "streams or channels between workers, each worker "
                        "fanning out to its LOCAL members — the manager's "
                        "interface is deliberately the shape that wraps). And "
                        "the ceilings are POLICY, not physics: eight members "
                        "and a 32-deep queue are demo-scale numbers chosen so "
                        "the failure modes are reachable from a browser; a "
                        "production room sizes them from the message rate and "
                        "the worst tolerable lag (queue depth ÷ messages per "
                        "second is exactly how far behind a member may fall), "
                        "and puts the numbers where the panel puts them — on "
                        "the page, not in a config file nobody reads."
                    ),
                ),
            ],
        ),
        # ── 6. Reconnection semantics ────────────────────────────────────────
        Section(
            id="reconnection-semantics",
            title="Reconnection semantics",
            blocks=[
                TextBlock(
                    kind="text",
                    id="recon-pitch",
                    text=(
                        "Every realtime connection dies — laptops sleep, "
                        "wifi drops, proxies time out idle streams, deploys "
                        "restart servers. The design question is never "
                        " WHETHER the connection drops but what both sides do "
                        "about it, and the answer splits exactly along the "
                        "protocol boundary. For SSE, the client side is "
                        "already written: ``EventSource`` reconnects "
                        "automatically, honors the server's ``retry`` hint, "
                        "and carries the last dispatched ``id`` back as "
                        "``Last-Event-ID`` — the server's only job is to make "
                        "the id MEAN something durable (this ticker's ids are "
                        "seqs in a shared ring) and to answer the header "
                        "honestly, which section three's gap-check already "
                        "covered: contiguous replay when the ring reaches "
                        "back, a fresh start when it does not, never a hole."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="recon-ws-pitch",
                    text=(
                        "WebSockets have no such free layer — the browser "
                        "fires ``close`` and shrugs — so reconnection is "
                        "APPLICATION protocol, written down and versioned "
                        "with the rest of it. The chat room's version: every "
                        "message carries its ``seq``; a client that reconnects "
                        "presents the last seq it saw as ``?since=``; the "
                        "server answers with the backfill window and one "
                        "honesty flag:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="recon-backfill-quote",
                    language="py",
                    caption="The backfill window: contiguous replay, current no-op, or the tail marked gapped.",
                    source="server/guide/domain/realtime/chat.py",
                    snippet=(
                        "        if since is None:\n"
                        "            return history.tail(self._scrollback), False\n"
                        "        replay = history.events_after(since)\n"
                        "        if replay:\n"
                        "            return replay, False\n"
                        "        if (history.newest_seq or 0) <= since:\n"
                        "            return [], False  # already current: nothing missed, nothing to send\n"
                        "        tail = history.tail(self._history_capacity)\n"
                        "        return tail, True  # the ring cannot reach back to `since` — best effort"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="recon-gap-read",
                    text=(
                        "The ``gapped`` flag is the whole lesson in one "
                        "boolean. A reconnecting client lives in one of three "
                        "worlds: it missed nothing (the server says so — "
                        "empty backfill, no drama); it missed a window the "
                        "server still has (contiguous replay, the gap "
                        "closes); or it missed MORE than the ring retains — "
                        "and here the dishonest options are tempting (replay "
                        "a hole and let the client believe it saw everything; "
                        "refuse and hard-reset) and the honest one is "
                        "unglamorous: serve the recent tail, FLAG it as "
                        "gapped, and let the client decide — a chat UI might "
                        "render a ``— messages lost in reconnection —`` "
                        "divider, which is exactly what serious chat products "
                        "do. What the client sees during the gap itself is "
                        "the third half of the contract, stated plainly: "
                        "NOTHING — no bytes flow on a dead connection, and "
                        "the only mitigations are keepalives that make death "
                        "DETECTABLE (idle streams should die loudly in "
                        "seconds, not silently in hours) and retry backoff "
                        "that keeps a thundering herd of reconnecting clients "
                        "from becoming its own outage. SSE buys you both from "
                        "the platform; over websockets you own them, and the "
                        "room's ``ping``/``pong`` exists so a client can "
                        "measure liveness on ITS schedule too."
                    ),
                ),
            ],
        ),
        # ── 7. Terminal companion ────────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole topic, from a shell — a live stream, a replay, a real chat round.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Six stops: the ticker watched with ``curl -N`` as "
                        "ticks arrive unbuffered (each one timestamped by the "
                        "reading loop, so the pacing is visible in the "
                        "terminal itself), the stream's headers — the "
                        "middleware-conversion proof that ``x-request-id`` "
                        "rides a streamed response — a Last-Event-ID replay "
                        "round, a real ``websockets`` client that joins the "
                        "chat room, talks, and reconnects with backfill, the "
                        "firehose stats after all that traffic, and the chat "
                        "panel's ceiling facts. The stack is up; every "
                        "command answers from the real substrate this topic "
                        "built."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-stream",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the live stream: watch ticks arrive one per pace interval\n"
                        "curl -sN 'localhost:8000/api/realtime/ticker?limit=4&paceMs=400' \\\n"
                        "  | while read -r line; do echo \"t=$(date +%S.%N | cut -c1-9)  $line\"; done"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-headers",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the middleware proof: a STREAMED response still carries the id\n"
                        "curl -sD - -o /dev/null -N 'localhost:8000/api/realtime/ticker?limit=1&paceMs=50' \\\n"
                        "  | grep -iE 'HTTP/|x-request-id|content-type|cache-control|x-accel-buffering'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-replay",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the replay round: remember an id, reconnect, watch it resume\n"
                        "MID=$(curl -sN 'localhost:8000/api/realtime/ticker?limit=2&paceMs=50' \\\n"
                        "  | grep -m1 '^id:' | cut -d' ' -f2)\n"
                        "echo \"reconnecting from Last-Event-ID: $MID\"\n"
                        "curl -sN -H \"Last-Event-ID: $MID\" 'localhost:8000/api/realtime/ticker?limit=1&paceMs=50' \\\n"
                        "  | head -6   # ready frame reports replayed: 1 — the missed tick, re-sent"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-chat",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the chat round: join, scrollback, live broadcast, reconnect backfill\n"
                        "# (run where uv + websockets live: the dev container; the server is reachable\n"
                        "#  as the compose service name from there)\n"
                        "docker exec -i fastapi_developers_guide_dev bash -lc \\\n"
                        "  'cd /workspaces/fastapi_developers_guide/server && uv run python' <<'EOF'\n"
                        "import asyncio, json, websockets\n"
                        "\n"
                        "BASE = \"ws://server:8000/api/realtime/chat/terminal-tour\"\n"
                        "\n"
                        "async def main() -> None:\n"
                        "    async with websockets.connect(f\"{BASE}?name=ada\") as ada:\n"
                        "        print(\"ada joined:\", json.loads(await ada.recv())[\"type\"])\n"
                        "        await ada.recv()  # roster\n"
                        "        await ada.send(json.dumps({\"type\": \"chat\", \"text\": \"before grace arrived\"}))\n"
                        "        async with websockets.connect(f\"{BASE}?name=grace\") as grace:\n"
                        "            json.loads(await grace.recv())  # joined\n"
                        "            json.loads(await grace.recv())  # roster\n"
                        "            scroll = json.loads(await grace.recv())  # scrollback on a fresh join\n"
                        "            print(\"grace scrollback:\", [m[\"text\"] for m in scroll[\"messages\"]])\n"
                        "            await ada.recv(); await ada.recv()  # note + roster for grace joining\n"
                        "            await ada.send(json.dumps({\"type\": \"chat\", \"text\": \"live line\"}))\n"
                        "            chat = json.loads(await grace.recv())\n"
                        "            print(\"grace saw live:\", chat[\"chat\"][\"sender\"], \"->\", chat[\"chat\"][\"text\"])\n"
                        "            last = chat[\"chat\"][\"seq\"]\n"
                        "        # grace is gone; ada keeps talking; grace reconnects with ?since\n"
                        "        await ada.send(json.dumps({\"type\": \"chat\", \"text\": \"sent while grace was away\"}))\n"
                        "        async with websockets.connect(f\"{BASE}?name=grace&since={last}\") as grace:\n"
                        "            json.loads(await grace.recv())  # joined\n"
                        "            json.loads(await grace.recv())  # roster\n"
                        "            frame = json.loads(await grace.recv())  # the backfill window\n"
                        "            print(f\"grace backfilled {len(frame['messages'])} gapped={frame['gapped']}:\",\n"
                        "                  [m[\"text\"] for m in frame[\"messages\"]])\n"
                        "\n"
                        "asyncio.run(main())\n"
                        "EOF"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-stats",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the firehose after all that traffic: ticks, clients, replays\n"
                        "curl -s localhost:8000/api/demo/realtime/ticker/stats | python3 -m json.tool\n"
                        "# stop 6 — the room's ceiling facts and close-code table\n"
                        "curl -s 'localhost:8000/api/demo/realtime/chat?room=terminal-tour' \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"ceilings:\", b[\"policy\"][\"maxRoomConnections\"], \"members/room ·\", \\\n"
                        "b[\"policy\"][\"perConnectionQueue\"], \"deep queues ·\", \\\n"
                        "b[\"policy\"][\"historyCapacity\"], \"backfill window\"); \\\n"
                        "[print(\" close\", c[\"code\"], \"—\", c[\"when\"]) for c in b[\"closeCodes\"]]'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stops 1–3 are the SSE story end to end: ticks you can "
                        "watch arrive, the request id stamped on a body that "
                        "never ends (the pure-ASGI conversion's whole point), "
                        "and a reconnect that picks up exactly where the id "
                        "said it left off. Stop 4 is the websocket story: two "
                        "real clients, a broadcast one of them never sees "
                        "echoed, a disconnect, and a reconnect whose backfill "
                        "carries the missed line under an honest gapped flag. "
                        "Stops 5–6 read the odometers. That closes the "
                        "media-realtime pair's second half — one topic left "
                        "in the group: background jobs (29), where work too "
                        "slow for a request goes to wait its turn."
                    ),
                ),
            ],
        ),
    ],
)
