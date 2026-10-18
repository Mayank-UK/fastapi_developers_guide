"""Topic 32 — Architecture (the platform group, the guide turned inward).

Every topic before this one taught a capability — routing, validation,
databases, auth — and each one quietly leaned on the SAME structural
decisions: layers with one dependency direction, routers that only
translate, a composition root that owns every wiring choice, failures as
values in the domain and raises at the edge. This topic makes those
decisions the subject themselves, taught against the repo you are reading:
why layering pays (the in-memory posts adapter promised a database
replacement from Phase 6 on and the port never changed), the layer map,
the dependency rule as an import direction, thin routers, the composition
root (app factory + provider wiring), errors across layers, the client's
deliberate mirror of the same rule — and the request-flow tracer as the
topic's demo INLINE: one payload that introspects the running app and
drives two REAL internal requests through every layer, the Ok round and
the Err round, with measured timings only where they were actually
measured.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="architecture",
    title="Architecture",
    subtitle=(
        "The guide's own structure as the subject: why layers pay, the layer "
        "map, the dependency rule, thin routers, the composition root (app "
        "factory + provider wiring), errors across layers, the client's "
        "mirror — and a tracer that follows one real request through every "
        "layer, live."
    ),
    group="platform",
    order=32,
    sections=[
        # ── 1. Why architecture ────────────────────────────────────────────
        Section(
            id="why-architecture",
            title="Why architecture",
            blocks=[
                TextBlock(
                    kind="text",
                    id="why-pitch",
                    text=(
                        "Architecture is the set of decisions that are hard to "
                        "change after the first hundred files exist: which code "
                        "may import which, where wiring happens, how a failure "
                        "travels, who owns a decision. Get them wrong and every "
                        "later topic pays interest — a bug fix touches five "
                        "folders, a new requirement needs a meeting, a test "
                        "needs a database. Get them right and change stays "
                        "local: this guide lived that promise for real. The "
                        "posts resource shipped in topic 11 with an in-memory "
                        "adapter behind a domain port and a comment saying a "
                        "database would arrive in Phase 6 — five topics and "
                        "four migrations later there IS a database, an ORM "
                        "layer, a GraphQL resolver and a gRPC servicer over "
                        "the same use cases, and the port, the use cases, and "
                        "the router never changed a line. That is not luck; "
                        "it is the dependency rule doing exactly what it was "
                        "designed to do, and this topic finally teaches it "
                        "explicitly instead of implicitly."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-what-it-buys",
                    text=(
                        "What layered architecture concretely buys, in the "
                        "vocabulary this repo uses every day: substitutability "
                        "(the adapter behind a port can be swapped — in-memory "
                        "for PostgreSQL, fake for live — because dependents "
                        "only know the port's shape), testability (a use case "
                        "is constructor-injected with anything that satisfies "
                        "its port, so domain tests run without sockets), "
                        "reviewability (the dependency rule makes every PR "
                        "auditable by import direction — a router importing "
                        "the data layer is visible in the diff, not hidden in "
                        "a call graph), and replaceability of the framework "
                        "itself (the domain knows nothing about FastAPI, so "
                        "the framework is a presentation detail rather than "
                        "the skeleton everything hangs from). None of that "
                        "requires a big system — this repo has exactly one "
                        "real resource and still benefits, because the rules "
                        "are about the direction of knowledge, not the size "
                        "of the codebase."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-where",
                    text=(
                        "Where this topic sits: by now you have met every "
                        "layer many times without the map — topic 06 taught "
                        "Depends without calling it the composition root's "
                        "delivery mechanism, topic 11 built the posts "
                        "substrate without dwelling on why the router imports "
                        "only the domain, topic 30 taught the error story "
                        "without naming the layer boundary it crosses. This "
                        "topic is the retrospective that names all of it, "
                        "quotes the real files in place, and ends with a demo "
                        "that proves the architecture is not a diagram: one "
                        "real request traced through every layer of the "
                        "running app, with the evidence labeled. Read it as "
                        "the guide reading itself."
                    ),
                ),
            ],
        ),
        # ── 2. The layer map ───────────────────────────────────────────────
        Section(
            id="the-layer-map",
            title="The layer map",
            blocks=[
                TextBlock(
                    kind="text",
                    id="map-pitch",
                    text=(
                        "The server is one package, ``guide/``, with a small "
                        "fixed set of top-level homes. Each exists because it "
                        "answers a different question, and the homes are also "
                        "the review vocabulary: when a change lands, which "
                        "folder it touches says what KIND of change it is. "
                        "The map, with each layer's one-sentence job:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="map-layers-list",
                    ordered=False,
                    items=[
                        "core/ — the shared kernel: config, the error taxonomy "
                        "and its envelope, Result, the scenario store, "
                        "logging, the request-id context; framework-free "
                        "machinery every other layer may use.",
                        "content/ — the guide's own teaching held as typed "
                        "data: the topic registry, section and block models, "
                        "startup validation; no behavior beyond serving "
                        "itself.",
                        "domain/ — the business vocabulary: entities, ports "
                        "(Protocols), use cases, and the pure payload "
                        "builders behind demos; imports core and nothing "
                        "else.",
                        "data/ — the adapters: repository implementations "
                        "over PostgreSQL, Redis, MongoDB, in-memory stores, "
                        "messaging; they IMPLEMENT domain ports and own "
                        "every driver import.",
                        "presentation/ — the edge: routers, middleware, "
                        "dependencies, websockets; parses and validates "
                        "input, calls use cases, maps Results to HTTP.",
                        "main.py — the composition root: the ``create_app()`` "
                        "factory that owns every wiring decision and is the "
                        "only place layers meet.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="map-entry-pitch",
                    text=(
                        "The entrypoint is deliberately boring so that the "
                        "interesting parts can be strict: ``create_app()`` "
                        "builds a fully independent FastAPI instance — own "
                        "routing table, own DI container — and every decision "
                        "after the first three lines is a wiring decision. "
                        "The head of the factory is the whole map in "
                        "miniature: configuration first, logging second, the "
                        "app object third, then per-app state — the seams "
                        "everything else hangs from:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="map-factory-quote",
                    language="py",
                    caption="create_app()'s opening moves: config, logging, app, per-app state.",
                    source="server/guide/main.py",
                    snippet=(
                        "def create_app() -> FastAPI:\n"
                        '    """Build one wired FastAPI application instance."""\n'
                        "    config = get_config()\n"
                        "    configure_logging(config.log_level)\n"
                        "    app = FastAPI(title=APP_TITLE, version=__version__, lifespan=lifespan)\n"
                        "\n"
                        "    app.state.scenario = ScenarioStore()\n"
                        "    app.state.span_log = SpanLog()\n"
                        "    app.state.content_registry = production_registry\n"
                        "    app.state.reqres_notes = NoteStore()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="map-per-app-pitch",
                    text=(
                        "The factory pattern earns its keep in tests: because "
                        "``create_app()`` builds a fresh instance with fresh "
                        "per-app state, every test gets its own seeded store, "
                        "its own scenario toggles, its own span log — no "
                        "shared mutable module state to reset, no test "
                        "ordering hazards. The module-level ``app`` exists "
                        "once per process only for the ASGI entrypoint "
                        "``guide.main:app`` that the Dockerfiles and compose "
                        "run. One function, two consumers, zero global "
                        "singletons — and the wires it pulls are the "
                        "composition root section's whole subject."
                    ),
                ),
            ],
        ),
        # ── 3. The dependency rule ─────────────────────────────────────────
        Section(
            id="the-dependency-rule",
            title="The dependency rule",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rule-pitch",
                    text=(
                        "The rule is one sentence: presentation → domain ← "
                        "data. The domain sits in the middle and knows "
                        "nobody; the two edges know the domain; the edges "
                        "never know each other. Concretely it is an IMPORT "
                        "direction, which is what makes it enforceable by "
                        "reading: routers import entities, ports, and use "
                        "cases; adapters import the same plus their drivers; "
                        "a router importing ``guide.data`` anything is a "
                        "violation, and so is a domain module importing "
                        "``fastapi``. The repo carries one documented "
                        "exemption — teaching-exhibit routers may import "
                        "data/ directly, marked teaching-exception — and "
                        "currently exercises it zero times: every quote in "
                        "every topic is production-shaped code."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rule-port-pitch",
                    text=(
                        "The hinge of the whole rule is the port: a Protocol "
                        "the domain owns and the adapters implement. The "
                        "posts port is four methods over plain domain shapes "
                        "— no driver types, no HTTP, no persistence details, "
                        "not even a class the adapter must subclass:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rule-port-quote",
                    language="py",
                    caption="PostRepository: the boundary the use cases depend on — a Protocol.",
                    source="server/guide/domain/posts/ports.py",
                    snippet=(
                        "@runtime_checkable\n"
                        "class PostRepository(Protocol):\n"
                        '    """What every posts adapter must do; returns snapshots, never live state."""\n'
                        "\n"
                        "    def list(self, query: PostListQuery) -> PostPage:\n"
                        '        """One filtered, sorted, paginated page of posts."""\n'
                        "        ...\n"
                        "\n"
                        "    def get(self, post_id: str) -> Post | None:\n"
                        '        """One post, or None when the id is unknown."""\n'
                        "        ...\n"
                        "\n"
                        "    def create(self, draft: PostCreate) -> Post:\n"
                        '        """Mint an id, stamp the clock, store the snapshot, return it."""\n'
                        "        ..."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rule-usecase-pitch",
                    text=(
                        "A use case states its entire dependency surface in "
                        "its constructor: it wants a ``PostRepository`` and "
                        "nothing else. That typing is the rule made "
                        "operational — mypy checks the adapter fits, the test "
                        "fixture can hand it a fake, and the composition root "
                        "(next section) is where a real adapter gets chosen:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rule-usecase-quote",
                    language="py",
                    caption="A use case's whole dependency surface: one constructor parameter.",
                    source="server/guide/domain/posts/use_cases.py",
                    snippet=(
                        "class ListPostsUseCase:\n"
                        '    """Serve one filtered, sorted, paginated page through the port."""\n'
                        "\n"
                        "    def __init__(self, posts: PostRepository) -> None:\n"
                        "        self._posts = posts\n"
                        "\n"
                        "    def execute(self, query: PostListQuery) -> Result[PostPage]:\n"
                        '        """Ask the port; the query\'s own constraints guarantee its shape."""\n'
                        "        return Ok(self._posts.list(query))"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rule-adapter-pitch",
                    text=(
                        "On the other side of the port, the adapter "
                        "implements the shape WITHOUT inheriting from "
                        "anything — structural typing is the point of a "
                        "Protocol, and the guide leans on it: the in-memory "
                        "adapter says so in its own docstring, and the "
                        "database adapters that joined later (SQLAlchemy "
                        "sessions, the ORM probe, the outbox store) satisfy "
                        "their ports the same way. The one-way knowledge is "
                        "worth saying out loud: the adapter knows the port "
                        "exists; the port does not know any adapter exists:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rule-adapter-quote",
                    language="py",
                    caption="The adapter side: implements the port, inherits from nothing.",
                    source="server/guide/data/posts/in_memory.py",
                    snippet=(
                        "class InMemoryPostRepository:\n"
                        '    """In-memory posts: seeded, per-app, deliberately unpersisted.\n'
                        "\n"
                        "    Implements the ``PostRepository`` port without inheriting from it —\n"
                        "    structural typing is the point of a Protocol (ruff/mypy verify the\n"
                        "    match in ``tests/data/test_in_memory_posts.py``).\n"
                        '    """'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rule-why-one-way",
                    text=(
                        "Why forbid the edges from knowing each other? "
                        "Because every leak compounds. A router that imports "
                        "the SQLAlchemy adapter to 'save a line of wiring' "
                        "has just made every future test of that route need "
                        "a database, and has made swapping the adapter a "
                        "router change too. An adapter that imports a router "
                        "to reuse a response model has just coupled storage "
                        "to the wire format — the DTO leak the family "
                        "invariant names explicitly. The rule is not "
                        "aesthetic; it is a budget for future change, and "
                        "the guide spends that budget constantly: the same "
                        "posts use cases serve REST (topic 11), GraphQL "
                        "(13), gRPC (15), the cache-aside lab (21), and the "
                        "messaging outbox (22) precisely because none of "
                        "those edges could reach past the port."
                    ),
                ),
            ],
        ),
        # ── 4. Thin routers ────────────────────────────────────────────────
        Section(
            id="thin-routers",
            title="Thin routers",
            blocks=[
                TextBlock(
                    kind="text",
                    id="thin-pitch",
                    text=(
                        "A router's whole job is translation, and the family "
                        "invariant fixes the shape of that job: parse and "
                        "validate input (pydantic does this at the "
                        "boundary), call ONE use case, map the returned "
                        "``Result`` onto an HTTP response. No business "
                        "logic in routers — not because handlers are "
                        "incapable of it, but because logic in a handler is "
                        "unreachable except through HTTP: untestable "
                        "without a request, unreusable by the GraphQL "
                        "resolver or the gRPC servicer or the worker, and "
                        "invisible to the authorization layer that wants to "
                        "guard ACTIONS rather than routes. The posts list "
                        "endpoint is the exemplar — read it as three "
                        "movements: the signature that declares what "
                        "arrives, the two-line Result flip, and the "
                        "response shaping that is genuinely the router's "
                        "own work:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="thin-list-quote",
                    language="py",
                    caption="list_posts: validate → call a use case → map Ok onto 200 + headers.",
                    source="server/guide/presentation/routers/posts.py",
                    snippet=(
                        '@router.get("/api/posts", response_model=PostPage)\n'
                        "def list_posts(\n"
                        "    query: Annotated[PostListQuery, Depends()],\n"
                        "    use_cases: PostUseCasesDep,\n"
                        "    response: Response,\n"
                        ") -> PostPage:\n"
                        '    """Serve one filtered, sorted, paginated page; pagination in headers."""\n'
                        "    result = use_cases.list_posts.execute(query)\n"
                        "    if isinstance(result, Err):\n"
                        "        raise result.failure\n"
                        "    page = result.value\n"
                        '    response.headers["x-total-count"] = str(page.total)\n'
                        '    response.headers["x-page-count"] = str(page.pages)\n'
                        "    link_header = format_link_header(build_page_links(query, page.total))\n"
                        "    if link_header is not None:\n"
                        '        response.headers["link"] = link_header\n'
                        "    return page"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="thin-anatomy",
                    text=(
                        "Notice how much of the thinness is done by "
                        "declaration before the body starts: the query model "
                        "is a pydantic type the framework validates, the use "
                        "cases arrive through a dependency (the composition "
                        "root's seam), and ``response_model=PostPage`` makes "
                        "serialization a framework concern. What remains in "
                        "the body is exactly the two things only the edge "
                        "can do: flip a failed Result into a raise, and "
                        "stamp HTTP-shaped facts (headers, Location, status "
                        "codes) onto the success. The failure flip is so "
                        "fixed it appears verbatim in all four endpoints of "
                        "this router — a two-line idiom, never a "
                        "per-endpoint error format, which is why topic 30 "
                        "could teach the entire error pipeline without a "
                        "single router-side special case."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="thin-dividends",
                    text=(
                        "The dividends show up the moment behavior grows. "
                        "The GraphQL resolvers (topic 13) and the gRPC "
                        "servicer (15) call the SAME use cases and get the "
                        "same validation and the same not_found semantics "
                        "for free — three transports, one behavior, because "
                        "the behavior never lived in the REST router. The "
                        "guarded edit from topic 24 stays thin the same way: "
                        "``require_owner_or`` is a dependency that resolves "
                        "a principal and raises before the handler runs, so "
                        "the authorization decision is a declaration beside "
                        "the signature, not an if-block inside the body. "
                        "When a route starts growing branches, that is the "
                        "architecture telling you a use case wants to exist "
                        "— the router is the wrong home for the logic, and "
                        "staying thin is how it stays honest."
                    ),
                ),
            ],
        ),
        # ── 5. The composition root ────────────────────────────────────────
        Section(
            id="the-composition-root",
            title="The composition root",
            blocks=[
                TextBlock(
                    kind="text",
                    id="root-pitch",
                    text=(
                        "Somewhere, SOME module has to know both sides — "
                        "which adapter satisfies which port, which "
                        "implementation sits behind which interface. "
                        "Layered architecture does not eliminate that "
                        "knowledge; it CONCENTRATES it, in exactly one "
                        "place: the composition root. Here that place is "
                        "``create_app()``. The posts wiring is the canonical "
                        "quote — the one function decides the adapter, "
                        "builds the use cases over it, and publishes the "
                        "bundle on ``app.state`` where providers can find "
                        "it. Routers never learn the adapter's name; tests "
                        "get per-app isolation because the decision runs "
                        "once per app instance:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="root-wiring-quote",
                    language="py",
                    caption="The root decides the adapter and wires the use cases — once per app.",
                    source="server/guide/main.py",
                    snippet=(
                        "    posts_repository: PostRepository = InMemoryPostRepository()\n"
                        "    app.state.posts_repository = posts_repository\n"
                        "    posts_use_cases = PostUseCases(\n"
                        "        list_posts=ListPostsUseCase(posts_repository),\n"
                        "        get_post=GetPostUseCase(posts_repository),\n"
                        "        create_post=CreatePostUseCase(posts_repository),\n"
                        "        replace_post=ReplacePostUseCase(posts_repository),\n"
                        "    )\n"
                        "    app.state.posts_use_cases = posts_use_cases"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="root-provider-pitch",
                    text=(
                        "The delivery mechanism between root and router is "
                        "the PROVIDER — a small callable FastAPI resolves "
                        "through ``Depends`` at request time. The posts "
                        "provider reads the bundle off ``app.state`` with an "
                        "isinstance guard, so a mis-wired app fails loudly "
                        "and typed on the first request rather than serving "
                        "garbage. This is the whole arc: the root wires, "
                        "the provider resolves, the handler declares:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="root-provider-quote",
                    language="py",
                    caption="The provider: app.state → typed bundle, guarded, once per request.",
                    source="server/guide/presentation/routers/posts.py",
                    snippet=(
                        "def get_post_use_cases(request: Request) -> PostUseCases:\n"
                        '    """FastAPI dependency: the posts use cases (wired in create_app)."""\n'
                        "    bundle = request.app.state.posts_use_cases\n"
                        "    if not isinstance(bundle, PostUseCases):\n"
                        '        raise AppError(FailureKind.INTERNAL, "Post use cases not wired on app.state")\n'
                        "    return bundle"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="root-vocabulary-framing",
                    text=(
                        "Providers are the composition root's vocabulary, "
                        "and the guide keeps a deliberate zoo of them — "
                        "topic 06's dependency-matrix demo exists to make "
                        "every shape measurable. The shapes in real use "
                        "around the repo:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="root-vocabulary-list",
                    ordered=False,
                    items=[
                        "Plain function — returns a value, cached per request "
                        "by default; the workhorse shape (get_post_use_cases "
                        "is one).",
                        "Callable class instance — FastAPI calls the "
                        "instance per request; carries configuration as "
                        "constructor state (the matrix's ApiKeyIssuer).",
                        "Yield dependency — setup before the handler, "
                        "teardown after the response is sent (the repo's "
                        "request_span; the exit stack owns the timing).",
                        "Sub-dependency chain — a provider that itself "
                        "declares Depends; FastAPI solves the tree "
                        "depth-first (the matrix's token→actor→verified "
                        "chain, quoted below).",
                        "app.state resolver — reads what the root wired, "
                        "isinstance-guarded; the seam that keeps wiring "
                        "swappable without touching handlers.",
                    ],
                ),
                CodeBlock(
                    kind="code",
                    id="root-chain-quote",
                    language="py",
                    caption="A three-deep provider chain, exactly as the matrix demo wires it.",
                    source="server/guide/presentation/dependencies/demo_flavors.py",
                    snippet=(
                        "def get_parsed_token() -> ParsedToken:\n"
                        '    """Chain base: no dependencies of its own."""\n'
                        "    return ParsedToken()\n"
                        "\n"
                        "\n"
                        "def get_authenticated_actor(\n"
                        "    token: Annotated[ParsedToken, Depends(get_parsed_token)],\n"
                        ") -> AuthenticatedActor:\n"
                        '    """Chain middle: resolves the base itself — FastAPI solves sub-dependencies."""\n'
                        "    return AuthenticatedActor(token)\n"
                        "\n"
                        "\n"
                        "def get_verified_request(\n"
                        "    actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],\n"
                        ") -> VerifiedRequest:\n"
                        '    """Chain top: depth 3 — this resolved through actor, actor through token."""\n'
                        "    return VerifiedRequest(actor)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="root-why-one-place",
                    text=(
                        "Why insist on one place? Traceability and "
                        "substitutability. Every wiring decision in the app "
                        "is greppable by reading ONE function top to bottom "
                        "— which adapter backs which port, which middleware "
                        "wraps which order, which store is optional and "
                        "degrades to a 503 envelope. And because the "
                        "decision is centralized, switching an "
                        "implementation is a one-line change at the root "
                        "with zero downstream edits: the demo scenario "
                        "store's fake/live data mode is the runtime version "
                        "of the same idea, and the test suite is the "
                        "systematic version — fixtures build the same app "
                        "factory and then override exactly the provider "
                        "seams they need (topic 34 takes that further). "
                        "When a codebase feels impossible to reason "
                        "about, the diagnosis is almost always wiring "
                        "scattered across modules; the composition root is "
                        "the cure."
                    ),
                ),
            ],
        ),
        # ── 6. Errors across layers ────────────────────────────────────────
        Section(
            id="errors-across-layers",
            title="Errors across layers",
            blocks=[
                TextBlock(
                    kind="text",
                    id="errors-pitch",
                    text=(
                        "Error handling is where architectures prove "
                        "themselves, because a failure must cross every "
                        "boundary the happy path crosses — and each layer "
                        "has a different natural way to botch it. This "
                        "repo's rule, taught piecewise since topic 30 and "
                        "stated here as architecture: inside the domain a "
                        "failure is a VALUE (``Result`` — visible in the "
                        "signature, impossible to ignore, no stack unwinding "
                        "through business code), and at the presentation "
                        "edge it becomes a RAISE, because past the router "
                        "the one channel that reliably reaches a boundary "
                        "you own is the exception pipeline. The use case "
                        "decides what a failure MEANS without knowing HTTP "
                        "exists:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="errors-usecase-quote",
                    language="py",
                    caption="The domain's half: a failure decided as a value, no HTTP in sight.",
                    source="server/guide/domain/posts/use_cases.py",
                    snippet=(
                        "    def execute(self, post_id: str, draft: PostCreate) -> Result[Post]:\n"
                        '        """Ok(replaced), or Err(not_found) — replace never creates."""\n'
                        "        post = self._posts.replace(post_id, draft)\n"
                        "        if post is None:\n"
                        '            return Err(AppError(FailureKind.NOT_FOUND, f"Post {post_id!r} not found"))\n'
                        "        return Ok(post)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="errors-edge-pitch",
                    text=(
                        "The edge flips the representation in two fixed "
                        "lines — the same flip in every router, quoted here "
                        "in the posts router's read endpoint. What the "
                        "router does NOT do is equally architectural: no "
                        "status code is chosen here (the taxonomy's table "
                        "already maps not_found to 404), no body is "
                        "formatted (one envelope shape serves every "
                        "failure), no log line is written (the handler "
                        "logs with the request id already attached):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="errors-edge-quote",
                    language="py",
                    caption="The edge's half: the two-line flip from value to raise.",
                    source="server/guide/presentation/routers/posts.py",
                    snippet=(
                        '@router.get("/api/posts/{post_id}", response_model=Post)\n'
                        "def read_post(post_id: str, use_cases: PostUseCasesDep) -> Post:\n"
                        '    """Serve one post; unknown ids are the shared 404 envelope."""\n'
                        "    result = use_cases.get_post.execute(post_id)\n"
                        "    if isinstance(result, Err):\n"
                        "        raise result.failure\n"
                        "    return result.value"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="errors-crossing",
                    text=(
                        "Past the raise, the remaining crossings are owned "
                        "by machinery every layer shares: the raised "
                        "``AppError`` unwinds through FastAPI's dependency "
                        "machinery, ExceptionMiddleware — the innermost "
                        "bookend of the middleware stack from topic 08 — "
                        "dispatches the one registered handler, and the "
                        "family envelope goes out with the request id the "
                        "request-id middleware bound, logged once with "
                        "everything an operator needs. Nothing is "
                        "swallowed anywhere on the journey: the domain's "
                        "Err is visible in a signature, the edge's raise is "
                        "visible in the router, the handler's response is "
                        "visible on the wire, and the log line ties all "
                        "three together. That end-to-end visibility ACROSS "
                        "layers is the actual requirement — the "
                        "values-then-raises split is just how this repo "
                        "achieves it honestly."
                    ),
                ),
            ],
        ),
        # ── 7. The client's mirror ─────────────────────────────────────────
        Section(
            id="the-clients-mirror",
            title="The client's mirror",
            blocks=[
                TextBlock(
                    kind="text",
                    id="mirror-pitch",
                    text=(
                        "The client is a React shell whose whole job is "
                        "rendering this content — and it deliberately "
                        "mirrors the server's architecture instead of "
                        "inventing its own. Same layer names, same rule: "
                        "``domain/`` defines ports as TypeScript interfaces, "
                        "``data/`` adapts HTTP behind them, ``ui/`` renders "
                        "and never imports ``data/`` directly, and a "
                        "composition root wires API → repository → use "
                        "case. The client's root is a small service-locator "
                        "container — symbol tokens in, singletons out — and "
                        "its wiring reads exactly like ``create_app()``'s "
                        "dependency section, one declaration block per "
                        "pipeline:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="mirror-container-quote",
                    language="ts",
                    caption="The client's composition root: tokens, then one wiring block per pipeline.",
                    source="client/src/core/container.ts",
                    snippet=(
                        "export const ContainerTokens = {\n"
                        "  AppConfig: Symbol('AppConfig'),\n"
                        "  // …\n"
                        "  MiddlewarePipelineApi: Symbol('MiddlewarePipelineApi'),\n"
                        "  MiddlewarePipelineRepository: Symbol('MiddlewarePipelineRepository'),\n"
                        "  GetMiddlewarePipelineDemoUseCase: Symbol('GetMiddlewarePipelineDemoUseCase'),\n"
                        "  // …\n"
                        "} as const;"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="mirror-wiring-quote",
                    language="ts",
                    caption="One pipeline wired at the root: API → repository → use case.",
                    source="client/src/core/container.ts",
                    snippet=(
                        "    this.register(ContainerTokens.MiddlewarePipelineApi, new MiddlewarePipelineApi(config));\n"
                        "    this.register(\n"
                        "      ContainerTokens.MiddlewarePipelineRepository,\n"
                        "      new MiddlewarePipelineRepositoryImpl(this.middlewarePipelineApi),\n"
                        "    );\n"
                        "    this.register(\n"
                        "      ContainerTokens.GetMiddlewarePipelineDemoUseCase,\n"
                        "      new GetMiddlewarePipelineDemoUseCase(this.middlewarePipelineRepository),\n"
                        "    );"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="mirror-port-pitch",
                    text=(
                        "The port looks the same too — an interface the "
                        "domain owns, returning the client's ``Result`` "
                        "type, with the HTTP adapter hidden behind it. "
                        "Every demo panel in the client resolves its use "
                        "case through the container, which is why the demo "
                        "specs can substitute fakes by re-registering one "
                        "token — the exact seam FastAPI's "
                        "``dependency_overrides`` gives the server's tests:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="mirror-port-quote",
                    language="ts",
                    caption="The client's port: domain-owned interface, Result-typed, HTTP invisible.",
                    source="client/src/domain/demo/middleware-pipeline-repository.ts",
                    snippet=(
                        "export interface MiddlewarePipelineRepository {\n"
                        "  /** Walk the live middleware chain once: stack, traced order, request id. */\n"
                        "  read(): Promise<Result<MiddlewarePipelineData>>;\n"
                        "}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="mirror-why",
                    text=(
                        "Why mirror at all, when the client is 'just' a "
                        "presentation shell? Because the same forces apply: "
                        "the client has transports to swap (the DTO layer "
                        "validates every payload shape the wire sends), "
                        "fakes to inject (fixture-driven specs without a "
                        "fetch stub in sight), and one place to answer ' "
                        "'where does THIS decision live'. The family rule "
                        "the mirror enforces is stated in the container's "
                        "own docstring: only the composition root imports "
                        "data/ adapters, views resolve through the "
                        "container, and data/ never imports the container "
                        "— the dependency rule, one language over. When "
                        "topic 34 teaches client testing, the seams this "
                        "mirror created are the entire technique."
                    ),
                ),
            ],
        ),
        # ── 8. Request-flow tracer (inline demo) ───────────────────────────
        Section(
            id="request-flow-tracer",
            title="Request-flow tracer",
            lead="This section carries the topic's demo — the architecture tracer.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="tracer-pitch",
                    text=(
                        "Everything above is the map; this demo is the "
                        "territory. The tracer endpoint answers ONE payload "
                        "that shows the architecture running: it "
                        "INTROSPECTS the live app (the built middleware "
                        "stack walked outermost-first to the router; the "
                        "traced endpoint's real dependency tree read off "
                        "the posts router; the adapter actually wired "
                        "behind the port, read off ``app.state`` with the "
                        "same isinstance guard the provider uses) and then "
                        "drives two REAL internal requests through the "
                        "application itself — a hand-built ASGI scope "
                        "handed to the app callable, the same in-process "
                        "channel the test client uses, no socket and no "
                        "staged responses. The endpoint itself is thin, "
                        "which is the point — the architecture demo "
                        "practices the architecture:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tracer-endpoint-quote",
                    language="py",
                    caption="The tracer endpoint: collect the facts, let the engine drive the rounds.",
                    source="server/guide/presentation/routers/demo/arch.py",
                    snippet=(
                        '@router.get(TRACER_PATH, response_model=ArchTracerPayload)\n'
                        "async def read_arch_tracer(request: Request) -> ArchTracerPayload:\n"
                        '    """Serve the live architecture trace: structure, wiring, two real rounds."""\n'
                        "    app = request.app\n"
                        "    return await build_arch_tracer_payload(\n"
                        "        app=app,\n"
                        "        stack_names=_built_stack_names(app),\n"
                        "        user_middleware_names=[m.cls.__name__ for m in app.user_middleware],\n"
                        "        route=_traced_route_facts(),\n"
                        "        wiring=_wiring_facts(app),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tracer-honesty",
                    text=(
                        "The tracer's honesty rules are strict, and worth "
                        "reading as an architecture lesson themselves: only "
                        "the three ASGI-boundary beats carry measured "
                        "milliseconds — the moment the request enters the "
                        "outermost layer, the moment ``http.response.start`` "
                        "leaves with status and headers, the moment the "
                        "last body message flushes — and no per-hop timing "
                        "is invented between them. Each hop row labels its "
                        "evidence: MEASURED (a timed beat), OBSERVED (a "
                        "fact read off the real response — the pagination "
                        "headers, the echoed request id, the envelope), or "
                        "INTROSPECTED (structure read off the running "
                        "app). Both rounds send an inbound ``x-request-id`` "
                        "and the responses echo it back — the round trip "
                        "is the real RequestIdMiddleware running inside "
                        "the traced requests, not a claim."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="arch:tracer",
                    title="The architecture tracer",
                    description=(
                        "Run the tracer and watch one request cross every "
                        "layer of the RUNNING app. The payload's structure "
                        "half is introspected live: the built middleware "
                        "chain (ServerErrorMiddleware outermost through "
                        "CORSMiddleware, SecurityHeadersMiddleware, "
                        "RequestIdMiddleware down to the router), the "
                        "matched /api/posts route with its REAL dependency "
                        "tree (query ← PostListQuery the model, use_cases ← "
                        "get_post_use_cases the provider), and the "
                        "composition wiring (port PostRepository, adapter "
                        "InMemoryPostRepository, bundle PostUseCases, wired "
                        "by create_app()). The trace half is two REAL "
                        "internal requests driven through the app at the "
                        "ASGI boundary: the OK round (GET /api/posts?page=2"
                        "&limit=4) crossing middleware, routing, dependency "
                        "resolution, the use case, the repository, Ok("
                        "PostPage), and the 200 + pagination-headers "
                        "mapping; the ERR round (GET /api/posts/nope) "
                        "crossing the repository's None, the use case's "
                        "Err(not_found), the router's raise, and the shared "
                        "handler's 404 envelope — with the envelope's "
                        "requestId matching the response header as the "
                        "proof. Each round shows its three measured beats "
                        "(enter → response.start → complete) and every hop "
                        "labels its evidence: measured, observed, or "
                        "introspected. Nothing between the beats is timed, "
                        "and nothing is staged."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tracer-coda",
                    text=(
                        "Read the tracer's rounds against the sections "
                        "above and the map closes: the stack rows are "
                        "topic 08's onion, the dependency rows are topic "
                        "06's mechanism wearing the composition root's "
                        "wiring, the Ok round is a thin router doing its "
                        "three movements, and the Err round is the whole "
                        "errors-across-layers story — value, raise, "
                        "handler, envelope, id — fired live against the "
                        "machinery topic 30 taught. The demo that proves "
                        "the architecture is itself built in the "
                        "architecture's shape: a pure engine in the "
                        "domain, a thin router at the edge, and not one "
                        "line of business logic in between."
                    ),
                ),
            ],
        ),
        # ── 9. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole architecture, from a shell — structure, wiring, two real rounds.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Six stops: the curriculum list (this topic is the "
                        "thirty-first), this topic's own detail with the "
                        "demo inline, the tracer's structure half (stack + "
                        "route + wiring), the two measured rounds with "
                        "their request-id round trips, the traced endpoint "
                        "itself over plain HTTP, and the 404 envelope the "
                        "Err round narrates. The stack is up; every answer "
                        "below comes from the running app quoting itself."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-index",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the curriculum: 31 topics, eight groups, platform last\n"
                        "curl -s localhost:8000/api/content \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"topics:\", len(b[\"topics\"]), \"| groups:\", [g[\"id\"] for g in b[\"groups\"]])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — this topic's detail: nine sections, the tracer inline in §8\n"
                        "curl -s localhost:8000/api/content/architecture | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "print(\"sections:\", len(t[\"sections\"]))\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-structure",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the tracer's structure half: the live stack, route, wiring\n"
                        "curl -s localhost:8000/api/demo/arch/tracer | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "print(\"stack:\", \" → \".join(l[\"name\"] for l in b[\"stack\"]))\n"
                        "r = b[\"route\"]\n"
                        "print(\"route:\", r[\"method\"], r[\"template\"], \"→\", r[\"endpoint\"],\n"
                        "      \"(response_model \" + r[\"responseModel\"] + \")\")\n"
                        "print(\"deps:\", [(d[\"param\"], d[\"provider\"], d[\"providerKind\"]) for d in r[\"dependencies\"]])\n"
                        "print(\"wiring:\", b[\"wiring\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-rounds",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the two measured rounds: beats, statuses, id round trips\n"
                        "curl -s localhost:8000/api/demo/arch/tracer | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "for r in b[\"rounds\"]:\n"
                        "    beats = \" → \".join(x[\"event\"] + \"@\" + str(x[\"offsetMs\"]) + \"ms\" for x in r[\"beats\"])\n"
                        "    print(r[\"outcome\"], r[\"requestLine\"], \"→\", r[\"status\"], \"|\", beats)\n"
                        "    facts = {f[\"name\"]: f[\"value\"] for f in r[\"facts\"]}\n"
                        "    print(\"   id:\", r[\"inboundRequestId\"], \"| echoed:\", facts.get(\"inboundIdEchoed\", facts.get(\"headerMatchesBody\")))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-posts",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the traced endpoint over plain HTTP: the same facts, your request\n"
                        "curl -sD - -o /dev/null 'localhost:8000/api/posts?page=2&limit=4' \\\n"
                        "  | grep -iE 'HTTP/|x-total-count|x-page-count|link|x-request-id'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-404",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — the Err round by hand: the envelope the tracer narrated\n"
                        "curl -s localhost:8000/api/posts/nope \\\n"
                        "  | python3 -c 'import json,sys; e=json.load(sys.stdin)[\"error\"]; print(\"404:\", e[\"code\"], \"|\", e[\"message\"], \"| id\", e[\"requestId\"][:12])'\n"
                        "curl -sD - -o /dev/null localhost:8000/api/posts/nope | grep -i x-request-id"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stops 1–2 read the architecture as content; stops "
                        "3–4 read it as evidence, with every row labeled by "
                        "how it is known; stops 5–6 reproduce the traced "
                        "rounds by hand and watch the same headers and "
                        "envelope answer. That is the architecture topic "
                        "complete: the layers named, the rule stated as an "
                        "import direction, the root concentrated in one "
                        "function, the error path crossing every boundary "
                        "visibly, the client mirroring the whole shape — "
                        "and one tracer that proves the map by walking it, "
                        "twice, in opposite directions of the Result. The "
                        "next topic points the same discipline outward: "
                        "observability, the layers made audible in "
                        "production."
                    ),
                ),
            ],
        ),
    ],
)
