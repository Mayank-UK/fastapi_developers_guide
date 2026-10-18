"""Topic 09 — request-response (third topic of the Request handling group).

The handler's own two objects, taught against this server's real code: the
Request object (the parsed view a handler actually receives) · pydantic
bodies + response_model (the typed contract in and the filtered shape out)
· Response/JSONResponse + status codes · headers and cookies ·
StreamingResponse + SSE · content negotiation · redirects — with the
topic's two live demos (``reqres:inspector`` in the first section,
``reqres:methods`` in the second) inline beside their teaching, and the
terminal curl tour last.

Every code block quotes a real repo file (the snippet ratchet verifies
it): the headers echo's collector, the request-id middleware's
response-side stamp, this topic's own inspector and notes playground
(builder + router, written for exactly this teaching), the error
taxonomy's JSONResponse construction, the runtime streaming demo's real
async generator and its StreamingResponse router, the headers demo's
negotiation set, and the routing explorer's redirect branch.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="request-response",
    title="The request and the response",
    subtitle=(
        "The two objects every handler touches — what the Request really "
        "holds, how bodies and response models shape the contract, and the "
        "responses FastAPI can send back."
    ),
    group="request-handling",
    order=9,
    sections=[
        # ── 1. The Request object (inline demo) ─────────────────────────────
        Section(
            id="the-request-object",
            title="The Request object",
            lead="The demo of this topic lives here — beside the teaching it proves.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="req-pitch",
                    text=(
                        "Topic 07 followed a request into the route table, and "
                        "topic 08 followed it through the onion around that "
                        "table — now it arrives at the destination. The "
                        "handler's side of the contract is one object: "
                        "Starlette's ``Request``, the parsed window onto the "
                        "raw ASGI scope that middleware and routing have been "
                        "passing inward the whole time. You rarely construct "
                        "one yourself; you DECLARE it — a ``request: "
                        "Request`` parameter — and FastAPI injects the live "
                        "instance for exactly this invocation. The headers "
                        "demo's collector is the smallest honest use in this "
                        "repo: four attribute reads, each a fact the scope "
                        "already carried"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="req-echo-collector",
                    language="py",
                    caption="The Request as parsed view: method, path, query, headers.",
                    source="server/guide/presentation/routers/demo/http.py",
                    snippet=(
                        "def _echo(request: Request, body_message: str | None = None) -> HttpHeadersEchoPayload:\n"
                        "    \"\"\"Collect the request facts once; the pure builder does the rest.\"\"\"\n"
                        "    return build_http_headers_echo(\n"
                        "        method=request.method,\n"
                        "        path=request.url.path,\n"
                        "        query=request.url.query,\n"
                        "        headers=request.headers,\n"
                        "        body_message=body_message,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="req-view-read",
                    text=(
                        "Each of those reads deserves one sentence, because "
                        "together they are the whole object. ``request."
                        "method`` and ``request.url.path`` are the two facts "
                        "routing matched on — still readable here, one layer "
                        "in. ``request.url`` is a parsed URL (scheme, "
                        "netloc, path, query), so ``request.url.query`` is "
                        "the raw query string exactly as it arrived. "
                        "``request.headers`` is a case-insensitive, "
                        "lowercasing mapping of header name to value — "
                        "``headers.get(\"content-type\")`` and ``headers."
                        "get(\"Content-Type\")`` read the same entry. And "
                        "the query has a second view: ``request."
                        "query_params``, a multi-dict that parses the query "
                        "string into pairs. That multi in multi-dict is a "
                        "real contract: a query string may repeat a key — "
                        "``?tag=a&tag=b`` — and ``query_params.get(\"tag\")`` "
                        "returns only the last value while ``query_params."
                        "multi_items()`` returns every pair. This topic's "
                        "first demo reflects the whole view back at you, so "
                        "the difference is something you can send and watch:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="req-inspector-collector",
                    language="py",
                    caption="The inspector's collector: every fact handed off as plain data.",
                    source="server/guide/presentation/routers/demo/reqres.py",
                    snippet=(
                        "def _inspect(request: Request, body_message: str | None) -> RequestInspectorPayload:\n"
                        "    \"\"\"Collect the live Request's facts once; the pure builder does the rest.\"\"\"\n"
                        "    client = request.client\n"
                        "    return build_request_inspector_payload(\n"
                        "        method=request.method,\n"
                        "        path=request.url.path,\n"
                        "        raw_query=request.url.query or None,\n"
                        "        query_pairs=request.query_params.multi_items(),\n"
                        "        headers=request.headers,\n"
                        "        client_host=client.host if client is not None else None,\n"
                        "        client_port=client.port if client is not None else None,\n"
                        "        request_id=current_request_id(),\n"
                        "        body_message=body_message,\n"
                        "    )"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="reqres:inspector",
                    title="The request inspector",
                    description=(
                        "Probe the server with your own request and watch "
                        "its view change: pick a query string (repeat a key "
                        "— ?tag=a&tag=b — and see every value collected, the "
                        "behavior a list[str] handler binds and a plain str "
                        "collapses to the last), add a custom x- header, "
                        "switch to POST with a body and watch content-type "
                        "and content-length appear. The payload reports the "
                        "method, path, raw query, the selected headers, the "
                        "client address the transport reported, and the "
                        "request id the middleware assigned two layers out — "
                        "the response's own x-request-id header carries the "
                        "same value. Everything shown is what the live "
                        "Request object actually saw on YOUR request."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="req-demo-coda",
                    text=(
                        "Two more Request surfaces round out the picture. "
                        "``request.client`` is the transport's peer address "
                        "(host and port) — present on real sockets, and the "
                        "inspector reports it whenever the server provides "
                        "one. And ``request.state`` is a per-request "
                        "scratchpad the request-id middleware already used "
                        "(topic 08 mirrored the id onto it precisely so code "
                        "outside the middleware's lifetime could recover "
                        "it). One discipline keeps all of this honest in "
                        "this repo: the Request is read where the request "
                        "is — a thin collector in the router — and the "
                        "facts travel inward as plain data, so domain "
                        "builders never import starlette at all. The "
                        "builder side of the inspector is that discipline "
                        "in miniature:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="req-builder-query",
                    language="py",
                    caption="Pure collection: repeated keys gather every occurrence, flagged.",
                    source="server/guide/domain/demos/request_inspector.py",
                    snippet=(
                        "    collected: dict[str, list[str]] = {}\n"
                        "    for name, value in query_pairs:\n"
                        "        collected.setdefault(name, []).append(value)\n"
                        "    query_params = [\n"
                        "        QueryParamView(name=name, values=values, is_repeated=len(values) > 1)\n"
                        "        for name, values in collected.items()\n"
                        "    ]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="req-when-to-use",
                    text=(
                        "When do you ask for the Request at all, versus "
                        "letting the signature do the work? The rule this "
                        "repo follows: typed parameters first — a path "
                        "variable, a query parameter, a pydantic body give "
                        "you validated, named, documented inputs, and topic "
                        "06 showed dependencies composing them; the Request "
                        "object is for the facts no signature can express, "
                        "the way-beyond-the-line leftovers — reflecting an "
                        "arbitrary header set, reading the peer address, "
                        "reaching app.state through ``request.app``, or "
                        "streaming a raw body. The body itself is the "
                        "boundary case: ``await request.body()`` gives the "
                        "raw bytes and ``request.stream()`` iterates chunks, "
                        "but reaching for those means opting OUT of the "
                        "validation, documentation, and error envelope the "
                        "typed path gives you — so this repo reads raw "
                        "bodies nowhere, and the next section is why."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="req-scope-read",
                    text=(
                        "One layer down, everything above is a view: the "
                        "object wraps the ASGI scope dict that topic 08 "
                        "traced through the onion, and every attribute is "
                        "a lazy read of it — ``request.method`` is "
                        "``scope[\"method\"]``, ``request.url.path`` parses "
                        "``scope[\"path\"]``, ``request.headers`` decodes "
                        "the raw byte pairs the server put there. The "
                        "request-id middleware exploited exactly that "
                        "duality when it mirrored the id onto ``request."
                        "state``: state is a plain dict under a scope key, "
                        "which is why the error handlers could read it back "
                        "from the scope directly after the friendlier "
                        "object's contextvar had been reset. The lesson "
                        "transfers: when a fact must outlive the Request's "
                        "ergonomics — cross a middleware boundary, survive "
                        "into an exception handler — the scope is the "
                        "durable thing, and the Request is its convenient "
                        "face for the duration of one call."
                    ),
                ),
            ],
        ),
        # ── 2. pydantic bodies + response_model (inline demo) ───────────────
        Section(
            id="pydantic-bodies-and-response-model",
            title="pydantic bodies and response_model",
            lead="The second demo of this topic lives here — the methods playground.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="body-pitch",
                    text=(
                        "A request body is the one input that is not "
                        "visible in the URL, so its contract lives entirely "
                        "in the signature: declare a pydantic model "
                        "parameter and FastAPI parses the JSON body into it "
                        "BEFORE your code runs — the full topic 05 pipeline "
                        "(coercion, validators, 422 on garbage) applied to "
                        "the bytes under the request line. The methods "
                        "playground this section is built around gives that "
                        "contract a resource to live on: an in-memory notes "
                        "collection with the request→response answer for "
                        "each verb deliberately different. The body model "
                        "first — note the Annotated Field constraints, "
                        "because an empty title must fail before the store "
                        "ever sees it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="body-create-model",
                    language="py",
                    caption="The POST/PUT body: constraints declared where the contract is.",
                    source="server/guide/domain/demos/request_methods.py",
                    snippet=(
                        "class NoteCreate(CamelModel):\n"
                        "    \"\"\"The POST/PUT body: the full representation a client sends.\"\"\"\n"
                        "\n"
                        "    title: Annotated[str, Field(min_length=1, max_length=80)]\n"
                        "    body: str = \"\"\n"
                        "    tags: list[str] = []"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="body-in-out",
                    text=(
                        "The interesting asymmetry is that the request model "
                        "and the response model are DIFFERENT models, and "
                        "that is the whole lesson. What comes in is what "
                        "the client is allowed to say; what goes out is "
                        "what the server is willing to show — and the "
                        "stored record is a third shape holding both plus "
                        "bookkeeping. The playground's store keeps a "
                        "``revision`` counter (bumped on every replace) on "
                        "every record; the response model simply does not "
                        "declare it, so it never crosses the wire:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="body-record-public",
                    language="py",
                    caption="Record vs public view: revision stays inside the server.",
                    source="server/guide/domain/demos/request_methods.py",
                    snippet=(
                        "class NoteRecord(CamelModel):\n"
                        "    \"\"\"What the store holds: the public fields plus internal bookkeeping.\"\"\"\n"
                        "\n"
                        "    id: int\n"
                        "    title: str\n"
                        "    body: str\n"
                        "    tags: list[str]\n"
                        "    created_at: str\n"
                        "    revision: int"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="body-public-model",
                    language="py",
                    caption="The response model: five fields, no revision, by omission.",
                    source="server/guide/domain/demos/request_methods.py",
                    snippet=(
                        "class NotePublic(CamelModel):\n"
                        "    \"\"\"The response model: exactly the fields the wire may carry.\n"
                        "\n"
                        "    ``revision`` is deliberately absent — the stored record keeps it, the\n"
                        "    response model filters it, and no client ever sees it.\n"
                        "    \"\"\"\n"
                        "\n"
                        "    id: int\n"
                        "    title: str\n"
                        "    body: str\n"
                        "    tags: list[str]\n"
                        "    created_at: str"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="body-response-model-read",
                    text=(
                        "``response_model=NotePublic`` on the route is what "
                        "activates the filter: FastAPI serializes whatever "
                        "the handler returns THROUGH that model — unknown "
                        "fields dropped, declared fields validated — so the "
                        "router below returns the full ``NoteRecord`` and "
                        "the wire only ever carries ``NotePublic``. This is "
                        "output filtering, distinct from the input "
                        "validation the body model does, and it is the "
                        "honest answer to \"how do I keep internal fields "
                        "off the wire\": not by careful dict-building, but "
                        "by declaring a smaller model and letting the "
                        "framework enforce the boundary. The create route "
                        "also shows the other half of the POST contract — "
                        "the success status is 201, not 200, and the "
                        "Location header names where the new resource "
                        "lives, resolved by reverse routing rather than "
                        "string-pasting:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="body-create-route",
                    language="py",
                    caption="POST done by the book: 201, Location via url_path_for, filtered body.",
                    source="server/guide/presentation/routers/demo/reqres.py",
                    snippet=(
                        "@router.post(\"/notes\", response_model=NotePublic, status_code=201)\n"
                        "def create_note(draft: NoteCreate, response: Response, store: NoteStoreDep) -> NoteRecord:\n"
                        "    \"\"\"Create from the validated body: 201 + Location names the new resource.\"\"\"\n"
                        "    note = store.create(draft)\n"
                        "    response.headers[\"location\"] = router.url_path_for(\"read_note\", note_id=note.id)\n"
                        "    return note"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="reqres:methods",
                    title="The methods playground",
                    description=(
                        "One resource, the whole contract, live: POST a "
                        "note (201 Created, Location shown, body filtered "
                        "through NotePublic); GET the collection and "
                        "inspect a note — notice there is no revision "
                        "field, though the server tracks one on every "
                        "record; PUT for a full replace (200 — the content "
                        "changes wholesale, identity metadata survives); "
                        "DELETE for 204 No Content, then GET the same id "
                        "for the honest 404 envelope. Send an invalid body "
                        "(empty title) and watch FastAPI's own 422 "
                        "validation_failed envelope come back — never a "
                        "half-created note."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="body-coda",
                    text=(
                        "The remaining verbs complete the contract table. "
                        "GET one note and PUT both carry ``{note_id}`` in "
                        "the path — an ``int`` annotation, so a non-numeric "
                        "id is a 422 before the handler runs (topic 07 "
                        "taught the extraction; the annotation is the "
                        "validation). PUT's semantics are FULL replace: "
                        "every content field arrives in the body or the "
                        "request fails validation — there is no partial "
                        "PATCH arithmetic here, which is exactly why topic "
                        "07 distinguished the verbs. DELETE answers 204 "
                        "with no body at all, the status code doing all "
                        "the talking. And the idempotency promises from "
                        "topic 03 are visible one endpoint at a time: PUT "
                        "twice leaves the same state (a second DELETE "
                        "answers 404 — deletion already happened, the "
                        "resource is simply gone), while POST twice "
                        "creates two notes. Try each in the playground, "
                        "then read the next section for what a response "
                        "actually IS below the return statement."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="body-read-route",
                    language="py",
                    caption="The None-to-404 ladder again, with the filter on the way out.",
                    source="server/guide/presentation/routers/demo/reqres.py",
                    snippet=(
                        "@router.get(\"/notes/{note_id}\", response_model=NotePublic)\n"
                        "def read_note(note_id: int, store: NoteStoreDep) -> NoteRecord:\n"
                        "    \"\"\"Serve one note through NotePublic; unknown ids are the 404 envelope.\"\"\"\n"
                        "    note = store.get(note_id)\n"
                        "    if note is None:\n"
                        "        raise AppError(FailureKind.NOT_FOUND, f\"Note {note_id} not found\")\n"
                        "    return note"
                    ),
                ),
            ],
        ),
        # ── 3. Response/JSONResponse + status codes ──────────────────────────
        Section(
            id="response-and-status-codes",
            title="Response, JSONResponse, and status codes",
            blocks=[
                TextBlock(
                    kind="text",
                    id="resp-pitch",
                    text=(
                        "What happens when a handler returns a value? "
                        "FastAPI serializes it through the response model, "
                        "sets 200 (or the declared status), adds the "
                        "content-type, and hands the result to the ASGI "
                        "channel topic 08 watched messages travel on. "
                        "Sometimes you need to own that last step yourself "
                        "— a status code no decorator default covers, "
                        "headers computed at response time, or a body the "
                        "shared pipeline must not touch — and then you "
                        "build a ``Response`` directly. The error taxonomy "
                        "is the repo's real specimen, because every "
                        "failure envelope in every demo you have run so "
                        "far was built by this one function:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="resp-envelope-code",
                    language="py",
                    caption="A JSONResponse built by hand: status, serialized body, headers.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "    request_id = resolve_request_id(request)\n"
                        "    body = ErrorResponse(\n"
                        "        error=ErrorBody(code=kind.value, message=message, request_id=request_id, details=details)\n"
                        "    )\n"
                        "    headers = {\"x-request-id\": request_id}\n"
                        "    if extra_headers:\n"
                        "        headers.update(extra_headers)\n"
                        "    return JSONResponse(\n"
                        "        status_code=status,\n"
                        "        content=body.model_dump(mode=\"json\", by_alias=True, exclude_none=True),\n"
                        "        headers=headers,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="resp-read",
                    text=(
                        "Read the choices, because each is a decision you "
                        "will re-make. The status comes from the taxonomy's "
                        "single kind-to-status mapping — never a magic "
                        "number at the call site. The content is "
                        "``model_dump(mode=\"json\")`` output: "
                        "JSON-compatible types, camelCase by alias, "
                        "optional-absent fields dropped — the same wire "
                        "convention every response model produces, done by "
                        "hand because a raw Response has no response model "
                        "to do it. And headers ride as a plain dict — "
                        "including the x-request-id stamp the envelope "
                        "sets for itself, for the topic 08 reason that "
                        "outermost-bookend responses never re-enter the "
                        "middleware that would otherwise stamp it. "
                        "Returning any Response subclass (JSONResponse, "
                        "PlainTextResponse, the StreamingResponse ahead) "
                        "bypasses response_model serialization entirely — "
                        "what you built is what goes on the wire."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="resp-pipeline-read",
                    text=(
                        "Pin down the ordinary path once, so the bypass is "
                        "a choice and not a surprise. When a handler "
                        "returns a model (or a dict — FastAPI accepts "
                        "both, and models are the house rule because the "
                        "declaration is the contract), serialization "
                        "happens AFTER the function returns: the value is "
                        "validated through the declared response model, "
                        "dropped fields stay dropped, aliases apply, "
                        "None-optional fields vanish under the route's "
                        "``response_model_exclude_none``. The handler "
                        "therefore never serializes itself — no "
                        "model_dump in a return statement, no hand-built "
                        "JSON — which is what keeps the wire convention "
                        "true everywhere: it is enforced at one boundary, "
                        "the same way the envelope and the request-id "
                        "header each got exactly one owner. The cost of "
                        "the bypass is symmetrical: a hand-built Response "
                        "opts out of all of it, so the taxonomy builds "
                        "its own dump carefully and the streaming routes "
                        "encode each line at the source."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="resp-status-teach",
                    text=(
                        "Status codes are the response half of the contract, "
                        "and the playground exercises the ones that matter "
                        "for one resource. The families, with the repo's "
                        "own examples:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="resp-status-list",
                    ordered=False,
                    items=[
                        "200 OK — the generic success; GET list, GET one, "
                        "and PUT's full-replace answer all use it.",
                        "201 Created — POST that minted a resource; the "
                        "playground's create route declares it and points "
                        "at the new note with Location.",
                        "204 No Content — success with deliberately nothing "
                        "to say; DELETE answers it, body empty by "
                        "definition.",
                        "307 Temporary Redirect — routing's trailing-slash "
                        "canonicalization (topic 07); the redirects "
                        "section takes the whole family.",
                        "404 Not Found — the handler-decided absence: "
                        "unknown topic ids, unknown note ids, the envelope "
                        "always shaped the same.",
                        "422 Unprocessable Content — FastAPI's validation "
                        "failure status: invalid bodies, invalid path "
                        "types, the {loc, msg, type} triples in details.",
                    ],
                ),
                CodeBlock(
                    kind="code",
                    id="resp-delete-code",
                    language="py",
                    caption="204 done right: the status declared, the body actually empty.",
                    source="server/guide/presentation/routers/demo/reqres.py",
                    snippet=(
                        "@router.delete(\"/notes/{note_id}\", status_code=204)\n"
                        "def delete_note(note_id: int, store: NoteStoreDep) -> Response:\n"
                        "    \"\"\"Delete the note: 204 No Content, nothing in the body.\"\"\"\n"
                        "    if not store.delete(note_id):\n"
                        "        raise AppError(FailureKind.NOT_FOUND, f\"Note {note_id} not found\")\n"
                        "    return Response(status_code=204)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="resp-status-coda",
                    text=(
                        "Two habits worth copying cold from those two "
                        "routes. Declare the status at the decorator "
                        "(``status_code=201`` / ``status_code=204``) so the "
                        "OpenAPI schema tells the truth and the handler "
                        "cannot forget it — the injected ``response: "
                        "Response`` parameter is then free to carry only "
                        "the dynamic parts, like Location. And when the "
                        "status says no content, send none: a 204 with a "
                        "JSON body is a contract violation some clients "
                        "will turn into a parse error. The failure paths "
                        "need no status arithmetic at all — the handler "
                        "raises, and the taxonomy's single mapping decides "
                        "the number, which is why every 404 you have "
                        "curled in three topics looked identical."
                    ),
                ),
            ],
        ),
        # ── 4. Headers and cookies ───────────────────────────────────────────
        Section(
            id="headers-and-cookies",
            title="Headers and cookies",
            blocks=[
                TextBlock(
                    kind="text",
                    id="hdr-pitch",
                    text=(
                        "Request headers you have already read — the "
                        "inspector reflects a selected set, and the echo "
                        "demo classified the whole zoo in topic 03. The "
                        "response side is the new move: headers you SET. "
                        "You have watched two already without the name for "
                        "it: every response's x-request-id (the pure ASGI "
                        "middleware stamping the header on the response's "
                        "start message as it passes — topic 28 shows that "
                        "wrapper in full) and the playground's Location. The "
                        "mechanisms differ by where they run, and the "
                        "request-id stamp is the cleanest real example of "
                        "the response-side moment:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="hdr-stamp-code",
                    language="py",
                    caption="Stamping the header on the start message: the response-side moment.",
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
                    id="hdr-ways",
                    text=(
                        "So there are three ways a header gets onto a "
                        "response in this repo, one per layer, and choosing "
                        "is about who knows the value:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="hdr-ways-list",
                    ordered=False,
                    items=[
                        "Decorator/parameter — the injected ``response: "
                        "Response`` in a handler: set headers on it and "
                        "return the model; FastAPI merges them (Location "
                        "on the create route).",
                        "Middleware — for every response on the app: "
                        "stamp the header on the http.response.start "
                        "message as it passes through the send channel "
                        "(the x-request-id stamp above).",
                        "Hand-built Response — the JSONResponse envelope "
                        "passing a headers dict, for responses that bypass "
                        "the model pipeline entirely.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="hdr-cookie-pitch",
                    text=(
                        "Cookies are headers with conventions — stated "
                        "honestly: this repo sets none today. A cookie is "
                        "a Set-Cookie response header the SERVER sends and "
                        "the CLIENT stores, then replays on later requests "
                        "as a Cookie request header, scoped by the "
                        "attributes baked into that Set-Cookie string. "
                        "Starlette gives the mechanics a typed surface: "
                        "``response.set_cookie(key, value, max_age=…, "
                        "httponly=True, secure=True, samesite=\"lax\")`` "
                        "composes the header — httponly hides it from "
                        "page JavaScript (document.cookie cannot read it), "
                        "secure restricts it to HTTPS, samesite tames "
                        "cross-site sending (topic 03's CSRF story) — and "
                        "``request.cookies`` is the parsed read view, a "
                        "plain dict of what the client sent back. Reading "
                        "is a one-liner today; WRITING one is the first "
                        "thing topic 23 does, because a login session done "
                        "right is a signed cookie with exactly those "
                        "attributes, and the auth demos will quote real "
                        "set_cookie calls when they exist. Until then the "
                        "inspector remains the honest place to watch the "
                        "round trip begin: its header list is whatever "
                        "your probe actually sent, cookie headers included."
                    ),
                ),
            ],
        ),
        # ── 5. StreamingResponse + SSE ───────────────────────────────────────
        Section(
            id="streaming-and-sse",
            title="StreamingResponse and server-sent events",
            blocks=[
                TextBlock(
                    kind="text",
                    id="stream-pitch",
                    text=(
                        "Everything so far built one JSON document and sent "
                        "it whole. The other shape is a response whose body "
                        "is PRODUCED over time — progress, logs, live "
                        "events — where the client should receive each "
                        "piece as it is ready rather than wait for the "
                        "end. Starlette's ``StreamingResponse`` takes any "
                        "iterator (sync or async) of bytes/str and sends "
                        "each item as it is yielded; pair it with an async "
                        "generator (topic 02) and the event loop "
                        "interleaves production with sending. The runtime "
                        "streaming demo is the repo's real, running "
                        "instance — the whole router:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="stream-router-code",
                    language="py",
                    caption="A StreamingResponse route: generator in, media type declared, no response_model.",
                    source="server/guide/presentation/routers/demo/runtime.py",
                    snippet=(
                        "@router.get(\"/streaming\")\n"
                        "async def read_streaming() -> StreamingResponse:\n"
                        "    \"\"\"Stream the async generator's chunks as NDJSON lines, as produced.\"\"\"\n"
                        "    return StreamingResponse(stream_runtime_chunks(), media_type=NDJSON_MEDIA_TYPE)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="stream-generator-read",
                    text=(
                        "Three details in those four lines are the "
                        "curriculum. ``response_model`` is deliberately "
                        "absent — the body is a SEQUENCE of JSON lines, "
                        "not one document, so there is no single model for "
                        "FastAPI to serialize; each line is typed where it "
                        "is produced and the router just declares the "
                        "media type. That type is ``application/x-ndjson`` "
                        "— newline-delimited JSON, the pragmatic feed "
                        "format where every line is independently "
                        "parseable and a truncated tail loses only its "
                        "last line. And the generator inside is ordinary "
                        "topic 02 material — an async def that yields, "
                        "awaiting simulated I/O between items, each line "
                        "encoded by the model's own serializer:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="stream-generator-code",
                    language="py",
                    caption="The producer: awaited ticks between yields — pace is real.",
                    source="server/guide/domain/demos/runtime_streaming.py",
                    snippet=(
                        "async def stream_runtime_chunks(\n"
                        "    item_count: int = STREAM_ITEMS, tick: float = STREAM_TICK\n"
                        ") -> AsyncIterator[str]:\n"
                        "    \"\"\"The demo's async generator: open line, awaited items, closing line.\"\"\"\n"
                        "    started = time.perf_counter()\n"
                        "    yield _encode(\n"
                        "        StreamChunk(\n"
                        "            seq=0,\n"
                        "            kind=\"open\",\n"
                        "            label=\"runtime-stream\",\n"
                        "            detail=f\"{item_count} items follow, one per awaited tick\",\n"
                        "        )\n"
                        "    )"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="stream-encode-code",
                    language="py",
                    caption="One wire line per chunk: the model serializes itself.",
                    source="server/guide/domain/demos/runtime_streaming.py",
                    snippet=(
                        "def _encode(chunk: StreamChunk) -> str:\n"
                        "    \"\"\"One wire line: camelCase JSON, optional-absent fields omitted.\"\"\"\n"
                        "    return chunk.model_dump_json(by_alias=True, exclude_none=True) + \"\\n\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="stream-sse-read",
                    text=(
                        "Server-sent events are the same machinery with a "
                        "standardized suit on. The ``text/event-stream`` "
                        "media type plus a small line protocol — ``data: "
                        "<payload>`` lines, a blank line per event, "
                        "optional ``event:``/``id:``/``retry:`` fields — "
                        "and the browser's EventSource API does reconnection "
                        "and last-event-id resumption for you. Swap the "
                        "demo's media type and encoder for that framing and "
                        "you have an SSE endpoint: one-directional "
                        "server→client push over plain HTTP, which is why "
                        "it fits feeds, tickers, and progress where "
                        "WebSockets' two-way channel (topic 28) is more "
                        "than needed. The caveats are the ones topic 08 "
                        "put on record: streaming wants the response "
                        "unbuffered — this repo rewrote its request-id "
                        "layer as pure ASGI when the realtime topics "
                        "landed (topic 28), exactly as its recorded "
                        "caveat promised — and proxy "
                        "buffering (nginx's ``X-Accel-Buffering: no``) is "
                        "the classic production gotcha. And a streaming "
                        "handler commits to the response before the body "
                        "exists — there is no turning a half-sent stream "
                        "into a 500, so errors after the first byte become "
                        "error EVENTS, not error statuses."
                    ),
                ),
            ],
        ),
        # ── 6. Content negotiation ───────────────────────────────────────────
        Section(
            id="content-negotiation",
            title="Content negotiation",
            blocks=[
                TextBlock(
                    kind="text",
                    id="nego-pitch",
                    text=(
                        "Topic 03 taught the model: the client advertises "
                        "what it can accept, the server picks a "
                        "representation, and 406 says the overlap was "
                        "empty. This topic's job is the server's side of "
                        "that handshake in FastAPI — and the honest first "
                        "fact is what this API does: nothing, "
                        "deliberately. The content API serves exactly one "
                        "representation (JSON) of every resource, so "
                        "there is nothing to negotiate; the demos you "
                        "have met read Accept only to ECHO it, as "
                        "negotiation-set evidence:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="nego-selection-code",
                    language="py",
                    caption="The echo's negotiation set — read to report, never to branch.",
                    source="server/guide/domain/demos/http_headers.py",
                    snippet=(
                        "BASE_HEADER_SELECTION: Final[tuple[str, ...]] = (\n"
                        "    \"user-agent\",\n"
                        "    \"accept\",\n"
                        "    \"accept-encoding\",\n"
                        "    \"content-type\",\n"
                        ")\n"
                        "\"\"\"Negotiation/identity headers every echo reports when the client sent them.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="nego-mechanics",
                    text=(
                        "The day a second representation appears (topic 27 "
                        "adds Accept-Language, and an API that also speaks "
                        "XML or a versioned media type is the classic "
                        "case), the mechanics stay small and explicit. "
                        "Read ``request.headers.get(\"accept\")``, parse "
                        "the weighted list (``application/json;q=0.9, "
                        "text/html`` — higher q wins, order breaks ties), "
                        "choose, and either serve the chosen type with a "
                        "matching content-type or answer 406. Doing it in "
                        "a dependency (topic 06) makes it a declared, "
                        "testable, reusable decision instead of "
                        "per-handler parsing — and returning a "
                        "hand-built Response with the negotiated media "
                        "type is exactly the section 3 skill. What FastAPI "
                        "does NOT do is automatic negotiation: "
                        "response_model always serializes JSON; there is "
                        "no built-in Accept dispatch. That is a feature "
                        "to read deliberately — most JSON APIs never need "
                        "the machinery, and the ones that do want the "
                        "decision in their own typed code where the 404s "
                        "and 406s flow through the same envelope as "
                        "everything else."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="nego-encoding",
                    text=(
                        "The quieter sibling is Accept-Encoding, and it "
                        "deserves its own sentence: response compression "
                        "is content coding, not content negotiation in "
                        "the representational sense, and it belongs in "
                        "MIDDLEWARE, not handlers — Starlette ships "
                        "GZipMiddleware, topic 08 recorded that this app "
                        "mounts none of the optional layers, and topic "
                        "38's performance work is where a compression "
                        "benchmark decides whether to. The division of "
                        "labor that falls out: representation choice "
                        "(language, media type, version) is application "
                        "policy — dependency or handler; transfer "
                        "encoding (compression, chunking) is transport "
                        "policy — middleware or server. Browsers send "
                        "both headers on every request; your code should "
                        "only ever care about one of them."
                    ),
                ),
            ],
        ),
        # ── 7. Redirects ─────────────────────────────────────────────────────
        Section(
            id="redirects",
            title="Redirects",
            blocks=[
                TextBlock(
                    kind="text",
                    id="redir-pitch",
                    text=(
                        "A redirect is a 3xx response that says: what you "
                        "want is somewhere else — here is the URI, ask "
                        "there. You have already been served one by this "
                        "app: Starlette's redirect_slashes turned "
                        "/api/content/ into a 307 toward the canonical "
                        "path in topic 07's tour. The explorer demo "
                        "replays that exact decision — and its branch is "
                        "the repo's real redirect logic, worth reading "
                        "closely because every redirect decision is this "
                        "shape: detect the near-miss, compute the "
                        "canonical target, answer with method and query "
                        "preserved:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="redir-explorer-code",
                    language="py",
                    caption="The trailing-slash redirect, computed: toggle, re-match, keep the query.",
                    source="server/guide/domain/demos/routing_explorer.py",
                    snippet=(
                        "    toggled = raw_path != \"/\" and raw_path.endswith(\"/\")\n"
                        "    alternate = raw_path.rstrip(\"/\") if toggled else f\"{raw_path}/\"\n"
                        "    if alternate != raw_path and any(\n"
                        "        _compile_template(template).match(alternate) is not None for template in paths\n"
                        "    ):\n"
                        "        target = alternate + (f\"?{raw_query}\" if raw_query else \"\")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="redir-family",
                    text=(
                        "The status you choose IS the contract, because it "
                        "tells the client what to do with method and body "
                        "on the re-issue — and this is where a decade of "
                        "historical damage needs one careful paragraph. "
                        "The old de-facto pair, 301 (permanent) and 302 "
                        "(found), predates clients that needed the "
                        "reassurance: browsers responded to BOTH by "
                        "rewriting POST into GET, losing the body, "
                        "because early implementations did and everyone "
                        "followed. The modern pair repairs it — 307 "
                        "guarantees the method and body survive the trip, "
                        "308 is the permanent version with the same "
                        "guarantee — which is why Starlette's slash fix "
                        "uses 307: a POST to the wrong slash variant must "
                        "re-issue as a POST. The map:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="redir-family-list",
                    ordered=False,
                    items=[
                        "301 Moved Permanently — permanent rewrite; caches "
                        "remember it; legacy clients may convert POST to "
                        "GET.",
                        "302 Found — temporary, legacy semantics; assume "
                        "nothing about the method surviving.",
                        "307 Temporary Redirect — temporary, method and "
                        "body guaranteed intact (this repo's only 3xx).",
                        "308 Permanent Redirect — permanent with the same "
                        "guarantee; the honest successor to 301 for "
                        "relocations.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="redir-send",
                    text=(
                        "Sending one yourself is the section 3 toolkit "
                        "again: ``RedirectResponse(url, "
                        "status_code=307)`` is a Response subclass — "
                        "return it from a handler and the Location header "
                        "is set for you. When an API genuinely wants one: "
                        "canonical URLs (the slash case), a moved "
                        "resource during a URL migration, or flows like "
                        "OAuth where the SPEC mandates redirects (topic "
                        "23's authorization-code dance is redirects all "
                        "the way down). When it does not: a JSON resource "
                        "API returns the new location as DATA — 201's "
                        "Location header on the playground's create route "
                        "is the difference; a client following links in "
                        "band needs no 3xx at all. The rule of thumb this "
                        "repo follows: redirects for BROWSERS and "
                        "protocol flows, links-in-the-representation for "
                        "APIs, and never a redirect where a 404's honesty "
                        "would serve the client better."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="redir-location-note",
                    text=(
                        "That Location-vs-redirect distinction deserves "
                        "its own caution, because the two travel under "
                        "the same header name. 201's Location is "
                        "INFORMATION — where the created thing lives, for "
                        "the client to remember or follow deliberately; "
                        "no compliant client re-issues anything "
                        "automatically. A 3xx's Location is an "
                        "INSTRUCTION — the client (or browser, or "
                        "redirect-following HTTP library) is expected to "
                        "ask again at the new address, immediately and "
                        "usually invisibly. Sending a 3xx where you meant "
                        "\"here is the address\" silently double-fires "
                        "non-idempotent requests when the follower is "
                        "automatic; sending 201-plus-Location where a "
                        "browser needed the instruction strands it. The "
                        "playground makes the information flavor "
                        "inspectable — watch the create response's "
                        "Location, then note nothing followed it until "
                        "you asked."
                    ),
                ),
            ],
        ),
        # ── 8. Terminal companion ────────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="The request→response contract, read straight off the wire.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-pitch",
                    text=(
                        "With the stack up (server on :8000), this tour "
                        "drives both demos from the shell. -i shows "
                        "status lines and headers — the response half of "
                        "the contract — and python3 -m json.tool keeps "
                        "the tour dependency-free:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-inspector",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the inspector: repeated keys collect, custom headers reflect\n"
                        "curl -s -i 'localhost:8000/api/demo/reqres/inspector?tag=a&tag=b&zoom=2' -H 'x-probe: hello' | head -40"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-inspector-post",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the POST variant: content-type and content-length appear\n"
                        "curl -s -X POST localhost:8000/api/demo/reqres/inspector -H 'content-type: application/json' -d '{\"message\":\"hi\"}' | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-create",
                    language="bash",
                    source=None,
                    snippet=(
                        "# POST: 201 + Location + the filtered body (no revision anywhere)\n"
                        "curl -s -i -X POST localhost:8000/api/demo/reqres/notes -H 'content-type: application/json' -d '{\"title\":\"from the tour\",\"body\":\"curl made this\",\"tags\":[\"terminal\"]}'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-put-delete",
                    language="bash",
                    source=None,
                    snippet=(
                        "# PUT full-replace: 200, content replaced — then DELETE: 204, no body\n"
                        "curl -s -i -X PUT localhost:8000/api/demo/reqres/notes/1 -H 'content-type: application/json' -d '{\"title\":\"replaced wholesale\"}'\n"
                        "curl -s -i -X DELETE localhost:8000/api/demo/reqres/notes/2"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-422",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the 422 path: an empty title fails validation before the store\n"
                        "curl -s -i -X POST localhost:8000/api/demo/reqres/notes -H 'content-type: application/json' -d '{\"title\":\"\"}'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-stream",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the streaming shape: NDJSON lines arriving as produced\n"
                        "curl -s -N localhost:8000/api/demo/runtime/streaming"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Every line of that tour was one of this topic's "
                        "contracts: a reflected request, a 201 with its "
                        "Location, a replace and a silent 204, a 422 "
                        "envelope with its {loc, msg, type} triples, and "
                        "a body that arrived as a stream. The next topic "
                        "zooms into the 422 — validation as a first-class "
                        "subject: the three layers that guard a boundary, "
                        "the Field and Annotated vocabulary the playground "
                        "previewed, and how much checking belongs at the "
                        "edge versus inside the domain."
                    ),
                ),
            ],
        ),
    ],
)
