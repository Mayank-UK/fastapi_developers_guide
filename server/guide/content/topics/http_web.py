"""Topic 03 — http-web: HTTP itself, with FastAPI as only the lens.

The protocol every handler in this server speaks, taught concept-first and
framework-agnostic: the journey of one of this guide's own requests ·
methods, status codes, and headers with the topic's echo demo INLINE ·
idempotency and safety · content negotiation · cookies, sessions, and the
same-origin policy · CORS (what it is and what it is not) · TLS/HTTPS and
why it terminates at the proxy · HTTP versions and what uvicorn actually
speaks · the terminal companion.

Every code block below quotes a real repo file (the snippet ratchet
verifies it); bash blocks are the sourcing-exempt exception, and the one
nginx quote is exempt by language while citing its path in prose.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="http-web",
    title="HTTP, the web's contract",
    subtitle=(
        "The protocol under every endpoint this guide serves — requests, "
        "responses, and the rules that make them trustworthy."
    ),
    group="foundations",
    order=3,
    sections=[
        # ── 1. The journey of one request ───────────────────────────────────
        Section(
            id="request-journey",
            title="The journey of one request",
            blocks=[
                TextBlock(
                    kind="text",
                    id="journey-overview",
                    text=(
                        "Every page of this guide is one HTTP conversation, so "
                        "start by following a real one. You open "
                        "http://localhost:5174/topics/http-web; the browser "
                        "resolves the port, opens a TCP connection, and sends a "
                        "request line — method, path, version — followed by "
                        "headers. In development that request never reaches the "
                        "FastAPI server directly: it lands on Vite's dev server "
                        "(the thing serving the React shell on :5174), which "
                        "applies one rule — paths starting with /api are "
                        "proxied elsewhere. The proxy is not a cosmetic "
                        "convenience; it is what makes the browser see ONE "
                        "origin. The page's JavaScript calls /api/content/... "
                        "same-origin as itself, and Vite forwards the request, "
                        "unchanged in semantics, to the FastAPI server — "
                        "rewriting the transport (its own client connection to "
                        "the server, potentially adding Host and connection "
                        "management of its own) while preserving method, path, "
                        "query, and headers. That one config decision is why "
                        "this repo develops with zero CORS wiring, a point the "
                        "CORS section returns to. The proxy's entire contract "
                        "is this block from the real client config:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="journey-vite-proxy",
                    language="ts",
                    caption="The dev proxy: /api leaves the browser same-origin, Vite forwards it.",
                    source="client/vite.config.ts",
                    snippet=(
                        "// In Docker the server is reachable as the compose service name, not localhost;\n"
                        "// API_PROXY_TARGET lets compose override the proxy target without editing code.\n"
                        "const apiProxyTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000';\n"
                        "// …\n"
                        "    server: {\n"
                        "      host: '0.0.0.0',\n"
                        "      port: 5174,\n"
                        "      strictPort: true,\n"
                        "      proxy: {\n"
                        "        '/api': { target: apiProxyTarget, ws: true }, // same-origin; ws carries the upgrade\n"
                        "      },\n"
                        "    },"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="journey-asgi",
                    text=(
                        "Next hop: uvicorn, the ASGI server. It owns the socket "
                        "and the protocol bytes — it parses the request line "
                        "and headers per HTTP/1.1, manages the connection, and "
                        "translates what arrived into an ASGI scope: a plain "
                        "dictionary describing the request (type, method, "
                        "path, query string, headers as raw bytes, client "
                        "address) plus two callables, receive and send. That "
                        "scope IS the boundary between \"speaking HTTP\" and "
                        "\"being a Python web app\"; FastAPI and Starlette "
                        "never see a socket. Inside that boundary the request "
                        "walks the wiring the app factory built at startup — "
                        "the request-id middleware wraps everything, the "
                        "shared exception handlers stand by, and the router "
                        "table decides which handler this path belongs to. "
                        "The factory is short enough to read as the map of "
                        "the journey's second half:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="journey-app-factory",
                    language="py",
                    caption="create_app: the composition root every request enters.",
                    source="server/guide/main.py",
                    snippet=(
                        "def create_app() -> FastAPI:\n"
                        "    \"\"\"Build one wired FastAPI application instance.\"\"\"\n"
                        "    config = get_config()\n"
                        "    configure_logging(config.log_level)\n"
                        "    app = FastAPI(title=APP_TITLE, version=__version__, lifespan=lifespan)\n"
                        "    # …\n"
                        "    app.add_middleware(RequestIdMiddleware)\n"
                        "    register_exception_handlers(app)\n"
                        "\n"
                        "    app.include_router(health.router)\n"
                        "    app.include_router(content.router)\n"
                        "    app.include_router(demo_scenario.router)\n"
                        "    app.include_router(demo_py.router)\n"
                        "    app.include_router(demo_runtime.router)\n"
                        "    app.include_router(demo_http.router)\n"
                        "    return app"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="journey-endpoint",
                    text=(
                        "The journey ends at a handler — the smallest real one "
                        "in this repo is the health probe. Note what it "
                        "declares: a dependency (the typed config, injected), "
                        "a response model (the published contract), and a "
                        "typed return. The way back is the mirror image: "
                        "FastAPI serializes the return value against the "
                        "response model, the middleware stack unwinds (the "
                        "request-id middleware stamps its header on the way "
                        "out), uvicorn writes status line + headers + body as "
                        "protocol bytes, and the proxy relays them to the "
                        "browser. One request, five cooperating layers — and "
                        "the rest of this topic is about the CONTRACT those "
                        "layers speak to each other:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="journey-health-endpoint",
                    language="py",
                    caption="The journey's destination: a real handler, three lines of intent.",
                    source="server/guide/presentation/routers/health.py",
                    snippet=(
                        "@router.get(\"/health\", response_model=HealthResponse)\n"
                        "def read_health(config: Annotated[AppConfig, Depends(get_config)]) -> HealthResponse:\n"
                        "    \"\"\"Report process liveness plus the environment it booted in.\"\"\"\n"
                        "    return HealthResponse(status=\"ok\", env=config.env)"
                    ),
                ),
            ],
        ),
        # ── 2. Methods, status codes, headers (inline demo) ─────────────────
        Section(
            id="methods-status-headers",
            title="Methods, status codes, and headers",
            lead="This section carries the topic's echo demo — beside the header taxonomy it proves.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="methods-verbs",
                    text=(
                        "A request's first line commits it to a METHOD, and "
                        "methods are semantics, not syntax:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="methods-verbs-list",
                    ordered=False,
                    items=[
                        "GET — fetch a representation.",
                        "HEAD — GET without a body.",
                        "OPTIONS — asks what is allowed.",
                        "PUT — stores the submitted state at the target URI.",
                        "DELETE — removes it.",
                        "POST — submits data to be processed by the target's own "
                        "logic.",
                        "PATCH — applies a partial change.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="methods-verb-promise",
                    text=(
                        "The verb is the server's "
                        "promise about what the request DOES — which is why "
                        "routing frameworks let one path carry different "
                        "handlers per verb, and why the same path answering "
                        "GET and POST differently is normal, not confusing. "
                        "This guide's own surface is deliberately small so "
                        "far: GET for reads, POST for the echo demo you are "
                        "about to use, PATCH for the scenario toggle. The "
                        "response's first line answers with a STATUS CODE, "
                        "and the families matter more than individual codes:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="methods-status-families-list",
                    ordered=False,
                    items=[
                        "1xx informational — interim protocol chatter (100 "
                        "Continue, 101 Switching Protocols).",
                        "2xx — success.",
                        "3xx — redirection.",
                        "4xx — the client's mistake.",
                        "5xx — the server's.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="methods-failure-table",
                    text=(
                        "This guide maps every failure it can "
                        "produce onto one small table — the single place "
                        "status codes are chosen:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="methods-status-map",
                    language="py",
                    caption="The guide's whole status vocabulary, in one dict.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "_HTTP_STATUS_BY_KIND: dict[FailureKind, int] = {\n"
                        "    FailureKind.VALIDATION_FAILED: 422,\n"
                        "    FailureKind.UNAUTHORIZED: 401,\n"
                        "    FailureKind.FORBIDDEN: 403,\n"
                        "    FailureKind.NOT_FOUND: 404,\n"
                        "    FailureKind.CONFLICT: 409,\n"
                        "    FailureKind.RATE_LIMITED: 429,\n"
                        "    FailureKind.SERVICE_UNAVAILABLE: 503,\n"
                        "    FailureKind.INTERNAL: 500,\n"
                        "}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="methods-status-semantics",
                    text=(
                        "Read those as protocol decisions, not arbitrary "
                        "labels. 422 (Unprocessable Content) tells the client "
                        "\"syntactically fine JSON, semantically invalid\" — "
                        "FastAPI's own convention for validation failures, "
                        "which this guide adopts deliberately. 404 belongs to "
                        "unknown resources (an unknown topic id gets exactly "
                        "that), 409 to conflicting state, 429 to rate limiting "
                        "with a Retry-After in the reliability topic. Statuses "
                        "the taxonomy does not name keep their truthful code "
                        "and take the nearest bucket — a 405 method-not-"
                        "allowed is rendered as the not_found bucket with "
                        "status 405 intact. After the status line come the "
                        "HEADERS, and the distinction worth internalizing "
                        "early is END-TO-END versus HOP-BY-HOP. End-to-end "
                        "headers (accept, content-type, user-agent, every x-* "
                        "extension) describe the request or the "
                        "representation and must survive every proxy intact. "
                        "Hop-by-hop headers — connection, te, trailer, "
                        "transfer-encoding, upgrade, and the proxy-"
                        "authenticate pair (the closed list in RFC 9110 "
                        "§7.6.1), plus keep-alive from HTTP/1.1's historic "
                        "persistent-connection machinery — describe ONE "
                        "transport connection and must "
                        "be consumed by each hop; they never reach application "
                        "code on a correctly-behaving server. That is why a "
                        "real deployment can echo your x-demo-trace header "
                        "back to you but will never show you the connection "
                        "header your client sent. The guide's own request-id "
                        "middleware is a live end-to-end example — it reads "
                        "one inbound header and stamps one outbound header, "
                        "on every response:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="methods-request-id",
                    language="py",
                    caption="End-to-end headers doing real work: the request-id round trip.",
                    source="server/guide/core/request_context.py",
                    snippet=(
                        "        request_id = _assign_request_id(_inbound_id(scope))\n"
                        "        token = _request_id.set(request_id)\n"
                        "        # Mirror into the shared ASGI scope so handlers outside this\n"
                        "        # middleware (ServerErrorMiddleware's 500 path) still see the id.\n"
                        "        _mirror_into_scope(scope, request_id)\n"
                        "# …\n"
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
                    id="methods-demo-intro",
                    text=(
                        "The best way to believe any of this is to see what a "
                        "server ACTUALLY receives, so this topic's demo is an "
                        "echo endpoint: fire a GET or POST at it, with or "
                        "without your own headers, and it reports back the "
                        "request line, the raw query, the request's content "
                        "type, and a selected view of the inbound headers — "
                        "the negotiation set (user-agent, accept, "
                        "accept-encoding, content-type), every x-* extension "
                        "header, and any hop-by-hop header that slipped "
                        "through — each classified end-to-end or hop-by-hop, "
                        "with the RFC's canonical hop-by-hop list riding "
                        "along. The logic is a pure builder; the selection "
                        "constant and the classification set are the teaching "
                        "core:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="methods-demo-selection",
                    language="py",
                    caption="What the echo shows, and against which list it classifies.",
                    source="server/guide/domain/demos/http_headers.py",
                    snippet=(
                        "BASE_HEADER_SELECTION: Final[tuple[str, ...]] = (\n"
                        "    \"user-agent\",\n"
                        "    \"accept\",\n"
                        "    \"accept-encoding\",\n"
                        "    \"content-type\",\n"
                        ")\n"
                        "\"\"\"Negotiation/identity headers every echo reports when the client sent them.\"\"\"\n"
                        "\n"
                        "HOP_BY_HOP_HEADERS: Final[frozenset[str]] = frozenset(\n"
                        "    {\n"
                        "        \"connection\",\n"
                        "        # …\n"
                        "        \"upgrade\",\n"
                        "    }\n"
                        ")\n"
                        "\"\"\"RFC 9110 §7.6.1's closed set + HTTP/1.1's keep-alive: consumed per hop.\"\"\""
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="methods-demo-router",
                    language="py",
                    caption="The echo pair: same path, two verbs, one declared response model.",
                    source="server/guide/presentation/routers/demo/http.py",
                    snippet=(
                        "@router.get(\"/headers\", response_model=HttpHeadersEchoPayload, response_model_exclude_none=True)\n"
                        "def read_headers_echo(request: Request) -> HttpHeadersEchoPayload:\n"
                        "    \"\"\"Echo the GET exactly as the server received it.\"\"\"\n"
                        "    return _echo(request)\n"
                        "\n"
                        "\n"
                        "@router.post(\n"
                        "    \"/headers\", response_model=HttpHeadersEchoPayload, response_model_exclude_none=True\n"
                        ")\n"
                        "def send_headers_echo(\n"
                        "    request: Request, body: HeadersDemoBody | None = None\n"
                        ") -> HttpHeadersEchoPayload:\n"
                        "    \"\"\"Echo the POST — body parsed, content type reported, headers classified.\"\"\"\n"
                        "    return _echo(request, body.message if body is not None else None)"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="http:headers",
                    title="What the server saw — the headers echo",
                    description=(
                        "GET and POST /api/demo/http/headers echo the request "
                        "exactly as the server received it: method, path, raw "
                        "query, content type, and selected headers — each "
                        "classified end-to-end vs hop-by-hop, with the "
                        "canonical hop-by-hop reference list alongside. "
                        "Choose a method, add a custom x-* header, fire, and "
                        "read what came back."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="methods-demo-coda",
                    text=(
                        "Read the demo with intent. Send a custom header and "
                        "watch it survive to application code (end-to-end, by "
                        "design). Compare GET with POST: the POST carries a "
                        "body, so a content-type appears in its echo and the "
                        "parsed message comes back — the server's proof it "
                        "understood the body's media type. Then look for "
                        "connection and find it only in the hop-by-hop list, "
                        "not among the received headers: uvicorn consumed it, "
                        "as the protocol requires. (A test client that talks "
                        "to the app in-process can leak hop-by-hop headers "
                        "into the scope — if you ever see connection in an "
                        "echo, that is the transport being honest about not "
                        "being a real hop, and exactly why the classification "
                        "is per-header rather than assumed.)"
                    ),
                ),
            ],
        ),
        # ── 3. Idempotency and safety ───────────────────────────────────────
        Section(
            id="idempotency-and-safety",
            title="Idempotency and safety",
            blocks=[
                TextBlock(
                    kind="text",
                    id="idem-definitions",
                    text=(
                        "Two properties of methods decide whether you may "
                        "retry a request, and conflating them causes real "
                        "outages. SAFE means the request changes no state "
                        "beyond incidental bookkeeping (serving it may log, "
                        "or bump a counter): GET, HEAD, OPTIONS, TRACE. "
                        "IDEMPOTENT means issuing it N times leaves the same "
                        "state as issuing it once: everything safe, plus PUT "
                        "and DELETE — PUT the same representation twice and "
                        "the stored state is identical; DELETE a resource "
                        "twice and it is just as gone (the second 404 is the "
                        "same state of the world, differently reported). POST "
                        "is neither: two identical submissions may create two "
                        "orders. PATCH is defined as neither in general — a "
                        "patch that says \"add one to the count\" is not "
                        "idempotent; one that says \"set the count to 7\" "
                        "happens to be. The distinction is the foundation of "
                        "every retry policy: a timeout on a GET can be "
                        "retried blindly; a timeout on a PUT can be retried "
                        "safely because a repeated application is harmless; "
                        "a timeout on a POST is an AMBIGUOUS event — the "
                        "request may or may not have been processed — and "
                        "naive retries are how customers get double-charged. "
                        "The standard remedies (client-generated idempotency "
                        "keys, server-side deduplication) are exactly the "
                        "webhook and reliability topics' subject matter, "
                        "where retries arrive with backoff and rate limits "
                        "(HTTP 429 plus Retry-After). One honesty note: "
                        "safety and idempotency are PROMISES the "
                        "implementation keeps, not magic the verb performs — "
                        "a GET handler that writes rows is not safe, it is "
                        "simply lying. This guide's own scenario toggle is a "
                        "convenient live example of a PATCH that happens to "
                        "be idempotent, beside a GET that is safe:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="idem-scenario-router",
                    language="py",
                    caption="Safe GET beside a set-state PATCH (idempotent in practice).",
                    source="server/guide/presentation/routers/demo/scenario.py",
                    snippet=(
                        "@router.get(\"/scenario\", response_model=ScenarioState)\n"
                        "def read_scenario(store: ScenarioStoreDep) -> ScenarioState:\n"
                        "    \"\"\"Report the current demo scenario.\"\"\"\n"
                        "    return store.get()\n"
                        "\n"
                        "\n"
                        "@router.patch(\"/scenario\", response_model=ScenarioState)\n"
                        "def update_scenario(patch: ScenarioPatch, store: ScenarioStoreDep) -> ScenarioState:\n"
                        "    \"\"\"Apply a partial update; the response is the resulting full state.\"\"\"\n"
                        "    return store.update(patch)"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="idem-probe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# safe: read the scenario twice — identical answers, no state moved\n"
                        "curl -s localhost:8000/api/demo/scenario && curl -s localhost:8000/api/demo/scenario\n"
                        "# set-state PATCH: applying it twice converges to the same state (idempotent in practice)\n"
                        "curl -s -X PATCH -H 'content-type: application/json' \\\n"
                        "  -d '{\"injectFailure\":\"latency\"}' localhost:8000/api/demo/scenario\n"
                        "# …and put the demo world back the way you found it\n"
                        "curl -s -X PATCH -H 'content-type: application/json' \\\n"
                        "  -d '{\"injectFailure\":\"none\"}' localhost:8000/api/demo/scenario"
                    ),
                ),
            ],
        ),
        # ── 4. Content negotiation ──────────────────────────────────────────
        Section(
            id="content-negotiation",
            title="Content negotiation",
            blocks=[
                TextBlock(
                    kind="text",
                    id="negotiate-proactive",
                    text=(
                        "HTTP lets client and server agree on representation "
                        "WITHOUT the URL changing. PROACTIVE negotiation is "
                        "the client stating preferences in request headers — "
                        "accept (media types), accept-language (the "
                        "internationalization topic builds a live negotiator "
                        "on it), accept-encoding (compression codings) — and "
                        "the server choosing among what it offers. Preferences "
                        "carry quality values: \"text/html,application/"
                        "json;q=0.9,*/*;q=0.1\" ranks HTML first, JSON at "
                        "90%, anything else as a last resort; q is a weight "
                        "in [0, 1], default 1, and q=0 means \"do not send me "
                        "this\". Two outcomes exist when the server cannot "
                        "honor the client: reactive negotiation (300 Multiple "
                        "Choices, the server listing alternatives) is rare in "
                        "practice; 406 Not Acceptable is the honest refusal. "
                        "The request-side counterpart is NOT negotiation: "
                        "content-type on a request declares what the body "
                        "IS, and 415 Unsupported Media Type is the refusal "
                        "when the server will not parse it. What does "
                        "Starlette/FastAPI actually do here? Deliberately "
                        "little: every JSON-returning handler answers "
                        "application/json regardless of accept — response "
                        "models drive serialization, not content "
                        "negotiation. A server that wants to honor accept "
                        "implements it (read the header, branch, or 406); "
                        "the framework staying out of it is the design "
                        "decision, not an omission. This guide does "
                        "negotiate one thing by construction — the wire "
                        "convention itself:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="negotiate-camel-model",
                    language="py",
                    caption="The guide's wire dialect: camelCase JSON, declared once.",
                    source="server/guide/core/serialization.py",
                    snippet=(
                        "class CamelModel(BaseModel):\n"
                        "    \"\"\"Base for every wire model: camelCase aliases, both-direction parsing, frozen.\"\"\"\n"
                        "\n"
                        "    model_config = ConfigDict(\n"
                        "        alias_generator=to_camel,\n"
                        "        populate_by_name=True,\n"
                        "        frozen=True,\n"
                        "    )"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="negotiate-content-route",
                    language="py",
                    caption="The content route: one media type, absent facts omitted.",
                    source="server/guide/presentation/routers/content.py",
                    snippet=(
                        "@router.get(\"\", response_model=ContentListResponse, response_model_exclude_none=True)\n"
                        "def list_content(\n"
                        "    registry: Annotated[ContentRegistry, Depends(get_content_registry)],\n"
                        ") -> ContentListResponse:\n"
                        "    \"\"\"Serve the whole topic index: groups then topics, each sorted by order.\"\"\"\n"
                        "    return ContentListResponse(\n"
                        "        version=CONTENT_API_VERSION,\n"
                        "        groups=sorted(registry.groups(), key=lambda group: group.order),\n"
                        "        topics=sorted(registry.summaries(), key=lambda summary: summary.order),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="negotiate-honesty",
                    text=(
                        "That response_model_exclude_none is a wire "
                        "discipline, not decoration: optional facts are "
                        "OMITTED rather than sent as JSON null, so a client's "
                        "validator can treat absent and null as different "
                        "statements. You can probe the honest posture from "
                        "the terminal — ask this guide's server for HTML and "
                        "observe that it answers JSON with a 200, because no "
                        "route branches on accept (the probe is in the "
                        "terminal companion). When a future topic needs real "
                        "negotiation — the i18n topic's Accept-Language "
                        "negotiator — it will read the header explicitly and "
                        "choose, which is precisely the point: negotiation is "
                        "application logic with protocol vocabulary, not "
                        "framework magic."
                    ),
                ),
            ],
        ),
        # ── 5. Cookies, sessions, same-origin ───────────────────────────────
        Section(
            id="cookies-sessions-same-origin",
            title="Cookies, sessions, and the same-origin policy",
            blocks=[
                TextBlock(
                    kind="text",
                    id="cookies-mechanics",
                    text=(
                        "HTTP is stateless — every request arrives with no "
                        "memory of the last. Cookies are the oldest repair: "
                        "the server sends a Set-Cookie RESPONSE header asking "
                        "the client to store a small piece of state, and the "
                        "browser attaches it as a Cookie REQUEST header on "
                        "every subsequent matching request, automatically, "
                        "with credentials semantics that fetch/XHR control "
                        "per-request. The attributes on Set-Cookie are the "
                        "entire security model and deserve verbatim "
                        "attention."
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="cookies-attributes-list",
                    ordered=False,
                    items=[
                        "Max-Age=3600 (or the older Expires) — sets lifetime "
                        "in seconds — Max-Age wins when both are present; "
                        "neither means a session cookie that dies with the "
                        "browser.",
                        "Domain and Path — scope where it is sent; leaving "
                        "Domain off is the tight default (host-only).",
                        "Secure — means never sent over plain HTTP.",
                        "HttpOnly — hides it from document.cookie — JavaScript "
                        "cannot read what it cannot exfiltrate trivially.",
                        "SameSite — gates cross-site sending: Strict never "
                        "crosses sites (even on top-level navigation), Lax "
                        "(the modern browser default) allows it on safe "
                        "top-level navigations, None must be paired with "
                        "Secure and exists for genuine cross-site contexts.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="cookies-session-composition",
                    text=(
                        "The SameSite tier is the first line of CSRF defense, "
                        "expanded in the security topic. A SESSION is the "
                        "standard composition: the cookie carries only an "
                        "opaque session id; the server owns the actual "
                        "state, looked up per request — the authentication "
                        "topic builds exactly that, with login cookies done "
                        "right as a live demo. Same-origin is the browser "
                        "policy all of this lives inside: two origins are "
                        "the same only when scheme, host, AND port all "
                        "match; script at http://localhost:5174 may not read "
                        "responses from http://localhost:8000 because the "
                        "ports differ. Note the honest asymmetry: cookies "
                        "are scoped by domain (optionally path), ignoring "
                        "scheme and port — cookie scoping is NOT the same "
                        "rule as the origin definition, which is exactly why "
                        "a dev server on :5174 proxying to :8000 is the "
                        "quiet life: with the proxy, there is only ever one "
                        "origin. This repo has no Set-Cookie anywhere yet "
                        "(nothing authenticates), so this section teaches "
                        "in prose and probes honestly — send a Cookie header "
                        "yourself and observe the server neither trusts nor "
                        "echoes it, because nothing parses it yet:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cookies-probe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# cookies the client would send — the server has no cookie parsing yet,\n"
                        "# so Cookie never appears in the echo (only x-* and the negotiation set do);\n"
                        "# mirror it into an x- header to see the value arrive:\n"
                        "curl -s -i -H 'Cookie: session=abc123' -H 'x-session-probe: abc123' \\\n"
                        "  localhost:8000/api/demo/http/headers | grep -iE 'set-cookie|x-session|HTTP/'\n"
                        "# the grep's silence on set-cookie is the honest answer: no session exists"
                    ),
                ),
            ],
        ),
        # ── 6. CORS ─────────────────────────────────────────────────────────
        Section(
            id="cors",
            title="CORS: what it is, and what it is not",
            blocks=[
                TextBlock(
                    kind="text",
                    id="cors-what",
                    text=(
                        "CORS is the most mis-taught mechanism in web "
                        "development, so start with what it is NOT: it is "
                        "not server security, and it does not block "
                        "anything by itself. It is a BROWSER-enforced "
                        "opt-in that relaxes the same-origin policy for "
                        "reads. The sequence: script at origin A fetches "
                        "origin B; the browser still SENDS the request "
                        "cross-origin; if B's response carries no Access-"
                        "Control-Allow-Origin that covers A, the browser "
                        "withholds the response from the SCRIPT (the server "
                        "was never protected — it already did the work; "
                        "curl and every non-browser client read it freely, "
                        "as the probe below shows). Servers opt in with "
                        "response headers: Access-Control-Allow-Origin "
                        "(exact origin, or * for public unauthenticated "
                        "resources), -Methods, -Headers, and — when cookies "
                        "or other credentials must ride along — Access-"
                        "Control-Allow-Credentials: true, at which point "
                        "* is forbidden and an exact origin is required. "
                        "Requests divide into two kinds. SIMPLE requests "
                        "(GET/HEAD/POST, only CORS-safelisted headers, "
                        "content-type limited to the form flavors and "
                        "text/plain) are sent directly and the response "
                        "headers are checked after the fact. Everything "
                        "else — a custom x-* header, JSON content-type, "
                        "DELETE/PATCH — triggers a PREFLIGHT: the browser "
                        "first sends OPTIONS with Access-Control-Request-"
                        "Method/Headers describing what it intends, and "
                        "only proceeds when the server approves; servers "
                        "can cache the approval with Access-Control-Max-"
                        "Age. That OPTIONS your framework auto-answers is "
                        "the preflight machine, not a bug. This guide's "
                        "development posture sidesteps all of it by design: "
                        "the browser talks only to the Vite dev server's "
                        "origin, and the proxy speaks to the API server-to-"
                        "server, where no same-origin policy exists "
                        "because no browser is involved:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cors-vite-proxy",
                    language="ts",
                    caption="Same-origin by construction: the browser never crosses origins in dev.",
                    source="client/vite.config.ts",
                    snippet=(
                        "const apiProxyTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000';\n"
                        "// …\n"
                        "      proxy: {\n"
                        "        '/api': { target: apiProxyTarget, ws: true }, // same-origin; ws carries the upgrade\n"
                        "      },"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cors-compose-env",
                    language="yaml",
                    caption="Inside compose the proxy targets the service name — still no browser in that hop.",
                    source=".docker/docker-compose.yml",
                    snippet=(
                        "    environment:\n"
                        "      # Inside compose the server is reachable by service name, not localhost.\n"
                        "      - API_PROXY_TARGET=http://server:8000"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cors-honesty",
                    text=(
                        "The production shape is the same trick with nginx "
                        "standing in for Vite (quoted in the TLS section): "
                        "one origin serves the shell and proxies /api, so "
                        "no cross-origin call ever happens. When this "
                        "guide's server finally DOES add CORS headers, in "
                        "the security topic, it will be for the legitimate "
                        "reason to have the mechanism: a browser client on "
                        "a DIFFERENT origin that the API deliberately "
                        "serves. Until then the honest probe answers 200 "
                        "with no Access-Control-Allow-Origin anywhere — "
                        "fine for the proxied shell (same-origin, the "
                        "browser checks nothing), and correctly unusable "
                        "by a cross-origin page's script:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cors-probe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# a browser would withhold this response's BODY from a cross-origin script;\n"
                        "# curl is not a browser, so you see everything — including the absence of\n"
                        "# any Access-Control-Allow-* header (this server has not opted in):\n"
                        "curl -s -i -H 'Origin: http://elsewhere:9999' localhost:8000/api/health"
                    ),
                ),
            ],
        ),
        # ── 7. TLS/HTTPS ────────────────────────────────────────────────────
        Section(
            id="tls-https",
            title="TLS and HTTPS",
            blocks=[
                TextBlock(
                    kind="text",
                    id="tls-handshake",
                    text=(
                        "HTTPS is HTTP spoken inside a TLS session, and the "
                        "handshake is worth one honest pass."
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="tls-handshake-steps-list",
                    ordered=True,
                    items=[
                        "ClientHello — the client opens TCP and sends the TLS "
                        "versions and cipher suites it knows, its key-share, "
                        "and two practically vital extensions — SNI (which "
                        "hostname it wants, so one IP can serve many "
                        "certificates) and ALPN (which application protocols "
                        "— http/1.1, h2 — it speaks, which is how HTTP/2 "
                        "gets negotiated without a separate round trip).",
                        "ServerHello plus CERTIFICATE CHAIN — the server "
                        "answers with a leaf certificate for the exact "
                        "hostname, the intermediates that link it upward, "
                        "ending at a root your client's trust store already "
                        "holds.",
                        "Client validation — chain signatures, the hostname "
                        "against the certificate's Subject Alternative "
                        "Names, validity dates.",
                        "Key exchange — (modern TLS 1.3) completes in the "
                        "same flight — the (EC)DHE inputs were already in "
                        "the hellos — and both sides derive symmetric "
                        "session keys; everything after is symmetric "
                        "encryption, fast by design. TLS 1.3 needs one round "
                        "trip (0-RTT on resumption); older TLS needed two.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="tls-hsts-and-posture",
                    text=(
                        "HSTS is the "
                        "response header (Strict-Transport-Security: "
                        "max-age=...) that tells browsers \"only ever "
                        "reach me over HTTPS\" — it exists because the one "
                        "unencrypted first request is a downgrade window; "
                        "it is trust-on-first-use and it commits the "
                        "browser, not the server. Where does TLS live in "
                        "this repo's production shape? At the proxy, and "
                        "only there — the family's deliberate posture. The "
                        "client's nginx container (config: .docker/client/"
                        "nginx.conf, whose language this guide's sourcing "
                        "ratchet exempts, hence cited in prose and quoted "
                        "below for reading) is the TLS termination point: "
                        "it would present the certificates, speak HTTPS to "
                        "browsers, and forward plain HTTP/1.1 to uvicorn "
                        "on the internal network:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tls-nginx-proxy",
                    language="nginx",
                    caption="Termination in one place: the proxy speaks to the app over plain HTTP/1.1.",
                    source=".docker/client/nginx.conf",
                    snippet=(
                        "    location /api/ {\n"
                        "        proxy_pass http://server:8000;\n"
                        "        proxy_http_version 1.1;\n"
                        "        proxy_set_header Upgrade $http_upgrade;\n"
                        "        proxy_set_header Connection 'upgrade';\n"
                        "        proxy_set_header Host $host;\n"
                        "        proxy_cache_bypass $http_upgrade;\n"
                        "    }"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tls-posture",
                    text=(
                        "Read those lines as posture: certificates live at "
                        "the edge where ACME renewal automation and HTTP/2 "
                        "for browsers belong; uvicorn CAN serve TLS itself "
                        "(uvicorn --ssl-keyfile/--ssl-certfile) and that is "
                        "fine for simple single-service deploys, but the "
                        "termination-at-proxy shape is what scales to "
                        "multiple backends, internal load balancers, and "
                        "zero application changes when certificates rotate "
                        "— the proxy_pass target never learns TLS "
                        "happened. The costs to keep honest: after "
                        "termination the app sees plain HTTP, so it must "
                        "know the real client scheme via forwarded headers "
                        "(X-Forwarded-Proto and friends — the deployment "
                        "and observability topics wire them properly "
                        "rather than trusting them blindly, since forged "
                        "forwarded headers are a classic SSRF-adjacent "
                        "bug), and the internal network is now a trust "
                        "boundary; mutual TLS or network segmentation are "
                        "the upgrades when that boundary is not physically "
                        "isolated. For this guide's dev stack none of this "
                        "is active yet — localhost over plain HTTP — which "
                        "is itself the honest third posture: local dev, "
                        "proxy-terminated prod, and direct TLS as the "
                        "exception, in that order of frequency in the "
                        "wild."
                    ),
                ),
            ],
        ),
        # ── 8. HTTP versions ────────────────────────────────────────────────
        Section(
            id="http-versions",
            title="HTTP versions: 1.1, 2, 3",
            blocks=[
                TextBlock(
                    kind="text",
                    id="versions-lineage",
                    text=(
                        "HTTP/1.0 opened a fresh TCP connection per request "
                        "and paid setup every time. HTTP/1.1 (1997, still "
                        "the workhorse) made persistent connections the "
                        "default — reuse the socket across requests — made "
                        "the Host header mandatory (one IP, many names: "
                        "name-based virtual hosting), and standardized "
                        "chunked transfer encoding for bodies of unknown "
                        "length. Its famous weakness is head-of-line "
                        "blocking at the request level: responses come back "
                        "in request order on a connection, so one slow "
                        "response stalls everything queued behind it; "
                        "browsers mitigate with ~6 parallel connections per "
                        "origin, which is a workaround, not a fix. HTTP/2 "
                        "(2015) replaced the text protocol with binary "
                        "framing: one TCP connection carries many "
                        "independent STREAMS — request/response pairs "
                        "interleaved in frames, headers compressed with "
                        "HPACK, prioritization expressible. This kills "
                        "HTTP-layer blocking; what survives is TCP-layer "
                        "blocking — one lost packet stalls the whole "
                        "connection until retransmission, because TCP "
                        "guarantees an ordered byte stream. HTTP/3 moves to "
                        "QUIC over UDP: TLS 1.3 integrated into the "
                        "transport, streams that retransmit independently "
                        "(transport-layer head-of-line blocking gone), "
                        "fewer round trips on connection setup, and "
                        "connection migration across IP changes (your "
                        "wi-fi-to-5G handover survives). What does THIS "
                        "server speak? HTTP/1.1, full stop — uvicorn "
                        "implements HTTP/1.1 (h11 by default; the "
                        "httptools accelerator rides in the standard "
                        "extra) and does not implement HTTP/2; modern "
                        "versions happen at the proxy edge, which is the "
                        "industry-norm division of labor the TLS section "
                        "already showed (browsers may speak h2 or h3 to "
                        "the proxy; the proxy speaks 1.1 upstream — its "
                        "proxy_http_version 1.1 line is in the nginx quote "
                        "above). ALPN is the mechanism that makes that "
                        "seamless: client and server agree the application "
                        "protocol during the TLS handshake:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="versions-uvicorn-dep",
                    language="toml",
                    caption="The app server's protocol engine, as declared.",
                    source="server/pyproject.toml",
                    snippet=(
                        "dependencies = [\n"
                        "    \"fastapi>=0.115\",\n"
                        "    # …\n"
                        "    \"uvicorn[standard]>=0.30\",\n"
                        "]"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="versions-probe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the wire, visible: request line, Host, and the 1.1 status line back\n"
                        "curl -sv -o /dev/null localhost:8000/api/health 2>&1 | grep -E '^(<|>) '"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="versions-coda",
                    text=(
                        "The probe shows the whole conversation curl had "
                        "with uvicorn: a GET line marked HTTP/1.1, the "
                        "mandatory Host header, and a 200 line in the same "
                        "version. Keep-alive means curl could immediately "
                        "reuse that connection for a second request — try "
                        "two URLs in one curl invocation and count the "
                        "connections. For a Python API server, that is the "
                        "correct amount of version engagement: speak 1.1 "
                        "well, let the edge speak everything else, and "
                        "know which layer owns which property."
                    ),
                ),
            ],
        ),
        # ── 9. Terminal companion ───────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="HTTP is a text protocol — read it raw, from the shell.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-pitch",
                    text=(
                        "With the stack up (server on :8000), this tour "
                        "exercises the topic against the real wire: status "
                        "line and headers with -i, the echo demo with a "
                        "custom header, a HEAD request, the same endpoint "
                        "over POST with a body, an honest content-"
                        "negotiation attempt, and the 404 envelope. Every "
                        "command is plain curl; python3 -m json.tool is "
                        "the only helper installed:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-health",
                    language="bash",
                    source=None,
                    snippet=(
                        "# status line, headers, body — the full response of the smallest endpoint\n"
                        "curl -s -i localhost:8000/api/health"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-index",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the curriculum index: http-web sits in foundations, order 3\n"
                        "curl -s localhost:8000/api/content | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-echo-get",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the demo, one custom header: echoed back, classified end-to-end\n"
                        "curl -s -i -H 'x-demo-trace: hello-http' localhost:8000/api/demo/http/headers"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-echo-post",
                    language="bash",
                    source=None,
                    snippet=(
                        "# same path over POST: a body, a content-type, and the parsed message back\n"
                        "curl -s -i -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"message\":\"via curl\"}' localhost:8000/api/demo/http/headers"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-head",
                    language="bash",
                    source=None,
                    snippet=(
                        "# HEAD asks for the GET's headers without a body — this stack answers\n"
                        "# 405: FastAPI routes match DECLARED methods, HEAD is not implicit, and\n"
                        "# the 405's allow header says exactly what is allowed\n"
                        "curl -s -I localhost:8000/api/health"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-negotiate",
                    language="bash",
                    source=None,
                    snippet=(
                        "# ask for HTML: the server answers 200 application/json anyway — no\n"
                        "# route branches on Accept (an honest posture, not an oversight)\n"
                        "curl -s -H 'Accept: text/html' localhost:8000/api/content/http-web \\\n"
                        "  -o /dev/null -w '%{http_code} %{content_type}\\n'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-404",
                    language="bash",
                    source=None,
                    snippet=(
                        "# unknown topic → 404, the shared error envelope, and x-request-id\n"
                        "curl -s -i localhost:8000/api/content/nope"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Notice what the tour never needed: a browser, a "
                        "GUI, or faith. Status lines, headers, and bodies "
                        "are text you can read; every claim this topic "
                        "made — hop-by-hop consumption, absent negotiation, "
                        "the envelope's shape — is one curl flag away. Even "
                        "the HEAD probe taught a truth you can verify: this "
                        "stack answers 405 with allow: GET, because routes "
                        "match their declared methods — protocols promise "
                        "semantics, implementations declare which they "
                        "honor. The next topic climbs one layer up this "
                        "same stack: FastAPI itself, the framework that "
                        "turns these protocol contracts into typed Python."
                    ),
                ),
            ],
        ),
    ],
)
