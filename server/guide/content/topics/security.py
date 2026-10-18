"""Topic 25 — Security (defaults and review, not a feature).

The state-and-auth group closes by widening from authority to THREATS:
the threat-model habit that decides what to protect before any code is
written, the response headers every API owes whether or not anyone reads
them, the CORS policy that is one line of config and one classic
misconfiguration, the rate limiter that protects the endpoints no
credential guards, the injection family that parameterization kills, the
request-forgery pair (CSRF in, SSRF out), the secrets discipline this
repo already practices, the OWASP API Top 10 mapped onto everything the
last 24 topics built, and the PII engine that turns privacy promises
into mechanisms. Two demos INLINE: the security lab (headers observer +
CORS explorer + a genuinely throttled burner) in the headers section,
and the PII lab (classification, masking by role, export, erasure with
counts as proof) in the GDPR section.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="security",
    title="Security",
    subtitle=(
        "The threat-model habit, security headers on every response, CORS "
        "without the classic misconfig, a real rate limiter with Retry-After, "
        "the injection family, CSRF and SSRF, secrets discipline, the OWASP "
        "API Top 10 mapped to this repo, and PII handled as mechanisms — two "
        "live labs: the security lab and the PII lab."
    ),
    group="state-auth",
    order=25,
    sections=[
        # ── 1. The threat-model habit ──────────────────────────────────────
        Section(
            id="the-threat-model-habit",
            title="The threat-model habit",
            blocks=[
                TextBlock(
                    kind="text",
                    id="threat-model-pitch",
                    text=(
                        "Security is not a feature you add in Phase 13; it is a "
                        "set of DEFAULTS you start with and a REVIEW you keep "
                        "doing. The habit that makes that practical is the "
                        "threat model: before you write the code, answer three "
                        "questions in one sentence each — WHAT am I protecting "
                        "(credentials, customer records, the availability of "
                        "the service), FROM WHOM (outsiders with network "
                        "access, authenticated users overreaching, insiders, "
                        "the operator of the next service over), and WHAT "
                        "HAPPENS WHEN it fails (an outage, a leak, a forged "
                        "verdict). Everything in this topic is an answer to "
                        "some threat model; nothing in it makes sense as "
                        "ritual. A header you cannot attach a threat to is "
                        "cargo cult, and a threat you never mapped to a "
                        "defense is a postmortem waiting for its date."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="threat-model-stride-pitch",
                    text=(
                        "STRIDE is the classic checklist for the first "
                        "question — six categories of bad thing, each one "
                        "concrete enough to check code against. You do not "
                        "need the full methodology to profit from it; the "
                        "six words are enough to interrogate a design. Mapped "
                        "onto this guide, each category already has a layer "
                        "that answers it:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="threat-model-stride-map",
                    ordered=False,
                    items=[
                        "Spoofing — who are you, really: topic 23's passwords, "
                        "sessions, API keys, and signed tokens answer identity "
                        "claims before anything trusts them.",
                        "Tampering — did this change in transit: TLS carries "
                        "the bytes, and topic 14's webhooks HMAC-sign payloads "
                        "so a receiver can prove integrity end to end.",
                        "Repudiation — did it happen, who did it: request ids "
                        "on every envelope (topic 8) plus the audit trail "
                        "topics 16 and 17 write in the same transaction as the "
                        "change.",
                        "Information disclosure — who can see this: response "
                        "models that filter fields, PII masking by role (this "
                        "topic), and error messages that never echo internals.",
                        "Denial of service — can one caller exhaust everyone: "
                        "the rate limiter this topic builds, backpressure "
                        "(topic 38), and the degradation discipline topics 19 "
                        "and 20 practice.",
                        "Elevation of privilege — can a user become more than "
                        "their role: topic 24's deny-by-default engine, scope "
                        "narrowing that never widens, and ownership checks.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="threat-model-habit-cadence",
                    text=(
                        "The second half of the habit is CADENCE: security as "
                        "review, not milestone. The codebase carries the "
                        "lesson — the auth engines were built to be read "
                        "wrong on purpose (constant-time comparisons, decoy "
                        "hash runs so an unknown user costs the same as a "
                        "wrong password), and every one of those decisions "
                        "was a one-line answer to a named threat. The review "
                        "version costs minutes: when a change adds an "
                        "endpoint, ask which STRIDE category it touches; when "
                        "it adds a dependency, ask what it can reach; when it "
                        "adds a field to a response model, ask which tier of "
                        "data that field is. The rest of this topic is the "
                        "repertoire those reviews draw from — and the two "
                        "labs at its center run the defenses live against "
                        "the real stack."
                    ),
                ),
            ],
        ),
        # ── 2. Security headers ────────────────────────────────────────────
        Section(
            id="security-headers",
            title="Security headers",
            lead="This section carries the topic's first demo — the security lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="headers-pitch",
                    text=(
                        "Response headers are the cheapest security control "
                        "in existence: no logic, no latency, no dependencies "
                        "— just a few lines stamped on every response that "
                        "tell the BROWSER to enforce something on your "
                        "behalf. They matter precisely because an API's "
                        "responses travel through places you do not control: "
                        "corporate proxies that mislabel content, portals "
                        "that iframe anything, extensions that meddle. Each "
                        "header closes one of those doors, and the reason to "
                        "send them from MIDDLEWARE rather than per-route is "
                        "the reason middleware exists at all — the error "
                        "paths, the ones an attacker actually probes, must "
                        "carry the same protections as the happy path. A 404 "
                        "that skips nosniff is the response most likely to be "
                        "rendered by some intermediary."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="headers-table-pitch",
                    text=(
                        "This guide's table is deliberately short — four "
                        "headers on every response plus one that is "
                        "TLS-only. Each earns its line with a threat it "
                        "answers, stated where the suite can pin it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="headers-static-quote",
                    language="py",
                    caption="The every-response table: four headers, one CSP, zero exceptions.",
                    source="server/guide/presentation/middleware/security_headers.py",
                    snippet=(
                        "API_CSP: Final = \"default-src 'none'; frame-ancestors 'none'; base-uri 'none'\"\n"
                        "# …\n"
                        "_STATIC_HEADERS: Final[dict[str, str]] = {\n"
                        "    \"X-Content-Type-Options\": \"nosniff\",\n"
                        "    \"X-Frame-Options\": \"DENY\",\n"
                        "    \"Referrer-Policy\": \"no-referrer\",\n"
                        "    \"Content-Security-Policy\": API_CSP,\n"
                        "}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="headers-csp-pitch",
                    text=(
                        "The interesting one is Content-Security-Policy, and "
                        "the interesting decision is that this app ships TWO "
                        "of them. A JSON API loads nothing — no scripts, no "
                        "styles, no images — so its CSP is a refusal: "
                        "``default-src 'none'`` means even an injected script "
                        "tag finds no source it is allowed to load from. But "
                        "the DOCS pages (/docs, /redoc) legitimately load "
                        "Swagger UI and ReDoc from a CDN and run an inline "
                        "bootstrap, so a single global policy would have to "
                        "be loose enough for the docs everywhere — strictly "
                        "worse. The middleware is path-aware instead, and "
                        "the HSTS line is scheme-aware: Strict-Transport-"
                        "Security is sent only over https, because over "
                        "plain http (dev) it is ignored by browsers and "
                        "dishonest about the connection — production stamps "
                        "it at the TLS proxy, which is where TLS ends:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="headers-dispatch-quote",
                    language="py",
                    caption="Stamp every response; swap the CSP on docs paths; HSTS only over https.",
                    source="server/guide/presentation/middleware/security_headers.py",
                    snippet=(
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
                    id="headers-demo-pitch",
                    text=(
                        "Try it: the lab reads its OWN live response — the "
                        "header table it shows is the one the middleware "
                        "actually stamped on the fetch that rendered it, "
                        "with the why for each entry. Below that sit the two "
                        "other labs this topic builds: the CORS explorer "
                        "(pick an origin, see the real allow/block verdict "
                        "from the policy the app runs) and the rate-limit "
                        "burner — a public endpoint with a real budget you "
                        "can drain to watch the 429 arrive with Retry-After. "
                        "Everything the panel claims is checkable with curl "
                        "in the terminal companion."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="security:lab",
                    title="The security lab",
                    description=(
                        "GET /api/demo/security serves the lab panel: the "
                        "security-header table with the WHY for each entry "
                        "(served from the middleware's own constants, so the "
                        "docs cannot drift from the enforcement), the REAL "
                        "CORS policy (the exact origin list, methods, "
                        "headers, and credential mode the app runs, plus the "
                        "wildcard misconfig note), and the burner's "
                        "rate-limit policy (window, budget, keying). The "
                        "client renders the OBSERVED response headers beside "
                        "the documented ones — what the live response "
                        "actually carries. The burner (POST "
                        "/api/demo/security/rate-limit/burn) is genuinely "
                        "throttled: each hit returns the remaining budget as "
                        "x-ratelimit-remaining, and the hit that drains it "
                        "never reaches the handler — the dependency raises "
                        "the 429 envelope with Retry-After."
                    ),
                ),
            ],
        ),
        # ── 3. CORS ────────────────────────────────────────────────────────
        Section(
            id="cors",
            title="CORS",
            blocks=[
                TextBlock(
                    kind="text",
                    id="cors-same-origin-pitch",
                    text=(
                        "The browser's same-origin policy is the rule CORS "
                        "negotiates: by default, a page at origin A cannot "
                        "read a response from origin B (an origin is scheme "
                        "+ host + port, so localhost:5174 and localhost:8000 "
                        "are DIFFERENT origins — this guide's own client and "
                        "server). The policy protects users, not servers — "
                        "it stops evil.example's JavaScript from reading "
                        "responses your logged-in browser fetches for it. "
                        "CORS is the opt-out mechanism: the server declares, "
                        "in response headers, which origins may read what, "
                        "and the browser enforces the verdict. Note the "
                        "direction: curl and server-to-server callers ignore "
                        "CORS entirely — it is a browser-mediated contract, "
                        "which is why the preflight exists at all."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cors-simple-vs-preflight",
                    text=(
                        "Requests split into two kinds. SIMPLE requests "
                        "(GET, POST with the boring content types, a short "
                        "header list) are sent straight to the server with "
                        "an ``Origin`` header attached; the server answers "
                        "with ``Access-Control-Allow-Origin`` or without it, "
                        "and the browser decides whether the page may READ "
                        "the response — the request already happened either "
                        "way, which is why simple non-GET requests must be "
                        "safe or idempotent to tolerate. Everything else — a "
                        "DELETE, a JSON POST with an Authorization header — "
                        "triggers a PREFLIGHT: the browser first sends "
                        "OPTIONS with the intended method and headers, and "
                        "only a matching ``allow`` answer lets the real "
                        "request leave at all. That OPTIONS round is not "
                        "router noise; it is the browser refusing to even "
                        "deliver a request the server has not approved."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cors-config-pitch",
                    text=(
                        "Starlette's ``CORSMiddleware`` implements all of "
                        "it; what remains for you is the POLICY, and this "
                        "guide states its policy once, in the domain, where "
                        "the wiring and the demo panel both read it — an "
                        "explicit origin list beside credentials, never a "
                        "wildcard:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cors-policy-quote",
                    language="py",
                    caption="The policy: one explicit dev origin, credentials allowed beside it.",
                    source="server/guide/domain/security/cors.py",
                    snippet=(
                        "ALLOWED_ORIGINS: Final[tuple[str, ...]] = (\"http://localhost:5174\",)\n"
                        "# …\n"
                        "ALLOW_CREDENTIALS: Final[bool] = True"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cors-wiring-quote",
                    language="py",
                    caption="The wiring: middleware added outermost so error envelopes carry the verdict too.",
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
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cors-misconfig",
                    text=(
                        "The classic misconfig is ``allow_origins=[\"*\"]`` "
                        "with ``allow_credentials=True``: the spec forbids a "
                        "wildcard origin on a credentialed response, so "
                        "permissive stacks 'helpfully' answer by ECHOING "
                        "whatever origin asked — at which point any website "
                        "can make your logged-in user's browser send "
                        "cookie-bearing requests and read the responses. "
                        "The fix is the shape above: exact origins, listed. "
                        "The middleware ordering carries the same lesson — "
                        "CORS is added LAST so it sits OUTERMOST, wrapping "
                        "even the error handlers: a cross-origin client must "
                        "be able to READ the 429 this topic's limiter "
                        "raises, or your throttle is invisible to precisely "
                        "the callers it addresses. The lab's explorer and "
                        "the terminal companion prove both verdicts from "
                        "real response headers: the allowed origin gets "
                        "``access-control-allow-origin`` echoed, the "
                        "disallowed one gets NO origin verdict at all — "
                        "without which the browser refuses the read, whatever "
                        "other headers ride along — and a disallowed "
                        "preflight gets a 400 before any handler runs."
                    ),
                ),
            ],
        ),
        # ── 4. Rate limiting ───────────────────────────────────────────────
        Section(
            id="rate-limiting",
            title="Rate limiting",
            blocks=[
                TextBlock(
                    kind="text",
                    id="ratelimit-why",
                    text=(
                        "Endpoints that check no credential — logins, "
                        "password resets, health checks, this topic's burner "
                        "— are the endpoints anyone may hammer, and hammering "
                        "is cheap: a laptop can try thousands of passwords a "
                        "second or hold enough connections open to make your "
                        "database the bottleneck for everyone. Authentication "
                        "does not help (the caller has none to check), so "
                        "the brake has to be something else: a budget of "
                        "requests per caller per window, enforced before the "
                        "handler runs. That placement is the architecture "
                        "point — the limit is a DEPENDENCY in this guide "
                        "(topic 6 called it out as a cross-cutting concern "
                        "years of sections ago), so the handler body never "
                        "contains throttle logic and the exhausted caller "
                        "never reaches it."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ratelimit-algorithm-pitch",
                    text=(
                        "The algorithm here is a true SLIDING WINDOW: keep "
                        "the timestamps of the last hits per key, drop the "
                        "ones older than the window, and admit only while "
                        "fewer than the budget remain. Sliding beats fixed "
                        "buckets honestly — a fixed one-minute bucket lets "
                        "a caller burst twice (end of bucket one, start of "
                        "bucket two) without ever exceeding 'per minute'. "
                        "One rule in the engine is easy to get wrong and "
                        "pinned by test: a DENIED hit is not recorded, so "
                        "hammering past the limit does not extend your own "
                        "lockout. The engine is pure and takes its clock "
                        "injected, which is why the whole allow-allow-429-"
                        "slide-allow sequence is a unit test with integer "
                        "times, not a sleep:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="ratelimit-engine-quote",
                    language="py",
                    caption="The sliding-window decision: prune, then admit under budget — denials recorded nowhere.",
                    source="server/guide/domain/security/rate_limit.py",
                    snippet=(
                        "        moment = self._clock() if now is None else now\n"
                        "        hits = self._prune(key, moment)\n"
                        "        if len(hits) >= self._policy.budget:\n"
                        "            retry_after = hits[0] + self._policy.window_s - moment\n"
                        "            return self._verdict(allowed=False, remaining=0, retry_after_s=retry_after)\n"
                        "        hits.append(moment)\n"
                        "        return self._verdict(\n"
                        "            allowed=True, remaining=self._policy.budget - len(hits), retry_after_s=None\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ratelimit-429-pitch",
                    text=(
                        "The wire contract is where rate limiting becomes "
                        "API design: the exhaustion answer is the standard "
                        "error envelope as ``rate_limited`` (429) — same "
                        "shape, same request id — with one addition the "
                        "status code owes its callers: ``Retry-After``, in "
                        "seconds, rounded UP (a client told 'try in 2.1 "
                        "seconds' must not try in 2). The header rides "
                        "``AppError.headers`` through the ONE taxonomy, and "
                        "the envelope's details carry the same numbers as "
                        "structured fields for programs that prefer them. "
                        "On the success path the handler stamps "
                        "``x-ratelimit-remaining``, so honest clients can "
                        "slow down before they are told to:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="ratelimit-dependency-quote",
                    language="py",
                    caption="The 429 with its Retry-After — one taxonomy, one header the status owes.",
                    source="server/guide/presentation/dependencies/rate_limit.py",
                    snippet=(
                        "    retry_after_s = max(1, math.ceil(verdict.retry_after_s or 0))\n"
                        "    raise AppError(\n"
                        "        FailureKind.RATE_LIMITED,\n"
                        "# …\n"
                        "        headers={\"Retry-After\": str(retry_after_s)},\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ratelimit-production-notes",
                    text=(
                        "Two production notes the lab makes visible by what "
                        "it is not. KEYING: this limiter keys on client IP "
                        "+ route, which is honest for direct traffic and "
                        "WRONG behind a proxy — there every caller shares "
                        "the proxy's IP, so a real deployment keys on the "
                        "forwarded-for header it trusts (and the demo "
                        "teaches the caveat rather than pretending it away). "
                        "STATE: the window lives in one process's memory, so "
                        "N uvicorn workers hold N independent budgets and "
                        "the real budget multiplies — the distributed form "
                        "is a Redis counter with expiry (topic 20's client, "
                        "topic 39's shedding), reached when the single-"
                        "process version stops being the truth."
                    ),
                ),
            ],
        ),
        # ── 5. The injection family ────────────────────────────────────────
        Section(
            id="the-injection-family",
            title="The injection family",
            blocks=[
                TextBlock(
                    kind="text",
                    id="injection-family-pitch",
                    text=(
                        "Injection is one bug wearing four costumes: data "
                        "that crosses into a place where it is suddenly "
                        "INTERPRETED as code — SQL into a query, a filename "
                        "into a path, an argument into a shell, a variable "
                        "into a template. The family cure is identical in "
                        "every costume and worth saying once, loudly: keep "
                        "data as data. Bind it as a parameter, resolve it "
                        "against an allow-list, pass it as a list element — "
                        "never splice it into a string that something "
                        "downstream will parse. Topic 17 already taught the "
                        "SQL half with a live demo (``db:sql-safety`` ran "
                        "the classic ``' OR '1'='1`` payload as a PARAMETER "
                        "and watched the database treat it as the literal "
                        "string it is); this section points back at that "
                        "proof, names the repo's pattern, and walks the "
                        "other three costumes."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="injection-sql-quote",
                    language="py",
                    caption="The repo's standing pattern: the value rides as a bound parameter, never into the SQL text.",
                    source="server/guide/data/db/repository.py",
                    snippet=(
                        "    async def filter_posts_by_title(self, filter_value: str) -> FilterProbe:\n"
                        "        \"\"\"Run the parameterized title filter and return what it matched.\"\"\"\n"
                        "        with _map_db_failures(\"filter_posts_by_title\"):\n"
                        "            pattern = f\"%{filter_value}%\"\n"
                        "            async with self._engine.connect() as connection:\n"
                        "                result = await connection.execute(sa.text(TITLE_FILTER_SQL), {\"pattern\": pattern})"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="injection-orm-note",
                    text=(
                        "Notice what the pattern makes impossible: the SQL "
                        "text is a constant, the value is a dictionary, and "
                        "the driver quarantines the two — there is no code "
                        "path from the user's string into the query's "
                        "grammar. The ORM half (topic 18) gets the same "
                        "guarantee for free because SQLAlchemy Core "
                        "expressions ARE bound parameters, and the one "
                        "place this repo builds SQL from parts — the "
                        "exhibit selector switching between three constant "
                        "query strings — chooses from a closed list, which "
                        "is the other half of the discipline: when text "
                        "must vary, vary it over constants YOU wrote, never "
                        "over input."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="injection-command-path-template",
                    text=(
                        "The other three costumes, each with its defensive "
                        "pattern — none has a repo counterpart yet (this "
                        "API shells out to nothing, serves no files until "
                        "topic 26, and renders no server-side templates), "
                        "so the patterns are stated here and land when "
                        "their topics do. COMMAND injection: never "
                        "``shell=True`` with interpolated strings; pass the "
                        "command as a LIST (``[\"tar\", \"-c\", user_name]``) "
                        "so the kernel receives argv, not a sentence to "
                        "parse — and ask first whether you need a shell at "
                        "all, because you almost never do. PATH TRAVERSAL "
                        "(``../../etc/passwd`` as a filename): never join "
                        "user input into a filesystem path; if you must, "
                        "``resolve()`` the result and verify it remains "
                        "inside the intended root — and topic 26 implements "
                        "exactly that check when uploads arrive. TEMPLATE "
                        "injection: render templates with AUTOESCAPE on and "
                        "pass user data as values, never as template source "
                        "— a JSON API like this one skips the costume "
                        "entirely, which is itself a decision worth knowing "
                        "you made."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="injection-review-habit",
                    text=(
                        "The review habit for the whole family is one "
                        "grep-shaped question at every boundary: WHERE does "
                        "untrusted text become part of something executed, "
                        "opened, or parsed? f-strings near SQL or shell "
                        "calls, ``+`` near paths, ``|safe`` in templates — "
                        "each is a place data stopped being data. The "
                        "defense is boring on purpose: parameterization is "
                        "not clever, it is just always right, which is why "
                        "it survives code review at 2 a.m. when clever "
                        "escaping functions do not."
                    ),
                ),
            ],
        ),
        # ── 6. CSRF and SSRF ───────────────────────────────────────────────
        Section(
            id="csrf-and-ssrf",
            title="CSRF and SSRF",
            blocks=[
                TextBlock(
                    kind="text",
                    id="csrf-pitch",
                    text=(
                        "CSRF is the browser's helpfulness weaponized "
                        "against your user: a page at evil.example can make "
                        "the browser send a request to your API — form posts "
                        "cross-origin without CORS permission, image tags, "
                        "fetches that fire and whose responses stay unread — "
                        "and if the browser attaches your session cookie, "
                        "the request arrives AUTHENTICATED as the victim. "
                        "The attacker never reads the response (same-origin "
                        "policy still holds); they only need the side "
                        "effect. That asymmetry dictates the defenses: "
                        "state-changing requests must be non-GET (topic 11's "
                        "method discipline — a GET must never mutate), and "
                        "the cookie must not ride along on cross-site "
                        "requests."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="csrf-samesite-pitch",
                    text=(
                        "The second half is one cookie flag, and topic 23 "
                        "set it on every session cookie this guide issues — "
                        "``SameSite=Lax`` lets the cookie ride top-level "
                        "navigations (clicking a link to the site works) "
                        "but withholds it from cross-site POSTs and "
                        "subresource fetches, which is exactly the shape "
                        "CSRF needs. ``HttpOnly`` sits beside it so page "
                        "JavaScript cannot read the value for an XSS to "
                        "exfiltrate:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="csrf-cookie-quote",
                    language="py",
                    caption="Topic 23's session cookie: HttpOnly, SameSite=Lax — CSRF's carrier closed.",
                    source="server/guide/domain/auth/session_service.py",
                    snippet=(
                        "        cookie = CookieInstruction(\n"
                        "            name=SESSION_COOKIE_NAME,\n"
                        "            value=sealed,\n"
                        "            max_age_seconds=SESSION_MAX_AGE_SECONDS,\n"
                        "            path=SESSION_COOKIE_PATH,\n"
                        "            httponly=True,\n"
                        "            samesite=\"lax\",\n"
                        "            secure=False,\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="csrf-secure-note",
                    text=(
                        "``secure=False`` is the dev-honesty flag: this "
                        "stack runs plain http, and a Secure cookie over "
                        "http would simply never come back; production "
                        "flips it behind TLS. The Bearer-token callers "
                        "(topic 23's other half) are CSRF-immune by "
                        "construction — the browser never attaches the "
                        "credential, the attacker's page cannot read "
                        "localStorage to attach it themselves, so a forged "
                        "cross-site request arrives credential-less and "
                        "dies at the 401. Cookie sessions pay for their "
                        "convenience with this entire section; that trade "
                        "is topic 23's deciding table, restated as a threat "
                        "here."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ssrf-pitch",
                    text=(
                        "SSRF is CSRF's outbound twin: your SERVER tricked "
                        "into making a request the attacker chose — the "
                        "URL-fetching feature ('import from this feed URL', "
                        "'validate this webhook target') handed "
                        "``http://169.254.169.254/latest/meta-data`` (the "
                        "cloud metadata endpoint that mints credentials) or "
                        "``http://localhost:6379/`` (this stack's Redis, "
                        "which has no business seeing your HTTP server's "
                        "requests). The threat model differs from CSRF in "
                        "direction — the caller is your own user, the "
                        "victim is your network's interior — and so do the "
                        "defenses, all of them about what the fetcher is "
                        "allowed to reach:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="ssrf-defenses",
                    ordered=False,
                    items=[
                        "Allow-list, not deny-list — resolve the host "
                        "against domains you explicitly permit (your "
                        "providers), because interior addresses have too "
                        "many spellings to deny one by one.",
                        "Pin the scheme — accept https only; http, file, "
                        "gopher, and friends are how interior services and "
                        "local files get probed.",
                        "No redirects — follow none, or re-validate each "
                        "hop; the allow-list checked example.com but the "
                        "redirect answers from 169.254.169.254.",
                        "Resolve, then connect — resolve DNS yourself and "
                        "connect to the IP you validated, or the name "
                        "answers differently the second time (DNS rebinding).",
                        "Cap the response — timeouts and size limits, so "
                        "the fetcher cannot be turned into a bandwidth or "
                        "memory proxy.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="ssrf-repo-note",
                    text=(
                        "This repo makes zero outbound HTTP calls today — "
                        "topic 14's webhook delivery SIMULATOR signs and "
                        "schedules but never dials out — so the list above "
                        "is the contract any future outbound feature "
                        "(topic 42's third-party integrations) inherits on "
                        "arrival. The honest way to hold that contract in "
                        "review: a PR that adds an outbound URL fetch "
                        "without an allow-list beside it is incomplete by "
                        "convention, the same way a PR adding an endpoint "
                        "without a response model is."
                    ),
                ),
            ],
        ),
        # ── 7. Secrets ─────────────────────────────────────────────────────
        Section(
            id="secrets",
            title="Secrets",
            blocks=[
                TextBlock(
                    kind="text",
                    id="secrets-pitch",
                    text=(
                        "A secret is any value whose leak changes who can "
                        "do what: signing keys, database URLs with "
                        "credentials, API keys you hold for other services. "
                        "The twelve-factor rule this repo runs on (topic 36 "
                        "teaches the full doctrine) is that secrets live in "
                        "the ENVIRONMENT, never in code — and pydantic-"
                        "settings is the discipline's mechanism: one typed "
                        "config, every field an env var, the schema visible "
                        "where reviewers read it. The two signing secrets "
                        "topic 23 added are the pattern on display — dev-"
                        "safe defaults so the stack boots anywhere, "
                        "production overrides by env, the override "
                        "obligation written where the default lives:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="secrets-config-quote",
                    language="py",
                    caption="AppConfig's secret pair: dev defaults that boot anywhere, prod overrides by env, on record.",
                    source="server/guide/core/config.py",
                    snippet=(
                        "    # The two signing secrets (topic 23): dev-only defaults let the stack boot\n"
                        "    # anywhere with zero setup, and NOTHING behind them is secret in dev — but\n"
                        "    # production MUST override both via FDG_JWT_SECRET / FDG_SESSION_SECRET\n"
                        "    # (distinct, high-entropy values); the validator below makes a default\n"
                        "    # secret in a non-dev env a startup failure instead of a quiet liability.\n"
                        "    jwt_secret: str = \"dev-only-jwt-secret-override-me-32+chars\"\n"
                        "    session_secret: str = \"dev-only-session-secret-override-me-32+chars\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="secrets-never-pitch",
                    text=(
                        "Storage is half the discipline; PROPAGATION is the "
                        "other half, and it is where secrets actually leak — "
                        "not from git, but from the four places tired code "
                        "copies them to. The never-list, enforced here by "
                        "review and worth pinning as its own checklist:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="secrets-never-list",
                    ordered=False,
                    items=[
                        "Logs — never log tokens, keys, cookie values, or "
                        "Authorization headers; this guide logs usernames "
                        "and request ids, and topic 23's engines log "
                        "outcomes, never material.",
                        "Error responses — the taxonomy's messages are "
                        "client-safe by construction; a stack trace or a "
                        "config dump in a 500 hands internals to whoever "
                        "provoked it.",
                        "Client payloads — credentials flow IN, never out: "
                        "the API-key demo returns the key exactly once at "
                        "creation, then only its prefix forever after.",
                        "Git — no .env in history, no secrets in fixtures; "
                        "dev defaults are the only literals allowed, and "
                        "they are labeled as fake on their own line.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="secrets-rotation-note",
                    text=(
                        "Rotation is the property that makes a secret "
                        "scheme survivable: a leaked secret you cannot "
                        "rotate is a permanent incident. The design "
                        "questions are mechanical — where does the new "
                        "value take effect (env in, process restart, no "
                        "code), what still trusts the old one (topic 23's "
                        "refresh families die on reuse detection; API keys "
                        "revocable by name), and who can read the store "
                        "(topic 36's 'secrets beyond .env' — the vault "
                        "question deployments answer). None of that needs "
                        "heroics; all of it needs to have been DECIDED "
                        "before the leak, which is the threat-model habit "
                        "from section one, applied to your own credentials."
                    ),
                ),
            ],
        ),
        # ── 8. OWASP API Security Top 10 ───────────────────────────────────
        Section(
            id="owasp-api-top-ten",
            title="OWASP API Security Top 10",
            blocks=[
                TextBlock(
                    kind="text",
                    id="owasp-pitch",
                    text=(
                        "The OWASP API Security Top 10 is the field's "
                        "checklist of how real APIs actually get hurt — not "
                        "theoretical bugs but the incident-report census. "
                        "Its value is as a REVIEW lens: read your design "
                        "against the ten and see which you have answered "
                        "and which you have merely not hit yet. Read "
                        "against this guide, every entry has a layer that "
                        "answers it — most of them in the state-and-auth "
                        "group you just finished — which is the point of "
                        "arranging a curriculum as a runnable app. The "
                        "first five sit on object-level boundaries and "
                        "identity:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="owasp-one-to-five",
                    ordered=True,
                    items=[
                        "API1 BOLA — object-level authorization: the "
                        "/posts/{id} edit is guarded by ownership-or-role "
                        "(topic 24), and the guard fetches the object so "
                        "the verdict is about THIS post.",
                        "API2 Broken authentication — topic 23: argon2 "
                        "passwords, sealed sessions, hashed API keys, signed "
                        "JWTs, and uniform-failure logins that leak nothing.",
                        "API3 Property-level authorization — response "
                        "models filter fields (topic 9's revision example) "
                        "and PII masking by role (this topic) shape what "
                        "each caller's payload may contain.",
                        "API4 Unrestricted resource consumption — the "
                        "sliding-window limiter above, pagination on "
                        "collection reads (topic 11), and topic 39's "
                        "shedding when limits are not enough.",
                        "API5 Function-level authorization — topic 24's "
                        "require_permission guards declare the action on "
                        "the route; moderation is admin-only by dependency, "
                        "not by an if-statement someone might forget.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="owasp-six-to-ten-pitch",
                    text=(
                        "The second five sit on flows, configuration, and "
                        "the boundaries of your own infrastructure — "
                        "several of them are answered by habits rather than "
                        "modules, which is exactly why they need naming:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="owasp-six-to-ten",
                    ordered=True,
                    items=[
                        "API6 Sensitive business flows — the rate limiter "
                        "again, aimed at automation: a checkout or "
                        "password-reset endpoint abused at machine speed is "
                        "hurt without a single 'vulnerability' in it.",
                        "API7 SSRF — the outbound defenses of section six: "
                        "allow-lists, pinned schemes, no redirects; no "
                        "outbound fetcher exists yet, and the contract is "
                        "waiting for the first one.",
                        "API8 Security misconfiguration — this topic's "
                        "headers and CORS plus topic 36's environment "
                        "discipline; misconfig is a defaults problem, and "
                        "defaults are code.",
                        "API9 Improper inventory — the OpenAPI surface "
                        "(topic 12) is the machine-readable inventory, and "
                        "drift tests keep it equal to the routes that "
                        "actually exist.",
                        "API10 Unsafe consumption of APIs — trust inbound "
                        "webhook payloads only past an HMAC (topic 14) and "
                        "treat third-party responses as hostile input "
                        "(topic 42): your client-side validations apply to "
                        "their data too.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="owasp-coda",
                    text=(
                        "Two honest caveats about checklists. They census "
                        "yesterday's incidents — your novel feature may "
                        "invent API11 — so the STRIDE habit from section "
                        "one is the generative tool and the Top 10 is the "
                        "empirical sanity check. And several entries "
                        "(BOLA above all) are not bugs a scanner finds: "
                        "they are DESIGNS that forgot a question. No "
                        "dependency fixes 'may this user touch this "
                        "object'; only the guard you wrote does — which is "
                        "why topic 24 made the guard the route's "
                        "declaration and this topic keeps pointing back."
                    ),
                ),
            ],
        ),
        # ── 9. PII and GDPR ────────────────────────────────────────────────
        Section(
            id="pii-and-gdpr",
            title="PII and GDPR",
            lead="This section carries the topic's second demo — the PII lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="pii-pitch",
                    text=(
                        "Personal data changes the threat model: the asset "
                        "is someone's identity, the adversary may be nobody "
                        "at all (a leak needs no attacker — an over-broad "
                        "response IS the incident), and the law joins the "
                        "review. The engineering translation is three "
                        "mechanisms, and they compose: CLASSIFY fields so "
                        "policy can be written once instead of per-endpoint "
                        "(what category is this, how sensitive, does an "
                        "honest partial form exist); MASK on output by the "
                        "CALLER'S ROLE, so the same record renders "
                        "differently for support than for the person "
                        "themselves; and MINIMIZE + ERASE so the data you "
                        "never needed is never there to leak and the data "
                        "you must forget provably goes away. GDPR's named "
                        "rights are the requirements list — access and "
                        "portability (export the subject's data), erasure "
                        "(delete it), minimization (collect the least) — "
                        "and each maps to one mechanism."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pii-classification-pitch",
                    text=(
                        "Classification lives in a rule table — pure data, "
                        "reviewable as data, exactly like topic 24's grant "
                        "table. Every field of the lab's customer record "
                        "gets a category, a sensitivity tier, and a "
                        "rationale; the tier decides whether masking "
                        "applies at all (public and internal fields pass "
                        "through — masking a country code is theater), and "
                        "the partial rule decides what survives at the "
                        "middle level: a card keeps its last four, an "
                        "email its domain, a national id NOTHING (some "
                        "fields have no honest partial form). The role "
                        "mapping is deliberately tiny — earning raw values "
                        "is a grant, not a default:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pii-mask-level-quote",
                    language="py",
                    caption="Roles to mask levels: admin sees raw, editor the residue, everyone else fails closed to full.",
                    source="server/guide/domain/security/pii.py",
                    snippet=(
                        "MASK_LEVEL_BY_ROLE: Final[dict[str, MaskLevel]] = {\n"
                        "    \"admin\": \"none\",\n"
                        "    \"editor\": \"partial\",\n"
                        "}\n"
                        "# …\n"
                        "    granted: MaskLevel = \"full\"\n"
                        "    for role in roles:\n"
                        "        level = MASK_LEVEL_BY_ROLE.get(role, \"full\")\n"
                        "        if order.index(level) > order.index(granted):\n"
                        "            granted = level\n"
                        "    return granted"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pii-erasure-pitch",
                    text=(
                        "Erasure is where implementations embarrass "
                        "themselves, because 'deleted' must mean "
                        "UNFINDABLE: a soft-delete flag that one forgetful "
                        "query skips is a record you still hold, and a "
                        "tombstone row holding the fields it promised to "
                        "forget is worse than the bug it patched. The "
                        "lab's store does the honest thing — a hard "
                        "delete — and answers with COUNTS, because "
                        "'erased' is a claim and '3 records → 2 records' "
                        "is a fact. Note what else the proof buys: the "
                        "next read is the standard 404 envelope, and the "
                        "masked-view pipeline never had a raw cache to "
                        "invalidate:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pii-erase-quote",
                    language="py",
                    caption="Right-to-erasure: hard delete, no tombstone — the store forgets for real.",
                    source="server/guide/domain/security/records.py",
                    snippet=(
                        "    def erase(self, customer_id: str) -> bool:\n"
                        "        \"\"\"Right-to-erasure: the record is GONE, or False if already absent.\n"
                        "\n"
                        "        A hard delete by design — a tombstone row holding the PII it\n"
                        "        promised to forget is the classic erasure bug, so the store does\n"
                        "        not keep one.\n"
                        "        \"\"\"\n"
                        "        return self._records.pop(customer_id, None) is not None"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pii-demo-pitch",
                    text=(
                        "Try it: the lab seeds three synthetic customers "
                        "(no real person's data — the first rule of demo "
                        "PII) and serves the full classification table "
                        "with every field's rationale. View a subject "
                        "anonymously and every sensitive field is masked; "
                        "mint alan (a viewer) and nothing changes — his "
                        "role earns nothing here; mint ada (the admin) and "
                        "the raw record appears, because admin is the "
                        "grant that earns it. Export and erase are "
                        "admin-gated for real — the 403 carries the reason "
                        "— and after an erasure the subject's next read is "
                        "the 404 envelope, with the before/after counts in "
                        "the proof. Reset reseeds the round."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="security:pii",
                    title="The PII lab",
                    description=(
                        "GET /api/demo/security/pii serves the panel: the "
                        "seeded subjects, the full field-classification "
                        "table (category, tier, partial rules, rationale), "
                        "the role→mask-level map over topic 24's own "
                        "roles, and the endpoints. GET "
                        "/api/demo/security/pii/subjects/{id} renders one "
                        "subject AS THE CALLER SEES IT — anonymous and "
                        "viewer at full mask, editor at partial, admin "
                        "raw; present an invalid credential and the "
                        "standard 401 answers instead. POST …/export and "
                        "POST …/erase are genuinely admin-gated (401 "
                        "without credentials, 403 with reasons otherwise): "
                        "export returns the RAW record plus its "
                        "classification (data portability), erase returns "
                        "the before/after counts and leaves the next read "
                        "a 404. POST /api/demo/security/pii/reset reseeds "
                        "the demo records."
                    ),
                ),
            ],
        ),
        # ── 10. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole topic, from a shell — real headers, real verdicts, a real 429.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Six stops: the security headers on a 200 and on a "
                        "404 (the error path is the one that matters), the "
                        "CORS verdicts — allowed origin, blocked origin, "
                        "and a disallowed preflight rejected before any "
                        "handler runs — the rate-limit budget drained to "
                        "the 429 with Retry-After, the PII masking ladder "
                        "from anonymous to admin, the admin-gated export "
                        "and the refused non-admin export, and the "
                        "erasure round with counts as proof. The stack is "
                        "up; every command answers from the real "
                        "substrate this topic built."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-headers",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the defensive headers, on a 200 and on the 404 an attacker probes\n"
                        "curl -sD - -o /dev/null localhost:8000/api/health | grep -iE 'x-content-type|x-frame|referrer|content-security'\n"
                        "curl -sD - -o /dev/null localhost:8000/api/nope | grep -iE 'HTTP/|x-content-type|x-frame'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-cors",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — CORS: the allowed origin, the blocked one, and a refused preflight\n"
                        "curl -sD - -o /dev/null -H 'Origin: http://localhost:5174' localhost:8000/api/health \\\n"
                        "  | grep -i access-control\n"
                        "curl -sD - -o /dev/null -H 'Origin: http://evil.example' localhost:8000/api/health \\\n"
                        "  | grep -ci access-control-allow-origin   # 0 — no origin verdict, no reading\n"
                        "curl -s -X OPTIONS -D - -o /dev/null \\\n"
                        "  -H 'Origin: http://evil.example' -H 'Access-Control-Request-Method: POST' \\\n"
                        "  localhost:8000/api/demo/security/rate-limit/burn | head -1"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-burn",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — burn the budget: five allowed, the sixth is the 429 with Retry-After\n"
                        "for i in 1 2 3 4 5 6; do\n"
                        "  curl -s -o /dev/null -w \"hit $i: %{http_code}  remaining-header=%header{x-ratelimit-remaining}\\n\" \\\n"
                        "    -X POST localhost:8000/api/demo/security/rate-limit/burn\n"
                        "done\n"
                        "curl -s -D - -X POST localhost:8000/api/demo/security/rate-limit/burn | grep -iE 'HTTP/|retry-after'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-pii-masking",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the masking ladder: anonymous, viewer, admin — same record, three views\n"
                        "SUBJECT=cust-2f9a41\n"
                        "curl -s localhost:8000/api/demo/security/pii/subjects/$SUBJECT \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"anonymous:\", [f[\"value\"] for f in b[\"fields\"] if f[\"field\"]==\"email\"])'\n"
                        "ALAN=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"username\":\"alan\",\"scopes\":[\"*\"]}' localhost:8000/api/demo/auth/jwt/mint \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"token\"])')\n"
                        "curl -s -H \"Authorization: Bearer $ALAN\" localhost:8000/api/demo/security/pii/subjects/$SUBJECT \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"viewer:  \", b[\"maskLevel\"], [f[\"value\"] for f in b[\"fields\"] if f[\"field\"]==\"email\"])'\n"
                        "ADA=$(curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"username\":\"ada\",\"scopes\":[\"*\"]}' localhost:8000/api/demo/auth/jwt/mint \\\n"
                        "  | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"token\"])')\n"
                        "curl -s -H \"Authorization: Bearer $ADA\" localhost:8000/api/demo/security/pii/subjects/$SUBJECT \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"admin:   \", b[\"maskLevel\"], [f[\"value\"] for f in b[\"fields\"] if f[\"field\"]==\"email\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-pii-export-erase",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — export is admin-gated for real; then the erasure round, counts as proof\n"
                        "curl -s -o /dev/null -w 'alan exports: %{http_code}\\n' \\\n"
                        "  -H \"Authorization: Bearer $ALAN\" -X POST localhost:8000/api/demo/security/pii/subjects/$SUBJECT/export\n"
                        "curl -s -H \"Authorization: Bearer $ADA\" -X POST localhost:8000/api/demo/security/pii/subjects/$SUBJECT/export \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"ada exports:\", b[\"record\"][\"email\"])'\n"
                        "curl -s -H \"Authorization: Bearer $ADA\" -X POST localhost:8000/api/demo/security/pii/subjects/$SUBJECT/erase \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"erased:\", b[\"recordsBefore\"], \"→\", b[\"recordsAfter\"])'\n"
                        "curl -s -o /dev/null -w 'after erase: %{http_code}\\n' \\\n"
                        "  localhost:8000/api/demo/security/pii/subjects/$SUBJECT\n"
                        "curl -s -X POST localhost:8000/api/demo/security/pii/reset \\\n"
                        "  | python3 -c 'import json,sys; print(\"reset:\", json.load(sys.stdin)[\"detail\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-panel",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — the lab panel: the header table, the CORS policy, the throttle policy\n"
                        "curl -s localhost:8000/api/demo/security \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); \\\n"
                        "print(\"headers:\", [h[\"header\"] for h in b[\"headers\"]]); \\\n"
                        "print(\"cors origins:\", b[\"cors\"][\"allowedOrigins\"]); \\\n"
                        "print(\"budget:\", b[\"rateLimit\"][\"budget\"], \"per\", b[\"rateLimit\"][\"windowSeconds\"], \"s\")'\n"
                        "curl -s localhost:8000/api/content/security | python3 -c '\n"
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
                        "Stops 1–3 watch the three defaults do their jobs on "
                        "the wire: headers on the error path, the CORS "
                        "verdicts both ways, a real 429 that tells the "
                        "caller when to come back. Stops 4–5 walk the PII "
                        "ladder — the same record through three pairs of "
                        "eyes, the export only the admin can pull, and an "
                        "erasure that ends in a 404 with the counts in "
                        "hand. That closes the state-and-auth group, and "
                        "with it the book's core: identity (23), authority "
                        "(24), and now posture (25) — the threat model, "
                        "the defaults, and the review habit that keeps "
                        "both honest. Phase 8 moves outward: files, "
                        "languages, realtime, and jobs."
                    ),
                ),
            ],
        ),
    ],
)
