"""Topic 06 — fastapi-dependencies: Depends, the framework's composition story.

Taught from the repo's own wiring: why DI belongs at a composition root ·
Depends basics on the real scenario store · dependency trees · yield
dependencies with setup/teardown that provably runs after the response ·
classes and callables as dependencies · caching, scoping, and the
threadpool fact (measured, not asserted) · dependency_overrides for tests
· dependencies as the shape of cross-cutting concerns — with the topic's
two demos INLINE (dep:lifecycle on yield dependencies, dep:matrix on
cross-cutting concerns) and the terminal companion closing.

Every code block below quotes a real repo file (the snippet ratchet
verifies it); bash blocks are the sourcing-exempt exception. The
request-span instrument in guide/presentation/dependencies/request_span.py
was written for this topic and is quoted by it and by topic 01's
context-manager section alike — production code, not an exhibit.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="fastapi-dependencies",
    title="Dependencies: Depends",
    subtitle=(
        "FastAPI's inversion-of-control story — how handlers declare what "
        "they need, the framework wires it, trees of providers resolve it, "
        "yield spans close after the response, and tests swap the whole "
        "thing with one override."
    ),
    group="framework",
    order=6,
    sections=[
        # ── 1. The DI idea ──────────────────────────────────────────────────
        Section(
            id="the-di-idea",
            title="The DI idea",
            blocks=[
                TextBlock(
                    kind="text",
                    id="di-pitch",
                    text=(
                        "Every handler needs things it did not create: "
                        "configuration, a store, a database session, the "
                        "identity of the caller. There are three bad ways to "
                        "get them:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="di-bad-ways-list",
                    ordered=False,
                    items=[
                        "A module-level global — hidden coupling, untestable, "
                        "wrong per-request.",
                        "Constructing them inside the handler — the handler now "
                        "knows how to build the world, and you rebuild it per "
                        "call.",
                        "A service locator the handler queries — inversion of "
                        "control in name only: the handler still fetches.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="di-fourth-option",
                    text=(
                        "Dependency inversion is the honest fourth option: "
                        "the handler DECLARES what it needs as a typed "
                        "parameter, and something else — as close to the edge "
                        "as possible — decides what to hand it. In FastAPI "
                        "the declaration is Depends(provider) and the "
                        "resolver is the framework itself, per request."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="di-composition-root",
                    text=(
                        "Where do the real objects come from? A composition "
                        "root: ONE place, at startup, where concrete things "
                        "are constructed and attached. This server's is "
                        "create_app() — it builds process-wide state and "
                        "hangs it on app.state, where providers find it by "
                        "request. The discipline that makes this DI rather "
                        "than globals-with-extra-steps: handlers never touch "
                        "app.state directly — they depend on providers, and "
                        "the providers are the only code that knows where "
                        "the singletons live. One wiring decision, one file:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="di-state-wiring",
                    language="py",
                    caption="The composition root's entire state wiring.",
                    source="server/guide/main.py",
                    snippet=(
                        "    app.state.scenario = ScenarioStore()\n"
                        "    app.state.span_log = SpanLog()\n"
                        "    app.state.content_registry = production_registry"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="di-family",
                    text=(
                        "The family contrast is instructive. Spring Boot "
                        "gives you a container: components are discovered, "
                        "scoped, injected by annotation, and a failure to "
                        "satisfy a bean graph is a boot-time event. FastAPI "
                        "is deliberately smaller: there is no container "
                        "object, no component scan, no scope taxonomy — a "
                        "dependency is any callable, its lifetime is the "
                        "request unless you decide otherwise, and the wiring "
                        "is visible Python you can read in five minutes. "
                        "What you keep is the essential part: the handler "
                        "depends on declarations, the composition root owns "
                        "construction, and tests replace providers without "
                        "touching either. What you give up — framework-"
                        "managed singletons, prototypes, request/session "
                        "scopes — turns out to be little loss, because a "
                        "provider function plus lru_cache or app.state "
                        "expresses each of those in plain code. The rest of "
                        "this topic walks the mechanism from the simplest "
                        "function dependency to override-powered tests."
                    ),
                ),
            ],
        ),
        # ── 2. Depends basics ───────────────────────────────────────────────
        Section(
            id="depends-basics",
            title="Depends basics",
            blocks=[
                TextBlock(
                    kind="text",
                    id="basics-pitch",
                    text=(
                        "The grammar is one import and one wrapper: a "
                        "parameter annotated with Depends(provider) tells "
                        "FastAPI to call provider() (or await it) during "
                        "request resolution and pass the result as that "
                        "parameter. The provider can be any callable — "
                        "function, class, instance with __call__ — and its "
                        "return type annotation is what the handler's "
                        "parameter effectively becomes for tooling. This is "
                        "not a framework-parallel type system: it is the "
                        "same introspection machinery topic 01 showed you "
                        "(FastAPI resolves your signature's annotations at "
                        "startup with typing.get_type_hints), which is why "
                        "a dependency's type errors are caught by mypy and "
                        "its wiring is visible to your editor. The guide's "
                        "most-used real dependency is the scenario store:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="basics-get-store",
                    language="py",
                    caption="A real dependency: find the store, verify it, hand it over.",
                    source="server/guide/core/scenario.py",
                    snippet=(
                        "def get_scenario_store(request: Request) -> ScenarioStore:\n"
                        "    \"\"\"FastAPI dependency: the app's scenario store (wired in create_app).\"\"\"\n"
                        "    store = request.app.state.scenario\n"
                        "    if not isinstance(store, ScenarioStore):\n"
                        "        raise AppError(FailureKind.INTERNAL, \"Scenario store not wired on app.state\")\n"
                        "    return store\n"
                        "\n"
                        "\n"
                        "ScenarioStoreDep = Annotated[ScenarioStore, Depends(get_scenario_store)]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="basics-anatomy",
                    text=(
                        "Three idioms in that quote repay attention. The "
                        "provider may itself take parameters — request here "
                        "— and FastAPI solves providers' parameters exactly "
                        "like handler parameters, recursively (the next "
                        "section is that recursion). The isinstance check "
                        "is defensive wiring made cheap: app.state is "
                        "untyped by nature, and the provider is where the "
                        "untyped edge gets narrowed to a typed value or a "
                        "typed failure — every handler downstream can "
                        "assume what it receives. And the Annotated alias "
                        "at the bottom is the house style: name the "
                        "dependency ONCE, so every handler spells it the "
                        "same way and a signature stays readable. Using it "
                        "is one import:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="basics-router",
                    language="py",
                    caption="The consuming handler: a typed parameter, no construction.",
                    source="server/guide/presentation/routers/demo/scenario.py",
                    snippet=(
                        "@router.get(\"/scenario\", response_model=ScenarioState)\n"
                        "def read_scenario(store: ScenarioStoreDep) -> ScenarioState:\n"
                        "    \"\"\"Report the current demo scenario.\"\"\"\n"
                        "    return store.get()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="basics-shorthand",
                    text=(
                        "Two variations complete the grammar. Depends() with "
                        "NO argument is the inference shorthand: write "
                        "store: ScenarioStore = Depends() and FastAPI uses "
                        "the annotation itself as the provider — for a class "
                        "annotation that means constructing it per request "
                        "(section 5 covers what that implies). And Depends "
                        "accepts parameters to shape resolution — "
                        "use_cache=False is the one that matters and gets "
                        "its own section. What there is NOT matters just as "
                        "much: no names, no strings, no registration step. "
                        "A dependency exists exactly when some signature "
                        "mentions it, which makes the wiring greppable in a "
                        "way container XML never was — the provider "
                        "function's name is the whole identity, and the "
                        "test override table (section 7) keys on precisely "
                        "that name."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="basics-coda",
                    text=(
                        "Notice what the handler does not know: where the "
                        "store lives, that app.state exists, how many "
                        "stores there are. Swap the wired store for a fake "
                        "(section 7 does exactly that) and this handler is "
                        "unchanged — that indifference is the entire value "
                        "of DI, purchased with one annotation. One more "
                        "basic worth naming: dependencies compose with the "
                        "REST of the signature. A handler can take path "
                        "parameters, a parsed body, and Depends-provided "
                        "objects side by side; FastAPI resolves them all "
                        "before the first line of your function runs, in "
                        "signature order. The handler body, meanwhile, "
                        "starts looking like what it always wanted to be: "
                        "business logic over ready-typed inputs."
                    ),
                ),
            ],
        ),
        # ── 3. Dependency trees ─────────────────────────────────────────────
        Section(
            id="dependency-trees",
            title="Dependency trees",
            blocks=[
                TextBlock(
                    kind="text",
                    id="trees-pitch",
                    text=(
                        "Providers can need things too, and they express "
                        "that the same way handlers do: Depends in their own "
                        "signatures. FastAPI solves the resulting graph "
                        "depth-first before the handler runs — a provider's "
                        "dependencies are resolved (and cached, section 6) "
                        "before the provider is called, so by the time your "
                        "handler executes, an entire tree of setup has "
                        "completed. The matrix demo this topic carries has a "
                        "real depth-3 chain, shaped like the auth story it "
                        "previews: a verified request is built from an "
                        "authenticated actor, which is built from a parsed "
                        "token — each layer declaring only the layer below "
                        "it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="trees-chain",
                    language="py",
                    caption="A real depth-3 chain: each provider depends on the one below.",
                    source="server/guide/presentation/dependencies/demo_flavors.py",
                    snippet=(
                        "def get_parsed_token() -> ParsedToken:\n"
                        "    \"\"\"Chain base: no dependencies of its own.\"\"\"\n"
                        "    return ParsedToken()\n"
                        "\n"
                        "\n"
                        "def get_authenticated_actor(\n"
                        "    token: Annotated[ParsedToken, Depends(get_parsed_token)],\n"
                        ") -> AuthenticatedActor:\n"
                        "    \"\"\"Chain middle: resolves the base itself — FastAPI solves sub-dependencies.\"\"\"\n"
                        "    return AuthenticatedActor(token)\n"
                        "\n"
                        "\n"
                        "def get_verified_request(\n"
                        "    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],\n"
                        ") -> VerifiedRequest:\n"
                        "    \"\"\"Chain top: depth 3 — this resolved through actor, actor through token.\"\"\"\n"
                        "    return VerifiedRequest(actor)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="trees-why",
                    text=(
                        "The tree shape is not decoration — it is how "
                        "cross-cutting design stays local. get_verified_request "
                        "does not know what a token is; the token provider "
                        "does not know actors exist. Each layer can be "
                        "tested alone, replaced alone (an override on "
                        "get_parsed_token re-points every layer above it), "
                        "and understood alone. The repo's existing trees are "
                        "the same pattern at smaller depth: the health "
                        "handler's config: Annotated[AppConfig, "
                        "Depends(get_config)] is a depth-1 tree whose root "
                        "is an lru_cache'd constructor, and the span "
                        "dependency in the next section resolves its log "
                        "through a sub-provider. When people say DI 'gets "
                        "out of hand', they usually mean a tree nobody can "
                        "see; the cure is not fewer dependencies but a "
                        "visible composition root and shallow, named "
                        "layers — which is all this repo's trees are. One "
                        "structural rule keeps them honest: providers may "
                        "depend on providers, but the graph must be acyclic "
                        "(FastAPI would recurse forever otherwise), and a "
                        "tree's leaves are exactly where real construction "
                        "happens — everything above a leaf is judgment, "
                        "not creation. Two runtime facts complete the "
                        "picture. Resolution is eager and total: if any "
                        "node of the tree raises, the handler never runs — "
                        "a validation error or an unauthorized in a "
                        "sub-dependency fails the request BEFORE your "
                        "endpoint is entered, which is precisely the "
                        "property cross-cutting concerns want (section 8). "
                        "And resolution order follows the tree depth-first, "
                        "so side effects in providers run outer-layer-last: "
                        "the deepest leaf constructs first, each layer up "
                        "receives its dependencies ready — the same "
                        "discipline as constructor injection in the spring "
                        "sibling, expressed as signatures instead of "
                        "containers."
                    ),
                ),
            ],
        ),
        # ── 4. Yield dependencies (demo: dep:lifecycle) ────────────────────
        Section(
            id="yield-dependencies",
            title="Yield dependencies: setup, teardown, and the truth about ordering",
            lead="This section carries the topic's first demo — watch a span close after the response.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="yield-pitch",
                    text=(
                        "A plain dependency hands over a value and is done. "
                        "A yield dependency wraps a WHOLE span: everything "
                        "before the yield is setup, the yielded value rides "
                        "into the handler, and everything after the yield — "
                        "best under finally — is teardown. You already met "
                        "the shape in topic 01: it is the generator-form "
                        "context manager, with the framework playing the "
                        "with-statement. The payoff is resource pairing that "
                        "cannot be forgotten: acquire a database session "
                        "before the handler, commit or roll it back after; "
                        "start a timing span, end it no matter how the "
                        "request went. The repo's real one is the request-"
                        "span instrument — the dependency every dep demo on "
                        "this server runs through:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="yield-open",
                    language="py",
                    caption="The repo's real yield dependency, complete.",
                    source="server/guide/presentation/dependencies/request_span.py",
                    snippet=(
                        "async def open_request_span(log: SpanLogDep) -> AsyncIterator[RequestSpan]:\n"
                        "    \"\"\"FastAPI yield dependency: setup, yield the span, teardown after send.\n"
                        "\n"
                        "    Everything before ``yield`` runs during dependency resolution (before\n"
                        "    the handler); the ``finally`` runs when FastAPI closes the request's\n"
                        "    ``AsyncExitStack`` — for a regular response, after the bytes have been\n"
                        "    sent. The dependency's own sub-dependency (``get_span_log``) is how the\n"
                        "    demo's override test swaps the log for a fake.\n"
                        "    \"\"\"\n"
                        "    span = RequestSpan(log)\n"
                        "    span.record(\"setup\")\n"
                        "    try:\n"
                        "        yield span\n"
                        "    finally:\n"
                        "        span.record(\"teardown\")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="yield-ordering",
                    text=(
                        "Now the claim every FastAPI engineer should own "
                        "precisely, because this guide verified it against "
                        "the installed framework and the demo below measures "
                        "it live: teardown runs AFTER the response has been "
                        "sent. Mechanically, FastAPI enters yield "
                        "dependencies into a request-scoped AsyncExitStack, "
                        "and the vendored request handler awaits the "
                        "response object INSIDE that stack — so the stack "
                        "closes (your finally) only after the bytes leave. "
                        "Three consequences:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="yield-consequences-list",
                    ordered=False,
                    items=[
                        "A handler can never report its own teardown — the "
                        "response is already committed before it runs; the "
                        "demo's payload confesses this with pendingEvents: "
                        "[teardown], and the sibling log endpoint shows the "
                        "rest.",
                        "Exceptions still run teardown — the finally is "
                        "guaranteed — but an exception raised AFTER yield "
                        "cannot change a response already sent; it can only "
                        "fail the request loudly (never swallow it with a "
                        "bare except: the framework detects and rejects "
                        "that).",
                        "Work you keep meaning to do 'after the response' — "
                        "metrics flush, audit write — has an exact home: "
                        "after the yield, before the finally's end.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="yield-send-moment",
                    text=(
                        "The demo's other half is the "
                        "instrument that timestamps the send moment itself, "
                        "because a Response object is an ASGI app whose "
                        "__call__ IS the send step:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="yield-response",
                    language="py",
                    caption="Stamping the send moment: the response records its own flush.",
                    source="server/guide/presentation/dependencies/request_span.py",
                    snippet=(
                        "class SpanResponse(JSONResponse):\n"
                        "    \"\"\"A JSON response that stamps its span's ``response`` event at the send moment.\n"
                        "\n"
                        "    FastAPI awaits the response object (an ASGI app) to send the bytes, and\n"
                        "    closes the request's ``AsyncExitStack`` — running yield-dependency\n"
                        "    teardown — only after that await completes. Recording inside\n"
                        "    ``__call__`` therefore timestamps the flush itself, which is what makes\n"
                        "    the log's ordering (… → response → teardown) a measurement, not a claim.\n"
                        "\n"
                        "    The body is built from a payload model exactly as FastAPI would\n"
                        "    (camelCase aliases, JSON-safe, nulls omitted), because a directly\n"
                        "    returned Response bypasses ``response_model`` serialization.\n"
                        "    \"\"\"\n"
                        "\n"
                        "    def __init__(self, span: RequestSpan, content: CamelModel) -> None:\n"
                        "        \"\"\"Serialize ``content`` now; stamp the span when this is awaited.\"\"\"\n"
                        "        super().__init__(\n"
                        "            content=content.model_dump(mode=\"json\", by_alias=True, exclude_none=True)\n"
                        "        )\n"
                        "        self._span = span\n"
                        "\n"
                        "    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:\n"
                        "        \"\"\"The send step itself: record, then let the JSON bytes leave.\"\"\"\n"
                        "        self._span.record(\"response\")\n"
                        "        await super().__call__(scope, receive, send)"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="dep:lifecycle",
                    title="A span's life, measured",
                    description=(
                        "Fire GET /api/demo/dep/lifecycle and the response "
                        "reports what the handler could know — span id, "
                        "setup timestamp, how far in the handler ran, and "
                        "pendingEvents confessing the teardown that has not "
                        "happened. Then read the log endpoint: the same "
                        "span's four beats, setup → handler → response → "
                        "teardown, sequenced in append order — the teardown "
                        "AFTER the response, because FastAPI closes the "
                        "request's dependency stack only after the bytes "
                        "are sent. Fire again and watch the bounded ring "
                        "(last 20 events) hold whole spans, newest last."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="yield-router",
                    language="py",
                    caption="The demo endpoints: one wrapped request, one log reader.",
                    source="server/guide/presentation/routers/demo/dep.py",
                    snippet=(
                        "@router.get(\"/lifecycle\", response_model=DepLifecyclePayload)\n"
                        "async def run_lifecycle(span: RequestSpanDep) -> SpanResponse:\n"
                        "    \"\"\"One wrapped request: record the handler beat, answer with span facts.\"\"\"\n"
                        "    span.record(\"handler\")\n"
                        "    payload = build_lifecycle_payload(\n"
                        "        span_id=span.span_id,\n"
                        "        setup_at=span.opened_at,\n"
                        "        handler_offset_ms=span.elapsed_ms(),\n"
                        "    )\n"
                        "    # A Response return bypasses response_model serialization — SpanResponse\n"
                        "    # builds the body from the payload model itself and stamps the send moment.\n"
                        "    return SpanResponse(span, payload)\n"
                        "\n"
                        "\n"
                        "@router.get(\"/lifecycle/log\", response_model=SpanLogSnapshot)\n"
                        "async def read_lifecycle_log(log: SpanLogDep) -> SpanLogSnapshot:\n"
                        "    \"\"\"Serve the bounded span ring — the ordering proof, as data.\"\"\"\n"
                        "    return SpanLogSnapshot(capacity=log.capacity, events=log.tail())"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="yield-coda",
                    text=(
                        "Read the demo's two-step dance as the lesson it "
                        "is: request one returns a body that is already "
                        "committed; request two reads the log where the "
                        "first request's teardown landed after the fact. "
                        "The tests pin the exact sequence — setup < handler "
                        "< response < teardown — against the running "
                        "framework, so if a future FastAPI ever changed the "
                        "ordering, this guide's suite would fail loudly "
                        "instead of teaching folklore. That is the standard "
                        "this whole topic holds itself to: every claim "
                        "about the framework in it is either quoted from "
                        "repo code or measured by a test you can run."
                    ),
                ),
            ],
        ),
        # ── 5. Classes and callables as dependencies ────────────────────────
        Section(
            id="classes-as-dependencies",
            title="Classes and callables as dependencies",
            blocks=[
                TextBlock(
                    kind="text",
                    id="classes-pitch",
                    text=(
                        "Depends accepts any callable, and that single rule "
                        "covers four shapes worth knowing:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="callable-shapes-list",
                    ordered=False,
                    items=[
                        "A function — the default you have seen.",
                        "A class — Depends(Correlation) CONSTRUCTS one per "
                        "request, FastAPI calling the class like a zero-argument "
                        "factory; handy for typed value objects, and the reason "
                        "you should not accidentally pass a class where you "
                        "meant an instance.",
                        "An instance with __call__ — the callable class, this "
                        "section's subject, where the provider object holds "
                        "configuration and each call mints per-request state.",
                        "A closure — any function built by another function, "
                        "which is how you parameterize providers without "
                        "classes at all.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="classes-issuer-lead",
                    text=(
                        "The matrix demo's API-key issuer is the real callable "
                        "class:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="classes-issuer",
                    language="py",
                    caption="A real callable class: configuration at module scope, minting per request.",
                    source="server/guide/domain/demos/dep_matrix.py",
                    snippet=(
                        "class ApiKeyIssuer:\n"
                        "    \"\"\"Callable-class flavor: FastAPI calls the instance like a function.\n"
                        "\n"
                        "    The provider object lives at module scope (one per process — where\n"
                        "    configuration belongs); ``__call__`` runs per request and mints a fresh\n"
                        "    key, carrying both identities so the demo can show provider-vs-product.\n"
                        "    \"\"\"\n"
                        "\n"
                        "    def __init__(self, prefix: str) -> None:\n"
                        "        self._prefix = prefix\n"
                        "\n"
                        "    def __call__(self) -> ApiKey:\n"
                        "        \"\"\"Mint one key: the per-request product of a process-wide provider.\"\"\"\n"
                        "        return ApiKey(\n"
                        "            value=f\"{self._prefix}-{uuid4().hex[:8]}\",\n"
                        "            issuer_token=identity_token(self),\n"
                        "        )"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="classes-instance",
                    language="py",
                    caption="Wiring it: Depends takes the INSTANCE, and calls it per request.",
                    source="server/guide/presentation/dependencies/demo_flavors.py",
                    snippet=(
                        "api_key_issuer: Final = ApiKeyIssuer(\"matrix\")\n"
                        "\"\"\"The callable-class provider: an INSTANCE — Depends calls it, not the class.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="classes-coda",
                    text=(
                        "The distinction in the wiring quote is the one "
                        "that bites beginners: Depends(api_key_issuer) "
                        "calls the instance (per-request keys, one shared "
                        "provider), while Depends(ApiKeyIssuer) would call "
                        "the CLASS — constructing a fresh issuer each "
                        "request and silently losing whatever the provider "
                        "was supposed to remember. When does the callable-"
                        "class shape earn its keep over a plain function? "
                        "When the provider needs configuration or state "
                        "that deserves a name and a type — a rate limiter "
                        "with its policy, a signer with its key id, an "
                        "issuer with its prefix — and you want that state "
                        "constructed once, tested directly, and visible in "
                        "the signature. A function with a module-level "
                        "constant does the same job until the constant "
                        "needs a name; the class is the named version. "
                        "Either way, the framework treats them "
                        "identically: solved per request, cached like any "
                        "dependency, overridable like any dependency — "
                        "which is the next section's subject."
                    ),
                ),
            ],
        ),
        # ── 6. Caching and scoping ─────────────────────────────────────────
        Section(
            id="caching-and-scoping",
            title="Caching and scoping",
            blocks=[
                TextBlock(
                    kind="text",
                    id="cache-pitch",
                    text=(
                        "Solve the same dependency twice in one request and "
                        "you get the same instance: FastAPI keys a per-"
                        "request cache by the provider callable itself, so "
                        "a store, a session, or a correlation context asked "
                        "for by three different parameters (or by a "
                        "sub-dependency AND a handler) is constructed once "
                        "and shared. That default is right far more often "
                        "than not — it is what makes 'the request's "
                        "database session' a coherent concept. "
                        "use_cache=False opts a specific Depends out: every "
                        "parameter asking that way re-runs the provider "
                        "and receives its own instance, which is exactly "
                        "what you want for things that must not be shared "
                        "— cursors, iterators, anything with position. The "
                        "matrix endpoint resolves both behaviors in one "
                        "request, and its signature IS the experiment:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cache-matrix-signature",
                    language="py",
                    caption="One signature, every caching flavor: the experiment, declared.",
                    source="server/guide/presentation/routers/demo/dep.py",
                    snippet=(
                        "@router.get(\"/matrix\", response_model=DepMatrixPayload)\n"
                        "async def read_dep_matrix(\n"
                        "    correlation: Annotated[Correlation, Depends(get_correlation)],\n"
                        "    budget_a: Annotated[RateBudget, Depends(get_rate_budget)],\n"
                        "    budget_b: Annotated[RateBudget, Depends(get_rate_budget)],\n"
                        "    cursor_a: Annotated[Cursor, Depends(open_cursor, use_cache=False)],\n"
                        "    cursor_b: Annotated[Cursor, Depends(open_cursor, use_cache=False)],\n"
                        "    verified: Annotated[VerifiedRequest, Depends(get_verified_request)],\n"
                        "    actor_direct: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],\n"
                        "    api_key: Annotated[ApiKey, Depends(api_key_issuer)],\n"
                        "    thread_view: Annotated[ThreadView, Depends(peek_threadpool)],\n"
                        ") -> DepMatrixPayload:\n"
                        "    \"\"\"Resolve the whole dependency matrix in one request; report identity proofs.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cache-evidence",
                    text=(
                        "budget_a and budget_b share a provider, so they "
                        "receive one instance; cursor_a and cursor_b opt "
                        "out and receive two. Identity claims need "
                        "evidence, and the demo's evidence is the oldest "
                        "trick in Python — id() rendered as a stable-while-"
                        "alive token (the request holds the objects, so "
                        "tokens cannot be recycled mid-request; equal token "
                        "means same instance, full stop):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cache-token",
                    language="py",
                    caption="How the demo observes identity without lying about it.",
                    source="server/guide/domain/demos/dep_matrix.py",
                    snippet=(
                        "def identity_token(obj: object) -> str:\n"
                        "    \"\"\"Stable-while-alive identity token: class name + ``id()`` in hex.\n"
                        "\n"
                        "    Within one request the resolved objects stay referenced, so tokens are\n"
                        "    stable and distinct instances get distinct tokens; two parameters see\n"
                        "    the same instance exactly when their tokens are equal.\n"
                        "    \"\"\"\n"
                        "    return f\"{type(obj).__name__}#{id(obj):x}\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cache-scoping",
                    text=(
                        "Scoping is the third axis, and FastAPI keeps it "
                        "honest by keeping it small. The cache is per "
                        "request: no session-scoped or application-scoped "
                        "dependencies exist in the framework. Something "
                        "that should live longer than a request is exactly "
                        "what the composition root owns — app.state for "
                        "mutable singletons, lru_cache for immutable "
                        "configuration (get_config), module scope for "
                        "provider objects like the issuer. Something "
                        "shorter than a request has a home too in this "
                        "FastAPI generation: Depends accepts a scope of "
                        "\"function\" or \"request\" for yield dependencies, "
                        "so a provider can close after the endpoint "
                        "function rather than after the response — an "
                        "escape hatch this repo has not needed, and you "
                        "will know when you do. One more scoping fact that "
                        "is easy to miss and the matrix measures: SYNC "
                        "dependencies — plain def, like every provider in "
                        "the matrix — run in the threadpool, not on the "
                        "event loop. That is a feature (a blocking provider "
                        "cannot stall the loop), and the demo's sync row "
                        "proves it by reporting thread names: the provider "
                        "ran on a worker thread while the async handler ran "
                        "on the loop's own thread. The corollary is the "
                        "performance topic's mantra two chapters early: "
                        "write async providers when the work is I/O, sync "
                        "providers when the work blocks — the framework "
                        "routes each to where it belongs, and the matrix "
                        "shows the routing as data."
                    ),
                ),
            ],
        ),
        # ── 7. dependency_overrides for testing ────────────────────────────
        Section(
            id="dependency-overrides",
            title="dependency_overrides for testing",
            blocks=[
                TextBlock(
                    kind="text",
                    id="overrides-pitch",
                    text=(
                        "Everything above — providers, trees, caches — "
                        "exists so that THIS section is trivial. Tests need "
                        "to replace real dependencies with fakes without "
                        "touching production wiring, and because every "
                        "handler receives its world through Depends, there "
                        "is exactly one seam to cut: app.dependency_overrides, "
                        "a mapping from provider callable to replacement. "
                        "Register an override and every route that depends "
                        "on that provider — directly or three layers down a "
                        "tree — receives your fake for the request. No "
                        "monkeypatching module attributes, no test-only "
                        "branches in constructors, no re-wiring routers. "
                        "The guide's own test suite does this to the span "
                        "instrument, and the test is real enough to quote:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="overrides-test",
                    language="py",
                    caption="A real test from this repo: one override re-points the whole instrument.",
                    source="server/tests/demo/test_dependency_overrides.py",
                    snippet=(
                        "def test_span_log_override_re_points_the_whole_instrument(\n"
                        "    overrides: FastAPI, client: TestClient\n"
                        ") -> None:\n"
                        "    fake = SpanLog(capacity=8)\n"
                        "    overrides.dependency_overrides[get_span_log] = lambda: fake\n"
                        "\n"
                        "    # The log endpoint reads the fake (its capacity gives it away)…\n"
                        "    log = client.get(\"/api/demo/dep/lifecycle/log\").json()\n"
                        "    assert log[\"capacity\"] == 8\n"
                        "    assert log[\"events\"] == []\n"
                        "\n"
                        "    # …and the lifecycle endpoint writes through it, because the yield\n"
                        "    # dependency resolves the log as its own sub-dependency.\n"
                        "    client.get(\"/api/demo/dep/lifecycle\")\n"
                        "    beats = [event[\"event\"] for event in client.get(\"/api/demo/dep/lifecycle/log\").json()[\"events\"]]\n"
                        "    assert beats == [\"setup\", \"handler\", \"response\", \"teardown\"]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="overrides-coda",
                    text=(
                        "Read what the override reached: not just the log "
                        "endpoint, but the yield dependency's own "
                        "sub-provider — the override propagated up the "
                        "tree, which is the recursion from section 3 "
                        "working in your favor. The habits that keep "
                        "overrides healthy:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="override-habits-list",
                    ordered=False,
                    items=[
                        "Clear the table when you are done — the fixture above "
                        "does; leaks are the classic flake.",
                        "Override the provider that is closest to the behavior "
                        "under test — an override on a leaf re-points every "
                        "tree above it: precise surgery, not a mock fest.",
                        "Let the fake be a real object with real types — a "
                        "ScenarioStore with crafted initial state, a SpanLog "
                        "with a different capacity — rather than a MagicMock; "
                        "the suite then tests behavior, not collaboration "
                        "guesses.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="overrides-honest-answer",
                    text=(
                        "This is also the honest answer to 'how do I test "
                        "handlers without a database': you never had to "
                        "have one, because the handler never knew there "
                        "was one. The testing topic (34) scales this "
                        "pattern to whole suites; cross-cutting concerns "
                        "are where it pays off daily, which is the last "
                        "teaching of this topic."
                    ),
                ),
            ],
        ),
        # ── 8. Cross-cutting concerns (demo: dep:matrix) ───────────────────
        Section(
            id="cross-cutting-dependencies",
            title="Dependencies as cross-cutting concerns",
            lead="This section carries the topic's second demo — a matrix of every flavor, resolved at once.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="crosscut-pitch",
                    text=(
                        "Auth, rate limiting, correlation, auditing: "
                        "concerns that touch every endpoint and belong to "
                        "no endpoint. Frameworks offer many mechanisms — "
                        "middleware, decorators, interceptors — and "
                        "FastAPI has those too (topic 08). But dependency "
                        "trees are often the better tool for cross-cutting "
                        "CONCERNS-with-data:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="crosscut-advantages-list",
                    ordered=False,
                    items=[
                        "A dependency composes — concerns stack as "
                        "sub-dependencies.",
                        "It is typed — the handler receives an "
                        "AuthenticatedActor, not a request attribute bag.",
                        "It fails loudly — raise in setup and the request never "
                        "reaches the handler; an unauthorized dependency "
                        "answers 401 before your code runs.",
                        "It is testable — section 7: override the tree's root "
                        "and the concern vanishes for the test.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="crosscut-compare",
                    text=(
                        "Compare the two "
                        "idioms honestly: middleware sees every request "
                        "but is downstream of routing and cannot feed the "
                        "handler typed values; a dependency feeds the "
                        "handler exactly what it declared but must be "
                        "declared on every route that wants it. The guide's "
                        "rule of thumb: middleware for concerns that never "
                        "talk to handlers (request ids, logging — see "
                        "core/request_context.py), dependencies for "
                        "concerns handlers consume (auth, budgets, spans). "
                        "The auth-shaped rows of the matrix endpoint show "
                        "the consumption side:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="crosscut-params",
                    language="py",
                    caption="Cross-cutting concerns as parameters: auth tree, key, budget, thread fact.",
                    source="server/guide/presentation/routers/demo/dep.py",
                    snippet=(
                        "    verified: Annotated[VerifiedRequest, Depends(get_verified_request)],\n"
                        "    actor_direct: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],\n"
                        "    api_key: Annotated[ApiKey, Depends(api_key_issuer)],\n"
                        "    thread_view: Annotated[ThreadView, Depends(peek_threadpool)],"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="dep:matrix",
                    title="The dependency matrix",
                    description=(
                        "One request to GET /api/demo/dep/matrix resolves "
                        "every flavor this topic taught and returns the "
                        "identity proofs: a function dependency's single "
                        "instance; a callable class's provider and its "
                        "minted key; the same cached dependency asked twice "
                        "(one instance, equal tokens); use_cache=False "
                        "asked twice (two instances, distinct tokens); a "
                        "depth-3 chain whose middle layer the handler also "
                        "requests directly (shared, because the cache keys "
                        "on the callable); and a sync provider inside the "
                        "async endpoint, its worker thread named beside "
                        "the handler's event-loop thread. Refresh and the "
                        "verdicts hold while the tokens change — new "
                        "request, new world, same rules."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="crosscut-coda",
                    text=(
                        "Read the matrix as a preview of where the guide "
                        "goes next with these shapes. Authentication (23) "
                        "turns ParsedToken into a real credential check "
                        "and the actor into a session or API-key identity; "
                        "authorization (24) grows the tree one layer — an "
                        "actor into required scopes and object ownership, "
                        "enforced by a dependency that raises 403; "
                        "security (25) adds the rate-limit dependency the "
                        "budget flavor sketches, backed by the redis topic "
                        "(20) when counters must survive a process. None "
                        "of that will change a handler signature's SHAPE — "
                        "one more typed parameter per concern, solved per "
                        "request, cached within it, overridable in tests. "
                        "That stability is the quiet argument of the whole "
                        "topic: learn Depends once, and the security "
                        "chapters are configuration, not new machinery."
                    ),
                ),
            ],
        ),
        # ── 9. Terminal companion ──────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="Dependencies, probed from the shell — two endpoints, one log, one matrix.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-pitch",
                    text=(
                        "With the stack up (server on :8000), this tour "
                        "drives both demos against the live app: the "
                        "lifecycle pair (fire, then read the log — the "
                        "ordering proof), the matrix (every flavor in one "
                        "request), and this topic's own content payload. "
                        "Plain curl; python3 -m json.tool is the only "
                        "helper:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-lifecycle",
                    language="bash",
                    source=None,
                    snippet=(
                        "# fire one wrapped request — note pendingEvents: the teardown has not run\n"
                        "curl -s localhost:8000/api/demo/dep/lifecycle | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-log",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the proof: the log holds setup → handler → response → teardown,\n"
                        "# sequences increasing — teardown sequenced AFTER the response\n"
                        "curl -s localhost:8000/api/demo/dep/lifecycle/log | python3 -m json.tool | head -n 30"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-twice",
                    language="bash",
                    source=None,
                    snippet=(
                        "# fire again, then read: two complete spans; the ring keeps the last 20 events\n"
                        "curl -s -o /dev/null localhost:8000/api/demo/dep/lifecycle\n"
                        "curl -s localhost:8000/api/demo/dep/lifecycle/log \\\n"
                        "  | python3 -c \"import json,sys; print([e['event'] for e in json.load(sys.stdin)['events']])\""
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-matrix",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the matrix: verdicts for cached (same-instance), uncached (distinct),\n"
                        "# chain sharing (shared-middle), and the threadpool thread names\n"
                        "curl -s localhost:8000/api/demo/dep/matrix | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-topic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# this page itself, as the content API serves it (sections → blocks)\n"
                        "curl -s localhost:8000/api/content/fastapi-dependencies | python3 -m json.tool | head -n 14"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Every stop was a claim made earlier, now with a "
                        "request attached: pendingEvents is the handler's "
                        "confession that its teardown had not run; the "
                        "log's sequences are the ordering this topic "
                        "pinned from the framework's own request handler; "
                        "the matrix's verdicts are id()-derived equality "
                        "measured inside one request; and the thread names "
                        "in its sync row are the threadpool fact, "
                        "unmasked. The next topic stays on the request "
                        "path but changes the layer: routing — how a path "
                        "meets its handler at all."
                    ),
                ),
            ],
        ),
    ],
)
