"""Topic 08 — middleware (second topic of the Request handling group).

The onion around routing — cross-cutting ASGI layers that see every
request before routing matches and every response after the handler
returns — taught against this server's own chain: the ASGI middleware
stack · @app.middleware and BaseHTTPMiddleware · pure ASGI middleware ·
ordering (last added is outermost) · exception handlers as the other
cross-cutting mechanism · what Starlette and FastAPI actually mount ·
custom patterns (request-id, request logging) — with the topic's live
demo (``middleware:pipeline``) inline in the first section, and the
terminal curl tour last.

Every code block quotes a real repo file (the snippet ratchet verifies
it): the composition root's middleware wiring, the request-id middleware
(the repo's first user layer), the pipeline demo's own pure-ASGI engine and
router, the error taxonomy's handler registration and envelope builder,
the app-info introspection, and the structlog pipeline.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="middleware",
    title="Middleware",
    subtitle=(
        "The onion around routing — ASGI layers that see every request on the "
        "way in and every response on the way out."
    ),
    group="request-handling",
    order=8,
    sections=[
        # ── 1. The ASGI middleware chain (inline demo) ──────────────────────
        Section(
            id="the-asgi-middleware-chain",
            title="The ASGI middleware chain",
            lead="The demo of this topic lives here — beside the teaching it proves.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="mw-pitch",
                    text=(
                        "Topic 04 walked a request through the pipeline — middleware, "
                        "then routing, then dependencies, then the endpoint — and then "
                        "spent its time at the destination. This topic takes the first "
                        "layer apart. A middleware is an ASGI application that wraps "
                        "another ASGI application: it holds the next layer as data and "
                        "runs code around awaiting it, which gives every layer exactly "
                        "two moments — code before the await sees the request on the "
                        "way IN, code after the await sees the response on the way "
                        "OUT. Stack the layers and you get an onion: the request "
                        "descends from the outermost layer to the router at the "
                        "center, the endpoint runs once, and the response ascends the "
                        "same layers in reverse. Routing (topic 07) is the terminal "
                        "app in the middle — middleware wraps the whole route table, "
                        "so a layer sees every request regardless of which route "
                        "matches, and no route can opt out."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="mw-wiring-code",
                    language="py",
                    caption="The composition root: one middleware, one handler table, side by side.",
                    source="server/guide/main.py",
                    snippet=(
                        "    app.state.scenario = ScenarioStore()\n"
                        "    app.state.span_log = SpanLog()\n"
                        "    app.state.content_registry = production_registry\n"
                        "\n"
                        "    app.add_middleware(RequestIdMiddleware)\n"
                        "    register_exception_handlers(app)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="mw-registration-text",
                    text=(
                        "add_middleware is the entire registration surface: it names a "
                        "class and hands the framework everything it needs to wrap one "
                        "more layer around the application. The chain composes at "
                        "STARTUP — Starlette builds it once, on the first request — so "
                        "there is no per-request assembly cost and no way to add a "
                        "layer mid-flight (the framework raises if you try after the "
                        "app has started). This app registers exactly one layer of its "
                        "own, RequestIdMiddleware, and the quote shows where it sits in "
                        "create_app: after the per-app state, right beside the "
                        "exception-handler registration it cooperates with (section "
                        "5), before any router is included. One line is the whole "
                        "cross-cutting surface so far — which is also why the layer "
                        "chosen for it had better be a good one. This topic's demo "
                        "makes the chain it joins observable, end to end:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="mw-demo-endpoint-code",
                    language="py",
                    caption="The demo endpoint — three live inputs, one payload, and a header proof.",
                    source="server/guide/presentation/routers/demo/middleware.py",
                    snippet=(
                        "@router.get(\"/pipeline\", response_model=MiddlewarePipelinePayload)\n"
                        "async def read_middleware_pipeline(request: Request) -> MiddlewarePipelinePayload:\n"
                        "    \"\"\"Serve the live middleware chain: composition, traced wrap order, request id.\"\"\"\n"
                        "    user_names = [middleware.cls.__name__ for middleware in request.app.user_middleware]\n"
                        "    return await build_middleware_pipeline_payload(\n"
                        "        stack_names=_built_stack_names(request.app),\n"
                        "        user_middleware_names=user_names,\n"
                        "        request_id=current_request_id(),\n"
                        "    )"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="middleware:pipeline",
                    title="The middleware pipeline",
                    description=(
                        "Run one request and watch the onion: the payload reports the "
                        "LIVE chain this app actually built — walked from the "
                        "outermost layer to the router — then replays exactly that "
                        "composition as a real in-memory pure-ASGI run, one tracing "
                        "layer per stack row, so the recorded events prove the wrap "
                        "order: request events descend, the handler runs once in the "
                        "middle, response events unwind in reverse. The requestId "
                        "field is the id the REAL RequestIdMiddleware assigned to the "
                        "very request fetching the payload — and the response's "
                        "x-request-id header carries the same value, stamped on the "
                        "way out. Try it with curl -i: both sides agree."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="mw-demo-coda",
                    text=(
                        "Three inputs make the payload honest. _built_stack_names "
                        "walks the RUNNING composition — the built chain, layer by "
                        "layer, down to the app's own router — so the stack rows are "
                        "what actually wraps every request, not a hardcoded claim "
                        "(that walk is quoted in the ordering section). The user "
                        "middleware names come from the declared registrations, which "
                        "is how each row gets classified framework, user, or router. "
                        "And current_request_id() reads the ambient id the real "
                        "request-id middleware bound before this handler started — "
                        "request-side evidence collected from inside the onion. The "
                        "response-side evidence rides for free: the x-request-id "
                        "header on this very response is stamped by that same "
                        "middleware AFTER the payload is built. The rest of the topic "
                        "covers the two ways to author a layer, the ordering rules, "
                        "the handler mechanism that shares the cross-cutting job, the "
                        "framework's own mounted layers, and the custom patterns "
                        "worth stealing."
                    ),
                ),
            ],
        ),
        # ── 2. @app.middleware + BaseHTTPMiddleware ─────────────────────────
        Section(
            id="app-middleware-and-basehttpmiddleware",
            title="@app.middleware and BaseHTTPMiddleware",
            blocks=[
                TextBlock(
                    kind="text",
                    id="bm-pitch",
                    text=(
                        "FastAPI offers two idioms for authoring the same layer. The "
                        "decorator — @app.middleware(\"http\") over a function taking "
                        "(request, call_next) — is sugar: FastAPI wraps the function "
                        "in BaseHTTPMiddleware for you. The class — subclass "
                        "BaseHTTPMiddleware, implement async def dispatch, register "
                        "with app.add_middleware(YourMiddleware) — is what this repo "
                        "uses, for the reasons classes usually win: the constructor "
                        "takes real dependencies, the layer is instantiable and "
                        "testable in isolation, and the registration site stays a "
                        "one-liner in the composition root. The security-headers "
                        "layer (topic 25) is the repo's living BaseHTTPMiddleware "
                        "specimen — the request-id middleware held this seat until "
                        "topic 28's SSE streams forced its conversion to pure ASGI "
                        "(the end of this section tells that story). A dispatch, "
                        "whole:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bm-dispatch-code",
                    language="py",
                    caption="A repo dispatch: forward the request, then stamp the response.",
                    source="server/guide/presentation/middleware/security_headers.py",
                    snippet=(
                        "    async def dispatch(\n"
                        "        self,\n"
                        "        request: Request,\n"
                        "        call_next: Callable[[Request], Awaitable[Response]],\n"
                        "    ) -> Response:\n"
                        "        \"\"\"Forward the request, then stamp headers on whatever comes back.\"\"\"\n"
                        "        response = await call_next(request)\n"
                        "        for name, value in _STATIC_HEADERS.items():\n"
                        "            response.headers[name] = value\n"
                        "        if request.url.path in _DOCS_PATHS:\n"
                        "            response.headers[\"Content-Security-Policy\"] = DOCS_CSP\n"
                        "        if request.url.scheme == \"https\":\n"
                        "            response.headers[HSTS_HEADER] = HSTS_VALUE\n"
                        "        return response"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bm-dispatch-read",
                    text=(
                        "dispatch replaces the raw ASGI call with two friendly "
                        "objects: a Request (parsed view of the scope — headers, "
                        "query, state) and a Response you return. Between them sits "
                        "call_next, which IS the rest of the onion — everything "
                        "inner, from the next middleware down through routing to the "
                        "endpoint — reduced to a single awaitable. So the method's "
                        "shape is the topic's whole model in miniature: lines before "
                        "the await are request-side, lines after it are "
                        "response-side. The try/finally is topic 01's context-manager "
                        "discipline applied to a middleware — the contextvar token is "
                        "reset no matter how the inner call ends — and it is the "
                        "same setup/teardown shape topic 06 showed in yield "
                        "dependencies, one layer further out. Note what the "
                        "response-side line does: mutate the Response object's "
                        "headers after call_next returns, which is precisely the "
                        "\"code after the await\" moment."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bm-caveat-intro",
                    text=(
                        "BaseHTTPMiddleware buys that readability at a real cost, and "
                        "this repo records the trade on the source file it paid — the "
                        "implementation-history section of the request-id "
                        "middleware's module docstring, quoted verbatim:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="bm-caveat-code",
                    language="py",
                    caption="The recorded trade-off, where the next editor will meet it.",
                    source="server/guide/core/request_context.py",
                    snippet=(
                        "Implementation history, on record: this layer began life as a\n"
                        "``BaseHTTPMiddleware`` subclass (readability first — the middleware topic\n"
                        "teaches that idiom with the security-headers layer). The caveat recorded\n"
                        "then came due in topic 28: ``BaseHTTPMiddleware`` bridges its friendly\n"
                        "``Request``/``Response`` objects through a per-request task, which buffers\n"
                        "the body and breaks streaming backpressure — server-sent events must flow\n"
                        "UNBUFFERED — and its http-only ``dispatch`` never sees websocket scopes at\n"
                        "all. Topic 28 rewrote it as the pure ASGI layer below: the request side\n"
                        "reads the raw scope, the response side stamps the header on the one\n"
                        "``http.response.start`` message as it passes (every body chunk flows\n"
                        "through untouched), and websocket scopes get the same contextvar + state\n"
                        "mirror — a websocket carries no response headers to stamp, so there the\n"
                        "id serves logging only."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bm-caveat-read",
                    text=(
                        "The mechanism behind the caveat: BaseHTTPMiddleware bridges "
                        "its friendly objects to raw ASGI by running call_next in a "
                        "per-request anyio task and feeding the response through a "
                        "channel, which means the Response you hold is a "
                        "re-assembled view and true streaming backpressure — the "
                        "server slowing the producer because the consumer is slow "
                        "(topic 02's streams) — does not survive the extra buffering. "
                        "For header-stamping that cost is zero, which is why the "
                        "security-headers layer above keeps the readable form; for "
                        "server-sent events and large downloads it is disqualifying. "
                        "Hence what happened, on schedule: when topic 28's realtime "
                        "work landed, the request-id layer was rewritten as pure "
                        "ASGI — the idiom the next section teaches, which is also "
                        "what both flavors compile down to. Its send-side stamping "
                        "is quoted in topic 28, right beside the SSE stream that "
                        "forced it."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="bm-decorator-read",
                    text=(
                        "About the decorator flavor, stated in prose because this repo "
                        "has none to quote: @app.middleware(\"http\") registers a "
                        "function with the same (request, call_next) shape as "
                        "dispatch, FastAPI wraps it in BaseHTTPMiddleware internals, "
                        "and the layer lands in the chain at the same position "
                        "add_middleware would put it. It is less ceremony for "
                        "one-off layers and more friction for anything serious — no "
                        "constructor means dependencies arrive as globals or "
                        "app.state lookups, and a bare function is harder to "
                        "instantiate in a test. The family rule of thumb falls out "
                        "of that: decorator for throwaway local experiments, class "
                        "for anything you intend to keep."
                    ),
                ),
            ],
        ),
        # ── 3. Pure ASGI middleware ──────────────────────────────────────────
        Section(
            id="pure-asgi-middleware",
            title="Pure ASGI middleware",
            blocks=[
                TextBlock(
                    kind="text",
                    id="asgi-pitch",
                    text=(
                        "Under both idioms sits the raw contract. An ASGI application "
                        "is a callable async def __call__(self, scope, receive, send) "
                        "— the (scope, receive, send) triple topic 04 met from the "
                        "server's side. scope is the dict of request facts (method, "
                        "path, headers) that routing also reads; receive is an "
                        "awaitable stream of inbound messages (request body chunks); "
                        "send is the outbound channel, where a response is literally "
                        "an http.response.start message carrying status and headers "
                        "followed by body messages. A pure ASGI middleware is just an "
                        "ASGI app that holds the next app and runs code around "
                        "awaiting it — no Request wrapper, no Response object, no "
                        "base class. The pipeline demo's engine is exactly that, and "
                        "it is real repo code:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="asgi-tracing-code",
                    language="py",
                    caption="The whole middleware idea in one class — the demo's tracing layer.",
                    source="server/guide/domain/demos/middleware_pipeline.py",
                    snippet=(
                        "class TracingMiddleware:\n"
                        "    \"\"\"Pure ASGI middleware: one event entering, one event exiting.\n"
                        "\n"
                        "    This is the whole middleware idea in one small class — hold the next\n"
                        "    ASGI app, run code BEFORE awaiting it (the request side), run code\n"
                        "    AFTER (the response side). No ``Request``/``Response`` objects and no\n"
                        "    base class: just the raw ``(scope, receive, send)`` contract every\n"
                        "    ASGI application already speaks.\n"
                        "    \"\"\"\n"
                        "\n"
                        "    def __init__(self, app: ASGIApp, stage: str, recorder: TraceRecorder) -> None:\n"
                        "        \"\"\"Wrap ``app``; events are recorded under ``stage``'s name.\"\"\"\n"
                        "        self._app = app\n"
                        "        self._stage = stage\n"
                        "        self._recorder = recorder\n"
                        "\n"
                        "    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:\n"
                        "        \"\"\"The ASGI call: descend, then unwind.\"\"\"\n"
                        "        self._recorder.record(self._stage, \"request\", f\"request descends through {self._stage}\")\n"
                        "        await self._app(scope, receive, send)\n"
                        "        self._recorder.record(\n"
                        "            self._stage, \"response\", f\"response ascends back through {self._stage}\"\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="asgi-tracing-read",
                    text=(
                        "Read it against section 2's dispatch and the mapping is "
                        "one-to-one. The constructor stores the wrapped app — "
                        "composition as plain data, which is why middleware can be "
                        "built, inspected, and wrapped again like any value. __call__ "
                        "records one event, awaits the inner app with the SAME scope, "
                        "receive, and send it was handed, then records another — those "
                        "two record calls are the request side and the response side, "
                        "the entire conceptual payload of the topic, with no "
                        "abstraction in between. The demo chains one of these per "
                        "stack row around a terminal endpoint app, using the same "
                        "wrapping loop Starlette itself uses:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="asgi-wraploop-code",
                    language="py",
                    caption="The wrapping loop: reversed names, so the first row ends up outermost.",
                    source="server/guide/domain/demos/middleware_pipeline.py",
                    snippet=(
                        "    app: ASGIApp = endpoint\n"
                        "    for name in reversed(stack_names[:-1]):\n"
                        "        app = TracingMiddleware(app, stage=name, recorder=recorder)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="asgi-wraploop-read",
                    text=(
                        "The loop wraps in REVERSED row order, so the first name in "
                        "the stack list is wrapped LAST and therefore sits outermost "
                        "— mirroring Starlette's build_middleware_stack, which lists "
                        "layers outermost-first and folds the list up from the router "
                        "end. That is also why the demo's terminal app records the "
                        "single handler event: it is the center of the onion, the "
                        "position routing occupies in the real app. The terminal then "
                        "sends a minimal two-message response — http.response.start, "
                        "then one body message — and those messages travel outward "
                        "through every layer's send, which is exactly the channel "
                        "every real response takes on its way to uvicorn."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="asgi-channel-read",
                    text=(
                        "Working at this level is more responsibility and more power. "
                        "Because you hold the channel, you can rewrite headers by "
                        "intercepting the start message before forwarding it, reject "
                        "early by sending your own response and simply not calling "
                        "the inner app, observe body chunks as they stream past, or "
                        "count bytes on the way out — things BaseHTTPMiddleware's "
                        "re-assembled Response makes awkward or impossible. Topic 06 "
                        "already used the same fact from the other direction: "
                        "SpanResponse stamped its event inside a Response object's "
                        "__call__, because a Response IS an ASGI app. The costs are "
                        "symmetrical: you must keep the channel honest (start "
                        "exactly once, before any body message; terminate bodies "
                        "correctly) and you give up the friendly objects. The "
                        "decision rule is the one the caveat section stated: default "
                        "to BaseHTTPMiddleware for readability; drop to pure ASGI "
                        "when streaming, backpressure, or protocol fidelity are the "
                        "point."
                    ),
                ),
            ],
        ),
        # ── 4. Middleware ordering ───────────────────────────────────────────
        Section(
            id="middleware-ordering",
            title="Middleware ordering",
            blocks=[
                TextBlock(
                    kind="text",
                    id="order-pitch",
                    text=(
                        "Order is the one part of middleware that behaves "
                        "counter-intuitively, so take it slowly. "
                        "app.add_middleware INSERTS the new layer at the FRONT of "
                        "the user-middleware list — so the LAST registration is the "
                        "OUTERMOST layer: it sees the request first and the response "
                        "last. Read create_app's add_middleware calls bottom-up and "
                        "you are reading the request order. This app registers one "
                        "layer, so today the rule is invisible — which is exactly why "
                        "the demo proves order from the running app instead of from "
                        "memory. Its payload's requestSideOrder and responseSideOrder "
                        "are two views of one walk:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="order-walk-code",
                    language="py",
                    caption="Order read from the truth: the built chain, walked to the router.",
                    source="server/guide/presentation/routers/demo/middleware.py",
                    snippet=(
                        "def _built_stack_names(app: FastAPI) -> list[str]:\n"
                        "    \"\"\"Walk the built chain outermost → the app's own router (the terminal).\"\"\"\n"
                        "    stack: ASGIApp = app.middleware_stack or app.build_middleware_stack()\n"
                        "    names: list[str] = []\n"
                        "    node: object = stack\n"
                        "    while node is not None and node is not app.router:\n"
                        "        names.append(type(node).__name__)\n"
                        "        node = getattr(node, \"app\", None)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="order-walk-read",
                    text=(
                        "The walk starts at the built chain's outermost callable and "
                        "follows each layer's app attribute — the same attribute the "
                        "tracing middleware's constructor stores — until it reaches "
                        "the application's own router, and the names come back in "
                        "request order because each layer's app IS the thing it "
                        "wraps. Two properties make this the right source. It reads "
                        "the RUNNING composition rather than a declared list, so the "
                        "payload cannot drift from what actually wraps requests. And "
                        "it is version-honest: FastAPI's own mounted layers appear "
                        "without anyone hardcoding them, which is how the demo knows "
                        "about layers that user_middleware does not list."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="order-bookends-read",
                    text=(
                        "The bookends around the user zone are fixed by the "
                        "framework, and they explain most ordering behavior. "
                        "Starlette always puts ServerErrorMiddleware outermost and "
                        "ExceptionMiddleware innermost, with the user layers between; "
                        "FastAPI adds ExceptionTelemetryMiddleware just inside the "
                        "server-error bookend and AsyncExitStackMiddleware just "
                        "inside the exception bookend (section 6 takes each in "
                        "turn). The consequences that matter day to day: exception "
                        "handlers run BENEATH every user layer, so user middleware "
                        "sees handler-built envelopes on the way out; and the "
                        "outermost bookend's own 500 responses never re-enter the "
                        "user zone at all. Ordering rules of thumb, in the "
                        "vocabulary those facts give you:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="order-rules-list",
                    ordered=False,
                    items=[
                        "Last added, first seen — add_middleware inserts at the front, "
                        "so the newest registration wraps everything older and meets "
                        "every request before any of them do.",
                        "Identify first — the request-id layer must sit outside "
                        "anything that logs or builds errors, or those lines lose "
                        "their correlation id; this app's single user layer wins by "
                        "construction.",
                        "Handlers run beneath you — ExceptionMiddleware dispatches "
                        "handlers inside the user zone, so your response-side code "
                        "sees the finished envelope — except bookend 500s, which "
                        "never re-enter.",
                        "Stamp outside transforms — a header set inside a compression "
                        "layer can be rewritten by it; layers that must speak the "
                        "final wire format belong outside transformers.",
                        "One composition root — every add_middleware call lives in "
                        "create_app; read them bottom-up as the request order, and "
                        "keep them together so the order is greppable.",
                        "Prove it, do not trust it — the pipeline demo's walk is the "
                        "check: requestSideOrder against the composition you "
                        "intended, from the running app.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="order-mistakes-read",
                    text=(
                        "The classic mistakes are all ordering mistakes wearing "
                        "disguises. CORS mounted inside compression breaks preflight "
                        "because the OPTIONS round-trip gets transformed before the "
                        "browser validates it. Authentication mounted outside the "
                        "request-id layer logs every rejection without an id. A "
                        "timing layer mounted innermost measures only the endpoint, "
                        "quietly excluding every framework and middleware cost — the "
                        "outermost position is the only one that sees the whole "
                        "onion. When a layer misbehaves, before debugging its code, "
                        "ask where it sits: the demo's stack panel answers for this "
                        "app, live."
                    ),
                ),
            ],
        ),
        # ── 5. Exception handlers as cross-cutting concerns ──────────────────
        Section(
            id="exception-handlers-as-cross-cutting",
            title="Exception handlers as cross-cutting concerns",
            blocks=[
                TextBlock(
                    kind="text",
                    id="exc-pitch",
                    text=(
                        "Middleware is one way to give an app a cross-cutting "
                        "behavior; exception handlers are the other. A handler is "
                        "not a wrapper but a dispatch entry: exception class in, "
                        "response-building function out, registered once at startup. "
                        "At request time, ExceptionMiddleware — the innermost "
                        "bookend — catches whatever the router lets escape, finds "
                        "the handler registered for the closest exception type, and "
                        "runs it. Where middleware is proactive (every request, both "
                        "directions), handlers are reactive (only failures, rendered "
                        "once). This app's entire handler table is wired by one "
                        "function from the error taxonomy, called from the line "
                        "beside add_middleware in section 1's quote:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="exc-register-code",
                    language="py",
                    caption="Four registrations: the taxonomy, validation, Starlette, last resort.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "def register_exception_handlers(app: FastAPI) -> None:\n"
                        "    \"\"\"Wire the taxonomy's handlers onto one app (called once per app).\"\"\"\n"
                        "    add = app.add_exception_handler\n"
                        "    add(AppError, handle_app_error)\n"
                        "    add(RequestValidationError, handle_request_validation_error)\n"
                        "    add(HTTPException, handle_http_exception)\n"
                        "    add(Exception, handle_unexpected_error)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="exc-register-read",
                    text=(
                        "Each registration answers one failure family. AppError is "
                        "the taxonomy's own type — domain and data layers raise it, "
                        "and its FailureKind maps to the truthful status (topic 04 "
                        "met the envelope). RequestValidationError is FastAPI's "
                        "signature/body/path validation failing — the 422 with "
                        "normalized {loc, msg, type} triples. HTTPException is "
                        "Starlette's, which keeps its status and takes the closest "
                        "kind bucket (routing's 405 from topic 07 landed here). And "
                        "bare Exception is the last resort — registered for "
                        "everything, so nothing escapes as a raw traceback. Because "
                        "dispatch is by exception type, your own layers can subclass "
                        "AppError later without touching this table. But that last "
                        "registration has a layering surprise hiding in it, recorded "
                        "where the surprise lives:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="exc-boundary-code",
                    language="py",
                    caption="The boundary fact: bookend responses never re-enter the stack.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        ") -> JSONResponse:\n"
                        "    \"\"\"Build the envelope JSONResponse, stamping the x-request-id header.\n"
                        "\n"
                        "    The header is set here (not only in the middleware) because responses\n"
                        "    produced by the outermost ServerErrorMiddleware never pass back through\n"
                        "    the middleware stack.\n"
                        "    \"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="exc-boundary-read",
                    text=(
                        "Register a handler for bare Exception and Starlette routes "
                        "it to ServerErrorMiddleware — the OUTERMOST layer, outside "
                        "every user middleware. A response produced there has "
                        "nothing outside it to pass back through, so it never "
                        "re-enters the stack: no user middleware sees it, and "
                        "nothing stamps the x-request-id header on the way out. That "
                        "is why the envelope builder sets the header itself, and why "
                        "it cannot rely on the request-id contextvar either — the "
                        "middleware's finally has already reset it during unwinding. "
                        "The lookup that survives both zones is two-step:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="exc-resolve-code",
                    language="py",
                    caption="Best-effort id lookup: contextvar inside, scope mirror outside.",
                    source="server/guide/core/request_context.py",
                    snippet=(
                        "def resolve_request_id(request: Request) -> str:\n"
                        "    \"\"\"Best-effort lookup: contextvar first, then the request's scope state.\n"
                        "\n"
                        "    Handlers running inside this middleware see the contextvar; the\n"
                        "    unhandled-exception handler runs outside it (ServerErrorMiddleware wraps\n"
                        "    user middleware) and reads the scope mirror instead.\n"
                        "    \"\"\"\n"
                        "    ambient = _request_id.get()\n"
                        "    if ambient:\n"
                        "        return ambient\n"
                        "    state_id = request.scope.get(\"state\", {}).get(\"request_id\")\n"
                        "    return state_id if isinstance(state_id, str) else \"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="exc-decision-read",
                    text=(
                        "The scope mirror from section 2's dispatch — "
                        "request.state.request_id — is what the second branch reads: "
                        "the ASGI scope outlives the contextvar's reset, so the "
                        "outermost handler still finds the id. One mechanism, two "
                        "lifetimes, and the demo's request-id round trip exercises "
                        "both zones on every green response and every 404. Choosing "
                        "between the two cross-cutting tools is now a shape "
                        "question: a concern that applies to every request in both "
                        "directions is middleware (ids, logging, CORS, compression); "
                        "a concern that renders specific failures is a handler "
                        "(envelopes, problem details); and some patterns are both "
                        "halves cooperating — request-id assigns and stamps in "
                        "middleware, embeds in handlers. Topic 30 takes the whole "
                        "taxonomy apart; here the lesson is the seam they share."
                    ),
                ),
            ],
        ),
        # ── 6. What Starlette mounts ─────────────────────────────────────────
        Section(
            id="what-starlette-mounts",
            title="What Starlette mounts",
            blocks=[
                TextBlock(
                    kind="text",
                    id="mounts-pitch",
                    text=(
                        "Every Starlette application — FastAPI included — builds the "
                        "same skeleton around its router, and FastAPI extends it with "
                        "layers of its own. You never register the skeleton "
                        "yourself; it is mounted by the stack builder at startup, "
                        "and your add_middleware calls fill the user zone in the "
                        "middle. The pipeline demo's stack panel is this app's "
                        "skeleton, row by row, so the catalog below can name each "
                        "one against something you can actually run:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="mounts-catalog-list",
                    ordered=True,
                    items=[
                        "ServerErrorMiddleware — Starlette's outermost bookend, "
                        "always present; last-resort 500s, and where the bare-"
                        "Exception handler runs (this app: the internal envelope).",
                        "ExceptionTelemetryMiddleware — FastAPI's seam just inside "
                        "it, observing exceptions that escape user middleware "
                        "before any handler answers.",
                        "The user zone — your add_middleware registrations, last "
                        "added outermost; this app's one row is "
                        "RequestIdMiddleware.",
                        "ExceptionMiddleware — Starlette's innermost bookend; "
                        "dispatches every registered exception handler, including "
                        "FastAPI's validation 422.",
                        "AsyncExitStackMiddleware — FastAPI's request-scoped exit "
                        "stack, where closeable resources unwind after the response "
                        "is sent.",
                        "The router — the terminal ASGI app: route matching (topic "
                        "07), dependencies (topic 06), the endpoint.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="mounts-honesty-read",
                    text=(
                        "Beyond the skeleton, Starlette SHIPS optional middleware "
                        "you mount on demand — CORSMiddleware for the browser "
                        "cross-origin protocol topic 03 taught, GZipMiddleware for "
                        "response compression, SessionMiddleware for signed-cookie "
                        "sessions, TrustedHostMiddleware for Host-header "
                        "allowlists. This app mounts none of them, and the guide "
                        "says so the honest way: an endpoint whose job is reporting "
                        "exactly that. The app-info demo from topic 04 is the "
                        "always-current list of what IS registered:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="mounts-appinfo-code",
                    language="py",
                    caption="Introspection through public surface: registrations as data.",
                    source="server/guide/presentation/routers/demo/fastapi.py",
                    snippet=(
                        "    return build_app_info_payload(\n"
                        "        title=app.title,\n"
                        "        version=app.version,\n"
                        "        environment=config.env,\n"
                        "        docs_url=app.docs_url,\n"
                        "        redoc_url=app.redoc_url,\n"
                        "        openapi_url=app.openapi_url,\n"
                        "        stack=_stack_versions(),\n"
                        "        middleware_names=[middleware.cls.__name__ for middleware in app.user_middleware],\n"
                        "        handler_names=_handler_names(app.exception_handlers),\n"
                        "        paths=app.openapi()[\"paths\"],\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="mounts-two-views-read",
                    text=(
                        "Notice the difference between this quote and section 4's "
                        "walk: app-info reads user_middleware and "
                        "exception_handlers — the DECLARED registrations — while the "
                        "pipeline demo walks the BUILT chain. That is why the two "
                        "payloads disagree usefully: app-info reports only the "
                        "names create_app registered, and the pipeline reports "
                        "every row of the built chain — the framework layers you "
                        "never registered included. "
                        "Neither is wrong; they answer different questions — what "
                        "did I add versus what actually wraps every request — and "
                        "you want both vocabulary and both endpoints when reasoning "
                        "about a production stack."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="mounts-boundary-read",
                    text=(
                        "One more mounted-surface fact, inherited from topic 07's "
                        "mount section: a mounted sub-app carries its OWN skeleton. "
                        "app.mount hands the inner application a path prefix and the "
                        "outer stack stops at the delegation — the outer user "
                        "middleware sees the request arrive and the response leave, "
                        "but nothing inner, and the inner app's ServerError "
                        "bookend answers its failures. Included routers share the "
                        "stack; mounted apps nest it. Restated in this topic's "
                        "terms, routing's share-or-isolate test still decides: "
                        "routes that should share this app's envelope, ids, and "
                        "logging belong in an included router; surfaces that must "
                        "deliberately not see this middleware get a mount."
                    ),
                ),
            ],
        ),
        # ── 7. Custom patterns (request-id / request logging) ────────────────
        Section(
            id="custom-patterns-request-id-and-logging",
            title="Custom patterns: request-id and request logging",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rid-pitch",
                    text=(
                        "The request-id middleware is the canonical custom layer — "
                        "small enough to hold in your head, useful enough to justify "
                        "itself on every project. The need: one request becomes many "
                        "log lines, one error envelope, one client report, and "
                        "possibly many service hops; correlating them needs one "
                        "value stamped onto all of those surfaces. The pattern has "
                        "four duties, and this repo's implementation is the "
                        "reference:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rid-assign-code",
                    language="py",
                    caption="Hostile-input discipline in three lines: strip, cap, mint.",
                    source="server/guide/core/request_context.py",
                    snippet=(
                        "REQUEST_ID_HEADER: str = \"x-request-id\"\n"
                        "_MAX_INBOUND_ID_LENGTH: int = 200\n"
                        "\n"
                        "_request_id: ContextVar[str] = ContextVar(\"fdg_request_id\", default=\"\")\n"
                        "\n"
                        "\n"
                        "def _assign_request_id(inbound: str | None) -> str:\n"
                        "    \"\"\"Normalize the inbound header: strip, cap at 200, default to uuid4 hex.\"\"\"\n"
                        "    candidate = (inbound or \"\").strip()[:_MAX_INBOUND_ID_LENGTH]\n"
                        "    return candidate or uuid4().hex"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="rid-duties-list",
                    ordered=True,
                    items=[
                        "Accept — the inbound x-request-id header is honored when "
                        "present, so a caller's own correlation id survives the trip "
                        "and comes back stamped on the response.",
                        "Mint — no inbound id means a fresh uuid4 hex; every "
                        "response is identifiable even when the caller sends "
                        "nothing.",
                        "Bind — a ContextVar carries the id across the whole await "
                        "chain (topic 02's async context), with a scope mirror for "
                        "the zone outside the middleware's lifetime.",
                        "Stamp — the response header is set on the way out, and "
                        "every error envelope embeds the same id via the handlers' "
                        "lookup from section 5.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="rid-defensive-read",
                    text=(
                        "The defensive posture is the teaching point. An inbound "
                        "header is attacker-controlled text: without the cap, a "
                        "hostile client sends a megabyte \"id\" and every log line, "
                        "error envelope, and response header for that request "
                        "carries the bloat. So the normalizer strips whitespace, "
                        "caps at 200 characters, and falls back to uuid4().hex — 32 "
                        "unpredictable hex characters, no dashes — when the result "
                        "is empty. That is the whole trust decision: caller ids are "
                        "echoed, never executed or parsed, and a garbage id degrades "
                        "to a fresh one instead of an error. The bind step is "
                        "equally deliberate: a contextvar, not a parameter, so the "
                        "fifty functions beneath the handler can read the id "
                        "without any of them growing an id argument — ambient "
                        "context with an explicit reset in the finally."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rid-logging-read",
                    text=(
                        "The sibling pattern, request logging, is half-built in this "
                        "repo today — stated honestly. Process-wide structured "
                        "logging exists from create_app's first line: every log "
                        "line renders as one JSON object with timestamp, level, and "
                        "event, machine-greppable from day one:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rid-configure-code",
                    language="py",
                    caption="The process-wide half of request logging, already real.",
                    source="server/guide/core/logging.py",
                    snippet=(
                        "    structlog.configure(\n"
                        "        processors=[\n"
                        "            structlog.processors.add_log_level,\n"
                        "            structlog.processors.TimeStamper(fmt=\"iso\"),\n"
                        "            structlog.processors.format_exc_info,\n"
                        "            structlog.processors.JSONRenderer(),\n"
                        "        ],\n"
                        "        wrapper_class=structlog.make_filtering_bound_logger(_numeric_level(level)),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rid-future-read",
                    text=(
                        "What does NOT exist yet is the per-request access-log "
                        "layer — the middleware that records method, path, status, "
                        "duration, and the request id once per request. It arrives "
                        "with observability (topic 33), where the request-id "
                        "contextvar becomes a bound log field and the layer's "
                        "dispatch times the whole onion with a perf_counter pair "
                        "around call_next. The shape is already fixed by this "
                        "topic's patterns: a BaseHTTPMiddleware (or pure ASGI once "
                        "streaming matters) that reads the ambient id, wraps "
                        "call_next, and logs exactly once on the way out — never "
                        "per-route, never swallowing the failure it reports. When "
                        "you write one, you will be recombining section 2's "
                        "dispatch skeleton with this section's id discipline; "
                        "nothing new is required, which is the sign the primitives "
                        "were right."
                    ),
                ),
            ],
        ),
        # ── 8. Terminal companion ────────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="The chain, read straight off the wire.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-pitch",
                    text=(
                        "With the stack up (server on :8000), this tour watches the "
                        "onion from the shell. The pipeline demo is the centerpiece; "
                        "the -i flags expose the x-request-id header — the "
                        "response-side proof the payload keeps promising — and "
                        "python3 -m json.tool keeps the tour dependency-free:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-index",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the declared curriculum: 8 topics now, three groups\n"
                        "curl -s localhost:8000/api/content | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# this topic, in full — it arrived through the same onion\n"
                        "curl -s localhost:8000/api/content/middleware | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-demo",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the demo: live stack, traced wrap order, the request id\n"
                        "curl -s localhost:8000/api/demo/middleware/pipeline | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-header",
                    language="bash",
                    source=None,
                    snippet=(
                        "# both sides agree: payload requestId == response x-request-id\n"
                        "curl -s -i localhost:8000/api/demo/middleware/pipeline | head -15"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-inbound",
                    language="bash",
                    source=None,
                    snippet=(
                        "# caller-supplied id survives the trip, capped and echoed\n"
                        "curl -s -i -H 'x-request-id: my-correlation-42' localhost:8000/api/demo/middleware/pipeline | head -15"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-404",
                    language="bash",
                    source=None,
                    snippet=(
                        "# failure path: envelope requestId == header, handler-made\n"
                        "curl -s -i localhost:8000/api/content/nope"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Every response in this tour carried an x-request-id — "
                        "assigned by the RequestId middleware on the way in, stamped "
                        "on the way out, embedded in the failure envelope by the "
                        "handlers, and matched by the demo's payload field each "
                        "time. That is the onion closed end to end: one request "
                        "through every middleware layer, observable from the shell. "
                        "The next topic follows the request the other direction — "
                        "inward past the middleware, into the Request object the "
                        "handler actually receives, the bodies it parses, and the "
                        "responses it shapes."
                    ),
                ),
            ],
        ),
    ],
)
