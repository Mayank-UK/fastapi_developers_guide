"""Topic 42 — Third-party services: integrate or build, then live with it.

The capstone of dependencies. Every topic before this one built things
or wired the stores this repo owns; this one is about everything the
app uses that it did NOT build — the packages in the manifest, the
backing services on the compose network, the machine-to-machine
credentials, and the vendor-shaped problems (email, payments, object
storage) every real application eventually faces. Everything quoted
here is this repository's real third-party surface: the manifest read
as a decision record, the optional-service timeout discipline, the
webhook HMAC signer/verifier, the in-repo OAuth2 provider, the GHCR
image rails and the shared caddy edge from the deploy pipeline, the
fail-fast secret validator and its compose rails. The vendor surfaces
this repo deliberately does NOT run — aiosmtplib, Stripe, cloud-storage
SDKs — are taught concept-first with sourcing-exempt recipes, never
fabricated as live integrations (the tests pin that honesty). The demo
is thirdparty:hub, INLINE in the integrating-vs-building section: four
inventories derived on the very request that serves them.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="third-party",
    title="Third-party services",
    subtitle=(
        "Integrating versus building — the decision this repo made for "
        "every piece it did not write, walked live over the real manifest "
        "(what was bought and why: the GraphQL engine, the password hasher, "
        "the signing formats, the queue, the drivers) beside what was "
        "deliberately built anyway (the circuit breaker, the webhook HMAC, "
        "the OAuth2 provider) · email over aiosmtplib taught concept-first "
        "with the timeout discipline it must copy · the email-as-a-job seam "
        "recapped, not re-taught · Stripe mapped onto the two mechanisms "
        "this repo already owns (signature verification, idempotent "
        "consumption) · cloud storage behind the FileStore port · and the "
        "keys, quotas, and blast radius every integration brings, analyzed "
        "over this repo's real secret surface — named, never shown."
    ),
    group="capstones",
    order=42,
    sections=[
        # ── 1. integrating vs building ────────────────────────────────────
        Section(
            id="integrating-vs-building",
            title="Integrating versus building",
            lead="This section carries the topic's demo — the third-party hub.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="tp-ivb-pitch",
                    text=(
                        "Third-party means code you did not write, running "
                        "on a schedule you do not control: a package pinned "
                        "in your manifest, a service on someone else's "
                        "network, an image in someone else's registry. Every "
                        "feature beyond your core domain eventually arrives "
                        "as the same decision — build it, or integrate it — "
                        "and the question is never whether you CAN build it "
                        "(you can build anything given enough quarters) but "
                        "which side of the line the piece belongs on. Build "
                        "and you own the edge cases forever, but the "
                        "behavior is exactly yours; integrate and the edge "
                        "cases are someone else's day job, but you inherit "
                        "their API shape, their release cadence, their "
                        "outages, and their invoice. This repo — a teaching "
                        "guide that also runs as a real stack — made that "
                        "decision for every piece it uses, and the decisions "
                        "are all on the record, which makes them teachable."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-ivb-axes-pitch",
                    text=(
                        "Six axes decide most integrate-versus-build "
                        "questions, and the honest version of the decision "
                        "scores each one rather than gesturing at all of "
                        "them:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="tp-ivb-axes",
                    ordered=False,
                    items=[
                        "Build cost — the true weeks to write, debug, and "
                        "harden the piece, counted against the day its edge "
                        "cases arrive: timezones in dates, slow loris on "
                        "sockets, greylisting on email.",
                        "Integration cost — the adapter you must write "
                        "anyway, the config surface, the version pins, the "
                        "upgrade treadmill: integrating is never zero "
                        "engineering, it is different engineering.",
                        "Blast radius — what a defect in the piece can take "
                        "down when it misbehaves, and whether the failure "
                        "mode is loud (an exception) or silent (wrong "
                        "answers with a 200).",
                        "Operational ownership — who gets paged when it "
                        "breaks: you at 3am for your code, a vendor's status "
                        "page for theirs; owning the pager is a cost the "
                        "invoice never shows.",
                        "Reversibility — how expensive the swap-out is if "
                        "the choice proves wrong: a port in front of the "
                        "decision is cheap to reverse, a scattered import "
                        "of the SDK is not.",
                        "Competence boundary — the categories where "
                        "subtly-wrong is catastrophic (cryptography, money, "
                        "parsing hostile input) and building is malpractice "
                        "regardless of how capable the team is.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="tp-ivb-manifest-pitch",
                    text=(
                        "The bought column is literally on the record: the "
                        "server's manifest, whose nineteen runtime "
                        "dependencies are each a decision that this repo "
                        "does not want to own that problem. Read as "
                        "decisions rather than a shopping list:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-ivb-manifest-quote",
                    language="toml",
                    caption=(
                        "The bought column: nineteen runtime dependencies, each one a "
                        "problem this repo declined to own."
                    ),
                    source="server/pyproject.toml",
                    snippet=(
                        "dependencies = [\n"
                        "    \"alembic>=1.20.0\",\n"
                        "    \"argon2-cffi>=25.1.0\",\n"
                        "    \"arq>=0.25.0\",\n"
                        "    \"asyncpg>=0.32.0\",\n"
                        "    # …\n"
                        "    \"pyjwt>=2.15.1\",\n"
                        "    \"redis>=8.1.0\",\n"
                        "    \"sqlalchemy[asyncio]>=2.1.4\",\n"
                        "    \"strawberry-graphql[fastapi]>=0.335.0\",\n"
                        "    \"structlog>=24.4\",\n"
                        "    \"uvicorn[standard]>=0.30\",\n"
                        "]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-ivb-manifest-reading",
                    text=(
                        "Score the visible lines against the axes. "
                        "argon2-cffi is the competence boundary in one "
                        "line: password hashing is cryptography, argon2 is "
                        "the Password Hashing Competition winner behind a "
                        "CFFI wrapper, and building it would be malpractice. "
                        "strawberry-graphql is build cost: a GraphQL engine "
                        "is a parser, a type system, an executor, and a "
                        "loader, and topic 13 proved the DataLoader batching "
                        "it brought with a spy test. arq is operational "
                        "ownership: queue semantics, retries, cron, and "
                        "worker supervision are a product, so the repo kept "
                        "only the retry POLICY pure in-domain and lets arq "
                        "execute its verdicts. pyjwt and itsdangerous are "
                        "the format rule — buy the signing format because "
                        "its pitfalls (algorithm confusion, missing-expiry "
                        "checks) are subtle and known, and keep the KEY and "
                        "the policy as your own. The wire drivers "
                        "(asyncpg, redis, motor) are bought and then "
                        "BOUNDED: the two-second optional-service timeouts "
                        "are this repo's own discipline layered over them, "
                        "as topic 39 taught."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-ivb-built-pitch",
                    text=(
                        "The built column is just as deliberate, and it is "
                        "not the same column as not-invented-here — each "
                        "build decision names what it declined to buy and "
                        "why the build is small. The clearest example is the "
                        "webhook signer: forty lines over the standard "
                        "library's hmac and hashlib, both halves in one "
                        "module so they cannot drift:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-ivb-built-quote",
                    language="py",
                    caption=(
                        "The built column's exhibit: machine-to-machine authentication in "
                        "forty lines of standard library — bought nothing, hid nothing."
                    ),
                    source="server/guide/domain/webhooks/signing.py",
                    snippet=(
                        "def sign_payload(*, secret: str, timestamp: int, payload: str) -> str:\n"
                        "    \"\"\"Sign one delivery: ``v1=`` + hex HMAC-SHA256 over ``\"{timestamp}.{payload}\"``.\"\"\"\n"
                        "    return f\"{SIGNATURE_SCHEME}={_mac(secret=secret, message=f'{timestamp}.{payload}')}\"\n"
                        "\n"
                        "\n"
                        "def signed_headers(*, secret: str, timestamp: int, payload: str) -> dict[str, str]:\n"
                        "    \"\"\"The two headers a signed delivery carries — timestamp plain, MAC prefixed.\"\"\"\n"
                        "    return {\n"
                        "        TIMESTAMP_HEADER: str(timestamp),\n"
                        "        SIGNATURE_HEADER: sign_payload(secret=secret, timestamp=timestamp, payload=payload),\n"
                        "    }"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-ivb-built-reading",
                    text=(
                        "Why build this and buy argon2? Because the "
                        "competence boundary sits in a different place: "
                        "HMAC-SHA256 and constant-time comparison ARE the "
                        "standard library's exported competency — using "
                        "them is integrating, at one level down. The "
                        "decision the signer represents is about the "
                        "boundary, not the arithmetic: the receiver's "
                        "raw-body-first discipline is this app's own "
                        "contract, and a signing SDK would own the one "
                        "boundary the lesson is about. The same reasoning "
                        "built the circuit breaker (pybreaker exists; the "
                        "substrate is about a hundred readable lines and "
                        "the states ARE the lesson topic 39 teaches) and "
                        "the OAuth2 provider (every protocol step "
                        "deliberately readable; a production system "
                        "integrates an identity provider instead, and the "
                        "row says so). Built is a teaching choice here — "
                        "in your production repo it is a cost choice, "
                        "scored on the same six axes."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-ivb-demo-pitch",
                    text=(
                        "The demo puts the whole question in one payload, "
                        "derived on the request that serves it: the "
                        "integrate-vs-build walk with every row VERIFIED "
                        "(each integrate row quotes the manifest "
                        "requirement line a real tomllib parse found; each "
                        "build row names the module file this server tree "
                        "actually carries), the real integration inventory "
                        "(the backing services and their failure modes, "
                        "the machine-to-machine authentication, the deploy "
                        "pipeline's artifact channels), the key/secret "
                        "surface as names and blast radii — values never "
                        "read, so the wire cannot carry one — and the "
                        "quotas this app really enforces, live where the "
                        "process can read them."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="thirdparty:hub",
                    title="The third-party hub",
                    description=(
                        "GET /api/demo/thirdparty/hub serves four "
                        "inventories, each row derived on this very "
                        "request · the DECISIONS walk — eight real "
                        "integrate-vs-build decisions (five integrate: "
                        "the GraphQL engine, password hashing, token "
                        "signing, the job queue, the wire drivers; three "
                        "build: the circuit breaker, the webhook HMAC, "
                        "the OAuth2 provider), every integrate row "
                        "verified by parsing server/pyproject.toml with "
                        "tomllib at request time and quoting the "
                        "requirement line found, every build row verified "
                        "by the module file existing in this server tree "
                        "· the INTEGRATIONS inventory — the three backing "
                        "services with their timeout/503 discipline, the "
                        "arq worker process, the webhook HMAC surface, "
                        "the OAuth2 code+PKCE flow, and the deploy "
                        "pipeline's third-party channels (the GHCR image "
                        "rails, the shared caddy edge), repo-root "
                        "evidence containment-checked where the repo is "
                        "mounted and honestly degraded on the live server "
                        "container · the SECRETS panel — the real "
                        "key/secret surface (FDG_JWT_SECRET, "
                        "FDG_SESSION_SECRET, FDG_DB_PASSWORD, the demo "
                        "webhook secret's honest public-by-design "
                        "divergence, the PROD_ENV_B64 concentrator), each "
                        "row naming the env var, the scope, and what a "
                        "leak would blast — never a value · the QUOTAS "
                        "panel — the real ceilings, live (the rate "
                        "limiter's policy, this app's engine pool size) "
                        "and declared (the realtime room and queue "
                        "ceilings, the upload cap) — with the behavior "
                        "at each ceiling."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-ivb-demo-reading",
                    text=(
                        "How to read the panel. Start with the decisions' "
                        "verified column — it is the honesty mechanism as "
                        "a feature: no row claims a package the manifest "
                        "does not carry or a module the tree does not "
                        "hold, because the panel checks both on every "
                        "request. Then read the integrations' when-down "
                        "column — it is the blast-radius axis made "
                        "concrete per dependency: PostgreSQL down is a "
                        "reconnect, Redis down is a bounded 503 for five "
                        "demos, the worker down is a queue that backs up "
                        "while the API keeps serving. The secrets panel "
                        "never shows a value by construction — the "
                        "builder never reads one — and the endpoint test "
                        "proves it by planting sentinel values and "
                        "asserting they appear nowhere in the serialized "
                        "payload. The quotas panel is the reminder that "
                        "every ceiling in this app is a number someone "
                        "chose on purpose, which is exactly how you "
                        "should read a vendor's limits too."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-ivb-builder-quote",
                    language="py",
                    caption=(
                        "The walk's verification engine: PEP 508 names matched against a "
                        "real tomllib parse of the manifest, on the request."
                    ),
                    source="server/guide/domain/demos/thirdparty_hub.py",
                    snippet=(
                        "def _requirement_line(dependencies: list[str], name: str) -> str | None:\n"
                        "    \"\"\"The manifest requirement whose PEP 508 name is ``name``, or None.\n"
                        "\n"
                        "    Strips extras and version operators before comparing, so\n"
                        "    ``strawberry-graphql[fastapi]>=0.335.0`` answers to ``strawberry-graphql``.\n"
                        "    \"\"\"\n"
                        "    wanted = name.lower().replace(\"_\", \"-\")\n"
                        "    for requirement in dependencies:\n"
                        "        head = requirement.split(\"[\", 1)[0]\n"
                        "        for operator in (\"===\", \"==\", \">=\", \"<=\", \"~=\", \"!=\", \">\", \"<\"):\n"
                        "            head = head.split(operator, 1)[0]\n"
                        "        if head.strip().lower().replace(\"_\", \"-\") == wanted:\n"
                        "            return requirement\n"
                        "    return None"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-ivb-router-quote",
                    language="py",
                    caption=(
                        "The demo's thin router: roots resolved, quota facts snapshotted off "
                        "the composition root, everything handed to the builder."
                    ),
                    source="server/guide/presentation/routers/demo/thirdparty.py",
                    snippet=(
                        "@router.get(HUB_PATH, response_model=ThirdPartyHubPanel)\n"
                        "async def read_third_party_hub_panel(\n"
                        "    request: Request,\n"
                        "    config: Annotated[AppConfig, Depends(get_config)],\n"
                        "    quotas: QuotaFactsDep,\n"
                        ") -> ThirdPartyHubPanel:\n"
                        "    \"\"\"Serve the third-party hub: decisions, integrations, secrets, quotas.\"\"\"\n"
                        "    server_root, repo_root = default_roots()\n"
                        "    return build_third_party_hub(\n"
                        "        server_root=server_root,\n"
                        "        repo_root=repo_root,\n"
                        "        config=config,\n"
                        "        quotas=quotas,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-ivb-coda",
                    text=(
                        "The rules of thumb the walk demonstrates, in "
                        "descending order of confidence: never build "
                        "crypto (the competence boundary is absolute); "
                        "rarely build queues, parsers, or engines (the "
                        "build cost is a product, and the ecosystem has "
                        "already paid it); always build the glue — the "
                        "adapter behind a port that translates between "
                        "the vendor's shape and your domain's, because "
                        "that is the reversible seam and nobody else can "
                        "write it for you; buy the format, keep the key "
                        "(pyjwt signs, but the key and the policy are "
                        "yours); and score every decision on the six "
                        "axes with numbers, not vibes — the demo's "
                        "verified column is what a decision record looks "
                        "like when it can still be checked automatically, "
                        "which is the only kind of record that stays "
                        "true. The rest of this topic walks the vendor-"
                        "shaped problems every real app meets — email, "
                        "payments, object storage — through the same "
                        "decision, honestly: what this repo really has, "
                        "and what the recipe would be."
                    ),
                ),
            ],
        ),
        # ── 2. email via aiosmtplib ───────────────────────────────────────
        Section(
            id="email-via-aiosmtplib",
            title="Email, concept-first (aiosmtplib)",
            blocks=[
                TextBlock(
                    kind="text",
                    id="tp-em-pitch",
                    text=(
                        "Email is the first integration nearly every "
                        "application needs and the one most often "
                        "underestimated. The protocol is old enough to "
                        "collect a pension (SMTP, 1982), but the modern "
                        "practice is younger and simpler: you do not talk "
                        "to recipient mail servers anymore — you hand "
                        "every message to a relay (Postmark, SES, Resend, "
                        "or a plain company SMTP host) because "
                        "deliverability is the provider's competency: "
                        "SPF, DKIM, and DMARC records, IP reputation, "
                        "greylist and bounce handling. The integrate-"
                        "versus-build answer is therefore settled twice "
                        "over — build cost (a correct SMTP client with "
                        "TLS and retry semantics) and competence boundary "
                        "(deliverability) both say integrate — and the "
                        "remaining decision is which client library and "
                        "which discipline to wrap it in."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-em-honesty-pitch",
                    text=(
                        "Full honesty first, the way this guide always "
                        "does it: aiosmtplib is NOT a dependency of this "
                        "repo. Nothing here sends real mail — the jobs "
                        "topic's email-as-a-job records sends into a "
                        "mailbox list, and the next section recaps "
                        "exactly that seam. So this section teaches the "
                        "library concept-first: what it is (an asyncio-"
                        "native SMTP client speaking the same envelope "
                        "as smtplib without blocking the loop), and the "
                        "one discipline any email adapter built for this "
                        "repo MUST copy from the adapters it would sit "
                        "beside — bound every outbound call:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-em-timeout-quote",
                    language="py",
                    caption=(
                        "The discipline the email adapter must copy: the optional-service "
                        "clients bound every phase of every call to two seconds."
                    ),
                    source="server/guide/data/mongo/client.py",
                    snippet=(
                        "SERVER_SELECTION_TIMEOUT_MS: Final = 2_000\n"
                        "\"\"\"How long an operation waits for a reachable mongod before failing.\n"
                        "\n"
                        "Short on purpose: when MongoDB is down, a demo request should degrade\n"
                        "to the 503 envelope in about two seconds, not hang a worker for the\n"
                        "30-second driver default.\n"
                        "\"\"\"\n"
                        "\n"
                        "CONNECT_TIMEOUT_MS: Final = 2_000\n"
                        "\"\"\"Per-connection handshake timeout — the other half of fast degradation.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-em-timeout-reading",
                    text=(
                        "An SMTP relay is exactly the kind of dependency "
                        "those constants exist for: remote, optional to "
                        "the core product, and perfectly capable of "
                        "hanging a handshake for minutes when it is "
                        "having a bad day. If the send happens in a "
                        "request handler, an unbounded SMTP call is the "
                        "topic-39 pathology verbatim — a parked worker "
                        "multiplying into pool exhaustion; if it happens "
                        "in the worker (where it belongs, next section), "
                        "an unbounded call still pins a worker slot for "
                        "the queue's whole concurrency budget. The "
                        "recipe below is the shape of the adapter that "
                        "would sit at the recorder port's seam — every "
                        "phase bounded, the connection always released, "
                        "credentials from the environment, never the "
                        "repo:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-em-recipe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# RECIPE — aiosmtplib is NOT installed in this repo (the jobs topic's\n"
                        "# recorder port is the seam it would plug into). To adopt it:\n"
                        "#   uv add aiosmtplib        # then one in-container: uv sync --locked\n"
                        "python3 - <<'PY'\n"
                        "# The adapter's shape at the recorder port's seam — bound, like every\n"
                        "# optional-service client this repo already runs:\n"
                        "import aiosmtplib\n"
                        "\n"
                        "async def send_via_relay(to: str, subject: str, body: str) -> None:\n"
                        "    client = aiosmtplib.SMTP(\n"
                        "        hostname=\"smtp.relay.example\",   # from config, not code\n"
                        "        port=587,\n"
                        "        start_tls=True,\n"
                        "        timeout=5.0,                     # the bound — every phase pays it\n"
                        "    )\n"
                        "    try:\n"
                        "        await client.connect()           # handshake: bounded\n"
                        "        await client.login(\"apikey\", \"…\")  # credentials: env, never the repo\n"
                        "        await client.send_message(build_message(to, subject, body))\n"
                        "    finally:\n"
                        "        await client.quit()              # the pool is never leaked\n"
                        "PY"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-em-recipe-reading",
                    text=(
                        "Read the recipe against the axes that built "
                        "this topic. The timeout is the whole integration "
                        "discipline in one parameter — aiosmtplib applies "
                        "it to connect, to the TLS handshake, and to each "
                        "command's reads, the same two-second philosophy "
                        "the mongo and redis clients encode as constants. "
                        "The try/finally around quit is blast radius "
                        "control: a send that raises still releases the "
                        "connection, so a flaky relay cannot leak sockets "
                        "across a worker's lifetime. The credentials come "
                        "from configuration because they are keys — the "
                        "last section of this topic is about exactly "
                        "that class of value. And notice what the recipe "
                        "does NOT contain: retry logic. Retrying a "
                        "possibly-sent email is a double-send risk, so "
                        "the retry posture belongs to the queueing layer "
                        "around the adapter, which is the next section's "
                        "entire point."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-em-provider-pitch",
                    text=(
                        "One more property of the email category that "
                        "generalizes to every provider-shaped "
                        "integration: the provider arrives with a "
                        "console, a quota, and a webhook habit. The "
                        "console gives you a sandbox (test API keys, "
                        "sandbox addresses, the deliverability dashboard "
                        "your own logs cannot fake); the quota is a "
                        "sending limit per second or per day that your "
                        "burstiest moment must fit under; and the "
                        "webhooks are how you learn what happened after "
                        "the handoff — deliveries, bounces, spam "
                        "complaints arrive as signed POSTs to your "
                        "endpoint, which is a surface you already met in "
                        "topic 14 and will meet again in the Stripe "
                        "section: verify the signature, dedupe the "
                        "delivery, and never trust the body until both "
                        "have happened."
                    ),
                ),
            ],
        ),
        # ── 3. email as a job — recap ─────────────────────────────────────
        Section(
            id="email-as-a-job-recap",
            title="Email as a job: the recap",
            blocks=[
                TextBlock(
                    kind="text",
                    id="tp-recap-pitch",
                    text=(
                        "Topic 29 already taught the pattern this "
                        "repository's email story rides — this section "
                        "recaps it rather than re-teaching it, and points "
                        "at the exact seam a real SMTP client would fill. "
                        "The four beats: COMPOSE at the boundary (the "
                        "request validates shape and answers 201 with a "
                        "job ticket), DEFER the send (the draft rides the "
                        "queue as JSON), SEND in the worker (where "
                        "seconds of SMTP latency cost nothing), and "
                        "RECORD the outcome (a row a support human can "
                        "read). The worker's task is quotable, and its "
                        "own docstring names this topic:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-recap-worker-quote",
                    language="py",
                    caption=(
                        "The real task from topic 29: validate at the worker, park poison, "
                        "record the send — and the promise this topic resolves honestly."
                    ),
                    source="server/guide/worker.py",
                    snippet=(
                        "async def send_email(ctx: dict[str, Any], payload: str) -> str:\n"
                        "    \"\"\"The classic deferred workload: validate at the worker, record the send.\n"
                        "\n"
                        "    The payload is validated HERE (not just at the API): the queue is\n"
                        "    open to more doors than the router, so the worker re-derives the\n"
                        "    contract — and a malformed draft classifies as poison (the input is\n"
                        "    wrong), parking straight to the dead-letter queue without spending\n"
                        "    one retry. Topic 42 swaps the recorder for a real SMTP client; the\n"
                        "    PATTERN — compose, defer, send, record — is this topic's lesson.\n"
                        "    \"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-recap-promise",
                    text=(
                        "That docstring contains a forward promise — "
                        "topic 42 swaps the recorder for a real SMTP "
                        "client — and this topic resolves it the honest "
                        "way: as the recipe in the previous section, not "
                        "a fabricated live integration, because this "
                        "guide does not ship dependencies it does not "
                        "run and does not pretend to send mail it does "
                        "not send. The SUBSTANCE of the promise is the "
                        "seam, and the seam is real and already "
                        "exercised: the recorder is one adapter behind "
                        "the jobs substrate, and the mailbox endpoint "
                        "says the honest thing in its own docstring:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-recap-mailbox-quote",
                    language="py",
                    caption=(
                        "The seam's own words: the recorded emails are one honest GET away, "
                        "and the panel never claims an SMTP that is not there."
                    ),
                    source="server/guide/presentation/routers/demo/jobs.py",
                    snippet=(
                        "@router.get(MAILBOX_PATH, response_model=MailboxPanel)\n"
                        "async def read_mailbox(service: JobsDep) -> MailboxPanel:\n"
                        "    \"\"\"The recorded emails — the demo's mailbox has no SMTP (topic 42 wires one).\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-recap-substrate",
                    text=(
                        "The pieces the recap stands on are all real and "
                        "all earlier topics': the pure retry policy in "
                        "domain/jobs (fixed or exponential schedules, "
                        "poison classification — a malformed email draft "
                        "is ValueError-shaped and therefore POISON, "
                        "parked without spending one retry), the arq "
                        "worker as a separate compose process over the "
                        "same Redis (so a wedged SMTP relay backs up a "
                        "queue instead of your API), the attempt trail "
                        "and dead-letter queue as the support human's "
                        "readable record, and the two observability "
                        "numbers (queue depth, oldest age) that tell you "
                        "the relay is slow before the users do. Swapping "
                        "the recorder for the previous section's "
                        "aiosmtplib adapter changes exactly one adapter "
                        "behind one port — the pattern's whole payoff, "
                        "and the clearest demonstration in this repo of "
                        "why the integrate-versus-build decision should "
                        "always leave a port at the seam."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-recap-idempotence",
                    text=(
                        "Two production notes the jobs topic recorded "
                        "and this one repeats because they ARE the "
                        "third-party reality of email: sending is "
                        "idempotence-hostile — at-least-once delivery "
                        "means the same job can run twice, and the "
                        "mitigation is to carry the job id in a message "
                        "header and check it on the provider's bounce or "
                        "dedupe side if double-sends are unacceptable; "
                        "and the address rule belongs at BOTH ends even "
                        "though it looks redundant — the boundary check "
                        "gives the user a fast 422, the worker check "
                        "keeps the queue honest for every other door "
                        "that can enqueue (replay, other enqueuers, a "
                        "manual Redis call). Both notes are instances of "
                        "one rule: the queue is a door you do not fully "
                        "control, so the contract is re-derived wherever "
                        "the work actually runs."
                    ),
                ),
            ],
        ),
        # ── 4. Stripe ─────────────────────────────────────────────────────
        Section(
            id="stripe",
            title="Stripe: payments, concept-first",
            blocks=[
                TextBlock(
                    kind="text",
                    id="tp-st-pitch",
                    text=(
                        "Payments are the category where the integrate-"
                        "versus-build question has exactly one answer, "
                        "and it is not close: you never build payment "
                        "processing, and you never touch a card number. "
                        "PCI DSS compliance for raw card data is a "
                        "multi-year audit program; letting Stripe's "
                        "browser widgets (Stripe.js, Elements) tokenize "
                        "the card means the number never crosses your "
                        "infrastructure at all — your API carries "
                        "tokens, amounts, and metadata. Honesty again, "
                        "up front: the Stripe SDK is NOT installed in "
                        "this repo, and nothing here charges anything. "
                        "What this section teaches is the SHAPE of the "
                        "integration, because Stripe is the best-"
                        "documented instance of a pattern you already "
                        "own in this repository — and recognizing a "
                        "pattern you own beats memorizing a vendor's "
                        "docs."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-st-surfaces-pitch",
                    text=(
                        "A payments integration is three surfaces, and "
                        "each one maps onto something this guide already "
                        "built:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="tp-st-surfaces",
                    ordered=False,
                    items=[
                        "The API surface — your server calls Stripe's "
                        "API through the SDK (create a PaymentIntent, "
                        "confirm a subscription) with a secret key; the "
                        "same outbound-call discipline as every adapter "
                        "here — bounded, credentialed from env, behind "
                        "a port.",
                        "The webhook surface — Stripe POSTs events to "
                        "YOUR endpoint (payment succeeded, charge "
                        "refunded), signed and at-least-once: verify "
                        "the signature, dedupe the delivery — exactly "
                        "topic 14's receiver and topic 22's idempotent "
                        "consumer.",
                        "The console surface — test mode with sandbox "
                        "cards, event replay, and a dashboard of every "
                        "charge: the provider's dev experience becomes "
                        "your debugging environment, the way the "
                        "scenario store is this repo's.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="tp-st-signature-pitch",
                    text=(
                        "The first mapping is the deep one. Stripe's "
                        "webhook signature header carries a timestamp "
                        "and an HMAC-SHA256 over the exact request body "
                        "— the same design as this repo's own webhook "
                        "signer, down to the two gates and their order. "
                        "Compare the receiver's verify function with "
                        "Stripe's documented verification steps and you "
                        "are reading the same algorithm twice:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-st-signature-quote",
                    language="py",
                    caption=(
                        "The design Stripe's signature follows: freshness first (the cheapest "
                        "gate), then a constant-time MAC over the exact raw body."
                    ),
                    source="server/guide/domain/webhooks/signing.py",
                    snippet=(
                        "    age_seconds = now - timestamp\n"
                        "    if abs(age_seconds) > max_skew_seconds:\n"
                        "        return Err(\n"
                        "            AppError(\n"
                        "                FailureKind.UNAUTHORIZED,\n"
                        "                f\"Webhook timestamp {timestamp} is outside the ±{max_skew_seconds}s \"\n"
                        "                f\"freshness window of {now}.\",\n"
                        "            )\n"
                        "        )\n"
                        "    expected = sign_payload(secret=secret, timestamp=timestamp, payload=payload)\n"
                        "    if not hmac.compare_digest(expected.encode(\"utf-8\"), signature.encode(\"utf-8\")):"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-st-signature-reading",
                    text=(
                        "Every property in that quote has a Stripe "
                        "counterpart. The timestamp rides inside the "
                        "signed message, so a captured delivery cannot "
                        "be re-dated — Stripe's t= value is covered by "
                        "the very MAC it accompanies, and the freshness "
                        "window (±300 seconds here) is the replay "
                        "defense. The MAC covers the EXACT payload "
                        "bytes, which is why both receivers read the "
                        "raw body before parsing — a receiver that "
                        "parses first and re-serializes verifies "
                        "nothing, because JSON re-serialization is not "
                        "byte-stable. And the comparison is constant-"
                        "time because string equality returns False at "
                        "the first differing byte, leaking a signature "
                        "one measured response at a time. The Stripe "
                        "SDK's construct_event does this whole dance "
                        "for you; this repo built it in forty lines to "
                        "teach it — competence-boundary logic either "
                        "way, and never something to wing in a "
                        "handler."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-st-idempotence-pitch",
                    text=(
                        "The second mapping is the delivery contract. "
                        "Webhook delivery is at-least-once — the same "
                        "event WILL arrive twice sometimes, and a "
                        "payment event handled twice is a double "
                        "fulfillment — so the handler needs the seen-"
                        "before check this repo's idempotent consumer "
                        "already implements, and the Stripe API takes "
                        "the same idea inbound as an Idempotency-Key "
                        "header on your own requests. The consumer's "
                        "loop, quoted from the messaging substrate:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-st-idempotence-quote",
                    language="py",
                    caption=(
                        "The dedupe every webhook handler needs: check the processed-set "
                        "before the work, remember after it — event ids are the keys."
                    ),
                    source="server/guide/domain/messaging/idempotence.py",
                    snippet=(
                        "        processed: list[str] = []\n"
                        "        skipped_duplicates: list[str] = []\n"
                        "        for entry in entries:\n"
                        "            if await self._store.seen(self._set_key, entry.event_id):\n"
                        "                skipped_duplicates.append(entry.event_id)\n"
                        "                continue\n"
                        "            await self._store.remember(self._set_key, entry.event_id)\n"
                        "            processed.append(entry.event_id)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-st-recipe-pitch",
                    text=(
                        "The recipe, honestly labeled as one — the SDK "
                        "is not installed, and this is the shape a real "
                        "endpoint in this stack would take, assembled "
                        "from the two mechanisms above plus the error "
                        "taxonomy's refusal discipline:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-st-recipe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# RECIPE — the Stripe SDK is NOT installed in this repo; this is the\n"
                        "# shape a real integration would take (stripe-python, from PyPI):\n"
                        "#   uv add stripe\n"
                        "python3 - <<'PY'\n"
                        "# The two decisions every Stripe webhook handler makes — verify\n"
                        "# first, dedupe always — plus the refusal discipline this repo uses:\n"
                        "import stripe\n"
                        "\n"
                        "stripe.api_key = \"sk_live_…\"  # from env — never the repo (§6)\n"
                        "\n"
                        "async def stripe_webhook(raw_body: bytes, signature: str) -> dict:\n"
                        "    payload = raw_body.decode()          # RAW body first — the repo's rule\n"
                        "    try:\n"
                        "        event = stripe.Webhook.construct_event(\n"
                        "            payload, signature, \"whsec_…\"  # t= + HMAC, constant-time —\n"
                        "        )                                #   signing.py's own design\n"
                        "    except ValueError:\n"
                        "        raise UnauthorizedError()        # refuse like verify_payload\n"
                        "    if seen(event.id):                   # at-least-once ⇒ dedupe first\n"
                        "        return {\"received\": True}         #   — the consumer's check\n"
                        "    handle(event)                        # only NOW does the money move\n"
                        "    remember(event.id)\n"
                        "    return {\"received\": True}\n"
                        "PY"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-st-recipe-reading",
                    text=(
                        "The order of operations in that handler is "
                        "the entire contract: raw body, signature "
                        "verification, dedupe, and only then the side "
                        "effect — swap any two neighbors and you have "
                        "either a forged event or a double fulfillment. "
                        "The 401-style refusal on bad signatures "
                        "matches the taxonomy's unauthorized kind, and "
                        "the keys in the recipe point at the last "
                        "section of this topic: sk_live keys and "
                        "webhook signing secrets are exactly the "
                        "blast-radius-shaped values the keys panel "
                        "names, and a leaked live secret key is the "
                        "widest blast a SaaS integration can carry — "
                        "it can move real money. Test mode (sk_test) "
                        "is the provider's sandbox and the only mode "
                        "that should ever touch a development branch's "
                        "environment."
                    ),
                ),
            ],
        ),
        # ── 5. cloud storage ──────────────────────────────────────────────
        Section(
            id="cloud-storage",
            title="Cloud storage behind the port",
            blocks=[
                TextBlock(
                    kind="text",
                    id="tp-cs-pitch",
                    text=(
                        "Object storage is the third classic vendor "
                        "surface: files that must outlive the request "
                        "and the process — uploads, exports, generated "
                        "documents — stored in a bucket (S3, R2, GCS) "
                        "instead of a local disk. This repo deliberately "
                        "does not run one: the files workbench from "
                        "topic 26 keeps bytes in an in-memory dict, "
                        "demo-scoped BY DECLARATION, and says so on its "
                        "own panel. What makes that honest rather than "
                        "thin is the PORT: the workbench service never "
                        "learns where bytes live, so the object-store "
                        "adapter is a composition-root decision "
                        "instead of a rewrite. The port is the "
                        "integrating-versus-building lesson in its "
                        "purest form — build the seam, buy the storage:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-cs-port-quote",
                    language="py",
                    caption=(
                        "The seam: adapters save, find, read, and list — the service above it "
                        "never learns whether the store is a dict, a disk, or a bucket."
                    ),
                    source="server/guide/domain/files/storage.py",
                    snippet=(
                        "@runtime_checkable\n"
                        "class FileStore(Protocol):\n"
                        "    \"\"\"The files persistence port: adapters save, find, read, and list.\"\"\"\n"
                        "\n"
                        "    def save(\n"
                        "        self,\n"
                        "        display_name: str,\n"
                        "        sanitized_name: str,\n"
                        "        body: bytes,\n"
                        "        declared_type: str,\n"
                        "        sniffed_type: str,\n"
                        "    ) -> StoredFile:\n"
                        "        \"\"\"Mint an id, stamp the clock, hold the snapshot + bytes, return metadata.\"\"\"\n"
                        "        ..."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-cs-port-reading",
                    text=(
                        "Read the port's signature as third-party "
                        "hygiene. The storage key is never the user's "
                        "filename — the adapter mints the id, so an "
                        "attacker controls no part of any key in the "
                        "store (the module names that rule twice: "
                        "file_id is server-minted, display_name is "
                        "data for headers and listings only). The "
                        "sniffed type travels beside the declared one, "
                        "so the adapter that finally writes bytes "
                        "somewhere can label them with what the magic "
                        "bytes said, not what the uploader claimed. "
                        "And the wiring comment in the composition "
                        "root says the swap out loud:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-cs-wiring-quote",
                    language="py",
                    caption=(
                        "The composition root's own words: the port is the seam, the adapter "
                        "swap is one line — the decision deferred, not foreclosed."
                    ),
                    source="server/guide/main.py",
                    snippet=(
                        "    # Topic 26's media substrate: the workbench service over the files port\n"
                        "    # — the in-memory adapter is demo-scoped BY DECLARATION (a restart loses\n"
                        "    # the store; the panel says so), and the port is the seam a disk or S3\n"
                        "    # adapter fills without touching the service.\n"
                        "    app.state.files_workbench = FilesWorkbenchService(InMemoryFileStore())"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-cs-recipe-pitch",
                    text=(
                        "The adapter a real bucket would get, as a "
                        "recipe — no cloud SDK is installed here, and "
                        "the shape is what matters: the port's "
                        "signature, an object store's mechanics, and "
                        "the two rules from the port reading above "
                        "applied at the boundary:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-cs-recipe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# RECIPE — no cloud-storage SDK is installed in this repo (NOT installed;\n"
                        "# the port is the seam); this is the adapter shape a real bucket\n"
                        "# would take (aioboto3, from PyPI):\n"
                        "#   uv add aioboto3\n"
                        "python3 - <<'PY'\n"
                        "# The S3 adapter's save(): the port's signature, an object store's\n"
                        "# mechanics, the port's two rules kept — minted keys, sniffed types:\n"
                        "import aioboto3\n"
                        "\n"
                        "async def save(display_name, sanitized_name, body, declared_type, sniffed_type):\n"
                        "    stored_id = mint_id()                      # server-minted key — never\n"
                        "    async with aioboto3.Session().client(\"s3\") as s3:   # the user's name\n"
                        "        await s3.put_object(\n"
                        "            Bucket=\"guide-uploads\",\n"
                        "            Key=f\"uploads/{stored_id}\",\n"
                        "            Body=body,\n"
                        "            ContentType=sniffed_type,        # what the magic bytes said\n"
                        "        )\n"
                        "    return stored_metadata(stored_id, display_name, sniffed_type, body)\n"
                        "PY"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-cs-recipe-reading",
                    text=(
                        "Two properties of the object-store world the "
                        "recipe gestures at and production must decide "
                        "deliberately. First, the client is bounded "
                        "like every other outbound call — aioboto3's "
                        "config carries read and connect timeouts, and "
                        "an unbounded PUT is the same hung-worker "
                        "arithmetic as an unbounded SMTP handshake. "
                        "Second, the big-file path is architectural, "
                        "not parametric: the workbench enforces its "
                        "2 MiB cap WHILE READING (cap plus one chunk — "
                        "a 422, never a buffered bomb), so an adapter "
                        "behind that port only ever sees bounded "
                        "bytes; for genuinely large media, the "
                        "production pattern is a presigned upload URL "
                        "— the server mints a scoped, expiring "
                        "credential and the browser PUTs directly to "
                        "the bucket, keeping the bytes out of the API "
                        "process entirely, which is the same "
                        "tokenization move the Stripe section made "
                        "with card numbers: keep the valuable payload "
                        "off your own infrastructure when the "
                        "provider can take it safely from the client."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-cs-coda",
                    text=(
                        "The cost model completes the decision. Object "
                        "storage is cheap per gigabyte and metered per "
                        "request and per egress byte — the bill scales "
                        "with traffic in a way a local disk does not, "
                        "and the quotas panel's honesty applies to "
                        "vendors too: request-rate limits exist, and "
                        "the burst behavior at them (throttling, "
                        "slow-down errors) belongs in the adapter's "
                        "degradation story, not in a surprise incident. "
                        "The decision frame from section one closes "
                        "the loop: this repo integrated nothing and "
                        "built the seam, because the teaching value is "
                        "the port and the bytes are throwaway; your "
                        "application scores the same axes with its own "
                        "numbers and usually lands on the bucket — "
                        "through the same port, changing the same one "
                        "wiring line."
                    ),
                ),
            ],
        ),
        # ── 6. keys, quotas, blast radius ─────────────────────────────────
        Section(
            id="keys-quotas-blast-radius",
            title="Keys, quotas, and blast radius",
            blocks=[
                TextBlock(
                    kind="text",
                    id="tp-kq-pitch",
                    text=(
                        "Every integration you add arrives carrying "
                        "keys and quotas: credentials that authenticate "
                        "you to the vendor, limits that shape how hard "
                        "you may lean on them, and a blast radius — the "
                        "set of things a leaked key or an exhausted "
                        "quota can damage. This section analyzes this "
                        "repository's own key surface honestly (the "
                        "hub panel's secrets rows are the live version "
                        "of this analysis), then generalizes the "
                        "discipline to the vendor keys this repo does "
                        "not have. The rule that governs everything: "
                        "name the variable, scope the value, and reason "
                        "about the blast — but never let the value "
                        "cross a wire you do not control, which "
                        "includes this page."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-kq-config-pitch",
                    text=(
                        "The real key surface is small and worth "
                        "knowing exactly: two signing secrets and one "
                        "database password, each with a named "
                        "environment variable, each defended at boot by "
                        "the config's fail-fast validator — the "
                        "mechanism that makes a forgotten secret a "
                        "startup failure instead of a quiet liability:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-kq-config-quote",
                    language="py",
                    caption=(
                        "The blast-radius defense at boot: a dev-default signing secret in any "
                        "non-dev environment refuses to start, naming the env vars to set."
                    ),
                    source="server/guide/core/config.py",
                    snippet=(
                        "        if self.env == _DEV_ENV:\n"
                        "            return self\n"
                        "        defaults = type(self).model_fields\n"
                        "        unset = [\n"
                        "            f\"FDG_{name.upper()}\"\n"
                        "            for name, field in defaults.items()\n"
                        "            if name.endswith(\"_secret\") and getattr(self, name) == field.get_default()\n"
                        "        ]\n"
                        "        if unset:\n"
                        "            raise ValueError(\n"
                        "                f\"env={self.env!r} refuses dev-default signing secrets: \"\n"
                        "                f\"{', '.join(unset)} must be set to real high-entropy values \"\n"
                        "                f\"(distinct from each other) before the app may start\"\n"
                        "            )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-kq-config-reading",
                    text=(
                        "That validator is blast-radius thinking made "
                        "executable: a dev-default JWT secret in "
                        "production means anyone who read the public "
                        "repository can mint tokens for any user — the "
                        "widest blast a web app carries — so the "
                        "refusal is loud, early, and names the exact "
                        "variables to set. The second door is the "
                        "compose rail, which refuses even earlier, at "
                        "render time, before any container starts:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-kq-compose-quote",
                    language="yaml",
                    caption=(
                        "The second door: compose's required-variable syntax makes an unset "
                        "secret a deploy-time error — the stack refuses to render."
                    ),
                    source=".docker/docker-compose.prod.yml",
                    snippet=(
                        "      - FDG_DATABASE_URL=postgresql+asyncpg://postgres:${FDG_DB_PASSWORD:?FDG_DB_PASSWORD must be set to a real database password}@postgres:5432/guide\n"
                        "      # …\n"
                        "      - FDG_JWT_SECRET=${FDG_JWT_SECRET:?FDG_JWT_SECRET must be set to a real high-entropy signing secret}\n"
                        "      - FDG_SESSION_SECRET=${FDG_SESSION_SECRET:?FDG_SESSION_SECRET must be set to a real high-entropy signing secret, distinct from FDG_JWT_SECRET}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-kq-handling",
                    text=(
                        "Where the real values live is as deliberate as "
                        "the doors that demand them: nowhere in the "
                        "repository. The production environment file is "
                        "materialized on the VM from a single GitHub "
                        "environment secret (PROD_ENV_B64) by the deploy "
                        "workflow; the committed file is only the "
                        "template, carrying placeholders long enough to "
                        "pass the validator while being obviously not "
                        "secrets. That one secret is a CONCENTRATOR — "
                        "it carries all three real values, so its blast "
                        "radius is the union of theirs, which is why it "
                        "lives in the platform's narrowest store (the "
                        "GitHub production environment) rather than in "
                        "any file a checkout can read. The same "
                        "concentrator idea is why the hub panel's "
                        "secret rows carry names and blast radii and "
                        "never values: the builder never reads a secret "
                        "value at all, so no serialization path — JSON, "
                        "repr, log — can carry one, and the endpoint "
                        "test plants sentinel values and proves they "
                        "appear nowhere in the payload."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-kq-quotas-pitch",
                    text=(
                        "Quotas are the other half of the vendor "
                        "contract, and this repo enforces its own "
                        "honestly — every ceiling in this app is a "
                        "named, documented number someone chose on "
                        "purpose. The clearest one, quoted from the "
                        "security substrate:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-kq-quotas-quote",
                    language="py",
                    caption=(
                        "A quota as code: five hits per ten seconds, keyed by client and route "
                        "— the number, the window, and the key named together."
                    ),
                    source="server/guide/domain/security/rate_limit.py",
                    snippet=(
                        "DEMO_POLICY: Final[RateLimitPolicy] = RateLimitPolicy(\n"
                        "    window_s=10.0, budget=5, keying=\"client ip + route\"\n"
                        ")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-kq-quotas-reading",
                    text=(
                        "The hub panel's quotas section reads that "
                        "policy LIVE off the running app (beside the "
                        "engine pool's size) and imports the domain's "
                        "own constants for the realtime ceilings (eight "
                        "members per room, thirty-two queued messages "
                        "per connection) and the upload cap (two MiB, "
                        "enforced while reading). The point of reading "
                        "them in one place is the transferable habit: "
                        "a quota without a documented behavior at the "
                        "ceiling is a number, not a policy — the 429 "
                        "with Retry-After, the 1013 close, the 422 "
                        "envelope are the POLICY, and the number merely "
                        "says when it fires. Vendor quotas deserve the "
                        "same respect in your integration adapter: "
                        "Stripe's live-mode rate limits, an email "
                        "provider's sends-per-second, an object "
                        "store's request rate all live in the "
                        "provider's dashboard and docs — they are not "
                        "observable from this repo, and the honest "
                        "adapter encodes them as configuration with a "
                        "degradation story (queue, back off, or shed), "
                        "never as a surprise."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-kq-coda",
                    text=(
                        "The section's discipline in one paragraph, "
                        "which is also the topic's: before adding any "
                        "dependency, write down its key's blast radius "
                        "in one sentence (what can a holder of this "
                        "value DO), give it the narrowest scope the "
                        "vendor allows (a test key in dev, a "
                        "restricted key in prod, one secret per "
                        "purpose — never one key shared across "
                        "purposes), keep it in the narrowest store "
                        "that works (env materialized at deploy, a "
                        "secrets manager at scale — never the repo, "
                        "never a log, never a payload), and know the "
                        "rotation story BEFORE you need it — a signing "
                        "secret's leak ends only at rotation, so "
                        "rotation must be an operation you have "
                        "rehearsed, not a design you discover you "
                        "lack at 3am. The integrate-versus-build "
                        "decision started this topic; the keys it "
                        "leaves behind are how you live with the "
                        "decision every day after."
                    ),
                ),
            ],
        ),
        # ── 7. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead=(
                "Third-party from a shell: the decision walk, the integration "
                "inventory, the secrets panel (names, never values), the "
                "quotas, and this topic's shape."
            ),
            blocks=[
                TextBlock(
                    kind="text",
                    id="tp-terminal-intro",
                    text=(
                        "Five stops on the running stack: the "
                        "integrate-versus-build walk with its verified "
                        "column, the real integration inventory with "
                        "each dependency's failure mode, the secrets "
                        "panel proving names-without-values on the "
                        "wire, the live quotas, and this topic's own "
                        "shape through both ports — every payload the "
                        "same stack this topic audited."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-terminal-decisions",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the integrate-vs-build walk, every row verified\n"
                        "curl -s localhost:8000/api/demo/thirdparty/hub | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for d in panel[\"decisions\"]:\n"
                        "    print(\"%-18s %-9s %s\" % (d[\"id\"], d[\"choice\"], d[\"verified\"][:76]))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-terminal-integrations",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the real integration inventory: what it is, what its failure does\n"
                        "curl -s localhost:8000/api/demo/thirdparty/hub | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for i in panel[\"integrations\"]:\n"
                        "    print(\"%-13s %-26s when down: %s\" % (i[\"kind\"], i[\"name\"], i[\"whenDown\"][:58]))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-terminal-secrets",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the secrets panel: names, scopes, blast radii — never values.\n"
                        "# The live proof: this dev server really holds the committed dev-default\n"
                        "# signing secret, so serialize the WHOLE payload and search for it —\n"
                        "# zero matches, because the builder never read it:\n"
                        "curl -s localhost:8000/api/demo/thirdparty/hub | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for s in panel[\"secrets\"]:\n"
                        "    print(\"%-22s %s\" % (s[\"envVar\"], s[\"blastRadius\"][:78]))\n"
                        "raw = json.dumps(panel)\n"
                        "print(\"dev-default secret anywhere in payload:\",\n"
                        "      \"dev-only-jwt-secret\" in raw or \"dev-only-session-secret\" in raw)'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-terminal-quotas",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the quotas: live reads beside declared constants\n"
                        "curl -s localhost:8000/api/demo/thirdparty/hub | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for q in panel[\"quotas\"]:\n"
                        "    print(\"%-16s %-34s (%s)\" % (q[\"id\"], q[\"quota\"], q[\"source\"]))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tp-terminal-shape",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — this topic's shape, the panel through the client proxy, the receipt\n"
                        "curl -s localhost:8000/api/content | python3 -c '\n"
                        "import json, sys\n"
                        "index = json.load(sys.stdin)\n"
                        "print(len(index[\"topics\"]), \"topics /\", len(index[\"groups\"]), \"groups\")'\n"
                        "curl -s localhost:8000/api/content/third-party | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'\n"
                        "curl -s localhost:5174/api/demo/thirdparty/hub \\\n"
                        "  | python3 -c 'import json,sys; p=json.load(sys.stdin); print(\"proxy decisions:\", len(p[\"decisions\"]))'\n"
                        "curl -s -o /dev/null -w 'health: %{http_code} in %{time_total}s\\n' localhost:8000/api/health"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tp-terminal-coda",
                    text=(
                        "Stops 1–2 are the topic's argument in two "
                        "payloads: every decision this repo made about "
                        "code it did not write, verified against the "
                        "manifest and the tree on the very request; "
                        "every real dependency with its failure mode "
                        "named. Stop 3 is the keys discipline made "
                        "visible — a panel about secrets that cannot "
                        "leak one by construction. Stop 4 reads the "
                        "ceilings this app chose, and stop 5 closes "
                        "the family loop: the topic taught integrating "
                        "versus building, served by a stack that "
                        "integrated its stores, bought its engine, "
                        "built its breaker, and never went down to "
                        "say so."
                    ),
                ),
            ],
        ),
    ],
)
