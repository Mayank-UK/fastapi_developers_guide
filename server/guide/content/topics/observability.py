"""Topic 33 — Observability: the three questions, answered by real signals.

The repo already runs every instrument this topic teaches, and most of it
became real WITH the topic: the structlog JSON pipeline (grown additively
— context merging first, the recent-events ring capture last before the
renderer), the pure-ASGI access-log middleware the middleware topic
promised ("it arrives with observability"), request ids bound into the
log context so every line during a request correlates, the deliberately
dependency-free liveness endpoint beside the optional-service 503
degradation that IS this repo's readiness story, and the two queue numbers
the jobs topic left as "the two observability numbers". What is NOT here
is taught honestly: Prometheus and OpenTelemetry are not dependencies —
the metrics section teaches the model concept-first against the repo's
real numbers, and the tracing section teaches OTel concept-first while
the fan-out demo correlates REAL request ids across header, envelope, and
log row on live data (with the honest lockfile fact that
opentelemetry-api rides in via fastapi itself). Two demos INLINE: the
structured-log viewer in the structlog-JSON section, the trace fan-out in
the OTel-tracing section.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="observability",
    title="Observability",
    subtitle=(
        "The three questions every running service must answer — is it up, "
        "is it working, why is it slow — and the instruments that answer "
        "them: structured JSON logs with request-id correlation (a live "
        "viewer over this app's real pipeline), the access-log middleware "
        "and level discipline, liveness versus readiness and what this "
        "repo's health endpoint deliberately does not check, metrics "
        "concept-first against the queue's two real numbers, and tracing "
        "taught concept-first while a real fan-out correlates ids across "
        "header, envelope, and log row."
    ),
    group="platform",
    order=33,
    sections=[
        # ── 1. Three questions ────────────────────────────────────────────
        Section(
            id="three-questions",
            title="Three questions",
            blocks=[
                TextBlock(
                    kind="text",
                    id="obs-questions-pitch",
                    text=(
                        "Everything in this topic serves three questions, and "
                        "it is worth fixing them before touching any tool. "
                        "One: IS IT UP — does the process exist, is it "
                        "accepting connections, would a restart help? Two: IS "
                        "IT WORKING — are requests succeeding at a normal "
                        "rate, are the dependencies it needs reachable, is "
                        "anything degraded? Three: WHY — when the answer to "
                        "two is 'no', what happened, for which request, and "
                        "where in its journey through the stack? Monitoring "
                        "is watching known signals for expected trouble; "
                        "observability is the stronger property of being able "
                        "to ask questions you did not anticipate when the "
                        "system was built. The first is a dashboard of "
                        "things you predicted; the second is the ability to "
                        "interrogate reality after the surprise. Production "
                        "systems need both, and the difference is usually "
                        "whether the underlying events were recorded with "
                        "enough structure and correlation to be re-queried."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-questions-instruments-framing",
                    text=(
                        "Four instrument families answer those questions, and "
                        "this guide runs real instances of the first and "
                        "last while teaching the middle two concept-first:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="obs-questions-instruments",
                    ordered=False,
                    items=[
                        "Health checks — a cheap endpoint that answers 'is it "
                        "up' for orchestrators and load balancers; this "
                        "repo's /api/health is the real thing.",
                        "Logs — timestamped, structured events recording what "
                        "the process did; this app's structlog JSON pipeline, "
                        "one machine-greppable object per line.",
                        "Metrics — numbers with names over time (request "
                        "rate, error rate, queue depth), aggregated rather "
                        "than stored per event; taught concept-first against "
                        "the queue's two real numbers.",
                        "Traces — the journey of one request across handlers "
                        "and services as a tree of correlated spans; this "
                        "repo's request-id correlation is the real seed of "
                        "the idea, OTel the ecosystem standard.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="obs-questions-why-structure",
                    text=(
                        "The connective tissue across all four is correlation "
                        "and structure, and this is where naive setups fail. "
                        "A log line that reads 'something went wrong for "
                        "somebody' answers nothing; the same line as a JSON "
                        "object carrying an event name, a level, a "
                        "timestamp, and the request id that caused it can be "
                        "found by grep, aggregated by a log system, and "
                        "joined to the exact response the client saw. This "
                        "repository treats that as an invariant: nothing is "
                        "swallowed, every failure logs with its request id, "
                        "and every error envelope the client receives "
                        "carries the same id back — one id tying what the "
                        "caller saw to what the server did. The rest of this "
                        "topic walks the instruments in the order a request "
                        "meets them: the log pipeline, the request-logging "
                        "middleware, the level vocabulary, health and "
                        "readiness, metrics, tracing — then the human "
                        "systems (alerting, process nets) that turn signals "
                        "into action."
                    ),
                ),
            ],
        ),
        # ── 2. structlog JSON ─────────────────────────────────────────────
        Section(
            id="structlog-json",
            title="structlog JSON",
            lead="This section carries the topic's first demo — the structured-log viewer.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="obs-structlog-pitch",
                    text=(
                        "A log statement is a function call that survives "
                        "into production; structure is what decides whether "
                        "it is data or noise. An unstructured line — "
                        "'User ada hit an error' — is prose: a human can "
                        "read it, but no tool can group it, count it, or "
                        "join it to anything. A structured event is a "
                        "key/value record with a stable event name: the "
                        "logger call names the event and passes facts as "
                        "keyword arguments, and the pipeline renders the "
                        "whole thing as one JSON object per line. This "
                        "server uses structlog — the manifest declares it "
                        "beside the framework itself — and configures the "
                        "entire pipeline in one call that runs from "
                        "create_app's first lines:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-structlog-configure-quote",
                    language="py",
                    caption="The whole pipeline: merge context, stamp level and time, fold tracebacks, capture, render.",
                    source="server/guide/core/logging.py",
                    snippet=(
                        "    structlog.configure(\n"
                        "        processors=[\n"
                        "            structlog.contextvars.merge_contextvars,\n"
                        "            structlog.processors.add_log_level,\n"
                        "            structlog.processors.TimeStamper(fmt=\"iso\"),\n"
                        "            structlog.processors.format_exc_info,\n"
                        "            recent_log().capture,\n"
                        "            structlog.processors.JSONRenderer(),\n"
                        "        ],\n"
                        "        wrapper_class=structlog.make_filtering_bound_logger(_numeric_level(level)),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-structlog-assembly",
                    text=(
                        "Read the processors list as an assembly line the "
                        "event dict travels, in order. merge_contextvars "
                        "folds in the request-scoped bound context — the "
                        "request id the request-id middleware binds, so "
                        "every line any code writes during a request "
                        "carries it without each call site passing it. "
                        "add_log_level stamps the level; TimeStamper adds "
                        "the ISO-8601 timestamp; format_exc_info folds any "
                        "exception's traceback into the event as a string. "
                        "The capture line is this topic's own substrate: "
                        "the recent-events ring, a bounded buffer holding "
                        "the process's last fifty events, snapshotted here "
                        "— after the interesting keys exist, before the "
                        "renderer flattens everything — so the viewer demo "
                        "below can serve real events. JSONRenderer, last, "
                        "turns the dict into the one-line JSON object "
                        "stdout actually receives. Structlog owns the app's "
                        "stream; uvicorn's own server lines go through the "
                        "stdlib logging beside it — two streams in one "
                        "process, both visible in the container's logs."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-structlog-call-shape",
                    text=(
                        "The call sites are where structure becomes habit. "
                        "The convention throughout this codebase: a "
                        "snake_case event name that names the FACT, plus "
                        "keyword arguments that carry the specifics, "
                        "request_id first among them. The shared error "
                        "handler for typed application errors is the "
                        "cleanest example — every failed request in the app "
                        "passes through it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-structlog-handler-quote",
                    language="py",
                    caption="The failure log: event name, request id, kind, message — one JSON object.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:\n"
                        "    \"\"\"AppError → its mapped status + envelope; logged with the request id.\"\"\"\n"
                        "    logger.warning(\n"
                        "        \"app_error\",\n"
                        "        request_id=resolve_request_id(request),\n"
                        "        kind=exc.kind.value,\n"
                        "        message=exc.message,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-structlog-demo-pitch",
                    text=(
                        "This section's demo makes the pipeline itself the "
                        "exhibit: a live structured-log viewer that "
                        "introspects the ACTIVE processor chain from "
                        "structlog's own process configuration and serves "
                        "the ring's real recent events — the very events "
                        "stdout receives. The panel request also logs two "
                        "of its own beats through the real logger before "
                        "reading the tail, stamped with this response's own "
                        "request id, so the panel always demonstrates "
                        "itself:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-structlog-beats-quote",
                    language="py",
                    caption="The panel's own beats — really logged, really rendered, really captured.",
                    source="server/guide/domain/demos/obs_viewer.py",
                    snippet=(
                        "    ring = recent_log()\n"
                        "    logger.info(\n"
                        "        \"obs_viewer_panel_opened\",\n"
                        "        request_id=request_id,\n"
                        "        panel=\"obs:viewer\",\n"
                        "        ring_capacity=ring.capacity,\n"
                        "    )\n"
                        "    logger.warning(\n"
                        "        \"obs_viewer_sample_warning\",\n"
                        "        request_id=request_id,\n"
                        "        detail=\"this panel's own warning-level beat — emitted so a second \"\n"
                        "        \"level is visible even on a quiet process\",\n"
                        "    )"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="obs:viewer",
                    title="The structured-log viewer",
                    description=(
                        "GET /api/demo/obs/viewer serves the LIVE pipeline "
                        "and the process's REAL recent log events. The "
                        "pipeline rows are introspected from structlog's "
                        "process configuration — the same chain every log "
                        "call in this app traverses, in execution order, "
                        "each with its role. The events list is the "
                        "recent-events ring the pipeline feeds: http_request "
                        "rows (one per request, from the access-log "
                        "middleware), app_error and "
                        "request_validation_failed rows from real failures "
                        "other requests hit, and the panel's own two beats "
                        "carrying this very response's x-request-id — find "
                        "the id in the header and match it in the rows. The "
                        "level row shows the configured level and its real "
                        "source. The ring is process-local and bounded — "
                        "a real log viewer reads aggregated stdout, which "
                        "the terminal companion shows."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-structlog-demo-reading",
                    text=(
                        "Reading the panel against the running stack is the "
                        "point: with the access-log middleware in place, "
                        "ordinary traffic keeps the ring warm — every "
                        "request you or the guide pages make adds one "
                        "http_request row, and any request that fails adds "
                        "its failure row beside it, both stamped with that "
                        "request's id. The endpoint behind the panel is as "
                        "thin as every other router in the stack:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-structlog-router-quote",
                    language="py",
                    caption="One GET, a pure payload builder, a declared response model.",
                    source="server/guide/presentation/routers/demo/obs.py",
                    snippet=(
                        "@router.get(VIEWER_PATH, response_model=LogViewerPanel)\n"
                        "async def read_log_viewer(\n"
                        "    request: Request, config: Annotated[AppConfig, Depends(get_config)]\n"
                        ") -> LogViewerPanel:\n"
                        "    \"\"\"Serve the live structured-log viewer: pipeline, level, recent events.\"\"\"\n"
                        "    return build_log_viewer_payload(\n"
                        "        request_id=resolve_request_id(request),\n"
                        "        configured_level=config.log_level,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-structlog-why-structlog",
                    text=(
                        "Why structlog over the standard library's logging "
                        "module? The stdlib is fully capable — handlers, "
                        "formatters, JSON via a custom formatter — and "
                        "structlog does not replace it so much as sit "
                        "beside it (uvicorn's own lines ride stdlib, "
                        "unchanged). What structlog buys is the pipeline "
                        "you just read: processors as explicit, composable "
                        "stages; key/value log calls that stay lazy (an "
                        "argument is only rendered if the level passes, a "
                        "point the Python-runtime topic proved); context "
                        "binding so correlation keys ride automatically; "
                        "and JSON rendering as one line of configuration "
                        "rather than a formatter class. The decision rule "
                        "this repo followed: reach for the library when "
                        "the PIPELINE is the product. The dependency "
                        "cost — one more name in the manifest — is exactly "
                        "the trade the dependency-management topic taught "
                        "you to weigh."
                    ),
                ),
            ],
        ),
        # ── 3. Request logging middleware ─────────────────────────────────
        Section(
            id="request-logging-middleware",
            title="Request logging middleware",
            blocks=[
                TextBlock(
                    kind="text",
                    id="obs-requestlog-pitch",
                    text=(
                        "The middleware topic recorded this layer honestly "
                        "as missing: 'what does NOT exist yet is the "
                        "per-request access-log layer — the middleware that "
                        "records method, path, status, duration, and the "
                        "request id once per request. It arrives with "
                        "observability.' It has arrived. Request logging in "
                        "a web app is three cooperating layers, and knowing "
                        "which layer owns what is most of the design:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="obs-requestlog-layers",
                    ordered=False,
                    items=[
                        "Server access log — the ASGI server's own line per "
                        "request (uvicorn's stdlib-logging stream); owns "
                        "wire-level facts, knows nothing about your domain.",
                        "Correlation id — the request-id middleware assigns "
                        "or accepts an id, stamps it on the response, and "
                        "binds it into the log context; owns identity, logs "
                        "nothing itself.",
                        "Application events — the access-log middleware's "
                        "one structured line per request plus every "
                        "handler's own failure events; owns the story, "
                        "correlated by the id the second layer minted.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="obs-requestlog-id-first",
                    text=(
                        "The id layer comes first because everything else "
                        "depends on it. Every request gets exactly one id: "
                        "the inbound x-request-id header when the client "
                        "supplies one (echoed, never executed), otherwise a "
                        "fresh uuid4. The middleware topic taught the "
                        "normalizer in depth; what observability adds is "
                        "the binding — the id now also rides as a structlog "
                        "contextvar for the duration of the exchange, so "
                        "any code the request touches logs it without "
                        "passing it around:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-requestlog-binding-quote",
                    language="py",
                    caption="Assign once, set the contextvar, mirror into the scope, bind into structlog.",
                    source="server/guide/core/request_context.py",
                    snippet=(
                        "        request_id = _assign_request_id(_inbound_id(scope))\n"
                        "        token = _request_id.set(request_id)\n"
                        "        # Mirror into the shared ASGI scope so handlers outside this\n"
                        "        # middleware (ServerErrorMiddleware's 500 path) still see the id.\n"
                        "        _mirror_into_scope(scope, request_id)\n"
                        "        # Bind into structlog's context so every log line this request's\n"
                        "        # code writes carries the id without passing it at each call site.\n"
                        "        _bind_log_context(request_id)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-requestlog-access-layer",
                    text=(
                        "The access-log layer is pure ASGI — the streaming "
                        "lesson from the realtime topic applies to logging "
                        "too: BaseHTTPMiddleware buffers bodies, so an "
                        "access log built on it would buffer every "
                        "streaming response. This layer instead observes "
                        "messages as they pass: it starts a perf_counter at "
                        "request-enter, reads the status and the stamped id "
                        "off the one http.response.start message, and logs "
                        "exactly once in a finally after the last body "
                        "chunk flushed — the whole onion timed end to end:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-requestlog-access-quote",
                    language="py",
                    caption="One http_request event per request: method, path, status, duration, id.",
                    source="server/guide/presentation/middleware/request_log.py",
                    snippet=(
                        "        try:\n"
                        "            await self.app(scope, receive, send_observing)\n"
                        "        finally:\n"
                        "            duration_ms = round((time.perf_counter() - started) * 1000, 1)\n"
                        "            logger.info(\n"
                        "                \"http_request\",\n"
                        "                method=method,\n"
                        "                path=path,\n"
                        "                status=status[0] if status else 0,\n"
                        "                duration_ms=duration_ms,\n"
                        "                request_id=request_id[0] if request_id else \"\",\n"
                        "            )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-requestlog-reading",
                    text=(
                        "Note the honest edges in those twelve lines. The "
                        "id on every access line is read from the "
                        "response's own x-request-id header — stamped by "
                        "the request-id middleware on the inside — so the "
                        "access log, the error envelopes, and the client "
                        "all see the SAME id without this layer knowing "
                        "anything about contextvars. Status 0 is the "
                        "truthful marker for the one path that never "
                        "crosses back through this layer: the last-resort "
                        "500, answered from outside the user stack, logs "
                        "no response.start here. And the finally means the "
                        "line is written even when the inner app raised — "
                        "an access log that only recorded successes would "
                        "be a very quiet kind of lie. The wiring is one "
                        "additive line in the composition root, wrapping "
                        "the request-id layer it reads from:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-requestlog-wiring-quote",
                    language="py",
                    caption="The composition root: the access-log layer sits just outside the id layer.",
                    source="server/guide/main.py",
                    snippet=(
                        "    app.add_middleware(RequestIdMiddleware)\n"
                        "    # Topic 33's access-log layer wraps the request-id layer: it reads the\n"
                        "    # id RequestIdMiddleware stamps on the response and logs one structured\n"
                        "    # http_request event per request — the whole onion timed end to end.\n"
                        "    app.add_middleware(RequestLogMiddleware)\n"
                        "    app.add_middleware(SecurityHeadersMiddleware)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-requestlog-spans",
                    text=(
                        "One more real instrument belongs in this story: "
                        "the request span. The dependencies topic built a "
                        "yield-dependency that opens a span before the "
                        "handler runs and closes it after the response has "
                        "been sent — four beats per request (setup, "
                        "handler, response, teardown) recorded into a "
                        "bounded ring. Where the access log answers 'what "
                        "crossed the wire', spans answer 'where did the "
                        "time go inside' — the same correlation discipline "
                        "one level deeper. The shape is six lines and "
                        "worth reading as the minimal unit of distributed-"
                        "tracing thinking, before the tracing section "
                        "generalizes it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-requestlog-span-quote",
                    language="py",
                    caption="The yield-dependency span: setup before the handler, teardown after the send.",
                    source="server/guide/presentation/dependencies/request_span.py",
                    snippet=(
                        "    span = RequestSpan(log)\n"
                        "    span.record(\"setup\")\n"
                        "    try:\n"
                        "        yield span\n"
                        "    finally:\n"
                        "        span.record(\"teardown\")"
                    ),
                ),
            ],
        ),
        # ── 4. Levels ─────────────────────────────────────────────────────
        Section(
            id="levels",
            title="Levels",
            blocks=[
                TextBlock(
                    kind="text",
                    id="obs-levels-pitch",
                    text=(
                        "A log level is a routing decision made at the call "
                        "site about who needs this line later: you are "
                        "tagging each event with the smallest audience that "
                        "should ever see it. Python's standard vocabulary, "
                        "and the one this app uses:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="obs-levels-vocabulary",
                    ordered=True,
                    items=[
                        "debug — the developer in the code; fine-grained "
                        "chatter, off in production by default.",
                        "info — the operator scanning a log; normal "
                        "notable events, this app's level for validation "
                        "failures and its per-request access lines.",
                        "warning — something failed but was handled; a "
                        "human should be able to glance at why — every "
                        "typed application error and HTTP exception here.",
                        "error — something failed and was not handled; the "
                        "unhandled-exception handler is this app's one "
                        "producer.",
                        "critical — the process is dying or data is at "
                        "risk; none in this codebase, and that is correct."
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="obs-levels-mechanics",
                    text=(
                        "The mechanics are one line of the pipeline "
                        "configuration: make_filtering_bound_logger "
                        "attaches the level to the LOGGER, and a call "
                        "below the configured level is dropped before any "
                        "processor runs — the event dict is never built, "
                        "arguments never rendered, the line never written. "
                        "That is why the level comes from configuration, "
                        "and this repo's handling of the config value is "
                        "worth quoting for its defensive posture: config "
                        "input is hostile, and an unknown level falls back "
                        "to INFO instead of crashing the app:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-levels-fallback-quote",
                    language="py",
                    caption="Unknown levels degrade to INFO — config input is hostile, boots must not die.",
                    source="server/guide/core/logging.py",
                    snippet=(
                        "    def _numeric_level(name: str) -> int:\n"
                        "        resolved = logging.getLevelName(name.upper())\n"
                        "        return resolved if isinstance(resolved, int) else logging.INFO"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-levels-config-quote",
                    language="py",
                    caption="The level is one setting among the process config, env-overridable.",
                    source="server/guide/core/config.py",
                    snippet=(
                        "    mongo_url: str = \"mongodb://localhost:27017\"\n"
                        "    log_level: str = \"info\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-levels-usage",
                    text=(
                        "FDG_LOG_LEVEL=debug boots the process with debug "
                        "events flowing; FDG_LOG_LEVEL=warning silences "
                        "the info stream entirely (including every access "
                        "line — try it on the running stack and watch the "
                        "viewer's ring go quiet between failures). The "
                        "repo's real producers map cleanly onto the "
                        "vocabulary, and the mapping is the teachable "
                        "part: validation failures log at info because "
                        "they are routine client mistakes, not server "
                        "trouble; typed application errors and HTTP "
                        "exceptions log at warning because they are "
                        "handled-but-noteworthy; exactly one producer logs "
                        "at error, and it is the last-resort handler for "
                        "unhandled exceptions, where the traceback itself "
                        "rides along:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-levels-error-quote",
                    language="py",
                    caption="The one error-level producer: unhandled exceptions, traceback folded in.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "    request_id = resolve_request_id(request)\n"
                        "    logger.error(\n"
                        "        \"unhandled_exception\",\n"
                        "        request_id=request_id,\n"
                        "        error=type(exc).__name__,\n"
                        "        exc_info=exc,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-levels-judgment",
                    text=(
                        "The judgment calls are where engineers actually "
                        "disagree, so name them. A level is not a severity "
                        "score for the event — it is a statement about the "
                        "READER: debug means 'nobody but someone in this "
                        "code', warning means 'an operator skimming after "
                        "an incident', error means 'an operator being "
                        "paged'. That framing settles the classic debates: "
                        "a client's malformed JSON is info (routine, "
                        "expected, handled); YOUR cache missing is info; "
                        "a dependency refusing connections is warning even "
                        "though the request failed, because the failure "
                        "was handled by design (the next section shows "
                        "exactly that producer). Reserve error for the "
                        "unhandled — if you log errors you silently fix, "
                        "you have trained everyone to ignore the word. And "
                        "never log-and-raise the same failure at two "
                        "levels: one event, one line, at the layer that "
                        "finalizes the outcome."
                    ),
                ),
            ],
        ),
        # ── 5. Health: liveness vs readiness ──────────────────────────────
        Section(
            id="health-liveness-readiness",
            title="Health: liveness vs readiness",
            blocks=[
                TextBlock(
                    kind="text",
                    id="obs-health-pitch",
                    text=(
                        "The health endpoint answers question one — is it "
                        "up — for machines that need to act on the answer: "
                        "the container orchestrator deciding whether to "
                        "restart you, the load balancer deciding whether "
                        "to route to you, the deployment pipeline deciding "
                        "whether the new version booted. The critical "
                        "design split is liveness versus readiness, "
                        "because the two answers drive OPPOSITE actions. "
                        "Liveness says 'this process can serve at all' — "
                        "if it fails, the platform should restart or "
                        "replace the process. Readiness says 'this process "
                        "can serve USEFULLY right now' — if it fails, the "
                        "platform should stop routing traffic to it but "
                        "leave it alone. Confuse them and you build the "
                        "classic outage amplifier: a readiness check "
                        "implemented as liveness, where one slow database "
                        "makes the orchestrator restart every healthy "
                        "app instance simultaneously."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-health-real-endpoint",
                    text=(
                        "This repo's real endpoint is deliberately, "
                        "documentedly liveness — it touches nothing:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-health-endpoint-quote",
                    language="py",
                    caption="The real /api/health: process liveness plus the environment it booted in.",
                    source="server/guide/presentation/routers/health.py",
                    snippet=(
                        "@router.get(\"/health\", response_model=HealthResponse)\n"
                        "def read_health(config: Annotated[AppConfig, Depends(get_config)]) -> HealthResponse:\n"
                        "    \"\"\"Report process liveness plus the environment it booted in.\"\"\"\n"
                        "    return HealthResponse(status=\"ok\", env=config.env)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-health-liveness-why",
                    text=(
                        "Why dependency-free? Because the process can be "
                        "perfectly alive while a dependency is down — that "
                        "is the whole optional-service discipline this "
                        "guide runs: the app boots with PostgreSQL, Redis, "
                        "or MongoDB unreachable, and only the features "
                        "that need them degrade. A liveness probe that "
                        "pinged the database would convert every database "
                        "blip into an app restart storm, the outage "
                        "amplifier again. The production compose file "
                        "probes exactly this contract — urllib on the real "
                        "route, because the slim runtime image ships no "
                        "wget or curl:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-health-compose-quote",
                    language="yaml",
                    caption="The prod container's healthcheck: the liveness route, probed by the venv python.",
                    source=".docker/docker-compose.prod.yml",
                    snippet=(
                        "    healthcheck:\n"
                        "      # The runtime image is python:3.13-slim — no wget, no curl. The venv\n"
                        "      # python (first on the image PATH) is the probe binary: urllib GET on\n"
                        "      # the real liveness route, dependency-free by design (the app's own\n"
                        "      # health contract).\n"
                        "      test: [\"CMD\", \"python\", \"-c\", \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5)\"]\n"
                        "      interval: 30s\n"
                        "      timeout: 5s\n"
                        "      retries: 3"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-health-readiness-gap",
                    text=(
                        "Now the honest gap: this repo has NO readiness "
                        "endpoint, and saying so precisely is the lesson. "
                        "A readiness check for this app would answer, per "
                        "request, 'can I serve the parts of the API this "
                        "deployment promises' — and the checks follow "
                        "directly from the wiring: a one-row SELECT "
                        "against PostgreSQL (the engine every data demo "
                        "rides), a PING against Redis (cache, streams, "
                        "jobs), maybe the mongo client's hello — each with "
                        "a short timeout, aggregated into a 200-or-503 "
                        "verdict the load balancer can route on. What "
                        "exists instead is finer-grained and arguably more "
                        "honest for this app's shape: per-feature "
                        "degradation. Each optional service maps its "
                        "failures to a 503 envelope AT THE FEATURE, with a "
                        "warning logged first — the observable symptom, "
                        "which is what observability means in practice:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-health-degradation-quote",
                    language="py",
                    caption="Optional-service discipline: Redis trouble becomes a logged warning + a 503 envelope.",
                    source="server/guide/data/redis/playground.py",
                    snippet=(
                        "@contextmanager\n"
                        "def _map_redis_failures(operation: str) -> Iterator[None]:\n"
                        "    \"\"\"Optional-service discipline: Redis trouble becomes service_unavailable.\"\"\"\n"
                        "    try:\n"
                        "        yield\n"
                        "    except AppError:\n"
                        "        raise\n"
                        "    except (RedisError, OSError) as exc:\n"
                        "        logger.warning(\n"
                        "            \"redis_playground_unavailable\",\n"
                        "            operation=operation,\n"
                        "            error=type(exc).__name__,\n"
                        "            detail=str(exc),\n"
                        "        )\n"
                        "        raise AppError(\n"
                        "            FailureKind.SERVICE_UNAVAILABLE,\n"
                        "            \"Redis is unreachable or unusable — this demo runs real commands \"\n"
                        "            \"against the live store and refuses to serve stale facts.\",\n"
                        "        ) from exc"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-health-synthesis",
                    text=(
                        "Read that producer as a health signal: every "
                        "redis_playground_unavailable warning in the log "
                        "stream IS a readiness fact, timestamped, "
                        "request-correlated, and attributable to one "
                        "dependency — the log stream you already collect "
                        "is the readiness probe you never wrote. That is "
                        "the general lesson of the section: health is not "
                        "one endpoint, it is a contract about WHO ACTS ON "
                        "the answer. Liveness belongs to the process "
                        "supervisor and must stay trivial; readiness "
                        "belongs to the router and may check dependencies "
                        "with short timeouts; and degradation belongs to "
                        "the feature, where this repo puts it. Kubernetes "
                        "users meet the same split as livenessProbe "
                        "versus readinessProbe — and the failure modes "
                        "are identical from Compose up."
                    ),
                ),
            ],
        ),
        # ── 6. Prometheus metrics ─────────────────────────────────────────
        Section(
            id="prometheus-metrics",
            title="Prometheus metrics",
            blocks=[
                TextBlock(
                    kind="text",
                    id="obs-metrics-pitch",
                    text=(
                        "Logs answer 'what happened, exactly'; metrics "
                        "answer 'how much, how often, how fast, over "
                        "time'. A metric is a named number with a small "
                        "type discipline — the event is counted or "
                        "measured at the source, then AGGREGATED (per "
                        "minute, per instance) rather than stored "
                        "individually, which is what makes months of trend "
                        "cheap and questions like 'is the error rate "
                        "climbing' answerable without grepping a "
                        "terabyte. Prometheus is the ecosystem standard: a "
                        "server that PULLS each target's /metrics endpoint "
                        "on an interval, reads a plain-text exposition "
                        "format, stores the time series, and evaluates "
                        "alert rules over it. The model matters more than "
                        "the tool; the types are the model:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="obs-metrics-types",
                    ordered=False,
                    items=[
                        "Counter — a number that only goes up (requests "
                        "total, errors total); the rate of change is the "
                        "signal, and resets mean restarts.",
                        "Gauge — a number that goes up and down (queue "
                        "depth, active connections); its absolute value is "
                        "the signal.",
                        "Histogram — observations bucketed into ranges "
                        "(request durations); yields counts, sums, and "
                        "quantiles like p95 latency."
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="obs-metrics-honest",
                    text=(
                        "Honest position, stated the way this guide states "
                        "everything: this repo does NOT expose /metrics "
                        "and prometheus-client is NOT a dependency — no "
                        "fabricated integration follows. What the repo has "
                        "is real NUMBERS that would feed metrics the day "
                        "the endpoint existed, and the jobs topic left "
                        "exactly that phrase on the record: for worker "
                        "queues, 'two observability numbers' catch most "
                        "incidents — the queue's depth and the age of its "
                        "oldest job. Both are computed from the queue's "
                        "own geometry, live:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-metrics-two-numbers-quote",
                    language="py",
                    caption="The two numbers, really computed: ZCARD depth, oldest age from the lowest score.",
                    source="server/guide/data/jobs/arq_jobs.py",
                    snippet=(
                        "    async def queue_stats(self) -> QueueStatsRow:\n"
                        "        \"\"\"The two numbers: ZCARD depth, oldest age from the lowest score.\"\"\"\n"
                        "        with _map_jobs_failures(\"queue_stats\"):\n"
                        "            pool = await self._pool()\n"
                        "            depth = int(await pool.zcard(QUEUE_KEY))\n"
                        "            oldest = await pool.zrange(QUEUE_KEY, start=0, end=0, withscores=True)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-metrics-mapping",
                    text=(
                        "Map the repo's existing facts onto the types and "
                        "the recipe writes itself. The access-log "
                        "middleware's one http_request event per request "
                        "is a counter plus a histogram observation waiting "
                        "to be recorded (label: status class); the cache "
                        "lab's x-cache hit/miss header is a hit-ratio "
                        "counter pair; the queue's two numbers are gauges "
                        "— depth is 'how far behind', oldest age is 'how "
                        "long since anything was processed', and a depth "
                        "that grows while age grows is a stalled worker. "
                        "The recipe, as commands rather than a fabricated "
                        "code quote:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-metrics-recipe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# The recipe this repo would run (NOT a dependency today — honest recipe):\n"
                        "# 1. add the client:  uv add prometheus-client\n"
                        "# 2. expose GET /metrics returning the exposition format\n"
                        "# 3. count requests by status class in the access-log middleware\n"
                        "#    and observe duration_ms in a histogram; gauge the queue's two numbers.\n"
                        "# The exposition format every target serves, plain text:\n"
                        "curl -s http://a-service-that-has-it/metrics | head -4\n"
                        "# # HELP http_requests_total Total requests.\n"
                        "# # TYPE http_requests_total counter\n"
                        "# http_requests_total{status=\"2xx\"} 1024\n"
                        "# http_requests_total{status=\"5xx\"} 3"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-metrics-coda",
                    text=(
                        "One habit from the pull model worth internalizing "
                        "even if you never run Prometheus: because the "
                        "server polls targets, a metric endpoint is "
                        "liveness-adjacent — an instance that stops being "
                        "scrapeable falls out of the data, and 'target "
                        "down' is itself a first-class signal. And because "
                        "metrics are pre-aggregated, they are the cheap "
                        "layer: log every event, metric every rate. The "
                        "alerting section returns to exactly that division "
                        "of labor — alerts on metrics, diagnosis in logs "
                        "and traces."
                    ),
                ),
            ],
        ),
        # ── 7. OTel tracing ───────────────────────────────────────────────
        Section(
            id="otel-tracing",
            title="OTel tracing",
            lead="This section carries the topic's second demo — the trace fan-out.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="obs-trace-pitch",
                    text=(
                        "A trace is the story of ONE request as it crosses "
                        "handlers, middleware, dependencies, and services: "
                        "a tree of spans, each with a name, a start, a "
                        "duration, and a parent. A log line is an event at "
                        "a point; a span is a bracket around a range. The "
                        "bracket is what answers 'where did the 400 "
                        "milliseconds go' when every individual line says "
                        "'fine'. Distributed tracing is that idea across "
                        "process boundaries: the request arrives at the "
                        "edge with context — a trace id naming the journey "
                        "and a span id naming the current hop — and every "
                        "service it touches records its span under the "
                        "same trace, typically propagated in a header "
                        "(the W3C traceparent standard). Assembled, the "
                        "spans rebuild the journey, however many services "
                        "it crossed."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-trace-real-mechanism",
                    text=(
                        "This repo already runs the seed of that idea, "
                        "for real: the request-id middleware ACCEPTS an "
                        "inbound id from a header, adopts it as the "
                        "request's identity, stamps it on the response, "
                        "and binds it into the log context — header-based "
                        "context propagation, exactly the shape "
                        "traceparent implements. What the repo does not "
                        "have is the tree: one flat id per request, no "
                        "parent-child relationships, no span timings "
                        "exported anywhere. The fan-out demo below builds "
                        "the missing half honestly, on real data: it "
                        "drives three REAL internal requests through the "
                        "live app at the ASGI boundary — the same "
                        "in-process technique the architecture tracer "
                        "pioneered — each carrying an inbound id DERIVED "
                        "from the panel request's own id: shared root "
                        "prefix, per-round suffix, one trace and one id "
                        "per child:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-trace-rounds-quote",
                    language="py",
                    caption="The fan-out's three rounds: one per outcome class this app produces.",
                    source="server/guide/domain/demos/obs_trace.py",
                    snippet=(
                        "    rounds_spec: list[tuple[str, str, str, str]] = [\n"
                        "        (\"ok\", \"GET /api/health\", \"/api/health\", \"\"),\n"
                        "        (\"not-found\", \"GET /api/posts/nope\", \"/api/posts/nope\", \"\"),\n"
                        "        (\n"
                        "            \"validation\",\n"
                        "            \"GET /api/posts?page=notanumber\",\n"
                        "            \"/api/posts\",\n"
                        "            \"page=notanumber\",\n"
                        "        ),\n"
                        "    ]"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="obs:trace",
                    title="The trace fan-out",
                    description=(
                        "GET /api/demo/obs/trace drives three REAL "
                        "internal requests through the running app — a "
                        "clean 200, the posts resource's 404, and FastAPI's "
                        "422 — each with an inbound request id derived "
                        "from this panel request's own id (the trace "
                        "root). The payload then correlates every round's "
                        "id in three places: the x-request-id header its "
                        "response echoed, the error envelope's requestId "
                        "for the failed rounds, and the log rows the round "
                        "actually produced — the access-log line plus the "
                        "failure line, one id tying them together. The "
                        "healthy round shows the good-news shape: its "
                        "lone access-log row with no failure row beside "
                        "it. Only the two ASGI-boundary beats carry "
                        "measured milliseconds; nothing is fabricated."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-trace-reading",
                    text=(
                        "The correlation read is one loop in the builder: "
                        "for each round, look the id up in the recent-"
                        "events ring — the same ring the viewer serves — "
                        "and the rows that come back are the round's "
                        "trace, reconstructed from what really happened. "
                        "The endpoint test pins the claim exactly, "
                        "envelope against header against every row:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-trace-test-quote",
                    language="py",
                    caption="The endpoint test pins correlation: one id, header, envelope, and every log row.",
                    source="server/tests/demo/test_obs_trace_endpoint.py",
                    snippet=(
                        "        # The envelope's requestId IS the round's inbound id.\n"
                        "        assert round_[\"envelopeRequestId\"] == round_[\"inboundRequestId\"]\n"
                        "        # Every log row the round produced carries the same id.\n"
                        "        assert round_[\"logEvents\"], f\"{label} round left no log rows\"\n"
                        "        assert all(e[\"requestId\"] == round_[\"inboundRequestId\"] for e in round_[\"logEvents\"])"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-trace-otel",
                    text=(
                        "Now OpenTelemetry itself, concept-first and "
                        "honest. OTel is a vendor-neutral standard plus "
                        "SDKs for exactly the mechanics you just watched, "
                        "generalized: automatic span creation around every "
                        "inbound request and every outbound HTTP/database "
                        "call, context propagated between services in "
                        "standard headers, and exporters shipping finished "
                        "spans to a backend (Jaeger, Tempo, a vendor) "
                        "where the tree is visualized. The lockfile fact "
                        "that makes this concrete: opentelemetry-api "
                        "ALREADY rides in this app's dependency graph — "
                        "fastapi itself depends on it — but the API "
                        "package alone records nothing; you would add the "
                        "SDK and an exporter:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-trace-lock-quote",
                    language="toml",
                    caption="The lock already carries opentelemetry-api — as fastapi's own transitive edge.",
                    source="server/uv.lock",
                    snippet=(
                        "[[package]]\n"
                        "name = \"fastapi\"\n"
                        "version = \"0.143.1\"\n"
                        "source = { registry = \"https://pypi.org/simple\" }\n"
                        "dependencies = [\n"
                        "    { name = \"annotated-doc\" },\n"
                        "    { name = \"opentelemetry-api\" },\n"
                        "    { name = \"pydantic\" },\n"
                        "    { name = \"starlette\" },\n"
                        "    { name = \"typing-extensions\" },\n"
                        "    { name = \"typing-inspection\" },\n"
                        "]"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-trace-recipe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# The recipe this repo would run (NOT a dependency today — honest recipe):\n"
                        "# 1. uv add opentelemetry-sdk opentelemetry-exporter-otlp \\\n"
                        "#      opentelemetry-instrumentation-fastapi\n"
                        "# 2. instrument the app at factory time; spans then flow for every request\n"
                        "#    (and traceparent headers propagate across your service calls).\n"
                        "# 3. run a collector/backend (Jaeger: docker run -p 16686:16686 jaegertracing/all-in-one)\n"
                        "#    and read the tree it assembles — the fan-out demo's shape, automatic."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-trace-coda",
                    text=(
                        "What the demo's derived ids preview against that "
                        "recipe: OTel's traceparent header carries ONE "
                        "trace id for the journey plus a NEW span id per "
                        "hop — the shared prefix and per-round suffix of "
                        "the fan-out are the same design in miniature, "
                        "which is the point of teaching the mechanism on "
                        "real data before naming the standard. The "
                        "transition cost is low precisely because the "
                        "correlation discipline already exists: every "
                        "failure already logs under an id, every envelope "
                        "already carries it back, and the access log "
                        "already attributes each request. Instrumentation "
                        "that arrives into a system with ids everywhere "
                        "is a drop-in; instrumentation that arrives into "
                        "anonymous logs is an archaeology project. Build "
                        "the id discipline first — this repo did — and "
                        "the standards slot in when the scale justifies "
                        "them."
                    ),
                ),
            ],
        ),
        # ── 8. Alerting ───────────────────────────────────────────────────
        Section(
            id="alerting",
            title="Alerting",
            blocks=[
                TextBlock(
                    kind="text",
                    id="obs-alerting-pitch",
                    text=(
                        "An alert is a page that costs a human's night. "
                        "Everything about alerting design follows from "
                        "taking that cost seriously: the question is never "
                        "'what could we be notified about' but 'what "
                        "should interrupt a human at 3am, and what should "
                        "that human then DO'. The industry's settled "
                        "answer is symptom-based alerting on service "
                        "level objectives: define what users experience "
                        "(availability, latency), measure it, and page "
                        "when the EXPERIENCE breaks — not when any "
                        "internal cause looks off. An SLO is a target "
                        "like '99.9% of requests succeed over 30 days'; "
                        "the error budget is the 0.1% you may spend "
                        "before paging. The framing flips the default "
                        "from 'tell me everything' to 'tell me when users "
                        "are hurt, with room to breathe'."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-alerting-fatigue",
                    text=(
                        "Alert fatigue is the failure mode that kills "
                        "on-call, and it deserves the bluntness: every "
                        "non-actionable page erodes trust, and a pager "
                        "nobody trusts is a pager nobody answers "
                        "accurately. A cause-based alert — 'CPU is 90%' — "
                        "pages when users feel nothing and stays silent "
                        "when they do; after a few of those, the alert "
                        "gets muted along with the one that mattered. The "
                        "discipline: page only on symptoms with a "
                        "runbook attached (what to do, in order, by "
                        "someone half-asleep), and let causes ride "
                        "dashboards and tickets where a calm human "
                        "triages them. If you cannot write the runbook, "
                        "you cannot write the alert."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-alerting-this-repo-framing",
                    text=(
                        "This repo's signals translate into concrete "
                        "alert candidates, each derivable from the "
                        "instruments you just met:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="obs-alerting-candidates",
                    ordered=False,
                    items=[
                        "Error rate — the access log's status field "
                        "aggregated by class; a 5xx rate over budget is "
                        "the canonical availability page.",
                        "Queue health — the jobs topic's two numbers; "
                        "depth growing while oldest age grows means "
                        "stalled workers, a page every queue operator "
                        "recognizes.",
                        "Dependency degradation — a burst of "
                        "service_unavailable envelopes or the "
                        "redis_playground_unavailable warning pattern "
                        "means a store the app expects is gone.",
                        "Silence — an access log that stops filling, or a "
                        "metrics target that stops being scrapeable, is "
                        "often the FIRST sign a process or pipeline died.",
                        "Unhandled exceptions — any unhandled_exception "
                        "event at all is worth a ticket; a cluster of "
                        "them is worth a page."
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="obs-alerting-coda",
                    text=(
                        "Notice the layering across those candidates: "
                        "metrics (rates over time) make the paging "
                        "decision, logs (correlated events) carry the "
                        "diagnosis, traces would carry the where. No "
                        "single instrument alerts well alone — counting "
                        "log lines at 3am is a poor man's metric with no "
                        "aggregation, and a metric with no logs behind it "
                        "pages you into a dark room. The division of "
                        "labor is the design: alert on metrics, diagnose "
                        "in logs, localize in traces, and keep every "
                        "layer correlated by the request id so the "
                        "3am-human can walk from the page to the cause "
                        "in two queries."
                    ),
                ),
            ],
        ),
        # ── 9. Process nets ───────────────────────────────────────────────
        Section(
            id="process-nets",
            title="Process nets",
            blocks=[
                TextBlock(
                    kind="text",
                    id="obs-nets-pitch",
                    text=(
                        "Signals without a process around them are just "
                        "noise with timestamps. The exception-handling "
                        "topic closed on process nets for FAILURES — the "
                        "safety nets that catch what code misses; "
                        "observability needs its own nets, the ones that "
                        "catch what a single dashboard misses. Four, and "
                        "the guide runs real instances of the first:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="obs-nets-pieces",
                    ordered=False,
                    items=[
                        "Verification drills — the errors explorer's "
                        "failure injection and this topic's fan-out are "
                        "practice runs: prove the signals fire BEFORE "
                        "production does it for you.",
                        "Dashboards — the queries you will need when "
                        "paged, built during calm hours; a dashboard "
                        "assembled during an incident is the incident "
                        "lasting longer.",
                        "Runbooks — the page's attached instructions; "
                        "every alert names its first three commands, "
                        "tested by someone who did not write them.",
                        "Postmortems — blameless written accounts of "
                        "incidents that feed back into alerts, dashboards, "
                        "and code; the net that makes the next one shorter."
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="obs-nets-watchmen",
                    text=(
                        "The last net is the reflexive one: watch the "
                        "watchmen. Observability itself fails — the log "
                        "shipper silently stops shipping, the metrics "
                        "target goes unscraped, the ring you are looking "
                        "at is stale — and it fails in the quietest "
                        "possible way, because everything looks fine when "
                        "nothing is being recorded. The defenses are "
                        "structural: heartbeats (the jobs worker's "
                        "heartbeat task exists for exactly this), "
                        "freshness checks on the data itself (when did "
                        "this stream last receive an event?), and "
                        "meta-monitoring that alerts on the monitoring "
                        "pipeline's own health. This repo's honest "
                        "boundary is worth restating: the ring is "
                        "process-local and in-memory, a teaching "
                        "instrument — the production answer is "
                        "aggregated, shipped, retained stdout, which is "
                        "precisely what the terminal companion's docker "
                        "logs stop shows you the seed of."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-nets-coda",
                    text=(
                        "Pull the whole topic into one sentence each "
                        "instrument can be held to: health checks tell "
                        "the machines what to do with your process; logs "
                        "tell the responding human what happened; metrics "
                        "tell the paging system when to wake them; traces "
                        "tell them where it went; and the process nets "
                        "make sure all of that survives contact with a "
                        "real incident. The observability checklist "
                        "topic near the end of the guide returns to audit "
                        "this list against the repo — the three "
                        "questions, answered on real signals, is the "
                        "whole standard."
                    ),
                ),
            ],
        ),
        # ── 10. Terminal companion ────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The observability stack from a shell: health, correlation, the viewer, the fan-out, real stdout.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="obs-terminal-intro",
                    text=(
                        "Six stops, every one on the running stack: the "
                        "liveness endpoint as-is, a 404 driven with a "
                        "chosen request id, that SAME id found in the "
                        "viewer's real log rows (correlation, proven), "
                        "the trace fan-out's three rounds, the real "
                        "rendered JSON lines from the server container's "
                        "stdout, and this topic's own detail through both "
                        "ports."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-terminal-health",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — liveness as-is: the process answers, no dependencies touched\n"
                        "curl -s -i localhost:8000/api/health"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-terminal-404",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — drive a failure with a CHOSEN id; note the header echo + envelope agreement\n"
                        "curl -s -i -H 'x-request-id: my-correlation-exercise' localhost:8000/api/posts/nope \\\n"
                        "  | grep -Ei 'x-request-id|\"requestId\"|\"code\"'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-terminal-viewer",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the viewer: find that same id on real log rows (correlation, proven)\n"
                        "curl -s localhost:8000/api/demo/obs/viewer | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "print(\"pipeline:\", \" -> \".join(p[\"processor\"] for p in panel[\"pipeline\"]))\n"
                        "print(\"level:\", panel[\"configuredLevel\"], \"| ring:\", panel[\"ringCapacity\"])\n"
                        "rows = [e for e in panel[\"events\"] if e[\"requestId\"] == \"my-correlation-exercise\"]\n"
                        "for e in rows:\n"
                        "    print(\" \", e[\"level\"], e[\"event\"],\n"
                        "          \" \".join(f[\"name\"] + \"=\" + f[\"value\"] for f in e[\"fields\"]))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-terminal-trace",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the trace fan-out: three real rounds, ids correlated 3 ways each\n"
                        "curl -s localhost:8000/api/demo/obs/trace | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "print(\"root:\", t[\"rootRequestId\"])\n"
                        "for r in t[\"rounds\"]:\n"
                        "    logs = \", \".join(e[\"event\"] + \"(\" + e[\"level\"] + \")\" for e in r[\"logEvents\"])\n"
                        "    print(\" \", r[\"label\"], r[\"status\"], \"| envelope:\", r[\"envelopeCode\"] or \"-\",\n"
                        "          \"| logs:\", logs)'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-terminal-stdout",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the REAL rendered lines: the server container's stdout stream\n"
                        "docker logs fastapi_developers_guide_server_dev --tail 6 2>&1 \\\n"
                        "  | grep -E 'http_request|app_error' | tail -4\n"
                        "# each line is one JSON object — the pipeline's actual output, unretouched"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="obs-terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — this topic's own detail: demos inline, companion last, both ports\n"
                        "curl -s localhost:8000/api/content/observability | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'\n"
                        "curl -s localhost:5174/api/content/observability \\\n"
                        "  | python3 -c 'import json,sys; print(\"proxy sections:\", len(json.load(sys.stdin)[\"sections\"]))'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="obs-terminal-coda",
                    text=(
                        "Stops 2 and 3 are the topic in miniature: you "
                        "chose an id, the failure carried it into the log "
                        "stream, and the viewer handed it back — the "
                        "exact walk a responding human does at 3am, minus "
                        "the pager. Stop 4 shows the fan-out version with "
                        "envelopes and log rows agreeing; stop 5 shows "
                        "the unretouched stdout every other view is a "
                        "lens over; stop 6 closes the loop the guide "
                        "always closes — the topic that taught "
                        "observability is itself observable, its demos "
                        "and companion served through the stack they "
                        "instrument."
                    ),
                ),
            ],
        ),
    ],
)
