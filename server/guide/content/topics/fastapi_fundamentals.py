"""Topic 04 — fastapi-fundamentals: the framework itself, on this repo.

The machinery every endpoint in this server runs on, taught from the app's
own code: uv project scaffolding · the app factory and route registration ·
the anatomy of a router · the ASGI pipeline's ordering · the life of one
real request · error handling's first steps · what FastAPI adds over
Starlette · the honest gap map · the docs mounts with the topic's
app-introspection demo INLINE · the --reload dev workflow · the terminal
companion.

Every code block below quotes a real repo file (the snippet ratchet
verifies it); bash blocks are the sourcing-exempt exception, and the one
dockerfile quote is exempt by language while citing its path.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="fastapi-fundamentals",
    title="FastAPI, the framework",
    subtitle=(
        "The machinery under every endpoint this guide serves — the app "
        "factory, the request pipeline, the Starlette floor — and what it "
        "deliberately leaves out."
    ),
    group="framework",
    order=4,
    sections=[
        # ── 1. Setup: a uv project ──────────────────────────────────────────
        Section(
            id="setup",
            title="Setup: a uv project",
            blocks=[
                TextBlock(
                    kind="text",
                    id="setup-pitch",
                    text=(
                        "A FastAPI service begins as a Python project, and in 2026 the "
                        "sensible scaffold is uv — one Rust binary that owns the "
                        "interpreter, the virtualenv, dependencies, and the lockfile. "
                        "Where the ecosystem once needed pyenv plus venv plus pip "
                        "plus pip-tools:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="uv-commands-list",
                    ordered=False,
                    items=[
                        "`uv init` — produces a pyproject.toml and pins a "
                        ".python-version.",
                        "`uv add` — resolves and installs a dependency into .venv "
                        "while recording a range in the manifest.",
                        "`uv run` — executes inside that venv without activation "
                        "ceremony.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="setup-shape",
                    text=(
                        "This server is exactly that shape: five runtime dependencies, "
                        "a dev group for the toolchain, and a committed uv.lock that "
                        "is the real dependency contract — the manifest states ranges "
                        "(fastapi>=0.115), the lock pins exact versions, and every "
                        "install everywhere runs `uv sync --locked`, which refuses to "
                        "re-resolve. That discipline is the whole trick: Docker "
                        "builds, the devcontainer, and a fresh clone all converge on "
                        "byte-identical environments because none of them ever "
                        "improvise. The manifest, quoted real:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="setup-manifest",
                    language="toml",
                    caption="Five runtime dependencies — the honest advertisement.",
                    source="server/pyproject.toml",
                    snippet=(
                        "[project]\n"
                        "name = \"guide\"\n"
                        "version = \"0.1.0\"\n"
                        "description = \"FastAPI Developers Guide server: the typed content API that is the guide\"\n"
                        "requires-python = \">=3.13\"\n"
                        "dependencies = [\n"
                        "    \"fastapi>=0.115\",\n"
                        "    \"pydantic>=2.9\",\n"
                        "    \"pydantic-settings>=2.6\",\n"
                        "    \"structlog>=24.4\",\n"
                        "    \"uvicorn[standard]>=0.30\",\n"
                        "]"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="setup-dev-group",
                    language="toml",
                    caption="The toolchain rides in the PEP 735 dev group.",
                    source="server/pyproject.toml",
                    snippet=(
                        "[dependency-groups]\n"
                        "dev = [\n"
                        "    \"httpx>=0.27\",\n"
                        "    \"mypy>=1.13\",\n"
                        "    \"pytest>=8.3\",\n"
                        "    \"pytest-asyncio>=0.24\",\n"
                        "    \"ruff>=0.8\",\n"
                        "]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="setup-commands",
                    text=("Read the manifest as decisions:"),
                ),
                ListBlock(
                    kind="list",
                    id="manifest-decisions-list",
                    ordered=False,
                    items=[
                        "requires-python >=3.13 — because the code uses PEP 695 "
                        "generics and modern unions without apology.",
                        "uvicorn[standard] — because the standard extra pulls the "
                        "accelerated protocol parsers (httptools, plus uvloop on "
                        "platforms that want it).",
                        "httpx in dev only — because the test client needs it and "
                        "production does not.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="setup-toolchain",
                    text=(
                        "The dev group is a "
                        "PEP 735 dependency-group, not an extra — `uv sync` installs "
                        "it by default and production images pass --no-dev, so test "
                        "tooling never ships in a serving image. The canonical command "
                        "sequence, from nothing to a running server:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="setup-bash",
                    language="bash",
                    source=None,
                    snippet=(
                        "# scaffold: pyproject.toml + .python-version + .venv\n"
                        "uv init --python 3.13\n"
                        "# runtime deps (recorded as ranges, resolved into uv.lock)\n"
                        "uv add \"fastapi>=0.115\" \"pydantic>=2.9\" \"pydantic-settings>=2.6\" \\\n"
                        "  \"structlog>=24.4\" \"uvicorn[standard]>=0.30\"\n"
                        "# toolchain into the dev group\n"
                        "uv add --group dev pytest pytest-asyncio httpx ruff mypy\n"
                        "# the ONLY install command anyone ever runs:\n"
                        "uv sync --locked\n"
                        "# run inside the venv, no activation needed\n"
                        "uv run uvicorn guide.main:app --reload"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="setup-coda",
                    text=(
                        "One more discipline worth copying: this repo pins nothing at "
                        "the exact-version level in the manifest — ranges live there, "
                        "exact pins live in the lock, and the lock is committed. A "
                        "vulnerability fix means `uv lock --upgrade-package <name>` "
                        "followed by a lock diff in review, not a surprise re-resolve "
                        "on some CI machine at 2am. The dependency-management topic "
                        "(31) takes the whole lifecycle apart; here the takeaway is "
                        "narrower — the framework is a dependency like any other, and "
                        "a FastAPI app is a Python package first."
                    ),
                ),
            ],
        ),
        # ── 2. The app: FastAPI() + route decorators ────────────────────────
        Section(
            id="the-app",
            title="The app: FastAPI() and route decorators",
            blocks=[
                TextBlock(
                    kind="text",
                    id="app-pitch",
                    text=(
                        "The FastAPI instance is the application. Constructing one is "
                        "cheap and framework-free of ceremony — `FastAPI(title=..., "
                        "version=...)` builds an empty ASGI application whose identity "
                        "strings feed the generated docs, and everything else is "
                        "attached:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="app-attachments-list",
                    ordered=False,
                    items=[
                        "Middleware — with add_middleware.",
                        "Exception handlers — with add_exception_handler.",
                        "State — with app.state.",
                        "Routes — either one at a time through decorators "
                        "(@app.get(\"/path\") registers a handler directly on the "
                        "instance) or in groups through include_router, which grafts "
                        "an APIRouter's whole route table in.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="app-factory-story",
                    text=(
                        "This repo uses the factory pattern: "
                        "create_app() wires a fresh, fully independent application per "
                        "call, and the module-level `app` exists exactly once for the "
                        "ASGI server's entry string guide.main:app. The factory shape "
                        "is not decoration — the test suite builds one app per test "
                        "(isolated state, isolated DI container), and the alternative "
                        "single global instance would leak scenario toggles between "
                        "tests. The whole composition root, verbatim:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="app-factory",
                    language="py",
                    caption="create_app: identity, state, middleware, handlers, routers.",
                    source="server/guide/main.py",
                    snippet=(
                        "def create_app() -> FastAPI:\n"
                        "    \"\"\"Build one wired FastAPI application instance.\"\"\"\n"
                        "    config = get_config()\n"
                        "    configure_logging(config.log_level)\n"
                        "    app = FastAPI(title=APP_TITLE, version=__version__, lifespan=lifespan)\n"
                        "\n"
                        "    app.state.scenario = ScenarioStore()\n"
                        "    app.state.content_registry = production_registry\n"
                        "\n"
                        "    app.add_middleware(RequestIdMiddleware)\n"
                        "    register_exception_handlers(app)\n"
                        "\n"
                        "    app.include_router(health.router)\n"
                        "    app.include_router(content.router)\n"
                        "    app.include_router(demo_scenario.router)\n"
                        "    app.include_router(demo_py.router)\n"
                        "    app.include_router(demo_runtime.router)\n"
                        "    app.include_router(demo_http.router)\n"
                        "    app.include_router(demo_fastapi.router)\n"
                        "    return app"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="app-entry",
                    language="py",
                    caption="The process-level instance uvicorn imports.",
                    source="server/guide/main.py",
                    snippet="app: Final = create_app()",
                ),
                TextBlock(
                    kind="text",
                    id="app-coda",
                    text=(
                        "Two registration idioms deserve one contrast. Decorator "
                        "registration (@app.get) couples a handler to the one app "
                        "instance — fine for a five-route service, and deliberately "
                        "not what this repo does, because a handler defined on a "
                        "specific app cannot be reused by the test factory's fresh "
                        "apps. APIRouter registration decouples: each router module "
                        "owns a prefix and tags, handlers hang off the router, and any "
                        "number of apps can include it. That is why every route in "
                        "this guide lives on an APIRouter — the composition root "
                        "decides which apps get which routers, and the routers "
                        "themselves never know. Note also what the factory puts on "
                        "app.state: the scenario store and the validated content "
                        "registry, both process-wide singletons the request handlers "
                        "reach through dependencies — the DI topic (06) formalizes "
                        "that seam."
                    ),
                ),
            ],
        ),
        # ── 3. Anatomy of a router ──────────────────────────────────────────
        Section(
            id="anatomy-of-a-router",
            title="Anatomy of a router",
            blocks=[
                TextBlock(
                    kind="text",
                    id="anatomy-pitch",
                    text=(
                        "The smallest real router in this repo is the health probe, "
                        "and it is the right size to learn the whole anatomy — every "
                        "part of it reappears on every router in the guide. Read it "
                        "line by line:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="anatomy-health",
                    language="py",
                    caption="The health router, whole — every house idiom in 14 lines.",
                    source="server/guide/presentation/routers/health.py",
                    snippet=(
                        "router = APIRouter(prefix=\"/api\", tags=[\"health\"])\n"
                        "\n"
                        "\n"
                        "class HealthResponse(BaseModel):\n"
                        "    \"\"\"Wire shape of the health payload (the published OpenAPI contract).\"\"\"\n"
                        "\n"
                        "    status: Literal[\"ok\"]\n"
                        "    env: str\n"
                        "\n"
                        "\n"
                        "@router.get(\"/health\", response_model=HealthResponse)\n"
                        "def read_health(config: Annotated[AppConfig, Depends(get_config)]) -> HealthResponse:\n"
                        "    \"\"\"Report process liveness plus the environment it booted in.\"\"\"\n"
                        "    return HealthResponse(status=\"ok\", env=config.env)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="anatomy-parts",
                    text=(
                        "The module creates one APIRouter with a prefix (\"/api\") and "
                        "a tag (\"health\" — the OpenAPI grouping you see in /docs) — "
                        "so the decorator's path is relative, and the full route is "
                        "prefix + path. The response model is a pydantic BaseModel "
                        "declared NEXT to the handler, not in a schemas.py far away: "
                        "the wire contract and the code that fills it change "
                        "together, and `status: Literal[\"ok\"]` types the constant "
                        "so tightly that an invalid value is a type error. The "
                        "decorator itself is the registration AND the documentation: "
                        "@router.get(\"/health\", response_model=HealthResponse) "
                        "says method, path, and contract in one line, and "
                        "response_model is load-bearing — FastAPI validates and "
                        "serializes the return THROUGH it, so a handler cannot "
                        "accidentally leak a field that is not in the contract, and "
                        "the OpenAPI schema derives from the same declaration. The "
                        "handler signature is where dependency injection enters: "
                        "config: Annotated[AppConfig, Depends(get_config)] means \"I "
                        "need the app config; framework, supply it\" — no globals, no "
                        "service locator, and the same statement the test suite "
                        "overrides. The return is a typed value, not a Response: "
                        "returning the model lets FastAPI do the serialization "
                        "(200 by default; you reach for explicit JSONResponse when "
                        "you need custom status or headers, in the request-response "
                        "topic 09). One handler, three declarations — path, contract, "
                        "dependencies — and zero lines of framework plumbing inside "
                        "the function body. That ratio is the house style: thin "
                        "routers, everywhere."
                    ),
                ),
            ],
        ),
        # ── 4. The ASGI pipeline ────────────────────────────────────────────
        Section(
            id="asgi-pipeline",
            title="The ASGI pipeline: middleware → routing → dependencies → endpoint",
            blocks=[
                TextBlock(
                    kind="text",
                    id="pipeline-order",
                    text=(
                        "Topic 03 ended at uvicorn handing an ASGI scope to the app; "
                        "this is what happens inside. A FastAPI application is a "
                        "layered ASGI callable, and the layers run in a FIXED order "
                        "for every request:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="pipeline-layers-list",
                    ordered=True,
                    items=[
                        "Starlette's ServerErrorMiddleware — the outermost, always "
                        "present, not yours.",
                        "The user middleware stack — in reverse registration order "
                        "(add_middleware pushes onto a list that is built "
                        "outside-in).",
                        "The router",
                        "Dependency resolution — for the matched route",
                        "Request parsing and validation",
                        "The endpoint function",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="pipeline-unwind",
                    text=(
                        "Responses unwind the "
                        "same stack in mirror order, and an exception raised "
                        "anywhere below a middleware unwinds the same way, with "
                        "each exception handler given its chance as the stack "
                        "collapses. One consequence deserves bold type: user "
                        "middleware runs INSIDE ServerErrorMiddleware, so a response "
                        "produced by the last-resort unhandled-exception handler "
                        "never passes back through user middleware — this repo "
                        "learned that the hard way, and its own code documents it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pipeline-middleware",
                    language="py",
                    caption="User middleware, doing real work on every request.",
                    source="server/guide/core/request_context.py",
                    snippet=(
                        "    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:\n"
                        "        \"\"\"Bind the id for the duration of the exchange; stamp the response.\"\"\"\n"
                        "        if scope[\"type\"] not in (\"http\", \"websocket\"):\n"
                        "            # lifespan (and any future scope type) has no request to identify.\n"
                        "            await self.app(scope, receive, send)\n"
                        "            return\n"
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
                CodeBlock(
                    kind="code",
                    id="pipeline-handlers",
                    language="py",
                    caption="Exception handlers registered at the composition root.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "def register_exception_handlers(app: FastAPI) -> None:\n"
                        "    \"\"\"Wire the taxonomy's handlers onto one app (called once per app).\"\"\"\n"
                        "    # Handlers narrow `exc` below the Exception the base signature declares\n"
                        "    # (each is registered for exactly that narrower class) — hence the ignores.\n"
                        "    add = app.add_exception_handler\n"
                        "    add(AppError, handle_app_error)  # type: ignore[arg-type]\n"
                        "    add(RequestValidationError, handle_request_validation_error)  # type: ignore[arg-type]\n"
                        "    add(HTTPException, handle_http_exception)  # type: ignore[arg-type]\n"
                        "    add(Exception, handle_unexpected_error)"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pipeline-outermost-truth",
                    language="py",
                    caption="The ServerErrorMiddleware truth, in this repo's own words.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:\n"
                        "    \"\"\"Last-resort handler: 500 internal, generic message, traceback logged.\n"
                        "\n"
                        "    Registered for bare ``Exception``, so Starlette routes it to the\n"
                        "    outermost ServerErrorMiddleware — the response never re-enters the\n"
                        "    middleware stack, hence the header is stamped here.\n"
                        "    \"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pipeline-coda",
                    text=(
                        "Trace the middleware quote against the ordering: it is a "
                        "pure ASGI layer (rewritten from its original "
                        "BaseHTTPMiddleware form when topic 28's SSE streams made "
                        "the recorded streaming caveat real), and await "
                        "self.app(scope, receive, send) is precisely the hand-off "
                        "to the REST of the stack — routing onward — with "
                        "everything around that call the middleware's window to "
                        "act before and after. The contextvar set/reset pair "
                        "scopes the request id to exactly the handler's lifetime, "
                        "and the scope mirror exists ONLY because of the "
                        "outermost-handler truth: when handle_unexpected_error "
                        "runs, this middleware has already unwound, so the "
                        "envelope builder reads the id from the scope instead of "
                        "the contextvar. Ordering is not a "
                        "detail you fight; it is a contract you design around. The "
                        "middleware topic (08) rebuilds this stack layer by layer "
                        "with a live pipeline demo."
                    ),
                ),
            ],
        ),
        # ── 5. Life of a request ────────────────────────────────────────────
        Section(
            id="life-of-a-request",
            title="Life of a request",
            blocks=[
                TextBlock(
                    kind="text",
                    id="life-walk",
                    text=(
                        "One request, end to end, through code you have now read all "
                        "of. curl issues `GET /api/health`. uvicorn accepts the "
                        "connection, parses the request line and headers, and calls "
                        "the ASGI application with a scope describing method GET, "
                        "path /api/health, and the raw headers. The stack unwinds "
                        "inward: ServerErrorMiddleware (idle, watching for "
                        "catastrophe), then RequestIdMiddleware.__call__ — no "
                        "inbound x-request-id header, so _assign_request_id mints a "
                        "uuid4 hex, binds it to the contextvar, mirrors it into the "
                        "scope, and calls onward. The router matches the path "
                        "against its route table and finds the one registered by "
                        "the health router's decorator. FastAPI then resolves the "
                        "endpoint's dependencies — Depends(get_config) builds (or "
                        "returns the cached) AppConfig from the environment — and "
                        "there is no body to validate on a GET. The endpoint runs: "
                        "three lines, returning a HealthResponse. The way out "
                        "serializes that model against response_model into JSON, "
                        "stamps content-type: application/json, unwinds through the "
                        "request-id middleware (which adds the x-request-id header "
                        "it promised), and uvicorn writes status line, headers, and "
                        "the 27-byte body onto the socket. Watch it happen:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="life-curl",
                    language="bash",
                    source=None,
                    snippet=(
                        "curl -s -i localhost:8000/api/health\n"
                        "# HTTP/1.1 200 OK            ← uvicorn's status line\n"
                        "# server: uvicorn            ← the ASGI server names itself\n"
                        "# content-type: application/json\n"
                        "# x-request-id: 3289ab80…    ← minted by the middleware on the way out\n"
                        "# {\"status\":\"ok\",\"env\":\"dev\"}   ← HealthResponse, serialized"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="life-coda",
                    text=(
                        "Every layer left a fingerprint you can point at: the "
                        "x-request-id header is the middleware's, the JSON body is "
                        "the response model's, the 200 is the framework's default "
                        "for a returned value, and server: uvicorn is the transport "
                        "naming itself. When something fails, the same walk explains "
                        "the failure's shape: an unknown path dies at ROUTING (the "
                        "404 envelope), a bad body dies at VALIDATION (422, before "
                        "the endpoint runs), a raised AppError dies in the endpoint "
                        "and is caught by the registered handler — and each of those "
                        "responses still carries the request id, because every path "
                        "out of the process passes the same seams. That "
                        "explainability is the real argument for knowing the "
                        "pipeline: nothing in a request's behavior is left "
                        "unattributable."
                    ),
                ),
            ],
        ),
        # ── 6. Error handling: first steps ──────────────────────────────────
        Section(
            id="error-handling-first-steps",
            title="Error handling: first steps",
            blocks=[
                TextBlock(
                    kind="text",
                    id="errors-pitch",
                    text=(
                        "FastAPI's default error behavior is decent but not yours: "
                        "unhandled exceptions become plain 500s, validation failures "
                        "become a 422 array of pydantic noise, and nothing correlates "
                        "an error to a log line. So the first thing this app's "
                        "factory does after middleware is register its own taxonomy "
                        "— one typed error class, one envelope, every failure shape "
                        "the same. The shape in three quotes: the buckets, one "
                        "handler, and the wire model. Layers raise AppError with a "
                        "FailureKind; handlers translate to status + envelope; "
                        "nothing outside this module invents either:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="errors-kinds",
                    language="py",
                    caption="Eight buckets — the app's entire failure vocabulary.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "class FailureKind(StrEnum):\n"
                        "    \"\"\"The eight failure buckets every error in the app maps onto.\"\"\"\n"
                        "\n"
                        "    VALIDATION_FAILED = \"validation_failed\"\n"
                        "    UNAUTHORIZED = \"unauthorized\"\n"
                        "    FORBIDDEN = \"forbidden\"\n"
                        "    NOT_FOUND = \"not_found\"\n"
                        "    CONFLICT = \"conflict\"\n"
                        "    RATE_LIMITED = \"rate_limited\"\n"
                        "    SERVICE_UNAVAILABLE = \"service_unavailable\"\n"
                        "    INTERNAL = \"internal\""
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="errors-handler",
                    language="py",
                    caption="One handler: log with the request id, answer the envelope.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:\n"
                        "    \"\"\"AppError → its mapped status + envelope; logged with the request id.\"\"\"\n"
                        "    logger.warning(\n"
                        "        \"app_error\",\n"
                        "        request_id=resolve_request_id(request),\n"
                        "        kind=exc.kind.value,\n"
                        "        message=exc.message,\n"
                        "    )\n"
                        "    return _build_error_response(\n"
                        "        request,\n"
                        "        http_status_for(exc.kind),\n"
                        "        exc.kind,\n"
                        "        exc.message,\n"
                        "        exc.details,\n"
                        "        extra_headers=exc.headers,\n"
                        "    )"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="errors-envelope",
                    language="py",
                    caption="The error object every client sees, in every failure.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "class ErrorBody(CamelModel):\n"
                        "    \"\"\"The ``error`` object of the envelope; wire keys are camelCase.\"\"\"\n"
                        "\n"
                        "    code: str\n"
                        "    \"\"\"Machine-readable failure kind (e.g. ``not_found``).\"\"\"\n"
                        "\n"
                        "    message: str\n"
                        "    \"\"\"Human-readable, client-safe message.\"\"\"\n"
                        "\n"
                        "    request_id: str\n"
                        "    \"\"\"The request id from the request-context middleware.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="errors-coda",
                    text=(
                        "That is the whole first-steps contract: one taxonomy typed "
                        "end to end (the StrEnum values ARE the wire codes), statuses "
                        "derived from a single mapping (validation_failed → 422, "
                        "FastAPI-idiomatically), every failure logged with its "
                        "request id, and every response shaped "
                        "{error: {code, message, requestId}} — curl any bad path on "
                        "this server and that is what comes back, with the "
                        "x-request-id header matching the log line. The framework "
                        "contributed the registration mechanism "
                        "(add_exception_handler, plus RequestValidationError and "
                        "Starlette's HTTPException as the two framework-native "
                        "exception kinds worth translating); everything above the "
                        "registration is the app's own design. RFC 9457 problem "
                        "details, failure injection, and the full taxonomy walkthrough "
                        "are topic 30's depth — the shape is what matters here."
                    ),
                ),
            ],
        ),
        # ── 7. Starlette underneath ─────────────────────────────────────────
        Section(
            id="starlette-underneath",
            title="Starlette underneath",
            blocks=[
                TextBlock(
                    kind="text",
                    id="starlette-split",
                    text=(
                        "FastAPI is a thin, opinionated layer over Starlette, and the "
                        "split is worth knowing precisely because it predicts where "
                        "documentation lives. Starlette IS: the ASGI application "
                        "object and its middleware stack, routing, the Request and "
                        "Response types (JSONResponse, StreamingResponse, "
                        "RedirectResponse...), the exception-handling machinery, "
                        "StaticFiles, WebSockets, and TestClient. FastAPI ADDS "
                        "exactly three big ideas on top: validation and "
                        "serialization via pydantic (declare a body or response_model, "
                        "get coercion and 422s), dependency injection via Depends "
                        "(declare parameters, get resolution, caching, overrides), "
                        "and OpenAPI generation (the schema in /openapi.json is "
                        "derived from your declarations — routes, response models, "
                        "tags — not written by hand). You can see the split in this "
                        "repo's own import sites:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="starlette-imports-errors",
                    language="py",
                    caption="The error module's imports: FastAPI's re-exports beside Starlette's own.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "import structlog\n"
                        "from fastapi import FastAPI, Request\n"
                        "from fastapi.exceptions import RequestValidationError\n"
                        "from starlette.exceptions import HTTPException\n"
                        "from starlette.responses import JSONResponse"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="starlette-imports-middleware",
                    language="py",
                    caption="Middleware: pure Starlette machinery, imported as such.",
                    source="server/guide/core/request_context.py",
                    snippet=(
                        "from fastapi import Request\n"
                        "from starlette.datastructures import Headers, MutableHeaders\n"
                        "from starlette.types import ASGIApp, Message, Receive, Scope, Send"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="starlette-imports-tests",
                    language="py",
                    caption="TestClient: built by Starlette on httpx, re-exported by FastAPI.",
                    source="server/tests/conftest.py",
                    snippet=(
                        "import pytest\n"
                        "from fastapi import FastAPI\n"
                        "from fastapi.testclient import TestClient\n"
                        "\n"
                        "from guide.core.config import get_config"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="starlette-coda",
                    text=(
                        "Those imports are deliberate citations, not accidents you "
                        "clean up: RequestValidationError is FastAPI's (it wraps "
                        "pydantic's errors — validation is FastAPI's contribution), "
                        "while HTTPException and JSONResponse are Starlette's, "
                        "fastapi merely re-exporting them for convenience; the "
                        "request-id middleware imports its whole toolkit — Headers, "
                        "MutableHeaders, the ASGI type aliases — from Starlette, "
                        "machinery that knows nothing of pydantic; and "
                        "fastapi.testclient.TestClient is "
                        "literally Starlette's TestClient passed through. The "
                        "practical payoff of knowing the boundary: when you read "
                        "FastAPI docs and the feature is really routing, responses, "
                        "or middleware, the authoritative detail lives in "
                        "Starlette's documentation — and when a bug seems to be in "
                        "\"FastAPI's\" responses, you are probably holding a "
                        "Starlette issue. This guide names the layer it means "
                        "throughout; the middleware topic (08) goes deeper into "
                        "Starlette's stack, and the api-documentation topic (12) "
                        "covers the OpenAPI generation that is FastAPI's own."
                    ),
                ),
            ],
        ),
        # ── 8. What FastAPI leaves out ──────────────────────────────────────
        Section(
            id="what-it-leaves-out",
            title="What FastAPI leaves out",
            blocks=[
                TextBlock(
                    kind="text",
                    id="gaps-pitch",
                    text=(
                        "FastAPI is a web framework, not an application platform, "
                        "and its scope discipline is a feature: the core gives you "
                        "routing, validation, DI, and docs, and leaves the rest to "
                        "explicitly chosen libraries — which this guide then teaches "
                        "one at a time. The honest gap map, each entry pointing at "
                        "the topic that fills it:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="gaps-map-list",
                    ordered=False,
                    items=[
                        "No database layer at all — no ORM, no connection pooling, "
                        "no query builder; the data topics build it deliberately "
                        "(sql-schema 16 designs tables, databases-sql 17 drives them "
                        "with asyncpg and Alembic migrations, sqlalchemy-orm 18 adds "
                        "the ORM on top).",
                        "No authentication or authorization — nothing in the "
                        "framework verifies who is calling; the authentication topic "
                        "(23) builds login cookies, API keys, and JWT, and "
                        "authorization (24) turns identity into permissions; "
                        "FastAPI's OAuth2 helpers are OpenAPI declarations, not "
                        "verification.",
                        "No sessions — HTTP is stateless and the framework keeps it "
                        "that way; session state is a storage decision (23 again, "
                        "with the redis topic 20 as the usual backing store).",
                        "No rate limiting — a framework-level hook exists "
                        "(middleware or a dependency — both taught), but the policy "
                        "and counters are yours; the security topic (25) implements "
                        "it.",
                        "No migrations — Alembic is a separate tool with its own "
                        "topic (17).",
                        "No background workers or schedulers — BackgroundTasks "
                        "exists for fire-and-forget in-process work, and its honest "
                        "limits — process lifetime, no retries — are exactly why the "
                        "background-jobs topic (29) graduates to real queues.",
                        "No template engine and no static serving beyond a mount you "
                        "wire yourself (next section); this app serves JSON and lets "
                        "the React shell own the browser.",
                        "No config management beyond pydantic-settings, which this "
                        "repo already uses and topic 36 takes further.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="gaps-more",
                    text=(
                        "None of these omissions are defects to route around — "
                        "they are the boundary that keeps the framework auditable. "
                        "The framework's job is the request; everything that "
                        "outlives a request is yours to design, and the rest of "
                        "this curriculum is that design."
                    ),
                ),
            ],
        ),
        # ── 9. Docs mounts and static files (inline demo) ───────────────────
        Section(
            id="static-and-docs-mounts",
            title="Docs mounts and static files",
            lead="This section carries the topic's demo — the app introducing itself.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="docs-pitch",
                    text=(
                        "Three routes on this application cost zero lines of your "
                        "code: /docs (interactive Swagger UI), /redoc (the "
                        "reference-style renderer), and /openapi.json (the machine "
                        "contract itself). They are constructor parameters — "
                        "docs_url, redoc_url, openapi_url — defaulted on, and "
                        "disablable by passing None when an API must not advertise "
                        "itself. The schema the docs render is GENERATED from what "
                        "you already declared: every route, parameter, and "
                        "response_model in this guide is in /openapi.json without a "
                        "single line of schema written by hand (the generation's "
                        "anatomy is topic 12). The /docs page is a small HTML shell "
                        "that loads Swagger UI from a CDN by default — fine for "
                        "development, and the deployment topic (37) shows the "
                        "self-hosted-assets posture for networks that cannot reach "
                        "one. Static files are the same idea, one step more manual: "
                        "Starlette's StaticFiles app plus app.mount(\"/static\", "
                        "StaticFiles(directory=\"static\")) serves a directory as a "
                        "sub-application — and this repo mounts none, honestly, "
                        "because a JSON API with a separate browser shell has "
                        "nothing static to serve. Which raises the question this "
                        "topic's demo answers: what IS actually on this app? Ask it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="docs-demo-router",
                    language="py",
                    caption="The demo endpoint: public introspection, no private APIs.",
                    source="server/guide/presentation/routers/demo/fastapi.py",
                    snippet=(
                        "@router.get(\"/app-info\", response_model=FastApiAppInfoPayload)\n"
                        "def read_app_info(\n"
                        "    request: Request, config: Annotated[AppConfig, Depends(get_config)]\n"
                        ") -> FastApiAppInfoPayload:\n"
                        "    \"\"\"Introspect the running app: identity, stack, wiring, and route table.\"\"\"\n"
                        "    app = request.app\n"
                        "    return build_app_info_payload(\n"
                        "        title=app.title,\n"
                        "        version=app.version,\n"
                        "        environment=config.env,\n"
                        "        # …\n"
                        "        paths=app.openapi()[\"paths\"],\n"
                        "    )"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="docs-demo-routes",
                    language="py",
                    caption="The route table's source: the OpenAPI schema, not app.routes.",
                    source="server/guide/domain/demos/fastapi_app_info.py",
                    snippet=(
                        "def _route_entry(path: str, item: Mapping[str, Any]) -> RouteEntry:\n"
                        "    \"\"\"Extract one route row: declared methods uppercased, tags unioned.\"\"\"\n"
                        "    methods = sorted(key.upper() for key in item if key in _HTTP_METHODS)\n"
                        "    tags = sorted(\n"
                        "        {\n"
                        "            tag\n"
                        "            for key, operation in item.items()\n"
                        "            if key in _HTTP_METHODS\n"
                        "            for tag in _tag_list(operation)\n"
                        "        }\n"
                        "    )\n"
                        "    return RouteEntry(path=path, methods=methods, tags=tags)"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="fastapi:app-info",
                    title="The app, introduced by itself",
                    description=(
                        "GET /api/demo/fastapi/app-info introspects the very server "
                        "serving this page: title, version, environment, the docs "
                        "mounts, the fastapi/starlette/pydantic versions, the "
                        "registered middleware and exception handlers, and the full "
                        "route table — built from the public OpenAPI schema, "
                        "including the endpoint you are calling right now."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="docs-coda",
                    text=(
                        "The route table's source is a deliberate lesson: it is "
                        "built from app.openapi()[\"paths\"], not app.routes, "
                        "because FastAPI's include_router (since 0.143) wraps "
                        "included routes and the wrapping entries expose no .path — "
                        "the OpenAPI schema is the stable public view of the "
                        "declared API, it is cached after the first call, and it "
                        "honestly contains no implicit HEAD or OPTIONS because this "
                        "framework routes only what you declared (topic 03's 405 "
                        "probe). Notice, reading the demo, that the three docs "
                        "mounts appear in the payload's docs object but NOT in the "
                        "route table — they live outside the schema, serving the "
                        "contract rather than being part of it. The endpoint is also "
                        "its own final proof: find /api/demo/fastapi/app-info GET "
                        "in the table, and note that the demo you are reading was "
                        "served through the very pipeline it displays."
                    ),
                ),
            ],
        ),
        # ── 10. The dev workflow: --reload ──────────────────────────────────
        Section(
            id="dev-workflow",
            title="The dev workflow: --reload",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dev-pitch",
                    text=(
                        "The inner loop is: edit, save, refresh — and uvicorn's "
                        "--reload flag is what makes that true. In reload mode "
                        "uvicorn watches the source tree and, on any change, "
                        "gracefully finishes in-flight requests and restarts the "
                        "application process with the new code. One caveat worth "
                        "learning the honest way, because this repo measured it: "
                        "a half-save with a syntax error takes the server DOWN, "
                        "not back to the old code — the reloader prints the "
                        "traceback and refuses connections until your next save "
                        "imports cleanly. The right response to a sudden "
                        "connection-refused during editing is to finish the save "
                        "and retry, not to diagnose. This repo's dev stack runs "
                        "exactly that, and the wiring is the interesting part — "
                        "the compose server service bind-mounts live source over "
                        "the image's code while an anonymous volume shields the "
                        "image-built venv, so edits land hot without ever touching "
                        "dependencies:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dev-compose-mounts",
                    language="yaml",
                    caption="Live source in, venv shielded: the reload stack's wiring.",
                    source=".docker/docker-compose.yml",
                    snippet=(
                        "    volumes:\n"
                        "      # Live source; anonymous volume over /app/.venv keeps the image-built\n"
                        "      # venv and keeps it off the host.\n"
                        "      - ./../server:/app\n"
                        "      - /app/.venv\n"
                        "      # Named uv cache (shared with the host-side verification runs): first\n"
                        "      # boot skips the full dependency download.\n"
                        "      - fdg-uv:/root/.cache/uv"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dev-cmd",
                    language="dockerfile",
                    caption="The dev server's actual command — the venv's uvicorn, reload on.",
                    source=".docker/server/Dockerfile",
                    snippet=(
                        "# The venv binary directly (not `uv run`): no implicit sync at boot — the\n"
                        "# anonymous /app/.venv volume is already seeded with exactly these deps.\n"
                        "CMD [\".venv/bin/uvicorn\", \"guide.main:app\", \"--reload\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dev-coda",
                    text=(
                        "The day-to-day flow is the devcontainer: open the repo in "
                        "the container, and the compose stack is already up — server "
                        "reloading on :8000, Vite shell proxying on :5174, data "
                        "services alongside; you edit on the host, code arrives "
                        "bind-mounted, and a save is live within a second. The "
                        "caveats worth internalizing early:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="reload-caveats-list",
                    ordered=False,
                    items=[
                        "--reload is a DEV tool only — production runs plain "
                        "uvicorn, no watcher (topic 37).",
                        "Every reload is a process restart, so in-memory state "
                        "resets — this repo's scenario toggle honestly forgets your "
                        "PATCH on each reload because ScenarioStore is process "
                        "state.",
                        "Reload watches code, not configuration — env vars are read "
                        "at boot, so an FDG_ change wants a container restart, not a "
                        "save.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="dev-dockerfile-detail",
                    text=(
                        "The Dockerfile comment carries one "
                        "more deliberate detail: the CMD invokes the venv's uvicorn "
                        "binary directly rather than `uv run`, refusing the implicit "
                        "sync at boot — in a container whose venv arrives by volume, "
                        "the fastest boot is the one that trusts what is already "
                        "installed."
                    ),
                ),
            ],
        ),
        # ── 11. Terminal companion ──────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="The framework's own surfaces, read from the shell.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-pitch",
                    text=(
                        "With the stack up (server on :8000), this tour walks the "
                        "framework fundamentals against the live app: the docs "
                        "mounts, the generated contract, the pipeline's fingerprints "
                        "on /api/health, the app-info demo, and this topic's own "
                        "content payload. Plain curl; python3 -m json.tool is the "
                        "only helper:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-docs",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the Swagger UI mount: an HTML page, generated, zero code of ours\n"
                        "curl -s -o /dev/null -w '%{http_code} %{content_type}\\n' localhost:8000/docs\n"
                        "# 200 text/html; charset=utf-8\n"
                        "#\n"
                        "# trailing slash? Starlette's redirect_slashes answers 307 to the canonical path\n"
                        "curl -s -o /dev/null -w '%{http_code} %{redirect_url}\\n' localhost:8000/docs/"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-openapi",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the machine contract: every route/model, generated from declarations\n"
                        "curl -s localhost:8000/openapi.json | python3 -m json.tool | head -n 12"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-health",
                    language="bash",
                    source=None,
                    snippet=(
                        "# one request, every layer's fingerprint: status line, server header,\n"
                        "# the middleware's x-request-id, the response model's JSON body\n"
                        "curl -s -i localhost:8000/api/health"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-demo",
                    language="bash",
                    source=None,
                    snippet=(
                        "# this topic's demo: the app's identity, wiring, and route table\n"
                        "curl -s localhost:8000/api/demo/fastapi/app-info | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-topic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# this page itself, as the content API serves it (sections → blocks)\n"
                        "curl -s localhost:8000/api/content/fastapi-fundamentals | python3 -m json.tool | head -n 14"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Everything the tour touches was declared in this topic's "
                        "quotes: the docs mounts are constructor defaults, the "
                        "schema is generated from the routers' decorators and "
                        "response models, the health response carries the "
                        "middleware's header, and the demo endpoint's own entry "
                        "sits in the route table it serves. The next topic descends "
                        "into the layer every one of those declarations leans on: "
                        "pydantic, the validation engine that makes a typed "
                        "boundary out of a function signature."
                    ),
                ),
            ],
        ),
    ],
)
