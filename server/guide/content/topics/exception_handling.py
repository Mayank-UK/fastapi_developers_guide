"""Topic 30 — Exception handling (the platform group opens).

The codebase has carried ONE error story since Phase 1: typed exceptions,
four exception handlers, eight failure kinds, a single envelope with a
request id on every failure. This topic finally TEACHES that machinery in
place: values vs raises (Result in the domain, AppError raised at the
edge), the taxonomy and its one status table, the handlers that map
everything onto the envelope, how the family envelope relates to RFC 9457
problem details, the 404 as the canonical walkthrough, failure injection
on demand (the scenario store plus the probe that finally reads it — the
topic's demo INLINE), what each failure writes into the log, and the nets
that catch what the process itself loses. The demo fires six of the eight
kinds against real endpoints from earlier topics; the two whose triggers
need conditions the running stack does not have say so in plain words.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="exception-handling",
    title="Exception handling",
    subtitle=(
        "Failures as values in the domain and raises at the edge, one "
        "taxonomy of eight kinds behind one envelope, the four exception "
        "handlers, RFC 9457 and how the family envelope maps onto it, the "
        "404 walkthrough, failure injection on demand, what each failure "
        "logs, and the nets beyond the process — with an explorer that "
        "fires the real kinds against real endpoints."
    ),
    group="platform",
    order=30,
    sections=[
        # ── 1. Values vs raises ───────────────────────────────────────────
        Section(
            id="values-vs-raises",
            title="Values vs raises",
            blocks=[
                TextBlock(
                    kind="text",
                    id="values-vs-raises-pitch",
                    text=(
                        "Every failure design picks one of two "
                        "representations, and this guide uses BOTH, each "
                        "where it is strong. A failure as a VALUE — a "
                        "returned ``Err`` the caller must handle — makes "
                        "the possibility visible in the type signature, "
                        "survives refactors, and forces every caller to "
                        "decide, right there, what happens next. A failure "
                        "as a RAISE unwinds the stack for you: it crosses "
                        "layers you do not want to thread error plumbing "
                        "through and lands wherever the catch sits. The "
                        "guide's rule follows from that asymmetry: inside "
                        "the domain a failure is a value (use cases "
                        "return it, nothing throws across layers), and at "
                        "the presentation edge the carried failure becomes "
                        "a raise — because from there ONE exception-handler "
                        "pipeline owns the rest of the journey."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="values-result-quote",
                    language="py",
                    caption="Result[T]: the domain's failure-as-value contract, in one type.",
                    source="server/guide/core/result.py",
                    snippet=(
                        "Use cases return ``Ok(value)`` or ``Err(AppError(...))`` so control flow stays\n"
                        "explicit and the presentation edge decides how a failure maps onto HTTP\n"
                        "(the domain never throws across layers). The variant types are frozen\n"
                        "dataclasses; accessing the wrong payload (``.value`` on ``Err``, ``.failure``\n"
                        "on ``Ok``) raises ``UnwrapError`` — a programming error, loudly surfaced.\n"
                        "# …\n"
                        "type Result[T] = Ok[T] | Err"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="values-err-payload-pitch",
                    text=(
                        "Notice what ``Err`` carries: not a string, not a "
                        "status code — the taxonomy's own ``AppError``, the "
                        "same object the exception handlers will render "
                        "later. That choice is what makes the handoff at "
                        "the edge a one-liner: the value and the raise are "
                        "the same thing, so nothing translates. The use "
                        "cases keep the discipline honest — existence is a "
                        "domain answer, so a missing post is "
                        "``Err(not_found)`` returned to the router, never a "
                        "404 formatted deep in the domain:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="values-usecase-quote",
                    language="py",
                    caption="GetPostUseCase: existence is this layer's answer, as a value.",
                    source="server/guide/domain/posts/use_cases.py",
                    snippet=(
                        "    def execute(self, post_id: str) -> Result[Post]:\n"
                        '        """Ok(post), or Err(not_found) carrying the client-safe message."""\n'
                        "        post = self._posts.get(post_id)\n"
                        "        if post is None:\n"
                        "            return Err(AppError(FailureKind.NOT_FOUND, f\"Post {post_id!r} not found\"))\n"
                        "        return Ok(post)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="values-edge-pitch",
                    text=(
                        "The edge, then, is where the representation flips. "
                        "A router that received a ``Result`` either holds a "
                        "value it can shape into a response, or holds the "
                        "``AppError`` it re-raises so the shared handlers "
                        "render it — the same two lines in every endpoint, "
                        "a pattern so fixed the posts router repeats it "
                        "verbatim four times. No router formats an error "
                        "body, picks a status, or writes a log line for "
                        "failures; those decisions already live downstream "
                        "of the raise:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="values-router-quote",
                    language="py",
                    caption="The edge flips the representation: Err's payload is re-raised, once.",
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
                    id="values-boundary-pitch",
                    text=(
                        "Why not Result everywhere, then? Because past the "
                        "router the call stack stops being yours: an "
                        "exception raised inside a dependency unwinds "
                        "through FastAPI's dependency machinery and the "
                        "middleware stack and STILL reaches a handler "
                        "registered for it, while a returned value would "
                        "just evaporate — there is nobody left to receive "
                        "it. The same asymmetry shows up in background "
                        "work (topic 29's worker) and anything running "
                        "outside a request: an exception is the only "
                        "channel that crosses a boundary you do not "
                        "control. The rule of thumb this guide practices: "
                        "a failure you EXPECT and handle in the very next "
                        "frame is a value; a failure that must travel to "
                        "a boundary you do not own is a raise — and the "
                        "taxonomy's AppError is the one raise worth "
                        "making, because the boundary at the end of the "
                        "journey already knows how to render it."
                    ),
                ),
            ],
        ),
        # ── 2. One taxonomy, eight kinds, one envelope ────────────────────
        Section(
            id="one-taxonomy-eight-kinds",
            title="One taxonomy, eight kinds, one envelope",
            blocks=[
                TextBlock(
                    kind="text",
                    id="taxonomy-pitch",
                    text=(
                        "Ad-hoc error handling rots exactly the way ad-hoc "
                        "routing does: every endpoint invents its own "
                        "codes, clients write a different switch per call, "
                        "and nobody can say what the API answers on a bad "
                        "day. The cure is the same as topic 11's — one "
                        "place owns the vocabulary. ``guide/core/errors.py`` "
                        "is that place: eight failure kinds, one kind-to-"
                        "status table, one error envelope, and nothing "
                        "outside it invents a status code or an error code "
                        "anywhere in the app. Eight is deliberate — small "
                        "enough to hold in your head, wide enough that a "
                        "client's generic handler has something meaningful "
                        "to switch on:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="taxonomy-enum-quote",
                    language="py",
                    caption="The whole vocabulary: eight kinds, one status table, zero exceptions.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "class FailureKind(StrEnum):\n"
                        '    """The eight failure buckets every error in the app maps onto."""\n'
                        "\n"
                        '    VALIDATION_FAILED = "validation_failed"\n'
                        '    UNAUTHORIZED = "unauthorized"\n'
                        '    FORBIDDEN = "forbidden"\n'
                        '    NOT_FOUND = "not_found"\n'
                        '    CONFLICT = "conflict"\n'
                        '    RATE_LIMITED = "rate_limited"\n'
                        '    SERVICE_UNAVAILABLE = "service_unavailable"\n'
                        '    INTERNAL = "internal"\n'
                        "\n"
                        "\n"
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
                    id="taxonomy-kinds-framing",
                    text=(
                        "Each kind earns its slot by meaning something "
                        "different to a CLIENT — a different remedy, a "
                        "different retry decision, a different thing to "
                        "show a user. The eight, with the client-side "
                        "reading of each:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="taxonomy-kinds-list",
                    ordered=False,
                    items=[
                        "validation_failed (422) — the request's shape is "
                        "wrong: a body, path, or query pydantic refused "
                        "before any handler ran; fix the request, do not "
                        "retry it unchanged.",
                        "unauthorized (401) — identity failed: no "
                        "credential, an expired token, a revoked key; "
                        "obtain credentials and try again.",
                        "forbidden (403) — identity holds, authority does "
                        "not: no role grants the action or the object is "
                        "someone else's; the deny reason rides details.",
                        "not_found (404) — a well-formed reference that "
                        "names nothing: a missing post, an unknown topic "
                        "id; also the bucket unnamed 4xx statuses borrow.",
                        "conflict (409) — valid request, moved world: a "
                        "duplicate id, a version that no longer matches; "
                        "re-read and decide.",
                        "rate_limited (429) — too much, too fast: the "
                        "budget is dry and Retry-After says when to come "
                        "back.",
                        "service_unavailable (503) — this path needs a "
                        "downstream that is not answering; the rest of the "
                        "app is still up, retry later.",
                        "internal (500) — a bug: nothing raised it on "
                        "purpose; the envelope is generic because "
                        "internals must not leak, and the log holds the "
                        "traceback.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="taxonomy-apperror-pitch",
                    text=(
                        "Layers speak this vocabulary by raising "
                        "``AppError`` — a typed exception carrying the "
                        "kind, a client-safe message, and two optional "
                        "channels. ``details`` is structured context for "
                        "programs (which fields failed validation, why a "
                        "verdict denied); ``headers`` exists because some "
                        "statuses semantically own a header — the 429 owns "
                        "``Retry-After`` — and the taxonomy is the one "
                        "place it can be attached so the handler renders "
                        "it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="taxonomy-apperror-quote",
                    language="py",
                    caption="AppError: kind + message + optional details/headers — the raise sites' whole API.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "class AppError(Exception):\n"
                        "    \"\"\"Typed application error: kind + message + optional details/headers.\n"
                        "# …\n"
                        "    def __init__(\n"
                        "        self,\n"
                        "        kind: FailureKind,\n"
                        "        message: str,\n"
                        "        details: dict[str, Any] | None = None,\n"
                        "        headers: dict[str, str] | None = None,\n"
                        "    ) -> None:\n"
                        "        self.kind = kind\n"
                        "        self.message = message\n"
                        "        self.details = details\n"
                        "        self.headers = headers\n"
                        "        super().__init__(message)\n"
                        "\n"
                        "    def __str__(self) -> str:\n"
                        '        return f"[{self.kind.value}] {self.message}"'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="taxonomy-envelope-pitch",
                    text=(
                        "And whatever raised it, wherever, the CLIENT sees "
                        "one shape: the envelope — an ``error`` object "
                        "with the machine code, the human message, and the "
                        "request id, plus optional details omitted from "
                        "the wire when absent. Topic 11 introduced this "
                        "shape as the API-design contract; here is the "
                        "model that produces it, wire keys camelCase "
                        "through the shared ``CamelModel`` base every "
                        "crossing-boundary model uses:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="taxonomy-envelope-quote",
                    language="py",
                    caption="The envelope's two models — the only error body the app can emit.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "class ErrorBody(CamelModel):\n"
                        '    """The ``error`` object of the envelope; wire keys are camelCase."""\n'
                        "\n"
                        "    code: str\n"
                        '    """Machine-readable failure kind (e.g. ``not_found``)."""\n'
                        "\n"
                        "    message: str\n"
                        '    """Human-readable, client-safe message."""\n'
                        "\n"
                        "    request_id: str\n"
                        '    """The request id from the request-context middleware."""\n'
                        "\n"
                        "    details: dict[str, Any] | list[dict[str, Any]] | None = None\n"
                        '    """Optional structured context; omitted from the wire when absent."""\n'
                        "\n"
                        "\n"
                        "class ErrorResponse(CamelModel):\n"
                        '    """The whole error envelope: ``{"error": {...}}``."""\n'
                        "\n"
                        "    error: ErrorBody"
                    ),
                ),
            ],
        ),
        # ── 3. Exception handlers ─────────────────────────────────────────
        Section(
            id="exception-handlers",
            title="Exception handlers",
            blocks=[
                TextBlock(
                    kind="text",
                    id="handlers-pitch",
                    text=(
                        "FastAPI (through Starlette) lets an app register a "
                        "handler per exception type; when that type "
                        "unwinds past a handler, the framework calls it "
                        "with the request and the exception instead of "
                        "letting the error become a bare 500. This app "
                        "registers exactly FOUR handlers, once per app in "
                        "``create_app`` — the taxonomy's own exception, "
                        "FastAPI's validation failure, Starlette's "
                        "HTTPException, and bare Exception as the last "
                        "resort. Between them, every raise in the codebase "
                        "reaches a handler that answers the family "
                        "envelope; there is no path from an exception to "
                        "the wire that skips this module:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="handlers-register-quote",
                    language="py",
                    caption="Four registrations, once per app — the complete catch surface.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "def register_exception_handlers(app: FastAPI) -> None:\n"
                        '    """Wire the taxonomy\'s handlers onto one app (called once per app)."""\n'
                        "    # Handlers narrow `exc` below the Exception the base signature declares\n"
                        "    # (each is registered for exactly that narrower class) — hence the ignores.\n"
                        "    add = app.add_exception_handler\n"
                        "    add(AppError, handle_app_error)  # type: ignore[arg-type]\n"
                        "    add(RequestValidationError, handle_request_validation_error)  # type: ignore[arg-type]\n"
                        "    add(HTTPException, handle_http_exception)  # type: ignore[arg-type]\n"
                        "    add(Exception, handle_unexpected_error)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="handlers-four-framing",
                    text=(
                        "Each handler owns one source of failure and its "
                        "own normalization decision — what survives from "
                        "the exception into the envelope:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="handlers-four-list",
                    ordered=True,
                    items=[
                        "AppError → handle_app_error — the taxonomy's own: "
                        "the mapped status, the raiser's message and "
                        "details verbatim, and AppError.headers riding "
                        "onto the response.",
                        "RequestValidationError → "
                        "handle_request_validation_error — FastAPI's "
                        "body/path/query checks: a 422 whose details are "
                        "the normalized {loc, msg, type} triples, pydantic's "
                        "noisy url/ctx context stripped.",
                        "HTTPException → handle_http_exception — "
                        "Starlette's own raises (a routeless 404, a 405): "
                        "the truthful status kept, the closest kind bucket "
                        "chosen, exc.headers preserved.",
                        "Exception → handle_unexpected_error — the last "
                        "resort for any unhandled raise: 500, a generic "
                        "message that leaks nothing, the traceback logged "
                        "with the request id.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="handlers-validation-pitch",
                    text=(
                        "The validation handler shows the normalization "
                        "idea at its most useful. Pydantic's raw errors "
                        "are rich — urls to docs, context dictionaries "
                        "with the constraint values — and none of it "
                        "belongs on the wire. The handler keeps exactly "
                        "the three fields a client can act on, logs the "
                        "failure at INFO (a bad body is the caller's "
                        "mistake, not the server's health), and renders "
                        "the envelope:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="handlers-validation-quote",
                    language="py",
                    caption="Normalization in action: raw pydantic errors in, {loc, msg, type} triples out.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "    details = [\n"
                        "        {\"loc\": list(err[\"loc\"]), \"msg\": err[\"msg\"], \"type\": err[\"type\"]} for err in exc.errors()\n"
                        "    ]\n"
                        "    logger.info(\n"
                        '        "request_validation_failed",\n'
                        "        request_id=resolve_request_id(request),\n"
                        "        detail_count=len(details),\n"
                        "    )\n"
                        "    return _build_error_response(\n"
                        "        request,\n"
                        "        422,\n"
                        "        FailureKind.VALIDATION_FAILED,\n"
                        '        "Request validation failed.",\n'
                        "        details,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="handlers-bucket-pitch",
                    text=(
                        "The Starlette handler carries the subtlest rule: "
                        "statuses exist that the taxonomy does not name — "
                        "405 method not allowed is the one this API "
                        "actually produces, because the posts resource "
                        "deliberately has no DELETE. The response must "
                        "keep the TRUTHFUL status (a 405 is not a 404) "
                        "while the code field still comes from the fixed "
                        "vocabulary, so unnamed 4xx statuses take the "
                        "closest client-error bucket and unnamed 5xx "
                        "statuses take internal. A client switching on "
                        "code sees a kind it knows; a client switching on "
                        "status sees the truth; neither sees a ninth kind "
                        "invent itself at runtime:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="handlers-bucket-quote",
                    language="py",
                    caption="Unnamed statuses: truthful status kept, closest kind bucket taken.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "def kind_for_http_status(status: int) -> FailureKind:\n"
                        '    """Map an HTTP status to the closest failure kind.\n'
                        "\n"
                        "    Statuses the taxonomy names map exactly; unnamed 4xx statuses take the\n"
                        "    ``not_found`` bucket (closest client-error kind — e.g. 405 method not\n"
                        "    allowed) and unnamed 5xx statuses take ``internal``. The response keeps\n"
                        "    the truthful status either way.\n"
                        '    """\n'
                        "    exact = _KIND_BY_HTTP_STATUS.get(status)\n"
                        "    if exact is not None:\n"
                        "        return exact\n"
                        "    return FailureKind.NOT_FOUND if status < 500 else FailureKind.INTERNAL"
                    ),
                ),
            ],
        ),
        # ── 4. RFC 9457 problems ──────────────────────────────────────────
        Section(
            id="rfc-9457-problems",
            title="RFC 9457 problems",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rfc-recap",
                    text=(
                        "Topic 11 stated the design position; this section "
                        "goes one layer down, because you will meet "
                        "problem details in the wild and should know "
                        "exactly what you are looking at. RFC 9457 "
                        "(\"Problem Details for HTTP APIs\", the revision "
                        "of 7807) standardizes error bodies: a ``type`` "
                        "URI identifying the problem CLASS, a ``title``, "
                        "the ``status``, a ``detail`` for this occurrence, "
                        "an ``instance`` pointing at this specific "
                        "occurrence — served as "
                        "``application/problem+json``, with extension "
                        "members allowed beside the standard five. Its "
                        "core insight is the same one this guide's "
                        "taxonomy encodes: an error's identity should be "
                        "machine-stable while its explanation stays human."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rfc-mapping-pitch",
                    text=(
                        "The family envelope maps onto that vocabulary "
                        "field for field — ``code`` is ``type`` with "
                        "shorter spelling (a fixed taxonomy instead of "
                        "URIs), ``message`` is ``title`` plus ``detail`` "
                        "collapsed into one field, ``requestId`` is "
                        "``instance`` with a correlation key instead of a "
                        "URI, and ``details`` is exactly the extension-"
                        "member channel the RFC invites. The one visible "
                        "divergence is the media type: this API serves "
                        "``application/json`` everywhere, problem+json "
                        "nowhere. The divergence is deliberate and worth "
                        "naming — a single media type for success AND "
                        "failure means one deserializer client-side, and "
                        "this guide's ``requestId`` does the correlation "
                        "work ``instance`` was designed for, better, "
                        "because it is also the key the SERVER logs."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rfc-type-discipline",
                    text=(
                        "The field problem+json gets wrong most often in "
                        "practice is ``type``. It is supposed to be a "
                        "STABLE class identifier — a URI you control, "
                        "resolving (ideally) to human documentation, that "
                        "changes only when the problem's meaning changes. "
                        "The failure modes are catalog: pointing ``type`` "
                        "at your documentation's homepage (useless to a "
                        "machine), encoding per-instance facts into it "
                        "(that is what ``detail`` and extension members "
                        "are for), or letting it drift per release so "
                        "every client switch breaks quarterly. This "
                        "guide's taxonomy dodges the whole class of bugs "
                        "by making the equivalent decision ONCE, in an "
                        "enum, with tests pinning the vocabulary — eight "
                        "kinds is eight kinds in every response, in the "
                        "logs, and in the client's failure mapping, "
                        "because they all read the same table."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rfc-choosing",
                    text=(
                        "When would you serve problem+json verbatim "
                        "instead? When your clients are not yours: a "
                        "public API consumed by strangers benefits from "
                        "the standard's tooling — generic problem viewers, "
                        "gateway middleware that understands the format, "
                        "SDK generators that turn ``type`` URIs into "
                        "enums. Inside one product family (one client, "
                        "one server, one log pipeline) the shorter "
                        "envelope with a request id wins on ergonomics. "
                        "The decision is reversible in ONE place "
                        "precisely because the taxonomy is the single "
                        "source — swap the renderer in "
                        "``_build_error_response`` and every endpoint "
                        "speaks problem+json tomorrow; that locality is "
                        "the entire argument for having a taxonomy at all."
                    ),
                ),
            ],
        ),
        # ── 5. The 404 problem ────────────────────────────────────────────
        Section(
            id="the-404-problem",
            title="The 404 problem",
            blocks=[
                TextBlock(
                    kind="text",
                    id="notfound-pitch",
                    text=(
                        "The 404 is the right place to watch the whole "
                        "pipeline work, because this app can produce the "
                        "same status from two completely different "
                        "sources. An APPLICATION 404 is a domain answer: "
                        "the content router looks up an unknown topic id "
                        "and raises ``AppError(not_found)`` with a "
                        "specific, client-safe message. A FRAMEWORK 404 "
                        "comes from Starlette itself when no route "
                        "matches at all — it surfaces as an "
                        "HTTPException, and the closest-bucket rule from "
                        "the last section is what renders it. Two sources, "
                        "one envelope — which is the point:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="notfound-content-quote",
                    language="py",
                    caption="The application 404: a domain answer raised from a thin router.",
                    source="server/guide/presentation/routers/content.py",
                    snippet=(
                        '@router.get("/{topic_id}", response_model=ContentDetail, response_model_exclude_none=True)\n'
                        "def read_topic(\n"
                        "    topic_id: str,\n"
                        "    registry: Annotated[ContentRegistry, Depends(get_content_registry)],\n"
                        ") -> ContentDetail:\n"
                        '    """Serve one topic\'s full payload + version; unknown ids are the 404 envelope."""\n'
                        "    topic = registry.topic_by_id(topic_id)\n"
                        "    if topic is None:\n"
                        "        raise AppError(FailureKind.NOT_FOUND, f\"Topic '{topic_id}' not found\")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="notfound-builder-pitch",
                    text=(
                        "Whatever the source, one private function builds "
                        "every error response in the app, and it is worth "
                        "reading closely because two of its lines carry "
                        "policy. The ``x-request-id`` header is stamped "
                        "HERE, not only in the request-id middleware, "
                        "because the last-resort handler's response never "
                        "passes back through the middleware stack — "
                        "without this line the 500s would be the only "
                        "responses on the wire with no id to grep. And "
                        "``exclude_none=True`` keeps the envelope's shape "
                        "stable: a failure without details serves a body "
                        "with no ``details`` key, never a ``null`` one — "
                        "the client DTO treats null as invalid, so the "
                        "omission is a contract, not a style:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="notfound-builder-quote",
                    language="py",
                    caption="One builder for every error response: envelope out, request id on the header.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "    request_id = resolve_request_id(request)\n"
                        "    body = ErrorResponse(\n"
                        "        error=ErrorBody(code=kind.value, message=message, request_id=request_id, details=details)\n"
                        "    )\n"
                        '    headers = {"x-request-id": request_id}\n'
                        "    if extra_headers:\n"
                        "        headers.update(extra_headers)\n"
                        "    return JSONResponse(\n"
                        "        status_code=status,\n"
                        '        content=body.model_dump(mode="json", by_alias=True, exclude_none=True),\n'
                        "        headers=headers,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="notfound-walkthrough",
                    text=(
                        "Walk it end to end with curl against the running "
                        "stack: GET /api/content/exception-handling answers "
                        "200 with this topic's sections; GET "
                        "/api/content/nope answers 404 with "
                        "``{\"error\": {code: not_found, message: Topic "
                        "'nope' not found, requestId: …}}`` and the same "
                        "id on the ``x-request-id`` header; DELETE "
                        "/api/posts/anything answers 405 — a truthful "
                        "status wearing the not_found code, the bucket "
                        "rule on display. The client's job is now uniform: "
                        "match on ``code`` for control flow, show "
                        "``message`` to a human, keep ``requestId`` for "
                        "the support ticket. The terminal companion runs "
                        "all three at the end of this topic."
                    ),
                ),
            ],
        ),
        # ── 6. Failure injection ──────────────────────────────────────────
        Section(
            id="failure-injection",
            title="Failure injection",
            lead="This section carries the topic's demo — the errors explorer.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="injection-pitch",
                    text=(
                        "You cannot teach, test, or trust a failure "
                        "pipeline that only fires by accident. The guide "
                        "has carried the answer since Phase 1 — the "
                        "scenario store, a runtime toggle every demo "
                        "reads: a data mode (fake in-memory or live "
                        "stores) and a failure injection (none, error, "
                        "latency), partial-updatable over PATCH "
                        "/api/demo/scenario with pydantic defending the "
                        "enum invariant on every merge. Until this topic "
                        "the injection modes had no live reader — the "
                        "store held a promise nobody called. The probe "
                        "below is the reader, and the demo wires the "
                        "whole story together:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="injection-scenario-quote",
                    language="py",
                    caption="The scenario store's wire state: two toggles, enum-defended on every update.",
                    source="server/guide/core/scenario.py",
                    snippet=(
                        "class ScenarioState(CamelModel):\n"
                        '    """Immutable snapshot of the demo scenario; wire is camelCase."""\n'
                        "\n"
                        "    data_mode: DataMode = DEFAULT_DATA_MODE\n"
                        "    inject_failure: FailureInjection = DEFAULT_FAILURE_INJECTION\n"
                        "\n"
                        "\n"
                        "class ScenarioPatch(CamelModel):\n"
                        '    """Partial update body for PATCH /api/demo/scenario.\n'
                        "\n"
                        '    Missing keys mean "unchanged" (never None-as-value) — the store merges\n'
                        "    with ``model_dump(exclude_unset=True)``.\n"
                        '    """\n'
                        "\n"
                        "    data_mode: DataMode | None = None\n"
                        "    inject_failure: FailureInjection | None = None"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="injection-probe-pitch",
                    text=(
                        "The probe endpoint is deliberately the most "
                        "dangerous-looking code in the guide: a raise of "
                        "a bare ``RuntimeError`` with no try/except "
                        "anywhere near it. That is the lesson — with "
                        "``injectFailure=error`` the raise travels the "
                        "full unhandled path: no handler matches it below "
                        "Exception, Starlette routes it to the outermost "
                        "ServerErrorMiddleware, the last-resort handler "
                        "logs the traceback with the request id (which "
                        "reaches it through the scope mirror, the "
                        "contextvar having been reset during unwinding), "
                        "and the client receives the generic 500 envelope "
                        "— no exception class, no message from the raise, "
                        "no stack trace on the wire. The latency mode "
                        "sleeps instead, because latency is a failure "
                        "mode too — one the stopwatch catches rather than "
                        "the taxonomy:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="injection-probe-quote",
                    language="py",
                    caption="The probe: the scenario's first live failure reader — no try/except by design.",
                    source="server/guide/presentation/routers/demo/errors.py",
                    snippet=(
                        "@router.get(PROBE_ROUTE, response_model=ProbeRow)\n"
                        "async def probe_scenario_injection(store: ScenarioStoreDep) -> ProbeRow:\n"
                        '    """Answer per the scenario\'s failure injection — no try/except by design.\n'
                        "\n"
                        "    ``injectFailure=error`` raises an unhandled RuntimeError: the last-resort\n"
                        "    handler logs the traceback (with the request id) and answers the generic\n"
                        "    500 envelope, proving internals never leak while the log sees everything.\n"
                        "    ``latency`` sleeps first; ``none`` answers immediately.\n"
                        '    """\n'
                        "    state = store.get()\n"
                        '    if state.inject_failure == "error":\n'
                        "        raise RuntimeError(\n"
                        '            "scenario-injected failure (injectFailure=error) — the outermost "\n'
                        '            "handler turns this into the generic 500 envelope"\n'
                        "        )\n"
                        '    if state.inject_failure == "latency":\n'
                        "        await asyncio.sleep(PROBE_LATENCY_SECONDS)\n"
                        "    return build_probe_row(state)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="injection-demo-pitch",
                    text=(
                        "Try it: the explorer below serves the eight kinds "
                        "from the taxonomy's own tables — status and "
                        "default message come straight from "
                        "guide/core/errors.py, so the panel cannot drift. "
                        "Six kinds carry a FIRE button that runs the real "
                        "trigger against real endpoints from earlier "
                        "topics: the 422 from a body the scenario model "
                        "refuses, the 401/403 pair from topic 24's "
                        "guarded edit (the 403 after minting a real "
                        "token), the 404 from the posts resource, the 429 "
                        "from topic 25's burner after its budget drains, "
                        "and the 500 from the inject-probe-reset round "
                        "trip this section built. Two kinds — conflict "
                        "and service_unavailable — show a recipe instead "
                        "of a button, and say why in plain words: their "
                        "raise sites are real (the arq duplicate guard, "
                        "the optional-store degradation guards) but their "
                        "live triggers need a condition the running stack "
                        "honestly does not have, and the panel does not "
                        "fake what it did not produce. Every fired round "
                        "shows the envelope AND the ``x-request-id`` "
                        "header beside it, with a match badge proving "
                        "they agree."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="errors:explorer",
                    title="The errors explorer",
                    description=(
                        "GET /api/demo/errors serves the panel: the eight "
                        "failure kinds with status, default message, real "
                        "raise site, and the log event each lands as — "
                        "derived from the taxonomy's own tables. Six "
                        "kinds fire LIVE against existing endpoints "
                        "(validation 422 via a rejected scenario patch, "
                        "unauthorized 401 and forbidden 403 via the "
                        "authz-guarded edit with a really minted token, "
                        "not_found 404 via the posts resource, "
                        "rate_limited 429 via the security burner's real "
                        "budget, internal 500 via the scenario inject-"
                        "probe-reset round trip); conflict and "
                        "service_unavailable present their recipes "
                        "honestly (arq's duplicate refusal never fires by "
                        "design; degradation needs an optional store "
                        "down). The scenario sub-panel drives GET/PATCH "
                        "/api/demo/scenario and the probe "
                        "/api/demo/errors/probe — inject, watch the 500 "
                        "envelope with its request id, reset, watch the "
                        "healthy 200. Every observed failure shows the "
                        "envelope beside the x-request-id header with a "
                        "match badge, paired with what the server logged "
                        "for that kind."
                    ),
                ),
            ],
        ),
        # ── 7. What logs on failure ───────────────────────────────────────
        Section(
            id="what-logs-on-failure",
            title="What logs on failure",
            blocks=[
                TextBlock(
                    kind="text",
                    id="logs-pitch",
                    text=(
                        "An error response answers the caller; a log line "
                        "answers the operator — and the second audience "
                        "is who you write for at 3 a.m. The app's logging "
                        "is structlog rendering one JSON object per line "
                        "(timestamp, level, event, then structured "
                        "fields), configured once in ``create_app``. "
                        "Nothing is string-formatted into prose: every "
                        "field is a name a log query can filter on, and "
                        "``format_exc_info`` is in the processor chain "
                        "precisely so the traceback of an "
                        "``exc_info=True`` call renders into the SAME "
                        "one-line JSON record instead of a multi-line "
                        "blob that breaks JSON-tailed pipelines:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="logs-config-quote",
                    language="py",
                    caption="The JSON pipeline every log line rides — tracebacks included, one object each.",
                    source="server/guide/core/logging.py",
                    snippet=(
                        "    structlog.configure(\n"
                        "        processors=[\n"
                        "            structlog.processors.add_log_level,\n"
                        '            structlog.processors.TimeStamper(fmt="iso"),\n'
                        "            structlog.processors.format_exc_info,\n"
                        "            structlog.processors.JSONRenderer(),\n"
                        "        ],\n"
                        "        wrapper_class=structlog.make_filtering_bound_logger(_numeric_level(level)),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="logs-events-framing",
                    text=(
                        "Each handler logs its own event, at a level that "
                        "means something — the four events this app can "
                        "emit on a failure, and what each carries:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="logs-events-list",
                    ordered=False,
                    items=[
                        "app_error · warning — every AppError: kind, "
                        "message, request id; the bread-and-butter "
                        "failure line for 401s, 403s, 404s, 409s, 429s, "
                        "503s.",
                        "request_validation_failed · info — rejected "
                        "bodies: request id and how many detail triples; "
                        "the caller's mistake, not the server's health.",
                        "http_exception · warning — Starlette-raised "
                        "failures: the truthful status and the bucket it "
                        "took.",
                        "unhandled_exception · error — the 500s: error "
                        "class, request id, and the full traceback "
                        "through exc_info — the only event that carries "
                        "one.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="logs-correlation-pitch",
                    text=(
                        "The thread that ties wire and log together is "
                        "the request id, and its lookup is subtler than "
                        "it looks. Handlers running INSIDE the request-id "
                        "middleware see the ambient ContextVar; the "
                        "last-resort handler runs OUTSIDE it — "
                        "ServerErrorMiddleware wraps user middleware, and "
                        "by the time it answers, the contextvar has been "
                        "reset during unwinding — so the lookup falls "
                        "back to the mirror the middleware wrote onto the "
                        "ASGI scope, which survives unwinding by design. "
                        "That fallback is why every 500 envelope still "
                        "carries the id a client can quote and an "
                        "operator can grep:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="logs-resolve-quote",
                    language="py",
                    caption="The id lookup that survives unwinding: contextvar first, scope mirror second.",
                    source="server/guide/core/request_context.py",
                    snippet=(
                        "def resolve_request_id(request: Request) -> str:\n"
                        '    """Best-effort lookup: contextvar first, then the request\'s scope state.\n'
                        "\n"
                        "    Handlers running inside this middleware see the contextvar; the\n"
                        "    unhandled-exception handler runs outside it (ServerErrorMiddleware wraps\n"
                        "    user middleware) and reads the scope mirror instead.\n"
                        '    """\n'
                        "    ambient = _request_id.get()\n"
                        "    if ambient:\n"
                        "        return ambient\n"
                        '    state_id = request.scope.get("state", {}).get("request_id")\n'
                        '    return state_id if isinstance(state_id, str) else ""'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="logs-unhandled-quote-pitch",
                    text=(
                        "The unhandled handler is the pair of halves "
                        "every 500 must get right: log EVERYTHING, answer "
                        "NOTHING. The ``exc_info=exc`` call puts the "
                        "whole traceback into the JSON record keyed by "
                        "the request id, while the response is the "
                        "generic message — an attacker who probes for "
                        "tracebacks, class names, or file paths gets a "
                        "fixed string for their trouble:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="logs-unhandled-quote",
                    language="py",
                    caption="The 500 contract: the log sees the traceback, the client never does.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "    request_id = resolve_request_id(request)\n"
                        "    logger.error(\n"
                        '        "unhandled_exception",\n'
                        "        request_id=request_id,\n"
                        "        error=type(exc).__name__,\n"
                        "        exc_info=exc,\n"
                        "    )\n"
                        "    return _build_error_response(request, 500, FailureKind.INTERNAL, _GENERIC_INTERNAL_MESSAGE)"
                    ),
                ),
            ],
        ),
        # ── 8. Process nets ───────────────────────────────────────────────
        Section(
            id="process-nets",
            title="Process nets",
            blocks=[
                TextBlock(
                    kind="text",
                    id="nets-pitch",
                    text=(
                        "Everything so far catches failures the process "
                        "can still handle. This section is about the nets "
                        "BELOW that — what answers when the exception "
                        "machinery itself is out of reach, and what "
                        "answers when the process is gone. The first net "
                        "below the handlers is structural: the middleware "
                        "stack's ordering, wired once in ``create_app``. "
                        "The request-id middleware sits innermost so "
                        "every exchange carries an id from the first "
                        "line it generates; CORS sits outermost so even "
                        "error envelopes are readable cross-origin; and "
                        "the exception handlers are registered after the "
                        "stack, wrapping the whole of it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="nets-wiring-quote",
                    language="py",
                    caption="The net below the handlers: middleware order + the four registrations.",
                    source="server/guide/main.py",
                    snippet=(
                        "    app.add_middleware(RequestIdMiddleware)\n"
                        "    app.add_middleware(SecurityHeadersMiddleware)\n"
                        "    app.add_middleware(\n"
                        "        CORSMiddleware,\n"
                        "        allow_origins=list(ALLOWED_ORIGINS),\n"
                        "        allow_credentials=ALLOW_CREDENTIALS,\n"
                        "        allow_methods=list(ALLOWED_METHODS),\n"
                        "        allow_headers=list(ALLOWED_HEADERS),\n"
                        "        max_age=PREFLIGHT_MAX_AGE_S,\n"
                        "    )\n"
                        "    register_exception_handlers(app)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="nets-ladder-framing",
                    text=(
                        "Below the process, the nets are owned by the "
                        "platform, and each answers the same two "
                        "questions — what does the caller see, what does "
                        "the operator see. The ladder from innermost to "
                        "outermost:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="nets-ladder-list",
                    ordered=True,
                    items=[
                        "The four exception handlers — the everyday net: "
                        "every raise becomes the family envelope with a "
                        "request id, and the log gets its event.",
                        "ServerErrorMiddleware — Starlette's outermost "
                        "wrap: the net that CATCHES the catch-all, "
                        "running the registered Exception handler "
                        "outside the middleware stack (why the envelope "
                        "stamps its own request-id header).",
                        "The uvicorn process — if the ASGI app itself "
                        "crashes mid-response or a worker dies, the "
                        "connection breaks: the caller sees a reset, not "
                        "an envelope, which is why the layers above do "
                        "the answering whenever they still can.",
                        "The restart policy — Docker's "
                        "unless-stopped brings a died process back; the "
                        "arq worker in this stack runs under exactly "
                        "that policy, because a job worker dying must "
                        "not take the queue's story with it.",
                        "The operator — the last net: health checks, "
                        "alerts, and the log lines this topic's failure "
                        "events exist to feed (topic 33 builds the "
                        "observability half properly).",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="nets-compose-pitch",
                    text=(
                        "The arq worker is the concrete example worth "
                        "quoting — a separate process, one command, one "
                        "restart policy: if the worker hits a poison "
                        "message and dies, the policy restarts it, the "
                        "retry engine's dead-letter queue holds the "
                        "blame, and the API server never noticed. Process "
                        "nets are boring on purpose; boring is what you "
                        "want from the layer whose job is to exist after "
                        "everything else stopped:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="nets-compose-quote",
                    language="yaml",
                    caption="A process net as config: the arq worker under unless-stopped.",
                    source=".docker/docker-compose.yml",
                    snippet=(
                        "  arq-worker:\n"
                        "    image: fdg_server_dev\n"
                        "    container_name: fastapi_developers_guide_arq_worker_dev\n"
                        "    restart: unless-stopped\n"
                        "    working_dir: /app\n"
                        '    command: sh -c "uv sync --locked && .venv/bin/arq guide.worker.WorkerSettings"'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="nets-shutdown-pitch",
                    text=(
                        "One net deserves a word before the tour because "
                        "it is the only one YOU write on a deadline: "
                        "graceful shutdown, the difference between a "
                        "restart your callers never notice and one that "
                        "turns into a burst of 500s. Uvicorn stops "
                        "accepting connections, waits out in-flight "
                        "requests, then runs the lifespan's shutdown "
                        "half — this app's closes the database engine, "
                        "stops the gRPC satellite, and releases the "
                        "clients, so nothing leaks across restarts. The "
                        "failure-mode lesson is the inverse of the rest "
                        "of the topic: shutdown is where you must "
                        "SWALLOW deliberately — close what you own, log "
                        "what failed to close, and exit anyway, because "
                        "hanging the shutdown to 'finish perfectly' "
                        "holds the restart hostage and converts one "
                        "process's death into the whole deployment's."
                    ),
                ),
            ],
        ),
        # ── 9. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole topic, from a shell — real envelopes, real ids, a real 500.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Six stops: the 404 and 422 envelopes with their "
                        "request ids on header and body, the 401/403 "
                        "ladder on topic 24's guarded edit with a really "
                        "minted token, the 429 from the security burner's "
                        "real budget with its Retry-After, the inject-"
                        "probe-reset round trip that produces a genuine "
                        "500 envelope (and the healthy 200 after the "
                        "reset), the explorer panel itself, and this "
                        "topic's content detail. The stack is up; every "
                        "command answers from the machinery this topic "
                        "taught, quoted, and finally let fail on "
                        "purpose."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-envelopes",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — two envelopes: the app 404 and the 422, ids on body AND header\n"
                        "curl -s localhost:8000/api/content/nope \\\n"
                        "  | python3 -c 'import json,sys; e=json.load(sys.stdin)[\"error\"]; print(\"404:\", e[\"code\"], \"|\", e[\"message\"], \"|\", e[\"requestId\"][:8])'\n"
                        "curl -sD - -o /dev/null localhost:8000/api/content/nope | grep -i x-request-id\n"
                        "curl -s -X PATCH -H 'content-type: application/json' -d '{\"injectFailure\": \"bogus\"}' \\\n"
                        "  localhost:8000/api/demo/scenario \\\n"
                        "  | python3 -c 'import json,sys; e=json.load(sys.stdin)[\"error\"]; print(\"422:\", e[\"code\"], \"|\", e[\"details\"][0][\"loc\"], e[\"details\"][0][\"type\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-ladder",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the 401/403 ladder on the authz-guarded edit (topic 24's guard)\n"
                        "EDIT=localhost:8000/api/demo/authz/posts/designing-urls-people-can-read\n"
                        "curl -s -o /dev/null -w 'no credential: %{http_code}\\n' -X PUT $EDIT\n"
                        "ALAN=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"username\":\"alan\",\"scopes\":[\"*\"]}' localhost:8000/api/demo/auth/jwt/mint \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"token\"])')\n"
                        "curl -s -X PUT -H \"Authorization: Bearer $ALAN\" $EDIT \\\n"
                        "  | python3 -c 'import json,sys; e=json.load(sys.stdin)[\"error\"]; print(\"403:\", e[\"code\"], \"|\", e[\"details\"][\"reason\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-burn",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — drain the real budget: five allowed, the sixth is the 429\n"
                        "for i in 1 2 3 4 5 6; do\n"
                        "  curl -s -o /dev/null -w \"hit $i: %{http_code}\\n\" -X POST localhost:8000/api/demo/security/rate-limit/burn\n"
                        "done\n"
                        "curl -sD - -X POST localhost:8000/api/demo/security/rate-limit/burn \\\n"
                        "  | grep -iE 'HTTP/|retry-after'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-inject",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the genuine 500: inject, probe, reset, probe\n"
                        "curl -s -X PATCH -H 'content-type: application/json' -d '{\"injectFailure\":\"error\"}' \\\n"
                        "  localhost:8000/api/demo/scenario \\\n"
                        "  | python3 -c 'import json,sys; print(\"injected:\", json.load(sys.stdin)[\"injectFailure\"])'\n"
                        "curl -sD - localhost:8000/api/demo/errors/probe | grep -iE 'HTTP/|x-request-id'\n"
                        "curl -s localhost:8000/api/demo/errors/probe \\\n"
                        "  | python3 -c 'import json,sys; e=json.load(sys.stdin)[\"error\"]; print(\"500:\", e[\"code\"], \"|\", e[\"message\"], \"| id\", e[\"requestId\"][:8])'\n"
                        "curl -s -X PATCH -H 'content-type: application/json' -d '{\"injectFailure\":\"none\"}' \\\n"
                        "  localhost:8000/api/demo/scenario > /dev/null\n"
                        "curl -s localhost:8000/api/demo/errors/probe \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"reset:\", b[\"status\"], \"|\", b[\"injectFailure\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-panel",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the explorer panel: eight kinds from the taxonomy's own tables\n"
                        "curl -s localhost:8000/api/demo/errors \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "rows=[(k[\"kind\"], k[\"httpStatus\"], k[\"trigger\"][\"mode\"]) for k in b[\"kinds\"]]; \\\n"
                        "print(\"kinds:\", [f\"{k} {s} ({m})\" for k,s,m in rows])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — this topic's own detail, demo inline in the failure-injection section\n"
                        "curl -s localhost:8000/api/content/exception-handling | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "print(\"sections:\", len(t[\"sections\"]))\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stops 1–3 watch the handlers render three sources "
                        "— a domain 404, a validation 422, the guard pair, "
                        "a dependency's 429 — into one shape with ids that "
                        "grep. Stop 4 is the topic's center: a real "
                        "unhandled exception, injected on demand, answered "
                        "by the outermost net with nothing leaked and "
                        "everything logged, then healed by a reset. The "
                        "two recipe kinds the panel could not fire live "
                        "(conflict's arq refusal that never comes, "
                        "service_unavailable's store that is healthily "
                        "up) have real raise sites this topic quoted — "
                        "the honest position is saying so, not staging "
                        "them. That opens the platform group: the error "
                        "story every later topic leans on is now itself a "
                        "documented, fireable thing."
                    ),
                ),
            ],
        ),
    ],
)
