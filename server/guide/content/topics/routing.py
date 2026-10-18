"""Topic 07 — routing (first topic of the Request handling group).

What routing is — the dispatch table that turns a request line into a
handler call — taught against this server's own routers: the @app.get
family · APIRouter prefixes and tags · path variables, query parameters,
and their patterns · how Starlette matches and what 404/405/307 really
mean · mounted sub-apps vs included routers · routing at scale — with the
topic's live demo (``routing:explorer``) inline in the first section, and
the terminal curl tour last.

Every code block quotes a real repo file (the snippet ratchet verifies
it): the composition root's include list, the health/content/scenario/http
routers, the explorer demo's own builder and endpoint, the error taxonomy's
status mapping, and the factory test that resolves routes the public way.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="routing",
    title="Routing",
    subtitle=(
        "The dispatch table between a request line and a handler — how FastAPI "
        "matches, binds parameters, and answers 404, 405, and 307."
    ),
    group="request-handling",
    order=7,
    sections=[
        # ── 1. What routing is (inline demo) ────────────────────────────────
        Section(
            id="what-routing-is",
            title="What routing is",
            lead="The demo of this topic lives here — beside the teaching it proves.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="routing-pitch",
                    text=(
                        "Every HTTP request arrives as two facts your code never sees "
                        "raw: a method and a path. Routing is the machinery that turns "
                        "those two facts into one function call — the dispatch table "
                        "between the wire (topic 03 walked a request's journey) and "
                        "the endpoint you wrote (topic 04 dissected one). The table "
                        "itself is ordinary data built at STARTUP, not at request "
                        "time: each entry is a method, a path template like "
                        "/api/content/{topic_id}, and the handler plus everything "
                        "FastAPI derived from its signature. Nothing matches by "
                        "convention, annotation scanning, or file layout — a route "
                        "exists because a registration call put it in the table, and "
                        "this app builds its whole table in one function, the "
                        "composition root:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="routing-includes",
                    language="py",
                    caption="create_app: the entire route table, assembled in wiring order.",
                    source="server/guide/main.py",
                    snippet=(
                        "    app.include_router(health.router)\n"
                        "    app.include_router(content.router)\n"
                        "    app.include_router(demo_scenario.router)\n"
                        "    app.include_router(demo_py.router)\n"
                        "        # …\n"
                        "    app.include_router(demo_routing.router)\n"
                        "    app.include_router(demo_dep.router)\n"
                        "    return app"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="routing-table-consequences",
                    text=(
                        "Reading that as a table explains three behaviors you have "
                        "already met. The table is per-app: create_app() builds a "
                        "fresh one each call, which is why tests get isolated "
                        "routing (and why two apps wire the same routes but own "
                        "separate tables). The table is built once, before the first "
                        "request — routing adds no per-request registration cost, and "
                        "a route that was never included is as absent as one never "
                        "written. And the table is the DECLARED surface: FastAPI "
                        "routes only what you registered, which is the same fact "
                        "topic 03 probed when a HEAD request 405'd against a GET "
                        "route — no implicit methods exist. This topic's demo makes "
                        "that table explorable: hand it a method and a path, and it "
                        "replays the router's resolution against the live app's "
                        "declared routes, reporting the matched template, the "
                        "parameters it would bind, or the 404/405/307 outcome with "
                        "the reasoning:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="routing-demo-endpoint",
                    language="py",
                    caption="The demo endpoint — note its own two query parameters.",
                    source="server/guide/presentation/routers/demo/routing.py",
                    snippet=(
                        "@router.get(\n"
                        "    \"/explorer\", response_model=RoutingExplorerPayload, response_model_exclude_none=True\n"
                        ")\n"
                        "def read_routing_explorer(\n"
                        "    request: Request,\n"
                        "    method: ExplorerMethod = \"GET\",\n"
                        "    path: Annotated[str, Field(pattern=_PATH_PATTERN)] = \"/api/health\",\n"
                        ") -> RoutingExplorerPayload:\n"
                        "    \"\"\"Match one simulated method+path against the app's declared route table.\"\"\"\n"
                        "    return build_routing_explorer_payload(\n"
                        "        method=method,\n"
                        "        path=path,\n"
                        "        paths=request.app.openapi()[\"paths\"],\n"
                        "    )"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="routing:explorer",
                    title="The route explorer",
                    description=(
                        "Pick a method and a path; the explorer matches them against "
                        "this very app's declared route table and shows the matched "
                        "template with its bound path/query parameters — or the honest "
                        "405 with allowed methods, the 307 trailing-slash redirect, "
                        "or the 404 with the nearest declared paths. Try HEAD against "
                        "/api/health: the 405 is the no-implicit-HEAD rule, live."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="routing-demo-coda",
                    text=(
                        "Two details in that endpoint are deliberate. The route table "
                        "comes from app.openapi()[\"paths\"], not app.routes — since "
                        "FastAPI 0.143, include_router wraps included routers and the "
                        "wrapping entries expose no .path attribute, so the OpenAPI "
                        "schema is the stable public view of the declared surface "
                        "(topic 04's app-info demo made the same choice). And the "
                        "endpoint's own method and path parameters are query "
                        "parameters with defaults and a pattern constraint — the "
                        "exact machinery the path-and-query section below teaches, "
                        "used by the demo that teaches it. The rest of the topic "
                        "walks the table's life: how routes get declared, organized, "
                        "parameterized, matched, and kept sane at scale."
                    ),
                ),
            ],
        ),
        # ── 2. The @app.get family ──────────────────────────────────────────
        Section(
            id="the-get-family",
            title="The @app.get family",
            blocks=[
                TextBlock(
                    kind="text",
                    id="get-family-pitch",
                    text=(
                        "Route registration is a decorator per HTTP verb: @app.get, "
                        "@app.post, @app.put, @app.patch, @app.delete, @app.options, "
                        "@app.head, @app.trace. Each is sugar over one underlying "
                        "call — app.add_api_route(path, endpoint, methods=[\"GET\"]) "
                        "— and each answers exactly one question the same way: when a "
                        "request with this method matches this path template, call "
                        "this function. The framework never infers verbs from your "
                        "handler's name or shape; DELETE is a decorator you wrote or "
                        "a 405 you will receive. This repo declares routes on "
                        "APIRouter instances rather than the app object (the next "
                        "section's organization) — the health router is the smallest "
                        "real example of the family:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="get-family-health",
                    language="py",
                    caption="A whole router: prefix, tag, one GET, declared response model.",
                    source="server/guide/presentation/routers/health.py",
                    snippet=(
                        "router = APIRouter(prefix=\"/api\", tags=[\"health\"])\n"
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
                    id="get-family-verbs-in-repo",
                    text=(
                        "The verb you declare is a contract claim, and topic 03's "
                        "method semantics are the reason: GET promises safety (no "
                        "side effects on the resource), PUT and DELETE promise "
                        "idempotence, POST promises neither. The router is where "
                        "that promise becomes code. This server deliberately uses "
                        "three verbs, each honestly:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="get-family-verbs-list",
                    ordered=False,
                    items=[
                        "GET — the read verb; every content, health, and demo "
                        "endpoint that only reports state, like read_health above "
                        "and the explorer itself.",
                        "POST — the submit verb; the headers demo's echo pair uses "
                        "it because a POST visibly carries a body (and a "
                        "content-type) that a GET cannot.",
                        "PATCH — the partial-update verb; the scenario toggle "
                        "applies a patch where missing keys mean unchanged — PUT "
                        "would claim a full replacement instead.",
                    ],
                ),
                CodeBlock(
                    kind="code",
                    id="get-family-patch",
                    language="py",
                    caption="The repo's one PATCH: partial update semantics, declared.",
                    source="server/guide/presentation/routers/demo/scenario.py",
                    snippet=(
                        "@router.patch(\"/scenario\", response_model=ScenarioState)\n"
                        "def update_scenario(patch: ScenarioPatch, store: ScenarioStoreDep) -> ScenarioState:\n"
                        "    \"\"\"Apply a partial update; the response is the resulting full state.\"\"\"\n"
                        "    return store.update(patch)"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="get-family-post",
                    language="py",
                    caption="The echo pair: same path, two verbs, two handlers.",
                    source="server/guide/presentation/routers/demo/http.py",
                    snippet=(
                        "@router.post(\n"
                        "    \"/headers\", response_model=HttpHeadersEchoPayload, response_model_exclude_none=True\n"
                        ")\n"
                        "def send_headers_echo(\n"
                        "    request: Request, body: HeadersDemoBody | None = None\n"
                        ") -> HttpHeadersEchoPayload:"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="get-family-decorator-kwargs",
                    text=(
                        "Beyond the verb, every decorator in the family accepts "
                        "the same declaration surface as route-level metadata: "
                        "response_model (what the 200 documents and validates — "
                        "every route in this repo declares one, the house "
                        "convention), status_code for the non-200 success "
                        "statuses (a POST that creates answers 201 when you say "
                        "so — the demos so far all answer 200), name for the "
                        "route's url_path_for identity when the function name "
                        "will not do, and deprecated to keep a route serving "
                        "while the docs mark it dying. None of that is matching "
                        "behavior — the decorator still answers only its one "
                        "verb — but it is worth meeting here because it is the "
                        "same one-line-per-route economy: the registration site "
                        "is where the route's whole public identity is declared, "
                        "and everything later in the pipeline (validation, "
                        "serialization, documentation) reads back from it. The "
                        "decorators do not compose — a handler is registered "
                        "once, under exactly the verbs its decorators name, in "
                        "the order the includes ran."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="get-family-same-path",
                    text=(
                        "The POST quote above shows the family's most useful property: "
                        "the same path may carry SEVERAL entries, one per verb, each "
                        "with its own handler, dependencies, and response model — "
                        "/api/demo/http/headers has both a GET and a POST, and "
                        "/api/demo/scenario pairs GET with PATCH. They are separate "
                        "rows in the table, not modes of one row; a request for a "
                        "verb no row declares is the 405 of the matching section "
                        "below. One naming note: the decorators' functions are named "
                        "read_/send_/update_ after their verb, because those names "
                        "are the route names url_path_for resolves later — the "
                        "at-scale section returns to that."
                    ),
                ),
            ],
        ),
        # ── 3. APIRouter + prefixes/tags ────────────────────────────────────
        Section(
            id="apirouter-prefixes-tags",
            title="APIRouter, prefixes, and tags",
            blocks=[
                TextBlock(
                    kind="text",
                    id="apirouter-pitch",
                    text=(
                        "FastAPI() itself carries the same decorator family — "
                        "@app.get works — but an app of more than a handful of "
                        "routes stops declaring them there, because the app object "
                        "would become one import-everything module with no seams. "
                        "APIRouter is the extract-class of routing: a route table "
                        "you build in its own module, then hand to the app. Its two "
                        "constructor arguments do the heavy lifting — prefix is "
                        "prepended to every route the router declares, so the "
                        "content router's routes say /{topic_id} while the wire "
                        "says /api/content/{topic_id}, and the prefix lives in "
                        "exactly one place; tags ride into OpenAPI and group the "
                        "docs by router (topic 12 shows the rendered result). This "
                        "server has one router per route family, each naming both:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="apirouter-content",
                    language="py",
                    caption="Prefix + tag at the router, path relative at the route.",
                    source="server/guide/presentation/routers/content.py",
                    snippet=(
                        "router = APIRouter(prefix=\"/api/content\", tags=[\"content\"])"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="apirouter-demo-router",
                    language="py",
                    caption="The explorer's own router — the same two-argument shape.",
                    source="server/guide/presentation/routers/demo/routing.py",
                    snippet=(
                        "router = APIRouter(prefix=\"/api/demo/routing\", tags=[\"demo:routing\"])"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="apirouter-include",
                    text=(
                        "include_router is the join: it copies every route the "
                        "router declared — prefix and all — into the app's table, "
                        "which is why create_app's include list IS the table's "
                        "construction log. The copy is a real merge with real "
                        "consequences. Routes from two routers may interleave by "
                        "registration order even though their modules sit apart. A "
                        "router may itself include other routers, prefix stacking "
                        "as it goes — the mechanism behind versioned mounts like "
                        "include_router(api_v2, prefix=\"/v2\") that keep one "
                        "codebase serving two URL generations. And dependencies "
                        "given to include_router wrap every copied route, which is "
                        "how a whole router grows an auth requirement in one line — "
                        "topic 24 leans on exactly that. Since FastAPI 0.143 there "
                        "is one caveat worth repeating from the demo above: "
                        "include_router wraps the included routes, and the wrapping "
                        "entries expose no .path, so code that introspects the "
                        "table should read the OpenAPI schema (or url_path_for) "
                        "instead of app.routes internals."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="apirouter-organization",
                    text=(
                        "The organization this repo settles on is the one the "
                        "family invariant already names: routers stay thin — parse "
                        "and validate input, call a use case, map the Result to a "
                        "response — and one module owns one family. The demo "
                        "routers make the granularity visible: py, pyd, runtime, "
                        "http, fastapi, routing, dep, middleware, reqres, and "
                        "whichever areas later topics add — one area per file, each with "
                        "its own /api/demo/<area> prefix and demo:<area> tag, so a "
                        "demo endpoint's URL, its docs grouping, and its module all "
                        "answer to the same word. Nothing enforces the alignment; "
                        "the registry's demo-id pattern (<area>:<name>) merely "
                        "mirrors it. The reward is diff locality — topic 06's "
                        "dependency demos arrived as one new router file plus one "
                        "include line, touching no other route's code."
                    ),
                ),
            ],
        ),
        # ── 4. Path variables / query parameters / patterns ────────────────
        Section(
            id="path-and-query-parameters",
            title="Path variables, query parameters, and patterns",
            blocks=[
                TextBlock(
                    kind="text",
                    id="params-pitch",
                    text=(
                        "A path template's {braces} are holes the router fills at "
                        "match time, and the filled values become handler "
                        "arguments by NAME — /api/content/{topic_id} with a "
                        "request for /api/content/routing calls read_topic("
                        "topic_id=\"routing\"). The declaration is one line in the "
                        "signature; the router extracts, and FastAPI validates "
                        "against the annotation before your code runs (topic 05's "
                        "pydantic pipeline, applied to the URL itself). This is "
                        "the repo's canonical example, whole:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="params-topic-id",
                    language="py",
                    caption="One path parameter, typed str, resolved by name.",
                    source="server/guide/presentation/routers/content.py",
                    snippet=(
                        "@router.get(\"/{topic_id}\", response_model=ContentDetail, response_model_exclude_none=True)\n"
                        "def read_topic(\n"
                        "    topic_id: str,\n"
                        "    registry: Annotated[ContentRegistry, Depends(get_content_registry)],\n"
                        ") -> ContentDetail:\n"
                        "    \"\"\"Serve one topic's full payload + version; unknown ids are the 404 envelope.\"\"\"\n"
                        "    topic = registry.topic_by_id(topic_id)\n"
                        "    if topic is None:\n"
                        "        raise AppError(FailureKind.NOT_FOUND, f\"Topic '{topic_id}' not found\")\n"
                        "    return ContentDetail.model_validate({**topic.model_dump(), \"version\": CONTENT_API_VERSION})"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="params-query-pitch",
                    text=(
                        "Query parameters are the same idea with a different "
                        "address: anything after the ? in the URL, parsed into "
                        "name=value pairs, bound to same-named signature "
                        "parameters that the path template does NOT claim. The "
                        "explorer endpoint is a live specimen — method and path "
                        "are not in its path template, so both arrive from the "
                        "query string, and both carry declarative behavior:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="params-explorer-signature",
                    language="py",
                    caption="A default makes a query param optional; a Literal rejects the rest as 422.",
                    source="server/guide/presentation/routers/demo/routing.py",
                    snippet=(
                        "ExplorerMethod = Literal[\"GET\", \"POST\", \"PUT\", \"PATCH\", \"DELETE\", \"HEAD\", \"OPTIONS\"]\n"
                        "\"\"\"The verbs a caller may simulate (TRACE never reaches a JSON API in practice).\"\"\"\n"
                        "\n"
                        "_PATH_PATTERN: str = r\"^/[^?#]*(?:\\?[^#]*)?$\"\n"
                        "\"\"\"Absolute path, optional query string — exactly what a browser location carries.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="params-where",
                    text=(
                        "Where a value lives is an API-design decision, and the "
                        "rule of thumb is identity versus configuration: the path "
                        "names WHAT you are addressing (topic_id identifies the "
                        "resource — change it and you address something else), "
                        "while the query tunes HOW the request behaves (the "
                        "explorer's method/path are inputs to a computation, "
                        "defaults sensible, order irrelevant). The browser URL bar "
                        "teaches the same split every day. The pattern vocabulary "
                        "this repo actually uses, in one place:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="params-patterns-list",
                    ordered=False,
                    items=[
                        "Bare annotation — topic_id: str binds a path segment with "
                        "the default str converter (one-or-more non-slash "
                        "characters); a mismatched shape cannot happen for str, "
                        "but int or bool annotations coerce and 422 on garbage.",
                        "Literal — method: ExplorerMethod narrows the accepted "
                        "values to a closed set at the signature; anything else "
                        "fails validation before the handler, as the 422 envelope "
                        "with the offending location.",
                        "Annotated + Field — path: Annotated[str, Field"
                        "(pattern=...)] constrains with a regex; min/max length, "
                        "and numeric bounds ride the same construct (topic 10 "
                        "widens it into the validation story).",
                        "Default value — method: ExplorerMethod = \"GET\" makes a "
                        "parameter optional with a documented fallback; omitted "
                        "from the query means the default, present-but-empty is "
                        "still validated.",
                        "Optional-of — body: HeadersDemoBody | None = None is the "
                        "body sibling: the request may carry no body at all, and "
                        "the handler branches on None.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="params-converters",
                    text=(
                        "Starlette also has an inline converter syntax this repo "
                        "does not use — written in prose, honestly: a template "
                        "segment {page:int} matches digits only and hands the "
                        "handler an int, {path:path} matches across slashes for "
                        "catch-all file paths, and {uid:uuid} a full UUID. The "
                        "default {name} is str in disguise. FastAPI codebases "
                        "usually reach the same goals with the typed-signature "
                        "style above because it lands the constraint in OpenAPI, "
                        "so the repo has no converter to quote — but you will "
                        "read the syntax in Starlette-era codebases, and now you "
                        "can place it: it is template-side where Annotated is "
                        "signature-side, two spellings of one idea."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="params-repeated-keys",
                    text=(
                        "Query parsing has its own small rulebook. Keys may "
                        "repeat — ?tag=a&tag=b — and whether that is an error, "
                        "the last value, or a list depends on the handler's "
                        "annotation: list[str] collects every occurrence, a "
                        "plain str takes the last (the explorer's builder makes "
                        "that choice explicit, last occurrence wins, "
                        "dict-style). Values are percent-decoded by the parser, "
                        "blank values survive only if you ask for them "
                        "(keep_blank_values above), and the separator is always "
                        "& with = for assignment — the query is a flat "
                        "convention, not a nested language. One boundary worth "
                        "knowing: the query string is PART of the URL, so it "
                        "lives in the request line the router sees, while a "
                        "body is a separate stream the handler parses — which "
                        "is why routing never looks at a body and why the "
                        "headers demo could put ?from=client-demo on its POST "
                        "URL and still carry a JSON body underneath."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="params-extraction-real",
                    text=(
                        "What the router actually does with a matched template is "
                        "small enough to hold in your head, and the explorer's "
                        "builder does it in miniature — the demo's matcher is the "
                        "teaching exhibit with a real home. The query side is one "
                        "partition plus the stdlib's parser:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="params-builder-query",
                    language="py",
                    caption="Splitting the query off, then parsing pairs (blank values kept).",
                    source="server/guide/domain/demos/routing_explorer.py",
                    snippet=(
                        "    raw_path, _, raw_query = path.partition(\"?\")\n"
                        "    query_pairs = parse_qsl(raw_query, keep_blank_values=True)"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="params-builder-bind",
                    language="py",
                    caption="Extraction is a groupdict — name to value, per template hole.",
                    source="server/guide/domain/demos/routing_explorer.py",
                    snippet=(
                        "class BoundParam(CamelModel):\n"
                        "    \"\"\"One parameter the router would bind for the handler.\"\"\"\n"
                        "\n"
                        "    name: str\n"
                        "    value: str\n"
                        "    source: ParamSource"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="params-coda",
                    text=(
                        "Read the demo's payload against this section: for "
                        "GET /api/content/routing it reports template "
                        "/api/content/{topic_id}, one path parameter (topic_id, "
                        "'routing', from the path), and however many query "
                        "parameters you appended — the same facts the real router "
                        "would hand read_topic, displayed one layer earlier in the "
                        "pipeline. When matching itself — the walk, the 404, the "
                        "405, the redirect — is the subject, the next section "
                        "takes it whole."
                    ),
                ),
            ],
        ),
        # ── 5. Matching + 404 ───────────────────────────────────────────────
        Section(
            id="matching-and-404",
            title="Matching, and what 404 really means",
            blocks=[
                TextBlock(
                    kind="text",
                    id="matching-pitch",
                    text=(
                        "With the table built and a request in hand, resolution is "
                        "a walk: Starlette compiles each template to a regex "
                        "(/api/content/{topic_id} becomes ^/api/content/"
                        "(?P<topic_id>[^/]+)$), walks the table in REGISTRATION "
                        "order, and the first full match wins. Method is checked "
                        "as part of the match — a template matches only if it "
                        "declares the request's verb — and the walk ends at the "
                        "first entry that matches both. Nothing scores partial "
                        "credit, nothing reorders: a request either finds its row "
                        "or falls off the end of the table. The explorer replays "
                        "exactly that walk against the declared schema:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="matching-loop",
                    language="py",
                    caption="The walk in miniature: compile, match, bind — first hit returns.",
                    source="server/guide/domain/demos/routing_explorer.py",
                    snippet=(
                        "    for template in sorted(paths):\n"
                        "        match = _compile_template(template).match(raw_path)\n"
                        "        if match is None:\n"
                        "            continue\n"
                        "        methods = _declared_methods(paths[template])\n"
                        "        path_params = _param_list(match.groupdict(), \"path\")\n"
                        "        query_params = _param_list(query_index, \"query\")\n"
                        "        if method in methods:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="matching-compile",
                    language="py",
                    caption="Template to regex: static literal, param one-or-more non-slash.",
                    source="server/guide/domain/demos/routing_explorer.py",
                    snippet=(
                        "    parts = [\n"
                        "        f\"(?P<{match.group(1)}>[^/]+)\"\n"
                        "        if (match := _PATH_SEGMENT_PARAM.match(segment))\n"
                        "        else re.escape(segment)\n"
                        "        for segment in segments\n"
                        "    ]\n"
                        "    return re.compile(\"^/\" + \"/\".join(parts) + \"$\")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="matching-404",
                    text=(
                        "Fall off the end of the table and the answer is 404 — but "
                        "a 404 from the ROUTER is mechanical, not semantic: it "
                        "means no declared template matched the path. The 404 you "
                        "return from application logic — resource-style not-found, "
                        "a known path with an unknown id — is yours to raise, and "
                        "the content router shows the boundary precisely: the "
                        "template /api/content/{topic_id} matched long before the "
                        "handler ran, routing succeeded, and THEN the registry "
                        "lookup missed:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="matching-404-raise",
                    language="py",
                    caption="Routing matched; the handler decides absence is not_found.",
                    source="server/guide/presentation/routers/content.py",
                    snippet=(
                        "    topic = registry.topic_by_id(topic_id)\n"
                        "    if topic is None:\n"
                        "        raise AppError(FailureKind.NOT_FOUND, f\"Topic '{topic_id}' not found\")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="matching-405",
                    text=(
                        "Between those two 404s live two more outcomes, both "
                        "already probed in earlier topics and now explainable from "
                        "the table's side. When a template matches the PATH but "
                        "declares a different method set, Starlette answers 405 "
                        "Method Not Allowed with an allow header naming exactly "
                        "the declared verbs — topic 03's HEAD probe hit this, "
                        "because FastAPI routes only declared methods and a GET "
                        "route does not implicitly serve HEAD. The 405 flows "
                        "through the same envelope as everything else, bucketed "
                        "by the taxonomy's closest-kind rule:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="matching-405-kind",
                    language="py",
                    caption="405 keeps its truthful status, takes the not_found bucket.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "def kind_for_http_status(status: int) -> FailureKind:\n"
                        "    \"\"\"Map an HTTP status to the closest failure kind.\n"
                        "\n"
                        "    Statuses the taxonomy names map exactly; unnamed 4xx statuses take the\n"
                        "    ``not_found`` bucket (closest client-error kind — e.g. 405 method not\n"
                        "    allowed) and unnamed 5xx statuses take ``internal``. The response keeps\n"
                        "    the truthful status either way.\n"
                        "    \"\"\"\n"
                        "    exact = _KIND_BY_HTTP_STATUS.get(status)\n"
                        "    if exact is not None:\n"
                        "        return exact\n"
                        "    return FailureKind.NOT_FOUND if status < 500 else FailureKind.INTERNAL"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="matching-redirect",
                    text=(
                        "The third outcome is the quietest: request /api/content/ "
                        "— trailing slash — and no template matches as written, "
                        "because the regexes end at the path's last segment. "
                        "Starlette's redirect_slashes retries the walk with the "
                        "slash toggled; a hit means 307 Temporary Redirect to the "
                        "canonical form, method and query preserved, and the "
                        "client re-issues the request there. Topic 04's curl tour "
                        "watched /docs/ do exactly this. The explorer surfaces it "
                        "as its own outcome with the redirect target, so the "
                        "difference between a 404 and a one-character 307 is "
                        "something you can see rather than believe. One last "
                        "matching fact that bites at scale: first match wins, so "
                        "an overlapping pair like /users/me declared before "
                        "/users/{user_id} quietly shadows the parameter route — "
                        "order is load-bearing, and the at-scale section makes it "
                        "a checklist item."
                    ),
                ),
            ],
        ),
        # ── 6. Mounted sub-apps ─────────────────────────────────────────────
        Section(
            id="mounted-sub-apps",
            title="Mounted sub-apps",
            blocks=[
                TextBlock(
                    kind="text",
                    id="mounts-pitch",
                    text=(
                        "include_router is not the only way one server grows "
                        "another's surface. app.mount(\"/prefix\", subapp) delegates "
                        "an entire ASGI application — its own routing, middleware, "
                        "and error handling — to a path prefix: the mount is a "
                        "single row in the OUTER table whose handler is the inner "
                        "app, matched by prefix and handed the request path with "
                        "the prefix stripped. That is the real distinction from "
                        "include_router: including MERGES route tables (both "
                        "routers' rows live in one table, one resolution walk, "
                        "shared middleware and exception handlers), while mounting "
                        "NESTS applications (the outer table has one prefix row; "
                        "the inner app resolves everything below it, with its own "
                        "stack). Use include_router for your own routes; reach for "
                        "a mount when the thing under the prefix is genuinely not "
                        "your router."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="mounts-real-counterparts",
                    text=(
                        "The classic mount residents are exactly those not-your-"
                        "router apps: Starlette's StaticFiles (a file-serving app — "
                        "app.mount(\"/static\", StaticFiles(directory=\"static\")), "
                        "the form topic 04 showed in prose), a GraphQL sub-app "
                        "(topic 13 mounts one under a path), an admin UI, or "
                        "another team's service embedded wholesale. This repo "
                        "calls app.mount zero times, and says so honestly — a "
                        "JSON API with a separate browser shell has nothing static "
                        "to serve. Its real mounted surfaces are the framework's "
                        "own: /docs, /redoc, and /openapi.json are constructor-"
                        "switched mounts FastAPI itself wires, and the app-info "
                        "demo reports them as first-class facts:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="mounts-docs-model",
                    language="py",
                    caption="The framework's mounted surfaces, as the demo reports them.",
                    source="server/guide/domain/demos/fastapi_app_info.py",
                    snippet=(
                        "class DocsMounts(CamelModel):\n"
                        "    \"\"\"Where the framework's built-in documentation surfaces live.\"\"\"\n"
                        "\n"
                        "    docs_url: str | None\n"
                        "    redoc_url: str | None\n"
                        "    openapi_url: str | None"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="mounts-stack-boundary",
                    text=(
                        "\"Its own stack\" is the phrase to take literally. A "
                        "request that enters a mount is one request from the "
                        "client's point of view, but it crosses a boundary: the "
                        "outer app's exception handlers do not catch the inner "
                        "app's errors, and its middleware sees the request only "
                        "up to the delegation (topic 08 unwinds the middleware "
                        "chain this boundary interrupts). For included routers "
                        "no such boundary exists — that is the practical test "
                        "for which tool a situation wants. If the routes should "
                        "share this app's envelope, logging, and request-id "
                        "machinery, they belong in an included router; if they "
                        "should deliberately NOT — a third-party dashboard whose "
                        "errors must not shape-shift into your envelope, a "
                        "static tree the kernel should serve untouched — the "
                        "mount's isolation is the feature, not a cost. This "
                        "guide's own composition keeps everything in one "
                        "envelope by construction: zero mounts, one included "
                        "table, one error taxonomy end to end."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="mounts-constructor",
                    text=(
                        "Those three are constructor parameters — docs_url, "
                        "redoc_url, openapi_url — defaulted on, disablable with "
                        "None when an API must not advertise itself. The factory "
                        "line that owns them is unremarkable precisely because "
                        "they are defaults:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="mounts-factory",
                    language="py",
                    caption="The defaults are the mounts: nothing here calls app.mount.",
                    source="server/guide/main.py",
                    snippet=(
                        "def create_app() -> FastAPI:\n"
                        "    \"\"\"Build one wired FastAPI application instance.\"\"\"\n"
                        "    config = get_config()\n"
                        "    configure_logging(config.log_level)\n"
                        "    app = FastAPI(title=APP_TITLE, version=__version__, lifespan=lifespan)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="mounts-coda",
                    text=(
                        "Two routing consequences close the section. A mount is "
                        "resolved by the same first-match walk as any row, so a "
                        "route declared BEFORE the mount at an overlapping path "
                        "wins — mounts do not override earlier routes, they join "
                        "the table in the order added (and app.mount calls in "
                        "FastAPI add after the constructor's own docs mounts). "
                        "And what is under a mount never appears in the outer "
                        "app's OpenAPI schema — the schema documents the declared "
                        "router surface, which is why the app-info demo lists "
                        "/api/... routes in its table but carries the docs mounts "
                        "in a separate object. Nesting an app nests its contract "
                        "too; documenting it is the inner app's job."
                    ),
                ),
            ],
        ),
        # ── 7. Routing at scale ─────────────────────────────────────────────
        Section(
            id="routing-at-scale",
            title="Routing at scale",
            blocks=[
                TextBlock(
                    kind="text",
                    id="scale-pitch",
                    text=(
                        "The table stays honest at a hundred routes only by "
                        "discipline, and the disciplines are structural, not "
                        "clever. This repo's layout rule is one file per route "
                        "family — stated where the code lives, in the package's "
                        "own docstring:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scale-init-docstring",
                    language="py",
                    caption="The layout rule, one line, where it is enforced by convention.",
                    source="server/guide/presentation/routers/__init__.py",
                    snippet=(
                        "\"\"\"Router modules — one file per route family, mounted by ``create_app()``.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scale-rules",
                    text=(
                        "Around that layout, the practices that keep a large table "
                        "navigable — each already visible somewhere in this repo:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="scale-practices-list",
                    ordered=False,
                    items=[
                        "Prefix at the router, never at each route — the family's "
                        "URL space has one spelling, and moving it is a one-line "
                        "constructor change (every router in this repo).",
                        "Tag per router — docs and schema group by the same word "
                        "as the module and the URL area; the demo routers' "
                        "demo:<area> tags make /docs readable at a glance.",
                        "Include in one place — the composition root's include "
                        "list is the table's construction log; grep it to know "
                        "what serves traffic (create_app above).",
                        "Specific before generic — first match wins, so declare "
                        "literal segments (/users/me) before parameter routes "
                        "(/users/{user_id}) in the same table, or the parameter "
                        "route shadows them.",
                        "Resolve, do not guess — tests and links build URLs with "
                        "url_path_for(name, **params) instead of string-pasting "
                        "paths, so renames fail loudly at the resolve site.",
                        "Introspect the public surface — the OpenAPI schema (or "
                        "app-info) is the table as data, for checks and tooling; "
                        "app.routes internals are neither stable nor complete "
                        "since 0.143's include wrapping.",
                    ],
                ),
                CodeBlock(
                    kind="code",
                    id="scale-url-path-for",
                    language="py",
                    caption="Reverse resolution + the 0.143 introspection caveat, as a real test.",
                    source="server/tests/test_app_factory.py",
                    snippet=(
                        "def test_health_route_registered(app: FastAPI) -> None:\n"
                        "    \"\"\"Route presence via the public resolver, not app.routes internals\n"
                        "    (include_router composes routers since FastAPI 0.143).\"\"\"\n"
                        "\n"
                        "    assert app.url_path_for(\"read_health\") == \"/api/health\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scale-url-path-for-note",
                    text=(
                        "That test is doing two things at once worth separating. "
                        "url_path_for(\"read_health\") is reverse routing — handler "
                        "name plus parameter values in, URL out — and because the "
                        "name is the handler function's name, a rename that misses "
                        "a call site fails the test rather than a user. And the "
                        "docstring records the family-wide caveat as a fact where "
                        "a future editor will meet it: route presence is asserted "
                        "through the public resolver because app.routes internals "
                        "do not survive include_router's wrapping. The same "
                        "discipline scales to the browser side — the client shell "
                        "navigates by topic id to /api/content/{topic_id} paths it "
                        "receives from the index, never paths it assembles."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scale-coda",
                    text=(
                        "Where routing ends, API design begins: this topic made "
                        "the mechanism honest — table, match, bind, 404/405/307 — "
                        "while the SHAPE of the paths themselves (resource nouns, "
                        "nesting depth, pagination and filtering as query "
                        "conventions) is deliberately not routing's question. "
                        "Topic 11 takes it, with the posts workbench as its demo; "
                        "topic 12 then shows how the declared table becomes "
                        "machine-readable documentation without a second source of "
                        "truth. Before either, the terminal companion below walks "
                        "this topic's own surface from the shell."
                    ),
                ),
            ],
        ),
        # ── 8. Terminal companion ───────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="The router's answers, read straight off the wire.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-pitch",
                    text=(
                        "With the stack up (server on :8000), this tour exercises "
                        "every outcome the matching section taught. The explorer "
                        "takes query parameters — method and path — so its URLs "
                        "are the section's lesson in miniature; python3 -m "
                        "json.tool keeps the tour dependency-free:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-index",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the declared curriculum: 7 topics, groups included\n"
                        "curl -s localhost:8000/api/content | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# this topic, in full — a path parameter resolved by the router\n"
                        "curl -s localhost:8000/api/content/routing | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-explorer-match",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the demo: match GET /api/content/routing against the declared table\n"
                        "curl -s 'localhost:8000/api/demo/routing/explorer?method=GET&path=/api/content/routing' | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-explorer-405",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the no-implicit-HEAD rule, as the explorer reports it\n"
                        "curl -s 'localhost:8000/api/demo/routing/explorer?method=HEAD&path=/api/health' | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-405-live",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the real thing: HEAD against a GET route 405s, allow names the verbs\n"
                        "curl -s -i -X HEAD localhost:8000/api/health"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-307",
                    language="bash",
                    source=None,
                    snippet=(
                        "# one trailing slash: 307 to the canonical path (watch location)\n"
                        "curl -s -o /dev/null -w '%{http_code} %{redirect_url}\\n' localhost:8000/api/content/"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-404",
                    language="bash",
                    source=None,
                    snippet=(
                        "# unknown topic: routing matched, the handler raised — one envelope\n"
                        "curl -s -i localhost:8000/api/content/nope"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Every outcome in this tour came from one table and one "
                        "walk: the 200s found their row, the 307 toggled a slash, "
                        "and the 404/405 fell off or missed the method set — all "
                        "rendered through the same envelope with an x-request-id "
                        "matching the server logs. The next topic follows the "
                        "request that routing hands onward, through the middleware "
                        "chain that wraps the whole walk."
                    ),
                ),
            ],
        ),
    ],
)
