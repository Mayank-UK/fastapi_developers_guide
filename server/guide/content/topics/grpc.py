"""Topic 15 — gRPC (fifth and final topic of the APIs group).

The contract comes first: a .proto file compiles into typed messages and
a typed client, the server implements a generated base class, and the
pair speaks protobuf frames over HTTP/2 — status codes and deadlines as
first-class citizens. This topic teaches the contract file (this repo's
REAL guide.proto, compiled and committed), the four stream kinds through
one PostService over the posts substrate, serving with grpcio's asyncio
API, stubs and channels — with the live demo ``api:grpc-console``
INLINE, performing real calls against a real in-process server — status
propagation and deadline semantics proven mid-stream, the codegen
pipeline and its lint/typing gates, and the terminal companion last:
a curl tour driving the console endpoint, honestly framed as this
repo's curl-friendly face over a protocol that is not curl-native.

Every code block quotes a real repo file (the snippet ratchet verifies
it): the .proto contract, the servicer, the runtime that hosts the
satellite, the console adapter, the demo router, the integration test,
and the pyproject gates that keep generated code honest.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="grpc",
    title="gRPC",
    subtitle=(
        "The contract compiles — protobuf messages, four stream kinds, "
        "status codes and deadlines as first-class citizens."
    ),
    group="apis",
    order=15,
    sections=[
        # ── 1. What gRPC is ────────────────────────────────────────────────
        Section(
            id="what-grpc-is",
            title="What gRPC is",
            blocks=[
                TextBlock(
                    kind="text",
                    id="grpc-pitch",
                    text=(
                        "Topics 11 through 14 built the API surface one "
                        "conversation at a time: REST named resources and "
                        "leaned on HTTP's vocabulary, GraphQL let the client "
                        "shape the answer, webhooks reversed the call. gRPC "
                        "starts from a different premise — that the most "
                        "valuable thing an API can ship is a CONTRACT BOTH "
                        "SIDES CAN COMPILE. You write a .proto file that "
                        "names services, methods, and the message types that "
                        "flow in and out; a compiler turns it into typed "
                        "classes for the server to implement and a typed "
                        "client for callers to import. The wire format is "
                        "protobuf — compact binary field records — and the "
                        "transport is HTTP/2, which is what lets one "
                        "long-lived connection carry many concurrent calls "
                        "and streams."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="grpc-where-it-wins",
                    text=(
                        "That trade buys very specific things. The contract "
                        "is checked at build time in every language with a "
                        "protobuf toolchain, so a renamed field is a compile "
                        "error in the caller, not a 3 a.m. production null. "
                        "Messages serialize to a few bytes where JSON "
                        "spells out every key name. The four streaming "
                        "shapes (section 3) come built in, where REST needs "
                        "SSE (topic 28 will) and GraphQL offers "
                        "subscriptions as an extension. And every call "
                        "carries a deadline and a status code from a shared "
                        "vocabulary — machinery topic 14 had to bolt onto "
                        "webhooks by hand is native here. The costs are just "
                        "as real:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="grpc-costs",
                    ordered=False,
                    items=[
                        "Binary opacity — you cannot read a protobuf frame "
                        "by eye or curl one by hand; debugging lives behind "
                        "tooling (this topic's console is that tooling).",
                        "Contract ceremony — a compiler step, generated "
                        "code, and a regeneration discipline JSON never "
                        "demanded (section 7 owns exactly this).",
                        "Browser exclusion — browsers do not speak the gRPC "
                        "wire protocol natively; public APIs face REST or "
                        "GraphQL, gRPC lives service-to-service.",
                        "Ecosystem gravity — deadlines, retries, and load "
                        "balancing arrive as libraries and patterns you "
                        "must actually adopt, not as HTTP freebies.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="grpc-where-it-lives",
                    text=(
                        "So gRPC's habitat is the inside of a system: a "
                        "microservice mesh where both ends are code you "
                        "control, polyglot teams sharing one .proto as the "
                        "interface contract, pipelines moving high call "
                        "volumes (the compact frames and multiplexed "
                        "connection pay off), and anywhere long-lived "
                        "streams between services are the product. Google "
                        "originated it for exactly that interior; cloud "
                        "infrastructure projects ship .proto files as their "
                        "public contracts. The vocabulary is small and "
                        "worth fixing now, because every section below "
                        "uses it:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="grpc-vocab",
                    ordered=False,
                    items=[
                        "Service — the named bundle of methods a .proto "
                        "declares; one server can host several.",
                        "Message — a typed record of numbered fields; "
                        "requests and replies are all messages.",
                        "Stub — the generated typed client for a service; "
                        "call its methods like local functions.",
                        "Channel — the connection a stub dials; one "
                        "channel multiplexes every call over HTTP/2.",
                        "Status — the outcome code of a call, from a "
                        "shared vocabulary richer than HTTP's (section 6).",
                        "Deadline — the caller-set time budget for one "
                        "call, enforced end to end (section 6).",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="grpc-repo",
                    text=(
                        "This repo now carries the whole story as real "
                        "code, on the same substrate topics 11 and 13 "
                        "built: guide/grpcapi/ holds the contract (.proto "
                        "plus its compiled form), guide/data/grpc/ hosts "
                        "the server and the client adapters, and a domain "
                        "port keeps presentation thin. One decision "
                        "deserves its own sentence because it shapes "
                        "everything you will read: the gRPC server runs "
                        "IN-PROCESS with the FastAPI app — a satellite the "
                        "console dials over real loopback TCP — so every "
                        "demo call is a genuine round trip, and the ASGI "
                        "app remains the only front door. The rest of the "
                        "topic walks the contract, the four shapes, the "
                        "server, the client, the failure model, and the "
                        "codegen, in that order."
                    ),
                ),
            ],
        ),
        # ── 2. The .proto file ────────────────────────────────────────────
        Section(
            id="the-proto-file",
            title="The .proto file",
            blocks=[
                TextBlock(
                    kind="text",
                    id="proto-pitch",
                    text=(
                        "Everything begins with one small file. proto3 — "
                        "the modern syntax — lets you declare messages "
                        "(typed records with numbered fields) and services "
                        "(named methods over those messages). Field NUMBERS "
                        "are the load-bearing part: on the wire, a field is "
                        "its number plus a value, never its name — which is "
                        "why renumbering or reusing a tag is the one edit "
                        "that silently breaks old callers. Types are "
                        "deliberately Spartan: scalars, strings, bytes, "
                        "enums, nested and repeated fields, maps. Here is "
                        "the real contract this repo serves, message by "
                        "message:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="proto-post-reply",
                    language="proto",
                    caption="guide.proto's PostReply: one substrate post, protobuf-spelled.",
                    source="server/guide/grpcapi/guide.proto",
                    snippet=(
                        "// One posts-substrate post as this contract serves it.\n"
                        "message PostReply {\n"
                        "  string slug = 1;\n"
                        "  string title = 2;\n"
                        "  string author = 3;\n"
                        "  string status = 4;\n"
                        "  repeated string tags = 5;\n"
                        "  string created_at = 6;\n"
                        "}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="proto-fields",
                    text=(
                        "Read it against what you already know. The names "
                        "are the substrate's vocabulary from topic 11 — "
                        "slug, title, author — snake_case because that is "
                        "protobuf convention (many JSON mouths of protobuf "
                        "camelCase by default; this repo's console "
                        "deliberately preserves the proto names so what "
                        "you see IS the contract). repeated marks a list. "
                        "There is no optional in this message because "
                        "proto3 scalars are always present with zero "
                        "values — an unset string is empty, an unset "
                        "repeated is empty — so defaults exist implicitly, "
                        "and the console prints every field, zeros "
                        "included, rather than omitting them. The summary "
                        "message shows the remaining shapes:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="proto-summary",
                    language="proto",
                    caption="ViewsSummary: scalars and a map — the client-streaming answer.",
                    source="server/guide/grpcapi/guide.proto",
                    snippet=(
                        "// The client-streaming answer: one summary after the last event.\n"
                        "message ViewsSummary {\n"
                        "  uint32 events = 1;\n"
                        "  uint32 unique_posts = 2;\n"
                        "  uint32 unique_viewers = 3;\n"
                        "  map<string, uint32> views_per_post = 4;\n"
                        "}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="proto-where",
                    text=(
                        "Where the file lives is a real decision with a "
                        "Python-specific consequence. This repo puts "
                        "guide.proto inside the package that owns its "
                        "compiled output (guide/grpcapi/), because protoc "
                        "derives generated IMPORT paths from the .proto's "
                        "path relative to its include root — this "
                        "placement makes the generated code import "
                        "guide.grpcapi.guide_pb2 as a proper package "
                        "module, ready for the wheel a production image "
                        "installs. A standalone protos/ directory is the "
                        "more common industry layout and works fine, but "
                        "then the generated import needs a build step to "
                        "fix up. Either way the discipline is identical to "
                        "topic 13's schema-first lesson: the file is the "
                        "source of truth, everything else is derived from "
                        "it, and the derived artifacts are committed so "
                        "deploys never need the compiler."
                    ),
                ),
            ],
        ),
        # ── 3. The four stream kinds ──────────────────────────────────────
        Section(
            id="the-four-stream-kinds",
            title="The four stream kinds",
            blocks=[
                TextBlock(
                    kind="text",
                    id="kinds-pitch",
                    text=(
                        "One keyword — stream — placed on a method's "
                        "parameter, its return, or both, yields four call "
                        "shapes off a single service. This matters more "
                        "than any transport detail: REST gives you "
                        "request/response and approximates the rest (SSE, "
                        "chunked uploads), GraphQL gives you "
                        "request/response plus subscriptions, and gRPC "
                        "treats all four as primitives. The syntax is "
                        "almost anticlimactic next to what it unlocks — "
                        "this is the complete service stanza of the real "
                        "contract:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="kinds-service",
                    language="proto",
                    caption="The whole service: stream on the return, the parameter, both, or neither.",
                    source="server/guide/grpcapi/guide.proto",
                    snippet=(
                        "// The four RPC shapes, one service. `stream` on the RETURNS side is\n"
                        "// server-streaming; on the PARAMETER side, client-streaming; on both,\n"
                        "// bidirectional; on neither, unary.\n"
                        "service PostService {\n"
                        "  rpc GetPost(GetPostRequest) returns (PostReply);\n"
                        "  rpc StreamPosts(StreamPostsRequest) returns (stream PostReply);\n"
                        "  rpc CountViews(stream ViewEvent) returns (ViewsSummary);\n"
                        "  rpc EchoChat(stream ChatNote) returns (stream ChatNote);\n"
                        "}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="kinds-mapping",
                    text=(
                        "Each kind maps to a natural job, and the substrate "
                        "picked jobs you have already met in earlier topics "
                        "so the SHAPES stand out against familiar payloads:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="kinds-list",
                    ordered=False,
                    items=[
                        "Unary — one request, one answer: GetPost(slug) is "
                        "REST's GET /api/posts/{slug} and GraphQL's "
                        "post(slug:) in one message pair.",
                        "Server-streaming — one request, a sequence of "
                        "answers: StreamPosts(tag) sends each matching post "
                        "as its own message, arriving as produced.",
                        "Client-streaming — a sequence of requests, one "
                        "answer: CountViews consumes view events and "
                        "replies with the single ViewsSummary tally.",
                        "Bidirectional — sequences both ways over one "
                        "long-lived call: EchoChat echoes each note back "
                        "while more notes are still arriving.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="kinds-why-care",
                    text=(
                        "Why care beyond aesthetics? Because the kinds "
                        "change what the RUNTIME must be good at. Unary "
                        "over HTTP/2 multiplexes thousands of calls per "
                        "connection — the microservice workhorse. "
                        "Server-streaming pushes bounded results (a page, "
                        "a log tail) and unbounded ones (a feed) with the "
                        "same code. Client-streaming uploads big or "
                        "open-ended inputs without buffering them whole. "
                        "Bidirectional is the full-duplex primitive that "
                        "chat, live dashboards, and multiplayer "
                        "coordination are built on — the shape topic 28 "
                        "will rebuild over WebSockets for browsers. And in "
                        "every streaming shape, messages flow as they are "
                        "produced: the server's await between yields "
                        "(section 4) is real concurrency, exactly the "
                        "asyncio mechanics topic 02 taught, now moving "
                        "protocol frames."
                    ),
                ),
            ],
        ),
        # ── 4. Serving with grpcio ────────────────────────────────────────
        Section(
            id="serving-with-grpcio",
            title="Serving with grpcio",
            blocks=[
                TextBlock(
                    kind="text",
                    id="serving-pitch",
                    text=(
                        "The server-side story is the thin-router "
                        "invariant wearing new clothes. The codegen "
                        "(section 7) hands you a base class with one "
                        "method per RPC; you subclass it and implement "
                        "each method over the SAME use cases the REST "
                        "router resolves — parse nothing (the decoder "
                        "already produced typed fields), call the domain, "
                        "map the Result to the protocol's answer. Where "
                        "the HTTP router raises AppError for the envelope "
                        "to render, the servicer aborts with a gRPC status "
                        "code. Here is the real unary method, complete:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="serving-getpost",
                    language="py",
                    caption="The servicer's unary method: use case in, message out, abort on Err.",
                    source="server/guide/data/grpc/servicer.py",
                    snippet=(
                        "    async def GetPost(\n"
                        "        self, request: Any, context: grpc.aio.ServicerContext\n"
                        "    ) -> Any:\n"
                        "        \"\"\"UNARY: one post by slug, or NOT_FOUND — the gRPC 404.\"\"\"\n"
                        "        result = self._posts.get_post.execute(request.slug)\n"
                        "        if isinstance(result, Err):\n"
                        "            await context.abort(grpc.StatusCode.NOT_FOUND, result.failure.message)\n"
                        "        return _reply_from_post(result.value)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="serving-streams",
                    text=(
                        "The streaming halves differ only in signature: a "
                        "server-streaming method is an async GENERATOR "
                        "(yield one message per result), a "
                        "client-streaming method consumes an async "
                        "iterator and returns one summary, and the "
                        "bidirectional one does both. The projection into "
                        "messages is a plain function — _reply_from_post "
                        "maps the domain Post onto the compiled PostReply "
                        "field by field, the exact analog of topic 13's "
                        "from_domain projections. And note what the "
                        "server-streaming body does between yields: a "
                        "deliberate asyncio.sleep paces this stream at "
                        "50ms per message, making it the topic's "
                        "intentionally slow method — the one section 6 "
                        "kills with a deadline. The client-streaming "
                        "tally, complete:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="serving-countviews",
                    language="py",
                    caption="Client-streaming: consume an async iterator, answer one summary.",
                    source="server/guide/data/grpc/servicer.py",
                    snippet=(
                        "        \"\"\"CLIENT-STREAMING: consume view events, answer one summary.\"\"\"\n"
                        "        events = 0\n"
                        "        per_post: Counter[str] = Counter()\n"
                        "        viewers: set[str] = set()\n"
                        "        async for event in request_iterator:\n"
                        "            events += 1\n"
                        "            per_post[event.slug] += 1\n"
                        "            viewers.add(event.viewer)\n"
                        "        return guide_pb2.ViewsSummary(\n"
                        "            events=events,\n"
                        "            unique_posts=len(per_post),\n"
                        "            unique_viewers=len(viewers),\n"
                        "            views_per_post=dict(per_post),\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="serving-runtime",
                    text=(
                        "Hosting is grpc.aio.server: add the servicer, "
                        "bind a port, start. Two lifecycle choices in this "
                        "repo are worth stealing for your own designs. "
                        "First, the server binds an EPHEMERAL loopback "
                        "port (port 0 — the OS assigns), so per-app "
                        "instances never collide and tests run "
                        "side by side. Second, it starts LAZILY on first "
                        "use, because a grpc.aio server must bind the "
                        "RUNNING event loop — topic 02's loop is the one "
                        "uvicorn is already turning, and the ASGI app and "
                        "the gRPC satellite share it by design. The "
                        "runtime that owns all of this is short enough to "
                        "read in full:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="serving-runtime-code",
                    language="py",
                    caption="The satellite's lifecycle: bind ephemeral, start once, share one channel.",
                    source="server/guide/data/grpc/runtime.py",
                    snippet=(
                        "            server = grpc.aio.server()\n"
                        "            guide_pb2_grpc.add_PostServiceServicer_to_server(\n"
                        "                PostServiceServicer(self._posts), server\n"
                        "            )\n"
                        "            port = server.add_insecure_port(f\"{BIND_HOST}:0\")\n"
                        "            if port == 0:\n"
                        "                raise RuntimeError(\"gRPC satellite failed to bind an ephemeral port\")\n"
                        "            await server.start()\n"
                        "            self._server = server\n"
                        "            self._address = f\"{BIND_HOST}:{port}\"\n"
                        "            # One shared channel for every console call — channels are the\n"
                        "            # expensive, multiplexed object; stubs over it are free.\n"
                        "            self._channel = grpc.aio.insecure_channel(self._address)\n"
                        "            return self._address"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="serving-shutdown",
                    text=(
                        "Shutdown is the mirror image: the app's lifespan "
                        "closes the channel, then stops the server, and "
                        "both are no-ops when the satellite never started "
                        "— which is exactly the fate of every app instance "
                        "that never touches the console. One architectural "
                        "note for honesty: a production gRPC service would "
                        "not usually live inside an HTTP app. It would be "
                        "its own process — the same servicer, a main that "
                        "runs asyncio.run around server.start() and awaits "
                        "termination, deployed beside the HTTP API the way "
                        "uvicorn deploys this one. The in-process satellite "
                        "is this repo's teaching configuration: real "
                        "sockets, real frames, real deadlines, one "
                        "substrate."
                    ),
                ),
            ],
        ),
        # ── 5. Stubs and channels ─────────────────────────────────────────
        Section(
            id="stubs-and-channels",
            title="Stubs and channels",
            lead="This section carries the topic's demo — the gRPC console.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="stubs-pitch",
                    text=(
                        "The client half of the codegen is the stub: a "
                        "class with one typed method per RPC, constructed "
                        "over a CHANNEL — the connection object that owns "
                        "the HTTP/2 session. The division of labor matters "
                        "for cost as much as correctness: a channel is the "
                        "expensive, stateful thing (name resolution, TLS, "
                        "the multiplexed connection), so real callers "
                        "create ONE and share it; stubs are thin skins you "
                        "mint freely. Calling is then just method syntax "
                        "— await stub.GetPost(request) for unary, async-for "
                        "over the call object for streams — with an "
                        "optional timeout that is the caller's deadline in "
                        "seconds. This repo's console adapter is the whole "
                        "pattern in one file, message conversion included:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="stubs-received",
                    language="py",
                    caption="Messages cross the boundary as plain field maps — proto names, defaults on.",
                    source="server/guide/data/grpc/console.py",
                    snippet=(
                        "def _received(index: int, message: Any) -> GrpcReceivedMessage:\n"
                        "    \"\"\"One protobuf message as a plain field map (proto names, defaults on).\"\"\"\n"
                        "    return GrpcReceivedMessage(\n"
                        "        index=index,\n"
                        "        fields=MessageToDict(\n"
                        "            message,\n"
                        "            preserving_proto_field_name=True,\n"
                        "            always_print_fields_with_no_presence=True,\n"
                        "        ),\n"
                        "    )"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="stubs-calls",
                    language="py",
                    caption="One stub over the shared channel: unary awaits, streams async-for.",
                    source="server/guide/data/grpc/console.py",
                    snippet=(
                        "        address = await self._runtime.ensure_started()\n"
                        "        stub = guide_pb2_grpc.PostServiceStub(self._runtime.channel)\n"
                        "        timeout = request.deadline_ms / 1000 if request.deadline_ms is not None else None\n"
                        "        # … elapsed-time capture and per-method dispatch live in the real file\n"
                        "            if request.method == \"get-post\":\n"
                        "                reply = await stub.GetPost(\n"
                        "                    guide_pb2.GetPostRequest(slug=request.slug), timeout=timeout\n"
                        "                )\n"
                        "                messages.append(_received(0, reply))\n"
                        "            elif request.method == \"stream-posts\":\n"
                        "                stream = stub.StreamPosts(\n"
                        "                    guide_pb2.StreamPostsRequest(tag=request.tag), timeout=timeout\n"
                        "                )\n"
                        "                index = 0\n"
                        "                async for reply in stream:\n"
                        "                    messages.append(_received(index, reply))\n"
                        "                    index += 1"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="stubs-honesty",
                    text=(
                        "Two honesty notes on that adapter. The upstream "
                        "direction — client-streaming and bidirectional "
                        "calls — is just an async generator fed to the "
                        "stub: the console builds one ViewEvent or ChatNote "
                        "message per request fact and yields them; the "
                        "protocol does the rest. And the conversion at the "
                        "boundary is deliberate policy, not convenience: "
                        "protobuf's json_format turns messages into plain "
                        "maps with the proto names preserved and "
                        "no-presence defaults INCLUDED, so an empty tally "
                        "prints all its zeros instead of vanishing — the "
                        "DTO discipline of every earlier topic, applied to "
                        "the newest wire format. The demo endpoint behind "
                        "all of it stays as thin as ever:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="stubs-router",
                    language="py",
                    caption="The console endpoints: the adapter performs the call, the builder shapes the payload.",
                    source="server/guide/presentation/routers/demo/api.py",
                    snippet=(
                        "@router.get(\"/grpc-console\", response_model=GrpcConsoleRoster, response_model_exclude_none=True)\n"
                        "async def read_grpc_console(console: GrpcConsoleDep) -> GrpcConsoleRoster:\n"
                        "    \"\"\"Serve the console roster: the live satellite, the contract, the methods.\"\"\"\n"
                        "    address = await console.ensure_ready()\n"
                        "    return build_grpc_console_roster(\n"
                        "        server_address=address,\n"
                        "        stream_pause_ms=STREAM_PAUSE_MS,\n"
                        "    )\n"
                        "\n"
                        "\n"
                        "@router.post(\"/grpc-console\", response_model=GrpcConsoleRound, response_model_exclude_none=True)\n"
                        "async def run_grpc_console(\n"
                        "    request: GrpcConsoleRequest, console: GrpcConsoleDep\n"
                        ") -> GrpcConsoleRound:\n"
                        "    \"\"\"Perform one REAL gRPC round and shape the adapter's outcome.\"\"\"\n"
                        "    outcome = await console.call(request)\n"
                        "    return build_grpc_console_round(request=request, outcome=outcome)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="stubs-demo-pitch",
                    text=(
                        "The console below puts you in the caller's seat of "
                        "everything above. Pick a method — all four stream "
                        "kinds are on the roster — bring its arguments, "
                        "optionally set a deadline in milliseconds, and "
                        "fire: the endpoint performs a REAL grpc.aio round "
                        "over the shared channel to the live satellite, and "
                        "the payload reports what actually happened — the "
                        "response messages in arrival order with their "
                        "protobuf field maps, the status code in grpc's own "
                        "vocabulary, elapsed milliseconds, and the exact "
                        "address the call went to. Fire the same streaming "
                        "method with and without a deadline and watch the "
                        "difference section 6 is about to explain."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="api:grpc-console",
                    title="The gRPC console",
                    description=(
                        "GET /api/demo/api/grpc-console serves the roster "
                        "(the live satellite's address, the service stanza "
                        "of the real guide.proto, the four methods with "
                        "their stream kinds, the stream pacing); POST "
                        "performs a REAL gRPC round — unary GetPost by "
                        "slug, server-streaming StreamPosts by tag, "
                        "client-streaming CountViews over uploaded view "
                        "events, bidirectional EchoChat over notes — with "
                        "an optional deadlineMs, and reports the response "
                        "message sequence, the status code, the elapsed "
                        "milliseconds, and the address the call really "
                        "went to."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="stubs-coda",
                    text=(
                        "One more client-side fact completes the picture: "
                        "channels are lazy and resilient by design — "
                        "insecure_channel does not connect at "
                        "construction, and a channel whose server restarts "
                        "reconnects within its backoff policy. That is why "
                        "the runtime can build the channel immediately "
                        "after start() without a readiness dance, and why "
                        "callers hold channels for the process lifetime "
                        "instead of per call. It is also the boundary of "
                        "this repo's ambitions: production clients add "
                        "retry policies and keepalive tuning on top of "
                        "the channel, and those are configuration on the "
                        "same object you just drove."
                    ),
                ),
            ],
        ),
        # ── 6. Status and deadlines ───────────────────────────────────────
        Section(
            id="status-and-deadlines",
            title="Status and deadlines",
            blocks=[
                TextBlock(
                    kind="text",
                    id="status-pitch",
                    text=(
                        "HTTP gives a REST API dozens of status codes and "
                        "the discipline to use a dozen of them; GraphQL "
                        "collapses everything into 200 plus an errors "
                        "array (topic 13); gRPC splits the difference with "
                        "a small closed vocabulary that travels WITH the "
                        "payload metadata instead of replacing it. You "
                        "have already seen NOT_FOUND minted by the "
                        "servicer's abort — the domain's own not-found "
                        "message riding along as the status detail, the "
                        "same sentence the REST envelope serves as 404. "
                        "The codes a service actually uses are few:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="status-codes",
                    ordered=False,
                    items=[
                        "OK — the call succeeded; the messages are the "
                        "answer.",
                        "NOT_FOUND — the named thing does not exist; the "
                        "gRPC sibling of the 404 envelope.",
                        "INVALID_ARGUMENT — the request failed validation "
                        "server-side; kin of the family's 422.",
                        "DEADLINE_EXCEEDED — the caller's time budget ran "
                        "out before the answer completed.",
                        "UNAVAILABLE — the server is not reachable or is "
                        "shutting down; the retryable one.",
                        "PERMISSION_DENIED / UNAUTHENTICATED — the caller "
                        "may not, or proved nothing; topics 23–24's "
                        "vocabulary, protocol-native.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="deadline-pitch",
                    text=(
                        "Deadlines are the half of this section that "
                        "changes how you THINK. A gRPC deadline is set by "
                        "the CALLER, per call, before the work starts — "
                        "this console passes it as the timeout on the stub "
                        "method, and production clients set one on every "
                        "outbound call as a matter of hygiene. Once set it "
                        "PROPAGATES: if the handling service calls another "
                        "service, the remaining budget travels along, and "
                        "when the budget hits zero every layer's I/O "
                        "starts failing with DEADLINE_EXCEEDED — the "
                        "distributed circuit breaker topic 39 will "
                        "formalize. A slow method plus a short deadline is "
                        "therefore not an error to prevent but an "
                        "experiment to run, and the console's paced stream "
                        "makes it repeatable: twelve posts at 50ms apart, "
                        "versus a 120ms budget."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="deadline-test",
                    language="py",
                    caption="The real integration test: a mid-stream deadline keeps its partial messages.",
                    source="server/tests/data/test_grpc_console_roundtrip.py",
                    snippet=(
                        "async def test_short_deadline_exceeds_midstream_and_keeps_partial_messages(\n"
                        "    satellite: tuple[GrpcRuntime, InProcessGrpcConsole],\n"
                        ") -> None:\n"
                        "    _, console = satellite\n"
                        "    # Twelve posts at 50ms apart ≈ 600ms; 120ms buys exactly two messages.\n"
                        "    outcome = await console.call(GrpcConsoleRequest(method=\"stream-posts\", deadline_ms=120))\n"
                        "    assert outcome.status_code == \"DEADLINE_EXCEEDED\"\n"
                        "    assert 1 <= len(outcome.messages) < 12\n"
                        "    assert outcome.elapsed_ms < 2000\n"
                        "    # The messages that DID arrive are complete, ordered, real.\n"
                        "    assert outcome.messages[0].fields[\"slug\"] == \"designing-urls-people-can-read\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="deadline-read",
                    text=(
                        "That test is the whole semantics in five "
                        "assertions, and the middle one is the part worth "
                        "internalizing: a deadline that lands mid-stream "
                        "is not a lost call. The messages that arrived "
                        "BEFORE the budget expired were delivered — "
                        "complete, in order, really received — and the "
                        "failure that follows describes only the rest. "
                        "Production designs lean on this constantly: a "
                        "client renders partial results and retries for "
                        "the remainder; a worker treats DEADLINE_EXCEEDED "
                        "as a signal the downstream is slow, not absent; "
                        "and the elapsed-time fact in every console "
                        "payload is the number you would alert on. The "
                        "adapter's failure mapping shows how little "
                        "machinery this takes — one except clause, caught "
                        "at the boundary, reported as data:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="status-mapping",
                    language="py",
                    caption="A failed RPC becomes a payload: code, detail, partial messages.",
                    source="server/guide/data/grpc/console.py",
                    snippet=(
                        "        except grpc.aio.AioRpcError as exc:\n"
                        "            name = exc.code().name\n"
                        "            status_code = (\n"
                        "                cast(GrpcStatusCode, name)\n"
                        "                if name in _KNOWN_STATUS_CODES\n"
                        "                else \"UNKNOWN\"\n"
                        "            )\n"
                        "            status_detail = exc.details() or \"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="status-coda",
                    text=(
                        "Notice what the console's HTTP endpoint does NOT "
                        "do with these outcomes: map them onto the error "
                        "envelope. A NOT_FOUND round still answers HTTP "
                        "200, because the CONSOLE's call succeeded — the "
                        "gRPC outcome is its payload, exactly as topic 13 "
                        "kept GraphQL's errors inside a 200. Three "
                        "protocols, one discipline: the outer transport "
                        "reports whether IT worked; the inner protocol's "
                        "vocabulary reports whether the WORK worked. When "
                        "you design your own gRPC-facing edges, that "
                        "sentence is the whole decision."
                    ),
                ),
            ],
        ),
        # ── 7. Protobuf codegen ───────────────────────────────────────────
        Section(
            id="protobuf-codegen",
            title="Protobuf codegen",
            blocks=[
                TextBlock(
                    kind="text",
                    id="codegen-pitch",
                    text=(
                        "The compiler is a dev-time tool — grpcio-tools — "
                        "and its invocation is one line you run when the "
                        "contract changes, never in production builds. "
                        "The include root (-I.) plus the .proto's path "
                        "decide the generated import path (section 2's "
                        "placement trick); the two output flags emit the "
                        "message modules and the service glue. Run from "
                        "server/:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="codegen-command",
                    language="bash",
                    source=None,
                    snippet=(
                        "# compile the contract into committed Python (run from server/)\n"
                        "uv run python -m grpc_tools.protoc -I. \\\n"
                        "  --python_out=. --grpc_python_out=. guide/grpcapi/guide.proto\n"
                        "\n"
                        "# what it produced (committed — deploys never need the compiler)\n"
                        "ls guide/grpcapi/"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="codegen-outputs",
                    text=(
                        "The outputs are two Python modules per contract. "
                        "guide_pb2.py holds the message classes — "
                        "PostReply, ViewsSummary — each wired to a "
                        "descriptor the protobuf RUNTIME (a separate "
                        "package, and a declared dependency for exactly "
                        "this reason) interprets: field access, "
                        "serialization, the json_format conversion the "
                        "console uses. guide_pb2_grpc.py holds the service "
                        "glue — the servicer base class the implementation "
                        "subclasses, the stub class clients construct, and "
                        "the registration function the runtime calls. They "
                        "are build artifacts, which raises a policy "
                        "question every Python service answers explicitly: "
                        "what do the gates do with code no human wrote? "
                        "This repo's answer is configured, narrow, and "
                        "written down where the tooling lives:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="codegen-gates",
                    language="toml",
                    caption="pyproject's contract with generated code: exempt the output, gate everything else.",
                    source="server/pyproject.toml",
                    snippet=(
                        "# Generated protobuf/gRPC code (guide.proto compiled by grpc_tools.protoc):\n"
                        "# committed build output so deploys never need the compiler — never lint it,\n"
                        "# never hand-edit it; the .proto is the source of truth (topic 15).\n"
                        "\"guide/grpcapi/guide_pb2*.py\" = [\"E501\", \"F401\", \"I001\", \"UP009\"]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="codegen-read",
                    text=(
                        "Read that policy as three rules. The generated "
                        "files are exempt BY PATH PATTERN — only "
                        "guide_pb2*.py, and only the specific rules they "
                        "trip (long descriptor lines, unused-looking "
                        "imports) — while the hand-written package init "
                        "beside them stays fully gated. mypy excludes the "
                        "same modules and treats their imports as Any, "
                        "which is why the servicer annotates its request "
                        "and reply types honestly as Any and the TYPED "
                        "seam lives one layer out, at the domain port — "
                        "exactly where this guide always put the types. "
                        "And nothing is generated at install or runtime: "
                        "the compiled modules are COMMITTED, so a "
                        "production image (which installs the wheel and "
                        "skips the dev group that carries grpcio-tools) "
                        "needs only grpcio and protobuf to serve."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="codegen-drift",
                    text=(
                        "The discipline that makes committed artifacts "
                        "safe is the same one topics 12 and 13 built for "
                        "generated docs and schemas: tests pin the derived "
                        "to the source. This repo's integration suite "
                        "asserts the console's proto excerpt equals the "
                        "service stanza of the real file verbatim, so the "
                        "teaching face cannot drift from the compiled "
                        "contract; regenerating after a .proto edit and "
                        "forgetting anything downstream fails a test, not "
                        "a deploy. That is the entire workflow: edit the "
                        ".proto, run the one-line compile, fix what the "
                        "compiler and the tests point at, and commit both "
                        "the contract and its compiled form together."
                    ),
                ),
            ],
        ),
        # ── 8. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="Eight real stops: the roster, all four stream kinds, a 404, a deadline — via the console.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-honesty",
                    text=(
                        "One honest admission before the commands: gRPC "
                        "is not curl-native. The frames are protobuf over "
                        "HTTP/2, and a terminal needs grpcurl (plus the "
                        ".proto, or a server with reflection enabled) or a "
                        "small script to speak it raw. This repo's answer "
                        "is the console endpoint you just met — a "
                        "curl-friendly HTTP face that performs the REAL "
                        "gRPC calls server-side and reports outcomes as "
                        "JSON — so the tour below exercises the actual "
                        "satellite, real statuses and real timing "
                        "included. Stops 1–2 read the roster and take the "
                        "unary happy path; stop 3 earns NOT_FOUND; stop 4 "
                        "streams a tagged slice; stop 5 kills the same "
                        "stream mid-flight with a deadline; stops 6–7 "
                        "upload a client-stream and open a bidi echo; "
                        "stop 8 watches the topic join the curriculum."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-roster",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the roster: live satellite address, the contract stanza, the four methods\n"
                        "curl -s localhost:8000/api/demo/api/grpc-console | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-unary",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — unary: one post by slug — one message, OK, a couple of milliseconds\n"
                        "curl -s -X POST localhost:8000/api/demo/api/grpc-console -H 'content-type: application/json' \\\n"
                        "  -d '{\"method\":\"get-post\",\"slug\":\"drafting-the-grpc-chapter\"}' \\\n"
                        "  | python3 -c '\n"
                        "import json, sys\n"
                        "r = json.load(sys.stdin)\n"
                        "print(\"status:\", r[\"statusCode\"], \"·\", r[\"elapsedMs\"], \"ms ·\", r[\"serverAddress\"])\n"
                        "print(\"title :\", r[\"messages\"][0][\"fields\"][\"title\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-notfound",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the gRPC 404: status NOT_FOUND carrying the domain's own message\n"
                        "curl -s -X POST localhost:8000/api/demo/api/grpc-console -H 'content-type: application/json' \\\n"
                        "  -d '{\"method\":\"get-post\",\"slug\":\"no-such-post\"}' \\\n"
                        "  | python3 -c '\n"
                        "import json, sys\n"
                        "r = json.load(sys.stdin)\n"
                        "print(\"status:\", r[\"statusCode\"], \"—\", r[\"statusDetail\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-stream",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — server-streaming: every http-tagged post, one message each, ~50ms apart\n"
                        "curl -s -X POST localhost:8000/api/demo/api/grpc-console -H 'content-type: application/json' \\\n"
                        "  -d '{\"method\":\"stream-posts\",\"tag\":\"http\"}' \\\n"
                        "  | python3 -c '\n"
                        "import json, sys\n"
                        "r = json.load(sys.stdin)\n"
                        "for m in r[\"messages\"]:\n"
                        "    print(m[\"index\"], m[\"fields\"][\"slug\"])\n"
                        "print(\"status:\", r[\"statusCode\"], \"·\", len(r[\"messages\"]), \"messages ·\", r[\"elapsedMs\"], \"ms\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-deadline",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the deadline: same stream, 120ms budget — partial messages, DEADLINE_EXCEEDED\n"
                        "curl -s -X POST localhost:8000/api/demo/api/grpc-console -H 'content-type: application/json' \\\n"
                        "  -d '{\"method\":\"stream-posts\",\"deadlineMs\":120}' \\\n"
                        "  | python3 -c '\n"
                        "import json, sys\n"
                        "r = json.load(sys.stdin)\n"
                        "print(\"arrived before the budget died:\", [m[\"fields\"][\"slug\"] for m in r[\"messages\"]])\n"
                        "print(\"status:\", r[\"statusCode\"], \"·\", r[\"elapsedMs\"], \"ms ·\", r[\"reasoning\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-countviews",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — client-streaming: upload three view events, get the one-line tally back\n"
                        "curl -s -X POST localhost:8000/api/demo/api/grpc-console -H 'content-type: application/json' \\\n"
                        "  -d '{\"method\":\"count-views\",\"viewEvents\":[\n"
                        "        {\"slug\":\"idempotency-retold\",\"viewer\":\"mak\"},\n"
                        "        {\"slug\":\"idempotency-retold\",\"viewer\":\"ada\"},\n"
                        "        {\"slug\":\"notes-on-rfc-9457\",\"viewer\":\"mak\"}]}' \\\n"
                        "  | python3 -c '\n"
                        "import json, sys\n"
                        "r = json.load(sys.stdin)\n"
                        "print(\"sent:\", r[\"sentMessages\"], \"events · status:\", r[\"statusCode\"])\n"
                        "print(json.dumps(r[\"messages\"][0][\"fields\"], indent=2))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-echochat",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 7 — bidirectional: notes flow in, echoes flow back, over one call\n"
                        "curl -s -X POST localhost:8000/api/demo/api/grpc-console -H 'content-type: application/json' \\\n"
                        "  -d '{\"method\":\"echo-chat\",\"chatNotes\":[\n"
                        "        {\"sender\":\"you\",\"text\":\"hello\"},\n"
                        "        {\"sender\":\"me\",\"text\":\"is this thing on?\"}]}' \\\n"
                        "  | python3 -c '\n"
                        "import json, sys\n"
                        "r = json.load(sys.stdin)\n"
                        "for m in r[\"messages\"]:\n"
                        "    print(m[\"fields\"][\"sender\"], \"->\", m[\"fields\"][\"text\"])\n"
                        "print(\"status:\", r[\"statusCode\"], \"·\", r[\"elapsedMs\"], \"ms\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-curriculum",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 8 — the APIs group complete: five topics, fifteen in the curriculum\n"
                        "curl -s localhost:8000/api/content | python3 -c '\n"
                        "import json, sys\n"
                        "body = json.load(sys.stdin)\n"
                        "apis = [t for t in body[\"topics\"] if t[\"group\"] == \"apis\"]\n"
                        "print(\"apis group:\", [t[\"id\"] for t in apis])\n"
                        "print(\"topics total:\", len(body[\"topics\"]))'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stop 5 is the topic in one command: the same "
                        "method that answered cleanly at stop 4, one "
                        "deadlineMs field smaller, arrives half-finished "
                        "with its survivor messages and the protocol's own "
                        "verdict — no envelope, no retry theater, just the "
                        "vocabulary doing its job. You have now driven all "
                        "four stream kinds, both failure modes, and the "
                        "full client surface of a real gRPC service from "
                        "a terminal. The APIs group closes here — five "
                        "ways to shape a contract — and the Data group "
                        "picks up the substrate underneath them: real "
                        "PostgreSQL schemas and the SQL that earns them."
                    ),
                ),
            ],
        ),
    ],
)
