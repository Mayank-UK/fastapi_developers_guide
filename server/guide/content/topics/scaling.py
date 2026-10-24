"""Topic 40 — Scaling: more copies, not more archaeology.

Deployment shipped one copy of everything; performance made the single
copy fast; reliability kept the single copy alive when its dependencies
failed. This topic is the multiplier view: what actually happens when
you run N copies of the server instead of one. Everything quoted here is
this repository's real scaling surface — the composition root that builds
in-process state per process, the honest split between state that lives
in the heap (posts substrate, scenario flags, auth state, rate budgets)
and state that lives outside it (PostgreSQL, Redis, MongoDB, the signed
cookie and JWT), the blue/green caddy flip and the per-color compose
projects as the repo's real traffic-splitting relatives, the indexed
schema and the shared engine pool as the data tier's scaling rails, the
nginx immutable-asset edge, and the realtime ceilings and 429s as the
backpressure this app already enforces. The demo is scaling:stateless,
INLINE in the statelessness section: one logical request walked through
two per-replica state worlds — a process-local write that never crosses,
beside a real Redis INCR that does.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="scaling",
    title="Scaling",
    subtitle=(
        "Serving more load by adding copies, not re-architecting: what "
        "scaling actually means along the request path, statelessness as "
        "a placement question (which of this repo's stores live in the "
        "process, which outside it, which in the browser — walked live by "
        "a two-replica round: one write that never crosses the process "
        "boundary, one real Redis INCR that does), load balancing and the "
        "repo's own blue/green caddy flip, replicas from compose services "
        "to per-color stacks, data at scale (indexes, pooling, read "
        "replicas and sharding as the honest prose), the CDN/edge story "
        "this stack actually ships (immutable hashed assets, no-cache "
        "index.html, zstd at the edge), backpressure from the realtime "
        "ceilings to the 429 envelope, and capacity as Little's law plus "
        "the two observability numbers."
    ),
    group="ship",
    order=40,
    sections=[
        # ── 1. what scaling means ────────────────────────────────────────
        Section(
            id="what-scaling-means",
            title="What scaling means",
            blocks=[
                TextBlock(
                    kind="text",
                    id="scl-wsm-pitch",
                    text=(
                        "Topics 37 through 39 built a stack that ships, "
                        "stays fast, and survives failure — one copy of "
                        "everything. Scaling is the next question: what "
                        "changes when demand exceeds what one copy can "
                        "do? The honest answer is that nothing about the "
                        "APPLICATION changes — the same code, the same "
                        "endpoints, the same database — but a set of "
                        "assumptions you never had to examine at one copy "
                        "suddenly become load-bearing: that state lives "
                        "where the request lands, that one database "
                        "connection is always available, that a slow "
                        "client is your client, that the file the browser "
                        "cached is the file you are serving. Scaling is "
                        "the discipline of examining those assumptions "
                        "BEFORE the traffic does it for you."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-wsm-axes-pitch",
                    text=(
                        "The word scales in two directions, and every "
                        "conversation about scaling goes wrong when the "
                        "two are conflated. Vertical scaling makes the "
                        "one copy bigger — more CPU, more memory, faster "
                        "disks. Horizontal scaling adds copies of the "
                        "stateless parts — a second server process, a "
                        "third, a fortieth. Vertical is a purchase order; "
                        "horizontal is an architecture. The whole topic "
                        "that follows is essentially the price list for "
                        "horizontal:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="scl-wsm-axes",
                    ordered=False,
                    items=[
                        "Vertical — a bigger machine: zero code change, "
                        "linear-ish cost, a hard ceiling, and a single "
                        "point of failure that reliability (topic 39) "
                        "would call a design flaw.",
                        "Horizontal app tier — more replicas of the "
                        "server: cheap copies, but every piece of "
                        "in-process state becomes a bug (this topic's "
                        "second section is that sentence, taught live).",
                        "Data tier — the databases the replicas share: "
                        "indexes and pooling first, then read replicas "
                        "and sharding when the single writer runs out.",
                        "Edge — bytes served closer to the client: "
                        "immutable assets cached for a year, the origin "
                        "answering only what must be fresh.",
                        "Shedding — deciding, on purpose, which work to "
                        "refuse when the rest is not enough: 429s, "
                        "bounded queues, retired slow consumers.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="scl-wsm-path",
                    text=(
                        "Trace one request through this stack and every "
                        "axis has a place to bite. The browser asks the "
                        "client host; in production the central caddy "
                        "container answers TLS and proxies to this app's "
                        "nginx; nginx serves the hashed assets from its "
                        "own disk (the edge axis — no Python involved at "
                        "all) and proxies /api/ to the server; the "
                        "server's event loop runs the middleware stack "
                        "and the handler, which calls use cases, which "
                        "call adapters, which reach PostgreSQL, Redis, "
                        "or MongoDB over the compose network (the data "
                        "axis). Topic 38 measured the single-copy "
                        "latency of exactly this path; scaling asks how "
                        "the path behaves when forty requests arrive at "
                        "once and when the server part of it exists in "
                        "four copies. Nothing in that sentence changes "
                        "the code — and everything changes the "
                        "assumptions."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-wsm-two-questions",
                    text=(
                        "Two questions organize everything that follows. "
                        "First: where does state live? A replica is a "
                        "copy of code plus whatever state the code keeps "
                        "in its own heap — if a second replica cannot "
                        "see a write the first one made, the load "
                        "balancer will route a user's next request to a "
                        "replica that lies to them. Second: how much is "
                        "enough? Copies cost money and data tiers have "
                        "ceilings, so capacity has to be measured, not "
                        "guessed. The rest of this topic answers the "
                        "first question with a live walk and an "
                        "inventory of this very app's state, and the "
                        "second with Little's law and the two numbers "
                        "the jobs substrate already serves."
                    ),
                ),
            ],
        ),
        # ── 2. statelessness ─────────────────────────────────────────────
        Section(
            id="statelessness",
            title="Statelessness: where state actually lives",
            lead="This section carries the topic's demo — the two-replica round.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="scl-st-pitch",
                    text=(
                        "A stateless service is not a service without "
                        "state — every useful application has state "
                        "somewhere. It is a service where NO request "
                        "depends on WHICH copy of the service handled "
                        "the previous one: any replica can answer any "
                        "request correctly, because everything the "
                        "answer needs either travels with the request, "
                        "lives outside the process, or is safely "
                        "derivable. That definition makes statelessness "
                        "a placement question, not a purity test — and "
                        "this repo answers it honestly rather than "
                        "ideologically: some state is deliberately "
                        "in-process (for teaching and per-test "
                        "isolation), some is externalized in the "
                        "datastores, and some lives in the browser. The "
                        "demo below introspects the real placement and "
                        "then proves, live, what each choice costs."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-st-split-pitch",
                    text=(
                        "The three placements, with this repo's real "
                        "residents in each:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="scl-st-placement",
                    ordered=False,
                    items=[
                        "In-process — the posts substrate (a dict seeded "
                        "with twelve posts), the scenario flags, the "
                        "auth state (sessions, API keys, refresh "
                        "families), the rate limiter's hit log, chat "
                        "rooms, the caching service's single-flight "
                        "locks: fast, free, and invisible to every other "
                        "replica.",
                        "Externalized — PostgreSQL's tables (the "
                        "Alembic-owned schema), Redis's streams and keys "
                        "(the cache payload, the jobs queue, this "
                        "demo's shared counter), MongoDB's collections: "
                        "one hop away, shared by every replica, and "
                        "surviving every restart.",
                        "Client-side — the session cookie and the JWT: "
                        "state the browser carries, with very different "
                        "server-side consequences, as the demo's "
                        "inventory shows.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="scl-st-wiring-pitch",
                    text=(
                        "Where the in-process half comes from is not a "
                        "mystery — it is the composition root. Every "
                        "process that runs this app builds its own "
                        "world in create_app, and the wiring says so "
                        "out loud: one adapter instance per app, the "
                        "routers never learning its name. The posts "
                        "resource is the canonical example:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-st-main-quote",
                    language="py",
                    caption=(
                        "The composition root builds in-process state per process — "
                        "run two copies of this app and each constructs its own world."
                    ),
                    source="server/guide/main.py",
                    snippet=(
                        "    # The posts resource: the composition root decides WHICH adapter\n"
                        "    # satisfies the domain port — in-memory today, a database from Phase 6\n"
                        "    # on — and wires the use cases over it once, per app (tests get\n"
                        "    # per-app isolation; the routers never learn the adapter's name).\n"
                        "    posts_repository: PostRepository = InMemoryPostRepository()\n"
                        "    app.state.posts_repository = posts_repository"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-st-main-reading",
                    text=(
                        "Read the comment as a scaling contract: per app "
                        "means per PROCESS. In the dev stack exactly one "
                        "process runs this code, so one dict holds the "
                        "posts and nobody notices. Run the same image "
                        "twice — or once under gunicorn with four "
                        "workers, which is four processes in one "
                        "container — and each process seeds its own "
                        "twelve posts and answers from its own dict. A "
                        "post created on replica A does not exist on "
                        "replica B. The scenario store's own module "
                        "docstring states the same contract for the "
                        "flags every demo reads:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-st-scenario-quote",
                    language="py",
                    caption=(
                        "The scenario store's stated contract: one store per app — "
                        "the in-process placement declared in its own words."
                    ),
                    source="server/guide/core/scenario.py",
                    snippet=(
                        "State snapshots (``ScenarioState``) are frozen and validated; updates build\n"
                        "a NEW snapshot by merging the patch into the current one and re-running\n"
                        "pydantic validation, so the store defends its own enum invariant even when\n"
                        "called with untyped input. The store instance lives on ``app.state.scenario``\n"
                        "(one per app — tests get per-app isolation); ``get_scenario_store`` is the\n"
                        "FastAPI dependency routers use to reach it."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-st-demo-pitch",
                    text=(
                        "The demo walks one logical request through two "
                        "replicas and shows the split with real state. "
                        "Because this app runs as one process, it "
                        "constructs what a second replica would "
                        "construct — a fresh ScenarioStore, exactly the "
                        "class create_app wires — and runs the same "
                        "round against a shared Redis counter, which "
                        "needs no simulation at all: the INCR is real, "
                        "the key really lives in the redis container, "
                        "and the second increment's answer really "
                        "contains the first's write."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="scaling:stateless",
                    title="Two replicas, one request",
                    description=(
                        "GET /api/demo/scaling/stateless introspects the "
                        "REAL state placement of the app serving it: the "
                        "process facts (pid, the live scenario flags, "
                        "the posts count) snapshot off the composition "
                        "root · a two-replica round — replica A's world "
                        "is a fresh ScenarioStore (the real class, "
                        "constructed per process exactly as create_app "
                        "does); A serves a PATCH (injectFailure → "
                        "latency); replica B's world is built the same "
                        "way and answers the same request WITHOUT EVER "
                        "SEEING A's write · the same round against the "
                        "shared counter — a real redis INCR on "
                        "guide_demo:scaling:shared: A's INCR returns 1, "
                        "B's returns 2, because the value lives in the "
                        "store, not in either process · a state-placement "
                        "inventory of eleven real rows (posts substrate, "
                        "scenario, auth state, rate budgets, chat rooms, "
                        "cache service, PostgreSQL, Redis, MongoDB, the "
                        "session cookie, the JWT) — each naming where it "
                        "lives and what a replica restart does to it, "
                        "with live counts where the app can read them."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-st-round-reading",
                    text=(
                        "How to read the panel. Steps 2–5 are the "
                        "in-process half: replica A's patch lands in A's "
                        "heap, and replica B — built identically, as a "
                        "second process would be — still answers with "
                        "the defaults. A load balancer that sends the "
                        "user's next request to B has silently lost "
                        "their toggle; that is the entire scaling "
                        "argument against in-process session state in "
                        "one round. Steps 6–9 are the externalized "
                        "half: the key is deleted first — a fresh "
                        "stage — then A increments it to 1 and B "
                        "increments it to 2: B's answer includes "
                        "A's write, which is only possible because "
                        "the number lives in the redis container. "
                        "Then the key gets a "
                        "self-cleaning TTL: the value outlives the "
                        "request, and would outlive a restart of both "
                        "replicas. The construction is quotable from "
                        "the payload builder itself:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-st-builder-quote",
                    language="py",
                    caption=(
                        "The round's honest construction: two real ScenarioStore worlds, "
                        "one shared key — and the live app's stores are never touched."
                    ),
                    source="server/guide/domain/demos/scaling_stateless.py",
                    snippet=(
                        "    replica_a = ScenarioStore()\n"
                        "    replica_b = ScenarioStore()\n"
                        "    # …\n"
                        "    # The write: replica A serves the scenario PATCH the way the real\n"
                        "    # endpoint would — the store's own update/merge machinery, no shortcuts.\n"
                        "    replica_a.update(ScenarioPatch(inject_failure=\"latency\"))"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-st-router-quote",
                    language="py",
                    caption=(
                        "The demo's thin router: snapshots the composition root's facts, "
                        "declares the response model, hands everything to the builder."
                    ),
                    source="server/guide/presentation/routers/demo/scaling.py",
                    snippet=(
                        "@router.get(STATELESS_PATH, response_model=StatelessPanel)\n"
                        "async def read_stateless_panel(\n"
                        "    counter: SharedCounterDep, process: ProcessFactsDep\n"
                        ") -> StatelessPanel:\n"
                        "    \"\"\"Serve the state-placement panel: two replicas, one shared counter.\"\"\"\n"
                        "    return await build_stateless_panel(counter=counter, process=process)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-st-honesty",
                    text=(
                        "The panel's honesty note says the part worth "
                        "memorizing: the two replicas are two state "
                        "worlds inside one process, because that is what "
                        "an honest single-process demo can construct — "
                        "but the outcome is identical to a real second "
                        "process, because the lesson is not about "
                        "processes, it is about where the VALUE lives. "
                        "The scenario write dies with its heap either "
                        "way; the counter lives in the store either "
                        "way. The process facts at the top of the panel "
                        "are real (this request's pid, this process's "
                        "live flags and counts), and the inventory "
                        "table names every store this repo actually "
                        "carries — including the two client-side rows "
                        "with opposite properties: the session cookie's "
                        "id resolves against IN-PROCESS auth state (so "
                        "a restart logs everyone out), while the JWT "
                        "carries its own claims and verifies as long "
                        "as the signing secret is stable (the "
                        "stateless credential)."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-st-production",
                    text=(
                        "What production would require is the mirror of "
                        "this repo's teaching trade. Sessions and rate "
                        "budgets move to Redis (or the rate limiter "
                        "accepts that N replicas enforce N times the "
                        "limit, and the limit is set accordingly); the "
                        "posts substrate moves fully to PostgreSQL "
                        "(the schema is already there — the in-memory "
                        "adapter is a teaching choice); the sticky "
                        "session is the classic workaround that avoids "
                        "the move by pinning each user to one replica "
                        "— trading the scaling you bought for the "
                        "affinity you just reintroduced, and making "
                        "every restart of that replica log out its "
                        "pinned users. Externalizing state costs a "
                        "network hop on every request; keeping it "
                        "in-process costs correctness the moment a "
                        "second copy exists. There is no third option, "
                        "and every scaling architecture is a position "
                        "on exactly that trade."
                    ),
                ),
            ],
        ),
        # ── 3. load balancing ────────────────────────────────────────────
        Section(
            id="load-balancing",
            title="Load balancing",
            blocks=[
                TextBlock(
                    kind="text",
                    id="scl-lb-pitch",
                    text=(
                        "Once there are two replicas, something has to "
                        "choose between them for every request: the load "
                        "balancer. It is the piece that makes N copies "
                        "look like ONE address — the DNS name points at "
                        "the balancer, the balancer points at the "
                        "replicas, and no client knows how many there "
                        "are. The choice of replica is where the "
                        "statelessness question becomes concrete: with "
                        "no shared state, ANY replica answers ANY "
                        "request correctly, so the balancer is free to "
                        "use the dumbest algorithm that spreads load. "
                        "With in-process state, every algorithm is "
                        "wrong sometimes — the right replica is the one "
                        "that already has the user's session, and "
                        "routing elsewhere is the bug the demo just "
                        "walked."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-lb-algos-pitch",
                    text=(
                        "The standard algorithms, and what each assumes:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="scl-lb-algos",
                    ordered=False,
                    items=[
                        "Round-robin — next replica in the ring: trivial, "
                        "fair over time, blind to the replica that is "
                        "slow or the request that is expensive.",
                        "Least-connections — fewest in-flight requests "
                        "wins: still simple, and it self-corrects when "
                        "one replica is slow because its count stays "
                        "high while it catches up.",
                        "IP-hash — hash the client IP to a consistent "
                        "replica: sticky routing by construction, which "
                        "is a feature for in-process sessions and a "
                        "liability the moment a replica dies and its "
                        "users' state dies with it.",
                        "Weighted — split by capacity when replicas are "
                        "uneven (the 8-core box gets twice the traffic "
                        "of the 4-core one): vertical and horizontal "
                        "scaling mixed in one fleet.",
                        "Latency/health-aware — route away from the "
                        "replica failing health checks: the balancer "
                        "becomes the first line of the reliability "
                        "story (topic 39's degradation, one layer up).",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="scl-lb-caddy-pitch",
                    text=(
                        "This repo's real traffic-splitting relative is "
                        "not a load balancer across replicas — it is the "
                        "blue/green flip at the TLS edge, and it is "
                        "worth reading because it is the same MACHINERY "
                        "with a different policy: one address, two "
                        "backends, a rule that decides which one gets "
                        "the traffic. The platform compose's header "
                        "documents the seam exactly:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-lb-flip-quote",
                    language="yaml",
                    caption=(
                        "The repo's real traffic splitter: one shared caddy edge, one flip "
                        "file, a reload instead of a restart — over a platform stack the "
                        "colors both stand on."
                    ),
                    source=".docker/docker-compose-platform.yml",
                    snippet=(
                        "# The TLS edge is\n"
                        "# NOT in this file — it is the infra repo's ONE shared `caddy` container\n"
                        "# (its own compose project at /opt/caddy on the VM, the only publisher of\n"
                        "# 80/443, serving every app on the box), which joins the external\n"
                        "# fdg_frontend network to reach this app's fdg_client_<color> containers by\n"
                        "# name. The seam between the stacks is the FLIP FILE\n"
                        "# ~/fastapi_developers_guide/platform/upstream.caddy (one line:\n"
                        "# reverse_proxy fdg_client_<color>:80): the deploy writes it, the shared\n"
                        "# caddy bind-mounts it read-only, and a release activates the flip with\n"
                        "# `docker exec caddy caddy reload --config /etc/caddy/Caddyfile` — graceful,\n"
                        "# no TLS blip.\n"
                        "# …\n"
                        "name: fdg_platform\n"
                        "\n"
                        "services:\n"
                        "  postgres:\n"
                        "    image: postgres:17"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-lb-flip-reading",
                    text=(
                        "Notice what the flip shares with a load "
                        "balancer and what it adds. Shared: one public "
                        "address, a routing decision made per request "
                        "by a component the client never sees, and "
                        "health as the input (the deploy only flips "
                        "after the new color passes its checks — topic "
                        "37's boot gates). Added: the decision is "
                        "ALL-OR-NOTHING per release — blue serves "
                        "everything until the flip, green serves "
                        "everything after — where a balancer across "
                        "replicas splits traffic continuously. The two "
                        "compose naturally: the same caddy that flips "
                        "between releases could load-balance across "
                        "green's N server containers with one more "
                        "line, and the same properties apply — the "
                        "flip is graceful because caddy reloads instead "
                        "of restarting, exactly the property topic "
                        "37's graceful-shutdown section built into the "
                        "server underneath it. And the prerequisite for "
                        "splitting traffic between blue and green at "
                        "all is that either color can answer any "
                        "request: statelessness again, one level up, "
                        "with the platform's external volumes carrying "
                        "the data both colors share."
                    ),
                ),
            ],
        ),
        # ── 4. replicas ──────────────────────────────────────────────────
        Section(
            id="replicas",
            title="Replicas: copies of the work",
            blocks=[
                TextBlock(
                    kind="text",
                    id="scl-rp-pitch",
                    text=(
                        "A replica is a copy of the stateless tier — "
                        "same image, same code, same configuration, its "
                        "own heap. Docker Compose makes the copy cheap: "
                        "`docker compose up --scale server=4` runs four "
                        "containers of the same service, and the "
                        "compose specification's `deploy.replicas` field "
                        "says the same thing declaratively for stacks "
                        "that schedule it (Swarm, Kubernetes — whose "
                        "absence from this repo topic 37 taught as an "
                        "honest, verifiable fact). What scaling DOES "
                        "change is everything the copies share: the "
                        "database they all point at, the network they "
                        "arrive over, and the address that fronts them. "
                        "This repo's stacks demonstrate all three "
                        "relationships for real."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-rp-worker-pitch",
                    text=(
                        "The dev stack's clearest replica-shaped fact is "
                        "a process copy that already runs: the arq "
                        "worker. It is the same image, the same "
                        "bind-mounted code, and the same Redis as the "
                        "server — a second PROCESS that never serves "
                        "HTTP but shares every store:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-rp-worker-quote",
                    language="yaml",
                    caption=(
                        "A replica of the work, one process over: same image, same code, "
                        "same stores — only the command differs."
                    ),
                    source=".docker/docker-compose.yml",
                    snippet=(
                        "  arq-worker:\n"
                        "    image: fdg_server_dev\n"
                        "    container_name: fastapi_developers_guide_arq_worker_dev\n"
                        "    restart: unless-stopped\n"
                        "    working_dir: /app\n"
                        "    command: sh -c \"uv sync --locked && .venv/bin/arq guide.worker.WorkerSettings\"\n"
                        "    environment:\n"
                        "      - FDG_ENV=dev\n"
                        "      - FDG_DATABASE_URL=postgresql+asyncpg://postgres:guide@postgres:5432/guide\n"
                        "      - FDG_REDIS_URL=redis://redis:6379\n"
                        "      - FDG_MONGO_URL=mongodb://mongo:27017"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-rp-worker-reading",
                    text=(
                        "That service is horizontal scaling of WORK "
                        "rather than of requests — the pattern a queue "
                        "worker fleet rides: scale workers independently "
                        "of the API because their bottleneck is "
                        "different (the API is bounded by request "
                        "latency, the workers by queue depth — topic "
                        "29, and the capacity section below returns to "
                        "exactly that distinction). The compose "
                        "mechanics it demonstrates are the same ones "
                        "`--scale` automates: one service definition, N "
                        "containers, shared dependencies. The one "
                        "honest caveat with `--scale` on THIS service "
                        "would be the container_name — a fixed name "
                        "admits exactly one container, which is why "
                        "scaled services drop it and let compose "
                        "number them."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-rp-prod-pitch",
                    text=(
                        "The production stacks take the same idea to "
                        "the release level: two whole app stacks, one "
                        "per color, sharing the platform's datastores. "
                        "The per-release compose's header states the "
                        "replication rule the whole deploy rides on:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-rp-prod-quote",
                    language="yaml",
                    caption=(
                        "Replication at release granularity: one compose file, two projects, "
                        "colors that never share a name — the server container_name carries the color."
                    ),
                    source=".docker/docker-compose.prod.yml",
                    snippet=(
                        "# PER-RELEASE APP STACK — booted per deploy under the project of one color:\n"
                        "#   COLOR=blue  IMAGE_TAG=sha-abc1234 docker compose -p fdg_blue  -f <this file> up -d --wait\n"
                        "#   COLOR=green IMAGE_TAG=sha-def5678 docker compose -p fdg_green -f <this file> up -d --wait\n"
                        "# The deploy script ALWAYS exports COLOR deliberately; the ${COLOR:-blue}\n"
                        "# default below only exists so a bare local `up` boots something (blue).\n"
                        "# There is deliberately NO top-level name: the -p flag names the project,\n"
                        "# and the two colors must never share one.\n"
                        "#\n"
                        "# The persistent platform (postgres + redis + mongo, project fdg_platform)\n"
                        "# lives in docker-compose-platform.yml and is booted BEFORE any app stack:\n"
                        "# the server's startup migration is best-effort, so the boot race is won by\n"
                        "# deploy ORDERING (platform `up -d --wait` fully healthy first) — depends_on\n"
                        "# cannot cross compose files.\n"
                        "# …\n"
                        "services:\n"
                        "  server:\n"
                        "    image: \"ghcr.io/mayank-uk/fastapi-guide-server:${IMAGE_TAG:?IMAGE_TAG is required}\"\n"
                        "    container_name: fdg_server_${COLOR:-blue}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-rp-honest",
                    text=(
                        "And the honest fact about the dev stack: it "
                        "runs ONE server process — uvicorn --reload, "
                        "single worker, the reload watcher being the "
                        "only other process with the code loaded. "
                        "Production's image runs gunicorn with uvicorn "
                        "workers, which is replication INSIDE one "
                        "container: N processes, one shared port, "
                        "gunicorn playing load balancer to its own "
                        "children. Every one of those workers is a "
                        "full create_app with its own in-process world, "
                        "which is why the statelessness section is the "
                        "prerequisite for this one: scaling the app "
                        "tier multiplies whatever placement you chose. "
                        "The demo's inventory is the checklist — every "
                        "in-process row is a thing the second worker "
                        "already cannot see, and every externalized row "
                        "is a thing it can."
                    ),
                ),
            ],
        ),
        # ── 5. data at scale ─────────────────────────────────────────────
        Section(
            id="data-at-scale",
            title="Data at scale",
            blocks=[
                TextBlock(
                    kind="text",
                    id="scl-da-pitch",
                    text=(
                        "The stateless tier scales by cheap copies; "
                        "the data tier does not, because every replica "
                        "of the app points at the SAME database, and a "
                        "database cannot be copied the way a container "
                        "can — its copies would disagree. So data "
                        "scaling is a different discipline with a "
                        "strict order of operations: first make the "
                        "one database do less work per query (indexes), "
                        "then make its connections a bounded, shared "
                        "resource (pooling), then read from copies "
                        "(read replicas), then split by key (sharding) "
                        "— each step an order of magnitude more "
                        "expensive than the one before it, which is why "
                        "the order matters."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-da-index-pitch",
                    text=(
                        "Indexes are the first lever because they are "
                        "pure win until they are not: a b-tree turns a "
                        "full-table scan into a logarithmic descent, "
                        "at the cost of write amplification (every "
                        "index maintained per INSERT) and disk. This "
                        "repo's schema migration says the important "
                        "things about them in its own voice — including "
                        "the two facts teams forget: PostgreSQL does "
                        "not index foreign keys for you, and an index "
                        "can cover PART of a table:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-da-index-quote",
                    language="py",
                    caption=(
                        "The schema's own index doctrine: FK indexes by hand, and a partial "
                        "index that never pays for the rows it will never serve."
                    ),
                    source="server/alembic/versions/0001_guide_schema.py",
                    snippet=(
                        "    # PostgreSQL does NOT auto-index foreign keys: every FK join and\n"
                        "    # every ON DELETE check would otherwise scan the table. One b-tree\n"
                        "    # per FK, by hand.\n"
                        "    op.create_index(\"ix_posts_author_id\", \"posts\", [\"author_id\"], unique=False)\n"
                        "    op.create_index(\"ix_comments_post_id\", \"comments\", [\"post_id\"], unique=False)\n"
                        "    # A PARTIAL index: only published posts are covered, so drafts never\n"
                        "    # bloat the tree the \"newest published first\" query reads.\n"
                        "    op.create_index(\n"
                        "        \"ix_posts_published_created_at\",\n"
                        "        \"posts\",\n"
                        "        [\"created_at\"],\n"
                        "        unique=False,\n"
                        "        postgresql_where=sa.text(\"status = 'published'\"),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-da-index-reading",
                    text=(
                        "The partial index is the scaling lesson in "
                        "miniature: the newest-published-first query — "
                        "the one the caching topic made the canonical "
                        "cached page — reads only published posts, so "
                        "the index covers only published posts and the "
                        "drafts never bloat the tree. Indexing is "
                        "query-shaped, not table-shaped: you index the "
                        "questions, not the data. Topic 16's "
                        "schema-explorer demo introspects every one of "
                        "these from the live database (tables, columns, "
                        "checks, indexes including the partial one), "
                        "and topic 17's EXPLAIN ANALYZE stop shows the "
                        "plan flipping from a scan to an index descent "
                        "— measurement being the only honest way to "
                        "know an index is doing its job."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-da-pool-pitch",
                    text=(
                        "Pooling is the second lever, and it is "
                        "REPLICAS times CONNECTIONS arithmetic: every "
                        "app process holds a small pool of database "
                        "connections, so twenty replicas with a "
                        "default pool of five are one hundred "
                        "connections against a PostgreSQL whose "
                        "`max_connections` is typically one hundred. "
                        "The pool is the bulkhead that keeps that "
                        "multiplication honest — this repo's engine "
                        "factory, with the reconnect behavior replicas "
                        "depend on:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-da-pool-quote",
                    language="py",
                    caption=(
                        "One engine per process, pre-ping reconnects: the pool every replica "
                        "carries against the shared database."
                    ),
                    source="server/guide/data/db/engine.py",
                    snippet=(
                        "def create_db_engine(config: AppConfig) -> AsyncEngine:\n"
                        "    \"\"\"Build the process's async engine from the app config's URL rail.\n"
                        "\n"
                        "    ``pool_pre_ping`` so a PostgreSQL restart between requests surfaces as\n"
                        "    a clean reconnect instead of a stale-socket error; pool sizing stays\n"
                        "    at SQLAlchemy's defaults until topic 38 measures real load.\n"
                        "    \"\"\"\n"
                        "    return create_async_engine(config.database_url, pool_pre_ping=True)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-da-pool-reading",
                    text=(
                        "`pool_pre_ping` is the scaling-relevant half "
                        "of that function: a replica whose pooled "
                        "connection went stale during a database "
                        "restart reconnects cleanly instead of failing "
                        "the request — statelessness of the "
                        "CONNECTION, one connection at a time. Topic "
                        "38 measured this pool live: SQLAlchemy's "
                        "AsyncAdaptedQueuePool at its default five "
                        "connections with a thirty-second checkout "
                        "timeout, which means one process can hold at "
                        "most five of the database's connections and "
                        "queues the rest. Size pools per the Little's "
                        "law arithmetic in the capacity section, not "
                        "by guesswork — and remember the pool is per "
                        "PROCESS, so the fleet's real connection count "
                        "is pool size times replicas."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-da-beyond",
                    text=(
                        "Read replicas and sharding are the levers "
                        "this repo deliberately does not run, and they "
                        "deserve honest prose rather than a fabricated "
                        "exhibit. A read replica is a second PostgreSQL "
                        "continuously fed the primary's write-ahead "
                        "log: reads scale horizontally (point the "
                        "read-heavy paths at it), writes do not, and "
                        "the cost is replication lag — a read-your-"
                        "writes violation the app must decide to "
                        "tolerate (a feed page) or route around (the "
                        "confirmation page after a write). Sharding "
                        "splits the data itself by a key (user id, "
                        "tenant, region) across independent databases: "
                        "it removes the single-writer ceiling entirely "
                        "and charges the full price — cross-shard "
                        "queries become application code, transactions "
                        "stop spanning shards, and resharding a live "
                        "system is one of the hardest operations in "
                        "the field. The pragmatic order this repo "
                        "models by restraint: index, pool, cache "
                        "(topic 21), and only then consider replicas "
                        "of the data — most systems that think they "
                        "need sharding need an index and a cache."
                    ),
                ),
            ],
        ),
        # ── 6. CDN / edge ────────────────────────────────────────────────
        Section(
            id="cdn-edge",
            title="CDN and the edge",
            blocks=[
                TextBlock(
                    kind="text",
                    id="scl-cd-pitch",
                    text=(
                        "The cheapest replica is the one you do not "
                        "run: the edge is every cache between the "
                        "browser and the origin — the browser's own "
                        "cache, the CDN's points of presence, the "
                        "proxy in front of the app. Edge scaling works "
                        "only on content that can be cached SAFELY, "
                        "and safe caching is a property of how you "
                        "NAME things. This repo ships the whole "
                        "pattern for real: Vite emits content-hashed "
                        "asset filenames, and the client's nginx "
                        "answers them with a one-year immutable "
                        "cache header:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-cd-assets-quote",
                    language="nginx",
                    caption=(
                        "Immutable hashed assets: the hash IS the cache key, so the "
                        "cache-for-a-year header can never serve a stale file."
                    ),
                    source=".docker/client/nginx.conf",
                    snippet=(
                        "    # Hashed static assets (Vite emits content-hashed filenames under\n"
                        "    # /assets/) — the hash IS the cache key, so cache forever.\n"
                        "    location /assets/ {\n"
                        "        expires 1y;\n"
                        "        add_header Cache-Control \"public, immutable\";\n"
                        "    }"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-cd-assets-reading",
                    text=(
                        "Why that header is safe is the entire trick: "
                        "the JavaScript bundle's filename contains a "
                        "hash of its CONTENT (index-CTcWVSen.js — the "
                        "topic-37 client build's real name), so a new "
                        "deploy produces a NEW filename. A cache entry "
                        "for the old name can never be wrong — the "
                        "bytes it holds are the only bytes that "
                        "filename ever named. Content addressing turns "
                        "caching from a staleness risk into a "
                        "correctness guarantee, which is why the "
                        "caching topic's section on hashed filenames "
                        "called it the one unconditionally safe "
                        "cache. A CDN in front of this origin would "
                        "replicate the same guarantee into its points "
                        "of presence: the same immutable header, "
                        "cached at the edge, users served from the "
                        "nearby POP instead of the origin. The one "
                        "file that must NOT be cached that way is the "
                        "one that names all the others:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-cd-index-quote",
                    language="nginx",
                    caption=(
                        "index.html revalidates every time: the one non-hashed file, "
                        "so a deploy is visible the moment it flips."
                    ),
                    source=".docker/client/nginx.conf",
                    snippet=(
                        "    # index.html must always be revalidated so deploys are picked up at once.\n"
                        "    location = /index.html {\n"
                        "        add_header Cache-Control \"no-cache, no-store, must-revalidate\";\n"
                        "        add_header Pragma \"no-cache\";\n"
                        "        expires 0;\n"
                        "    }"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-cd-index-reading",
                    text=(
                        "index.html references the hashed bundles by "
                        "name, so it is the single file whose "
                        "freshness gates every deploy: revalidate it "
                        "always (no-cache means revalidate, not "
                        "never-store), and a user's next navigation "
                        "fetches the new HTML, which references the "
                        "new hashes, which miss the cache exactly "
                        "once and then cache for a year. Deploy "
                        "visibility in one file; permanence in "
                        "everything else. The same file's gzip block "
                        "carries the compression half of the edge "
                        "story, with a comment that names the layering "
                        "honestly:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-cd-gzip-quote",
                    language="nginx",
                    caption=(
                        "App-level gzip as belt-and-suspenders — the central caddy edge "
                        "already compresses domain-wide, and skips already-encoded upstreams."
                    ),
                    source=".docker/client/nginx.conf",
                    snippet=(
                        "    # Gzip text assets (belt-and-suspenders: the central Caddy edge already\n"
                        "    # compresses, and skips already-encoded upstreams).\n"
                        "    gzip on;\n"
                        "    gzip_types text/plain text/css application/javascript application/json image/svg+xml;\n"
                        "    gzip_min_length 1024;"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-cd-coda",
                    text=(
                        "That comment is the edge doctrine in two "
                        "lines: compression happens ONCE, at the "
                        "outermost hop (the shared caddy serving "
                        "zstd/gzip domain-wide), and inner layers "
                        "neither re-compress already-encoded responses "
                        "nor fight the edge for the job. Topic 38 "
                        "measured the win on real payloads (gzip cut "
                        "the largest API response by 63.8 percent); "
                        "the edge multiplies that win by every "
                        "geographical hop it removes. What stays at "
                        "the origin, deliberately, is everything "
                        "dynamic: the /api/ proxy passes straight "
                        "through to the server, because API answers "
                        "carry per-request truth (a scenario flag, a "
                        "request id, a live count) that no cache may "
                        "serve for you — the caching topic's "
                        "what-not-to-cache rule, enforced here by "
                        "configuration."
                    ),
                ),
            ],
        ),
        # ── 7. backpressure ──────────────────────────────────────────────
        Section(
            id="backpressure",
            title="Backpressure and shedding",
            blocks=[
                TextBlock(
                    kind="text",
                    id="scl-bp-pitch",
                    text=(
                        "Scaling's last resort is refusing work, and "
                        "it deserves first-class design rather than "
                        "accident. Backpressure is the system telling "
                        "its producers to slow down — a bounded queue "
                        "that fills, a connection count that caps, a "
                        "429 that says when to come back — instead of "
                        "absorbing load until memory or latency fails "
                        "somewhere you did not choose. Topic 39 framed "
                        "the same mechanisms as reliability (bulkheads "
                        "and shedding against overload); scaling adds "
                        "the framing that matters here: backpressure "
                        "is how a system at capacity stays AT capacity "
                        "instead of past it, degrading the edges of "
                        "its workload rather than the whole. This "
                        "repo's realtime manager carries the pattern "
                        "in its most concrete form — two named "
                        "ceilings, enforced atomically:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-bp-ceiling-quote",
                    language="py",
                    caption=(
                        "The realtime ceilings as named constants: members per room, "
                        "queued messages per connection — and the join that enforces one of them under a lock."
                    ),
                    source="server/guide/domain/realtime/manager.py",
                    snippet=(
                        "MAX_ROOM_CONNECTIONS: Final[int] = 8\n"
                        "\"\"\"Members per room — the full-room ceiling (rejection close code 1013).\"\"\"\n"
                        "\n"
                        "PER_CONNECTION_QUEUE: Final[int] = 32\n"
                        "\"\"\"Queued wire messages per connection — the slow-consumer ceiling.\"\"\"\n"
                        "# …\n"
                        "        async with self._join_lock:\n"
                        "            members = self._rooms.setdefault(room, {})\n"
                        "            if len(members) >= self._max_room_connections:\n"
                        "                raise RoomFullError(room, self._max_room_connections)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-bp-ceiling-reading",
                    text=(
                        "Every piece of that quote is a scaling "
                        "decision made explicit. The constants are "
                        "NAMED and documented — a ceiling nobody can "
                        "quote is a ceiling nobody sized. The join "
                        "check runs UNDER THE LOCK so two concurrent "
                        "joins cannot both claim the last slot — "
                        "admission control is only honest if it is "
                        "atomic. And the per-connection queue is the "
                        "subtler half: topic 28 taught the retire "
                        "mechanics (a member whose queue is full has "
                        "fallen a whole queue-depth behind, and "
                        "broadcast retires it with close code 1013 "
                        "rather than ever awaiting it) — the sender "
                        "never slows down for one slow consumer, "
                        "because the queue's boundedness already made "
                        "that decision. That is backpressure's "
                        "essential trade: someone feels the pressure "
                        "(the slow consumer gets disconnected, the "
                        "throttled client gets a 429), and the "
                        "decision of WHO feels it was made in advance, "
                        "deliberately, instead of by whichever "
                        "resource happens to exhaust first."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-bp-limiter-pitch",
                    text=(
                        "The HTTP-side version is the rate limiter, "
                        "and its engine shows the other property a "
                        "shed needs: denial that costs the system "
                        "nothing and extends nothing. The hit method "
                        "records allowed requests and refuses — "
                        "without recording — the ones past budget:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-bp-limiter-quote",
                    language="py",
                    caption=(
                        "Admission control arithmetic: a hit past budget is denied from the "
                        "window's own numbers — and a denial records nothing."
                    ),
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
                    id="scl-bp-limiter-reading",
                    text=(
                        "The verdict rides out as the 429 envelope "
                        "with Retry-After (topic 25 built the "
                        "dependency; topic 39 read it as a shed). "
                        "Scaling adds the deployment arithmetic the "
                        "demo's inventory row states plainly: the "
                        "budget is per PROCESS, so N replicas behind "
                        "a balancer enforce N times the configured "
                        "limit — five hits per ten seconds becomes "
                        "twenty across four replicas, and a client "
                        "hammering one address round-robins its way "
                        "to four separate budgets. Fixing that is "
                        "the state-placement section's trade again: "
                        "shared budgets live in Redis (the limiter's "
                        "own hit log externalized), and the cost is "
                        "one Redis round trip per request. Pools are "
                        "the quiet third member of the family — the "
                        "five-connection database pool from the last "
                        "section is a bulkhead whose fullness queues "
                        "requests up to the thirty-second timeout, "
                        "which is backpressure by waiting rather than "
                        "by refusing, and topic 38 measured both "
                        "halves of it."
                    ),
                ),
            ],
        ),
        # ── 8. capacity ──────────────────────────────────────────────────
        Section(
            id="capacity",
            title="Capacity: how much is enough",
            blocks=[
                TextBlock(
                    kind="text",
                    id="scl-cp-pitch",
                    text=(
                        "Every scaling decision above needs one number "
                        "as input: how much load can the current stack "
                        "actually carry? Capacity planning is "
                        "measurement plus arithmetic, and the "
                        "arithmetic has been the same since 1961. "
                        "Little's law says that in any stable system, "
                        "the average number of items inside (L) equals "
                        "the arrival rate (λ) times the average time "
                        "each spends inside (W): L = λ × W. It is "
                        "famous because it needs almost no assumptions "
                        "— no distribution, no topology — and because "
                        "it converts the three numbers you can measure "
                        "into each other."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-cp-littles",
                    text=(
                        "Run it against this stack's own numbers. "
                        "Topic 38 measured the server answering in the "
                        "low milliseconds; suppose a realistic "
                        "database-touching request averages 40 "
                        "milliseconds of latency (W). At 100 requests "
                        "per second (λ), the system holds L = 100 × "
                        "0.04 = 4 requests in flight at any instant — "
                        "and four in-flight requests against a "
                        "five-connection pool means the pool is nearly "
                        "saturated already. Push to 250 per second and "
                        "L = 10: five requests hold the pool and five "
                        "wait, and the waiting shows up as latency, "
                        "which increases W, which increases L — the "
                        "queueing spiral topic 39 called cascading "
                        "failure, here visible as arithmetic. Little's "
                        "law tells you WHEN to add capacity (when L "
                        "approaches the bulkheads you set in the "
                        "backpressure section) and which lever moves "
                        "the equation: replicas divide λ per copy; "
                        "the pool bounds L per copy; latency work "
                        "(topic 38) shrinks W everywhere. And the "
                        "caching topic already demonstrated the "
                        "cheapest capacity move in this whole guide — "
                        "the stampede round's eight concurrent "
                        "requests coalesced to ONE origin fetch, "
                        "dividing the origin's effective λ by eight "
                        "with no new hardware at all."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-cp-numbers-pitch",
                    text=(
                        "For the queue-shaped part of the system, "
                        "capacity has two numbers, and this repo "
                        "serves them from the live Redis — the jobs "
                        "substrate's queue stats, depth and oldest "
                        "age, in one adapter method:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-cp-numbers-quote",
                    language="py",
                    caption=(
                        "The two numbers, served live: queue depth from ZCARD, and the "
                        "oldest job's wait from the lowest score in the zset."
                    ),
                    source="server/guide/data/jobs/arq_jobs.py",
                    snippet=(
                        "    async def queue_stats(self) -> QueueStatsRow:\n"
                        "        \"\"\"The two numbers: ZCARD depth, oldest age from the lowest score.\"\"\"\n"
                        "        with _map_jobs_failures(\"queue_stats\"):\n"
                        "            pool = await self._pool()\n"
                        "            depth = int(await pool.zcard(QUEUE_KEY))\n"
                        "            oldest = await pool.zrange(QUEUE_KEY, start=0, end=0, withscores=True)\n"
                        "            # …\n"
                        "            oldest_score = float(oldest[0][1]) if oldest else None\n"
                        "            return QueueStatsRow(\n"
                        "                depth=depth,\n"
                        "                oldest_age_seconds=oldest_age_seconds(_now_ms(), oldest_score),\n"
                        "            )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-cp-numbers-reading",
                    text=(
                        "Depth alone is ambiguous — a hundred queued "
                        "jobs is a crisis or a Tuesday depending on "
                        "how fast they drain — and age alone is "
                        "ambiguous the other way (one stuck job can "
                        "be arbitrarily old). Together they are a "
                        "complete capacity signal: depth rising with "
                        "age rising means the workers are underwater "
                        "(scale the fleet); depth rising with age "
                        "flat means a burst is draining (scale "
                        "nothing); depth flat with one ancient job "
                        "means a poison message (topic 29's DLQ). "
                        "That is why topic 29 called them the two "
                        "observability numbers, and the same pair "
                        "generalizes to every queue in a scaled "
                        "system — the pool's checked-out count and "
                        "wait time, the balancer's in-flight requests "
                        "and their p95, the replica's event-loop lag "
                        "and queue depth. Two numbers, a threshold on "
                        "each, and a decision wired to the crossing: "
                        "that is a capacity plan."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-cp-loadtest",
                    text=(
                        "The measurement half is load testing, and "
                        "this repo's stance is the one the whole "
                        "guide practices: measure the real thing, "
                        "bounded, and distrust the average. The "
                        "performance topic's bench is the harness "
                        "philosophy in miniature — real bytes, real "
                        "compression, real probes, every row measured "
                        "on the request that reports it — and a load "
                        "test is the same discipline sustained: "
                        "constant arrival rate against the real stack "
                        "(the scripted curl loops this guide's "
                        "terminal companions already write), stepping "
                        "up until a signal crosses its threshold. "
                        "Watch the percentile, not the mean — the "
                        "pool's thirty-second checkout tail is "
                        "invisible in a mean and decisive in a p99 — "
                        "and watch the two numbers while you step. "
                        "The load test's job is not to prove the "
                        "system fast; it is to find the FIRST "
                        "bulkhead that fills, so that when real "
                        "traffic doubles you already know which "
                        "ceiling hits first and what you will do "
                        "about it."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-cp-coda",
                    text=(
                        "The topic in one sequence, which is also "
                        "the order to apply it in: measure (Little's "
                        "law over real latencies), place state "
                        "(externalize what replicas must share, "
                        "accept the hop), balance (any replica, any "
                        "request), replicate (copies of the stateless "
                        "tier, workers and web alike), index and pool "
                        "the data tier before dreaming of sharding "
                        "it, cache the immutable at the edge and "
                        "revalidate the one file that names the rest, "
                        "shed with named ceilings when capacity is "
                        "reached, and watch the two numbers that tell "
                        "you when to do it all again. None of it is "
                        "exotic; all of it is this repo's actual "
                        "configuration, read at fleet size."
                    ),
                ),
            ],
        ),
        # ── 9. Terminal companion ────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead=(
                "Scaling from a shell: the two-replica round, the state-placement "
                "inventory, the shared counter through both ports, and this topic's shape."
            ),
            blocks=[
                TextBlock(
                    kind="text",
                    id="scl-terminal-intro",
                    text=(
                        "Five stops on the running stack: the process "
                        "facts and the full two-replica round, the "
                        "state-placement inventory with its live "
                        "counts, the shared counter's survival across "
                        "two separate requests, this topic's own "
                        "shape, and the health receipt — the stack "
                        "that taught scaling never going down to do "
                        "it."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-terminal-round",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the process facts, then the two-replica round, step by step\n"
                        "curl -s localhost:8000/api/demo/scaling/stateless | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for f in panel[\"process\"]:\n"
                        "    print(\"%-14s %s\" % (f[\"id\"], f[\"value\"]))\n"
                        "print()\n"
                        "for r in panel[\"replicaRound\"]:\n"
                        "    print(\"%-2d  %-9s %-46s %s\" % (r[\"step\"], r[\"side\"], r[\"label\"], r[\"observed\"]))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-terminal-inventory",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the state-placement inventory: every real store, placed\n"
                        "curl -s localhost:8000/api/demo/scaling/stateless | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for row in panel[\"inventory\"]:\n"
                        "    print(\"%-16s %-13s %s\" % (row[\"id\"], row[\"placement\"], row[\"evidence\"][:70]))\n"
                        "print()\n"
                        "for v in panel[\"verdicts\"]:\n"
                        "    print(\"%-12s %s\" % (v[\"id\"], v[\"value\"][:80]))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-terminal-counter",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the shared counter survives even THIS request ending:\n"
                        "# two separate GETs, each resetting the stage first — the verdict rows\n"
                        "# always end at 2, and the key itself lives on under its ttl\n"
                        "curl -s localhost:8000/api/demo/scaling/stateless | python3 -c '\n"
                        "import json, sys\n"
                        "r = json.load(sys.stdin)[\"replicaRound\"]\n"
                        "print(\"round 1:\", r[6][\"observed\"], \"then\", r[7][\"observed\"])'\n"
                        "curl -s localhost:8000/api/demo/scaling/stateless | python3 -c '\n"
                        "import json, sys\n"
                        "r = json.load(sys.stdin)[\"replicaRound\"]\n"
                        "print(\"round 2:\", r[6][\"observed\"], \"then\", r[7][\"observed\"], \"— fresh stage, same proof\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-terminal-shape",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — this topic's shape, and the panel through the client proxy\n"
                        "curl -s localhost:8000/api/content | python3 -c '\n"
                        "import json, sys\n"
                        "index = json.load(sys.stdin)\n"
                        "print(len(index[\"topics\"]), \"topics /\", len(index[\"groups\"]), \"groups\")'\n"
                        "curl -s localhost:8000/api/content/scaling | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'\n"
                        "curl -s localhost:5174/api/demo/scaling/stateless \\\n"
                        "  | python3 -c 'import json,sys; p=json.load(sys.stdin); print(\"proxy round:\", p[\"replicaRound\"][7][\"observed\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="scl-terminal-health",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the receipt: the stack that taught scaling is still fast\n"
                        "curl -s -o /dev/null -w 'health: %{http_code} in %{time_total}s\\n' localhost:8000/api/health"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="scl-terminal-coda",
                    text=(
                        "Stops 1–3 are the topic's argument in one "
                        "payload: the flags a second replica cannot "
                        "see, the counter it can, and the inventory "
                        "naming where every store in this application "
                        "actually lives. Stop 4 closes the loop the "
                        "family always closes — the topic is served "
                        "through the client proxy by the same stack "
                        "whose placement it just audited — and stop 5 "
                        "is the receipt. Scaling was taught without a "
                        "single restart."
                    ),
                ),
            ],
        ),
    ],
)
