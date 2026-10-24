"""Topic 43 — Advanced architecture: the whole system, honestly mapped.

The final capstone. Forty-two topics built the pieces; this one stands
back and asks the system-level questions: where each consistency
guarantee actually lives (ACID inside PostgreSQL, eventual consistency
across streams and the outbox), what the domain vocabulary this repo
has used since topic 11 is called in the wider world (entities, value
objects, aggregates, ports — the DDD names, mapped onto real files),
why the monolith-first argument is this repository itself, what really
passes between services when a request does not, how a saga undoes a
distributed operation step by step, what CQRS honestly means at this
repo's scale, how event sourcing stores what HAPPENED instead of what
IS, and how one request id crosses every boundary it meets. The two
demos drive the REAL patterns substrate this topic added under
``guide/domain/patterns/`` — the saga coordinator (arch:saga, inline
in the sagas section) and the event store with its pure fold
(arch:eventstore, inline in the event sourcing section) — the same
way the reliability topic drives its real circuit breaker.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="advanced-architecture",
    title="Advanced architecture",
    subtitle=(
        "The system-level capstone: a consistency map of where every "
        "guarantee in this stack actually lives (ACID inside PostgreSQL's "
        "transactions, eventual consistency across Redis streams and the "
        "transactional outbox, CAP as the prose constraint behind both) · the "
        "domain-driven design vocabulary mapped file by file onto this repo's "
        "own layout (entities, value objects, aggregates — and the ports that "
        "have been Protocols since topic 11) · the monolith-first argument "
        "made by this very repository (one deployable, modular inside, the "
        "deploy pipeline as the evidence) · what actually passes between "
        "services when no request crosses the boundary (streams, outbox "
        "events, idempotent consumption) · sagas driven LIVE through the real "
        "coordinator — a committed four-step run, then a failing run whose "
        "compensations unwind in reverse with per-step ledger proof · CQRS "
        "taught honestly (the read/write shapes this repo really has, and why "
        "it stops short of the full pattern) · event sourcing driven LIVE "
        "through the real event store — append five facts, fold the state "
        "back out event by event, rebuild it in a second store, refuse a "
        "stale writer · and tracing across every boundary, from the "
        "x-request-id round trip to the correlation ids events and jobs "
        "carry."
    ),
    group="capstones",
    order=43,
    sections=[
        # ── 1. the consistency map ───────────────────────────────────────
        Section(
            id="consistency-map",
            title="The consistency map",
            lead="Where every guarantee in this stack actually lives.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="aa-cm-pitch",
                    text=(
                        "Consistency is not one property a system has or "
                        "lacks; it is a MAP of smaller guarantees, each one "
                        "owned by a specific mechanism in a specific place. "
                        "This stack has exactly two kinds of places. Inside "
                        "one PostgreSQL transaction, the database gives you "
                        "ACID — atomicity (all writes commit or none do), "
                        "consistency (every constraint is checked against "
                        "the committed state), isolation (concurrent "
                        "transactions do not read each other's half-done "
                        "work), durability (a commit survives the crash "
                        "that follows it). The migration that built this "
                        "repo's schema is the map's first region: every "
                        "CHECK, UNIQUE, and foreign key in it is a "
                        "consistency rule the DATABASE enforces, not the "
                        "application — which is exactly why topic 16 wrote "
                        "them as constraints rather than validation code."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-cm-sql-quote",
                    language="sql",
                    caption=(
                        "ACID's local region: constraints the database "
                        "enforces inside every transaction — not lines of "
                        "application code that could be forgotten."
                    ),
                    source="server/alembic/versions/0001_guide_schema.py",
                    snippet=(
                        "sa.CheckConstraint(\n"
                        "    \"status IN ('draft', 'published')\", "
                        "name=op.f(\"ck_posts_status_domain\")\n"
                        "),\n"
                        "sa.CheckConstraint(\n"
                        "    \"char_length(title) BETWEEN 1 AND 120\", "
                        "name=op.f(\"ck_posts_title_length\")\n"
                        "),\n"
                        "sa.ForeignKeyConstraint(\n"
                        "    [\"author_id\"],\n"
                        "    [\"authors.id\"],\n"
                        "    name=op.f(\"fk_posts_author_id_authors\"),\n"
                        "    ondelete=\"RESTRICT\",\n"
                        "),\n"
                        "sa.PrimaryKeyConstraint(\"id\", name=op.f(\"pk_posts\")),\n"
                        "sa.UniqueConstraint(\"slug\", name=op.f(\"uq_posts_slug\")),"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-cm-second-region",
                    text=(
                        "The second region begins the moment a write has to "
                        "reach a SECOND store — publish an event to a Redis "
                        "stream after committing a post to PostgreSQL, say. "
                        "No transaction spans both, so ACID is gone by "
                        "construction; what replaces it is EVENTUAL "
                        "consistency, and the honest engineering question is "
                        "never 'how do we make it immediate' (you cannot) but "
                        "'what intermediate states are allowed, and who "
                        "cleans up the duplicates.' Topic 22's transactional "
                        "outbox is this repo's answer and the map's second "
                        "region: the business write and its event commit in "
                        "ONE PostgreSQL transaction, and a relay publishes "
                        "the event afterwards — which means the event "
                        "arrives late, and if the relay dies between "
                        "publishing and marking, it arrives TWICE."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-cm-relay-quote",
                    language="py",
                    caption=(
                        "The eventual region: poll, publish, mark — three "
                        "steps with real gaps between them, single-flighted "
                        "by one lock."
                    ),
                    source="server/guide/domain/messaging/outbox_service.py",
                    snippet=(
                        "async with self._relay_lock:\n"
                        "    self._cycle += 1\n"
                        "    discovered = await self._outbox.unpublished(request.batch)\n"
                        "    published: list[PublishedEntryRow] = []\n"
                        "    for row in discovered:\n"
                        "        entry_id = await self._producer.append(\n"
                        "            OUTBOX_STREAM,\n"
                        "            EventDraft(\n"
                        "                event_id=row.event_id,\n"
                        "                event_type=row.event_type,\n"
                        "                payload=row.payload,\n"
                        "            ),\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-cm-cap",
                    text=(
                        "Behind both regions sits CAP, best read as prose "
                        "rather than a theorem to recite: when a network "
                        "partition (the P) separates parts of a distributed "
                        "store, the store must choose between consistency "
                        "(the C — refusing answers that might be stale) and "
                        "availability (the A — answering anyway). This repo's "
                        "stance is visible in its own wiring: PostgreSQL, "
                        "Redis, and MongoDB are each independently durable "
                        "stores with NO cross-store transactions, so a "
                        "partition between them cannot corrupt either side — "
                        "it can only delay delivery, which the outbox's "
                        "at-least-once relay plus the idempotent consumer "
                        "turn into an eventually-consistent no-op. The "
                        "practical takeaway for any FastAPI service: decide "
                        "per WRITE which region it lives in. A write that "
                        "touches one PostgreSQL transaction gets full ACID; "
                        "a write whose effects must reach other services "
                        "goes through the outbox and accepts eventual "
                        "consistency deliberately — never a dual write "
                        "hoped across two connections, which is the one "
                        "design that guarantees torn state."
                    ),
                ),
            ],
        ),
        # ── 2. DDD vocabulary ────────────────────────────────────────────
        Section(
            id="ddd-vocabulary",
            title="DDD vocabulary, on this repo's layout",
            lead="The names the wider world uses for what topics 10–11 built.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="aa-ddd-pitch",
                    text=(
                        "Domain-driven design (DDD) started as a way to keep "
                        "code organized around the business it serves rather "
                        "than the tables it stores, and its vocabulary has "
                        "been quietly present in this repo since the posts "
                        "substrate landed in topic 11. An ENTITY is an object "
                        "whose identity, not its attributes, defines it — a "
                        "post is still the same post after you edit its "
                        "title, because its id survives the edit. A VALUE "
                        "OBJECT is the opposite: defined entirely by its "
                        "attributes, disposable, safely copied — this repo's "
                        "drafts and queries behave as value objects, which "
                        "is why pydantic's immutable-by-default snapshots fit "
                        "them so naturally. An AGGREGATE is a cluster of "
                        "entities treated as ONE consistency unit, with a "
                        "single root through which all changes enter — and "
                        "the boundary is drawn where a transaction's "
                        "guarantees stop, which in this repo means: one "
                        "aggregate per PostgreSQL transaction, events "
                        "carrying the news to everything else."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-ddd-entity-quote",
                    language="py",
                    caption=(
                        "The value object this repo has shipped since topic "
                        "11: a create draft whose validation lives on the "
                        "model — an invalid one cannot be constructed."
                    ),
                    source="server/guide/domain/posts/entities.py",
                    snippet=(
                        "class PostCreate(CamelModel):\n"
                        "    \"\"\"The POST/PUT body: the full representation a client sends.\"\"\"\n"
                        "\n"
                        "    title: Annotated[str, Field(min_length=1, max_length=120)]\n"
                        "    body: Annotated[str, Field(max_length=5000)] = \"\"\n"
                        "    author: Annotated[str, Field(min_length=1, max_length=40)]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-ddd-ports-pitch",
                    text=(
                        "The fourth DDD word is the one this guide has used "
                        "hardest: a PORT is the interface the domain owns "
                        "and the outside world adapts to — in this repo, "
                        "literally a typing.Protocol in domain/, implemented "
                        "by an adapter in data/, wired at the composition "
                        "root. The pattern's payoff is directional "
                        "dependencies: presentation depends on domain, data "
                        "depends on domain, and domain depends on nothing "
                        "but itself — the rule topic 32 traced through the "
                        "running app. The mapping is one-to-one with files "
                        "you have already read:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="aa-ddd-mapping",
                    ordered=False,
                    items=[
                        "Entity — Post: identity by id, snapshot semantics, "
                        "the wire representation and the domain object in "
                        "one frozen model (domain/posts/entities.py).",
                        "Value object — PostCreate, PostListQuery: validated "
                        "by construction, copied freely, no identity to "
                        "defend; invalid shapes die at the edge (topic 10).",
                        "Aggregate — the post with its identity metadata: "
                        "one root, one transaction, created and replaced "
                        "through the repository port as a whole unit.",
                        "Port — PostRepository: the Protocol the use cases "
                        "speak; repositories in DDD terms are the adapters "
                        "that satisfy it (domain/posts/ports.py).",
                        "Repository — InMemoryPostRepository and the "
                        "SQLAlchemy-backed readers: the data/ adapters that "
                        "own storage details the domain never learns.",
                        "Domain service — PostUseCases: thin orchestration "
                        "over the port, the seam where business policy "
                        "grows (domain/posts/use_cases.py).",
                    ],
                ),
                CodeBlock(
                    kind="code",
                    id="aa-ddd-port-quote",
                    language="py",
                    caption=(
                        "The port: a runtime-checkable Protocol the adapters "
                        "implement — 'returns snapshots, never live state.'"
                    ),
                    source="server/guide/domain/posts/ports.py",
                    snippet=(
                        "@runtime_checkable\n"
                        "class PostRepository(Protocol):\n"
                        "    \"\"\"What every posts adapter must do; returns snapshots, never live state.\"\"\"\n"
                        "\n"
                        "    def list(self, query: PostListQuery) -> PostPage:\n"
                        "        \"\"\"One filtered, sorted, paginated page of posts.\"\"\"\n"
                        "        ...\n"
                        "\n"
                        "    def get(self, post_id: str) -> Post | None:\n"
                        "        \"\"\"One post, or None when the id is unknown.\"\"\"\n"
                        "        ..."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-ddd-coda",
                    text=(
                        "What this repo deliberately does NOT do is the "
                        "heavier half of DDD: bounded contexts as separate "
                        "deployables, context translation maps, a ubiquitous "
                        "language enforced across teams. Those tools pay off "
                        "when multiple teams own one model; this repo has "
                        "one model and one deployable, so it takes the "
                        "vocabulary that keeps a MONOLITH honest — entities, "
                        "value objects, aggregates, ports — and leaves the "
                        "organizational machinery for the day it is "
                        "warranted. That restraint is itself the next "
                        "section's argument."
                    ),
                ),
            ],
        ),
        # ── 3. monolith first ────────────────────────────────────────────
        Section(
            id="monolith-first",
            title="Monolith first",
            lead="This repository IS the argument.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="aa-mono-pitch",
                    text=(
                        "The industry's default assumption — that a serious "
                        "backend means microservices — deserves the "
                        "cross-examination this repo's existence gives it. "
                        "The monolith-first argument (argued most memorably "
                        "by Martin Fowler's 'MonolithFirst' note) says: "
                        "build ONE deployable with clean INTERNAL module "
                        "boundaries first, because you cannot know where "
                        "the seams should go until the domain has taught "
                        "you, and a well-modularized monolith can be split "
                        "along existing seams later, while a bad "
                        "microservice split is expensive to undo. The "
                        "premium you pay for microservices is real and "
                        "recurring: network failure modes between your own "
                        "components, distributed tracing as a necessity "
                        "rather than a nicety, per-service deploy pipelines, "
                        "and the exact consistency problems this topic "
                        "spends its other sections on."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-mono-evidence",
                    text=(
                        "This repository is that argument, executed. ONE "
                        "server process carries forty-plus topics' worth of "
                        "capability — content, posts, GraphQL, gRPC, four "
                        "databases' worth of adapters, auth, realtime, jobs "
                        "— and the composition root wires all of it in one "
                        "function, one include_router call per area. The "
                        "modularity that microservices would enforce with "
                        "network boundaries, the monolith enforces with "
                        "Python boundaries: the dependency rule "
                        "(presentation → domain ← data) checked by import "
                        "discipline and mypy, one error taxonomy, one "
                        "middleware stack every area shares. When a "
                        "capability needed to be genuinely separate, the "
                        "repo split a PROCESS, not the application: the arq "
                        "worker and the gRPC satellite run beside the HTTP "
                        "server over shared stores, and the deploy pipeline "
                        "still ships them as small variations of one image."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-mono-router-quote",
                    language="py",
                    caption=(
                        "One composition root, one routing table: every "
                        "area the guide has built, included by the app "
                        "factory in one function."
                    ),
                    source="server/guide/main.py",
                    snippet=(
                        "app.include_router(health.router)\n"
                        "app.include_router(content.router)\n"
                        "app.include_router(posts.router)\n"
                        "# …\n"
                        "app.include_router(demo_msg.router)\n"
                        "app.include_router(demo_auth.router)\n"
                        "# …\n"
                        "app.include_router(demo_arch.router)"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-mono-compose-quote",
                    language="yaml",
                    caption=(
                        "The deploy pipeline's whole product surface: two "
                        "images — a server and a presentation-only client."
                    ),
                    source=".docker/docker-compose.prod.yml",
                    snippet=(
                        "  server:\n"
                        "    image: \"ghcr.io/mayank-uk/fastapi-guide-server:"
                        "${IMAGE_TAG:?IMAGE_TAG is required}\"\n"
                        "# …\n"
                        "  client:\n"
                        "    image: \"ghcr.io/mayank-uk/fastapi-guide-client:"
                        "${IMAGE_TAG:?IMAGE_TAG is required}\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-mono-when",
                    text=(
                        "The honest version of the argument is not "
                        "'monolith forever' but 'split when a measured "
                        "reason arrives': a team-scaling boundary (two "
                        "teams shipping one deployable step on each "
                        "other), a scaling boundary (one hot path that "
                        "must scale independently), or a risk boundary "
                        "(a capability whose failure must not share a "
                        "process with payments). Topic 40 walked the "
                        "scaling question concretely — this stack scales "
                        "by replicating the stateless monolith against "
                        "externalized state, which is exactly why the "
                        "shared counter demo moved its state to Redis "
                        "first. When a split does become warranted, the "
                        "seams to split along already exist: the areas' "
                        "port/adapter boundaries ARE the future service "
                        "boundaries, and the events that cross them "
                        "today through the outbox are the contracts they "
                        "would cross tomorrow over the network."
                    ),
                ),
            ],
        ),
        # ── 4. between services ──────────────────────────────────────────
        Section(
            id="between-services",
            title="Between services",
            lead="What passes between components when no request does.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="aa-btw-pitch",
                    text=(
                        "Inside one service, a function call passes control; "
                        "between services, a MESSAGE passes it — and "
                        "everything hard about distributed architecture "
                        "starts right there, because a message can be "
                        "delivered late, delivered twice, or (until the "
                        "retry budget gives up) not delivered at all. This "
                        "repo teaches that world with real machinery rather "
                        "than diagrams: topic 22's messaging substrate runs "
                        "a Redis stream as its transport, the transactional "
                        "outbox as its durability bridge out of PostgreSQL, "
                        "and an idempotent consumer as its duplicate "
                        "defense. Cross-referenced in full there, the "
                        "architecture-level points are three. First, the "
                        "CONTRACT between services is data, not code: the "
                        "event's id, type, and payload, defined by ports "
                        "both sides can read. Second, delivery semantics "
                        "are a CHOICE the consuming side makes possible: "
                        "at-least-once delivery plus an idempotent "
                        "consumer equals an exactly-once EFFECT. Third, "
                        "ordering is per stream, not global — the property "
                        "the next section's sagas rely on."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-btw-processed-quote",
                    language="py",
                    caption=(
                        "The inter-service contract as a port: seen before "
                        "the work, remembered after it — the two halves of "
                        "idempotent consumption."
                    ),
                    source="server/guide/domain/messaging/ports.py",
                    snippet=(
                        "@runtime_checkable\n"
                        "class ProcessedEventStore(Protocol):\n"
                        "    \"\"\"The idempotent consumer's processed-set — event ids already handled.\"\"\"\n"
                        "\n"
                        "    async def seen(self, set_key: str, event_id: str) -> bool:\n"
                        "        \"\"\"True when ``event_id`` was already processed (the set remembers).\"\"\"\n"
                        "        ...\n"
                        "\n"
                        "    async def remember(self, set_key: str, event_id: str) -> None:\n"
                        "        \"\"\"Record ``event_id`` as processed — AFTER the work, not before.\"\"\"\n"
                        "        ..."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-btw-outbox-pitch",
                    text=(
                        "The outbox half deserves one architecture-level "
                        "re-read, because it is the bridge EVERY pattern in "
                        "this topic's second half stands on. A service that "
                        "must both commit a write and announce it cannot "
                        "do those two things atomically — so it does the "
                        "atomic half inside its own database (the business "
                        "row and the event row commit together) and lets a "
                        "relay do the non-atomic half (publish, then mark) "
                        "with at-least-once semantics. The result is a "
                        "guarantee you can build on: an event that was "
                        "committed WILL eventually reach the stream, no "
                        "matter when the process died. That single "
                        "promise is why sagas can span services and why "
                        "event-sourced projections can be rebuilt: both "
                        "are just consumers of a log that cannot lose "
                        "committed facts."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-btw-dualwrite-quote",
                    language="py",
                    caption=(
                        "The atomic half: the post and its event commit in "
                        "one PostgreSQL transaction or neither does."
                    ),
                    source="server/guide/domain/messaging/outbox_service.py",
                    snippet=(
                        "async def create_with_event(self, draft: OutboxPostDraft) -> OutboxWriteRow:\n"
                        "    \"\"\"The dual write, atomic: post and event commit together or not at all.\"\"\"\n"
                        "    row = await self._outbox.create_post_with_event(draft)\n"
                        "    if row.committed:\n"
                        "        self._creates += 1"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-btw-coda",
                    text=(
                        "Two honest footnotes complete the picture. gRPC "
                        "(topic 15) is the other inter-service style this "
                        "repo really runs — synchronous, schema-first, a "
                        "function call that crosses a network — and the "
                        "choice between it and messaging is the "
                        "architecture's oldest fork: request/response "
                        "needs the answer NOW and can fail fast; "
                        "event-driven work can absorb the answer being "
                        "late. And webhooks (topic 14) are simply the "
                        "outbound face of the same discipline: someone "
                        "else's at-least-once delivery into your HTTP "
                        "endpoint, which is why the receiving side "
                        "verified signatures and the sending side carried "
                        "a retry policy with a dead letter."
                    ),
                ),
            ],
        ),
        # ── 5. sagas ─────────────────────────────────────────────────────
        Section(
            id="sagas",
            title="Sagas",
            lead="This section carries the topic's first demo — arch:saga.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="aa-saga-pitch",
                    text=(
                        "Take the outbox's promise — a committed event WILL "
                        "arrive — and try to build the classic distributed "
                        "operation: an order that must reserve stock in one "
                        "service, charge a card in another, book a shipment "
                        "at a third, and announce itself to a fourth. No "
                        "transaction spans them, so ACID is unavailable; "
                        "the SAGA pattern replaces rollback with "
                        "COMPENSATION. The operation becomes a sequence of "
                        "local transactions, each paired with an undo "
                        "action written before the forward step ever runs; "
                        "if step three fails, the saga runs the "
                        "compensations for the steps that already "
                        "committed, in REVERSE order — refund the card, "
                        "then release the stock — leaving the world as it "
                        "found it, minus the audit trail. The undo is "
                        "business work, not database magic: a refund takes "
                        "days, a released slot is visible to other orders "
                        "the instant it frees. That is the price of "
                        "distributed operations, and the saga pays it "
                        "explicitly instead of pretending it away."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-saga-definition-quote",
                    language="py",
                    caption=(
                        "The saga's document: four forward steps, each "
                        "naming its undo — a reviewer reads the compensation "
                        "plan before the first step runs."
                    ),
                    source="server/guide/domain/patterns/saga.py",
                    snippet=(
                        "DEMO_ORDER_SAGA: Final = SagaDefinition(\n"
                        "    name=\"order-fulfillment\",\n"
                        "    steps=(\n"
                        "        SagaStep(\n"
                        "            action=\"reserve-item\",\n"
                        "            compensates=\"release-item\",\n"
                        "            describes=\"hold one unit of stock locally (a real transaction)\",\n"
                        "        ),\n"
                        "        # …\n"
                        "    ),\n"
                        ")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-saga-substrate-pitch",
                    text=(
                        "This repo's saga substrate is real, tested domain "
                        "code in guide/domain/patterns/saga.py — the same "
                        "standing as the circuit breaker topic 39 drives. "
                        "The coordinator is pure orchestration: it runs "
                        "forward steps in definition order, remembers "
                        "every step that completed, and on the first "
                        "failure turns around and runs the completed "
                        "steps' compensations newest-first, recording an "
                        "evidence line for every single entry — including "
                        "the failure, and including a compensation that "
                        "itself refuses (recorded, never swallowed; the "
                        "undo continues with older steps either way). The "
                        "line that carries the whole pattern is one word:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-saga-reverse-quote",
                    language="py",
                    caption=(
                        "The pattern in one word: reversed(completed) — undo "
                        "runs over the completed steps, newest first."
                    ),
                    source="server/guide/domain/patterns/saga.py",
                    snippet=(
                        "entries: list[SagaLogEntry] = []\n"
                        "order: list[str] = []\n"
                        "for step in reversed(completed):"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-saga-demo-pitch",
                    text=(
                        "The demo below drives the REAL coordinator through "
                        "both of a saga's lives. The happy run commits all "
                        "four steps. The failing run injects a "
                        "deterministic failure at the third step — the "
                        "carrier is full — by raising inside that step's "
                        "own effect, the one honest way a step fails; watch "
                        "the run log run forwards, stop at the failure, "
                        "then run BACKWARDS through refund-card and "
                        "release-item, each with its own ledger evidence, "
                        "and check the balances panel: stock, cents, and "
                        "held slots all return to their starting values, "
                        "while the never-reached fourth step left no "
                        "trace at all."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="arch:saga",
                    title="Saga: the compensating transaction, run live",
                    description=(
                        "The real SagaCoordinator over a scratch ledger: a "
                        "committed four-step run, then a failing run whose "
                        "compensations unwind in reverse with per-step "
                        "evidence and a net-zero balance proof."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-saga-demo-reading",
                    text=(
                        "Two readings of that panel repay the time. First, "
                        "the failure injection lives in the step's own "
                        "effect — the demo builder wires each step as an "
                        "effect over one shared scratch ledger, and the "
                        "failing variant simply raises from inside "
                        "book-shipment, exactly as a real carrier call "
                        "would:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-saga-builder-quote",
                    language="py",
                    caption=(
                        "The demo's injected failure point: a raise inside "
                        "the step's own effect — never a faked log line."
                    ),
                    source="server/guide/domain/demos/arch_saga.py",
                    snippet=(
                        "if fail_at == \"book-shipment\":\n"
                        "    effects[\"book-shipment\"] = failing(\"book-shipment\", FAILURE_REASON)\n"
                        "else:\n"
                        "\n"
                        "    def book() -> str:\n"
                        "        _inc(ledger, \"slots_held\")\n"
                        "        return f\"carrier slot held ({ledger.slots_held} of 2 free slots taken)\"\n"
                        "\n"
                        "    effects[\"book-shipment\"] = book"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-saga-durability",
                    text=(
                        "Second, the panel's durability rows are the honest "
                        "boundary of what you just watched: the "
                        "coordinator you saw is the pattern's DECISION "
                        "core, in-process and per-request. A production "
                        "saga survives crashes because its steps ride the "
                        "outbox (committed events WILL arrive, at least "
                        "once, and the idempotent consumer makes the "
                        "redelivery harmless) and because the saga's own "
                        "run log is an event stream a restarted "
                        "coordinator reads forward to find where it "
                        "stopped — the same replay property the "
                        "event-store demo below demonstrates directly. "
                        "The wiring that serves the panel is one more "
                        "thin router over a declared response model, "
                        "consistent with every demo since topic 3:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-saga-router-quote",
                    language="py",
                    caption=(
                        "The demo's plumbing: a thin GET over the pure "
                        "builder, response model declared."
                    ),
                    source="server/guide/presentation/routers/demo/arch.py",
                    snippet=(
                        "@router.get(SAGA_PATH, response_model=ArchSagaPanel)\n"
                        "async def read_arch_saga() -> ArchSagaPanel:\n"
                        "    \"\"\"Serve the saga panel: a committed run, then compensations in reverse.\"\"\"\n"
                        "    return build_arch_saga_panel()"
                    ),
                ),
            ],
        ),
        # ── 6. CQRS ──────────────────────────────────────────────────────
        Section(
            id="cqrs",
            title="CQRS",
            lead="Separate the write model from the read model — honestly sized.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="aa-cqrs-pitch",
                    text=(
                        "Command Query Responsibility Segregation (CQRS) "
                        "starts from an observation you have already met in "
                        "this repo: the shape a client SENDS and the shape "
                        "a client READS rarely want to be the same object, "
                        "even when they describe the same thing. A command "
                        "(a write) wants narrow, strictly validated input; "
                        "a query (a read) wants denormalized, "
                        "presentation-ready output. Most systems keep one "
                        "model and accept the friction; CQRS formalizes the "
                        "split — a WRITE model that accepts commands and "
                        "enforces invariants, and READ models (plural on "
                        "purpose) shaped per query, kept up to date by "
                        "events or views. At full scale that means "
                        "different STORES: commands commit to a normalized "
                        "aggregate while projections build the read tables "
                        "each screen needs, rebuilt from the event log at "
                        "any time."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-cqrs-repo-honesty",
                    text=(
                        "This repo is NOT full CQRS, and saying exactly "
                        "where it stops is the useful lesson. What it has "
                        "is the COMMAND/QUERY split at every layer: "
                        "PostCreate is a command shape, PostPage a query "
                        "answer; the use cases separate reads from writes "
                        "one class per verb; the router distinguishes GET "
                        "from POST/PUT down to status codes and the "
                        "Location header. What it deliberately lacks is "
                        "the second STORE — reads and writes go through "
                        "one repository over one set of tables, because "
                        "at this guide's scale the projection machinery "
                        "would be architecture theater. The honest sizing: "
                        "CQRS earns its second store when read and write "
                        "workloads diverge (a hot feed read a thousand "
                        "times an hour, say, beside rare writes), and it "
                        "PAYS for it with eventual consistency between the "
                        "sides — a freshly written row may not be in the "
                        "projection yet, a fact the UI must be designed to "
                        "survive. Everything in between is available "
                        "incrementally, as this repo's real shapes show:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-cqrs-usecase-quote",
                    language="py",
                    caption=(
                        "The query side: one use case per verb, the read "
                        "shape (PostPage) already different from the write "
                        "shape (PostCreate)."
                    ),
                    source="server/guide/domain/posts/use_cases.py",
                    snippet=(
                        "class ListPostsUseCase:\n"
                        "    \"\"\"Serve one filtered, sorted, paginated page through the port.\"\"\"\n"
                        "\n"
                        "    def __init__(self, posts: PostRepository) -> None:\n"
                        "        self._posts = posts\n"
                        "\n"
                        "    def execute(self, query: PostListQuery) -> Result[PostPage]:\n"
                        "        \"\"\"Ask the port; the query's own constraints guarantee its shape.\"\"\"\n"
                        "        return Ok(self._posts.list(query))"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-cqrs-query-quote",
                    language="py",
                    caption=(
                        "A read model in miniature: the list query is a "
                        "closed, validated vocabulary — pagination, "
                        "filters, sort — not a free-for-all."
                    ),
                    source="server/guide/domain/posts/entities.py",
                    snippet=(
                        "page: Annotated[int, Field(ge=1, le=10_000)] = 1\n"
                        "limit: Annotated[int, Field(ge=1, le=100)] = DEFAULT_LIST_LIMIT\n"
                        "author: str | None = Field(default=None, min_length=1, max_length=40)\n"
                        "tag: str | None = Field(default=None, min_length=1, max_length=40)\n"
                        "status: PostStatus | None = None\n"
                        "sort: PostSort = \"newest\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-cqrs-projections",
                    text=(
                        "The repo's nearest approach to a real projection "
                        "is worth naming, because you have already watched "
                        "it run: the search demo's tsvector column and "
                        "GIN index (topic 17) is a DERIVED read structure "
                        "maintained beside the mutable rows — PostgreSQL "
                        "itself recomputes it on write, which is the "
                        "same bargain as an event-fed projection with "
                        "the consistency strengthened to synchronous. The "
                        "caching topic (21) added the temporal half: a "
                        "cache-aside read model with TTL-driven staleness, "
                        "invalidated by the write side — eventual "
                        "consistency between write and read, chosen "
                        "deliberately, exactly as a CQRS projection would "
                        "be. That is the pragmatic ladder: separate the "
                        "SHAPES first (this repo), add derived read "
                        "STRUCTURES when queries demand them (topic 17), "
                        "and only split the stores when the workload "
                        "numbers say so."
                    ),
                ),
            ],
        ),
        # ── 7. event sourcing ────────────────────────────────────────────
        Section(
            id="event-sourcing",
            title="Event sourcing",
            lead="This section carries the topic's second demo — arch:eventstore.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="aa-es-pitch",
                    text=(
                        "A mutable row stores the ANSWER — the current "
                        "state — and throws away the question's history. "
                        "Event sourcing inverts that: store what HAPPENED "
                        "(a permanent, append-only stream of facts) and "
                        "DERIVE the current state by replaying the facts "
                        "in order whenever it is needed. The benefits "
                        "follow from that one inversion: perfect audit "
                        "for free (the history IS the record, not a "
                        "side-channel that can drift), the ability to "
                        "answer NEW questions about old data (build a "
                        "fresh projection by writing a new fold over "
                        "the same stream), and optimistic concurrency "
                        "for free (the version number is the fact "
                        "count). The costs are equally real and this "
                        "topic will not hide them: reads require "
                        "folding (so projections become necessary, "
                        "which drags in CQRS), the event vocabulary "
                        "must be evolved carefully forever, and "
                        "privacy obligations collide with a log whose "
                        "entire point is that it never forgets."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-es-substrate-pitch",
                    text=(
                        "This repo's event store — real, tested, in "
                        "guide/domain/patterns/ — is deliberately the "
                        "SMALLEST honest version of the pattern: a "
                        "port, an in-memory adapter behind it (the "
                        "posts area's port/adapter split, replayed), "
                        "and a pure fold. The stored fact carries the "
                        "store's three stamps — identity, dense "
                        "per-stream version, clock time — and nothing "
                        "else; writers submit drafts and cannot forge "
                        "any of the three:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-es-event-quote",
                    language="py",
                    caption=(
                        "The fact itself: frozen, stamped by the store — "
                        "identity, dense version, time."
                    ),
                    source="server/guide/domain/patterns/event_store.py",
                    snippet=(
                        "@dataclass(frozen=True, slots=True)\n"
                        "class StoredEvent:\n"
                        "    \"\"\"One immutable fact, as stored: the draft plus the store's stamps.\n"
                        "\n"
                        "    ``version`` is the event's dense position in ITS stream (1-based);\n"
                        "    ``occurred_at`` is the clock token the adapter was holding when the\n"
                        "    fact was appended. Frozen: a stored fact never changes after this.\n"
                        "    \"\"\"\n"
                        "\n"
                        "    event_id: str\n"
                        "    stream: str\n"
                        "    event_type: str\n"
                        "    payload: Mapping[str, object]\n"
                        "    version: int\n"
                        "    occurred_at: str"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-es-fold-pitch",
                    text=(
                        "All of the pattern's semantics live in the FOLD "
                        "— the pure left-fold that walks a stream's "
                        "history and applies each fact's handler to the "
                        "state so far. Purity is the load-bearing "
                        "property: because handlers copy-in and return "
                        "the next state, the same history folds to the "
                        "same state every time, on every machine, after "
                        "every restart — which is what makes rebuilds, "
                        "projections, and replay safe. An event type "
                        "with no handler raises rather than skipping: "
                        "a log you cannot fully read is a defect, not "
                        "an inconvenience."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-es-fold-quote",
                    language="py",
                    caption=(
                        "The read side: a pure left-fold over ordered "
                        "history — same facts in, same state out, always."
                    ),
                    source="server/guide/domain/patterns/event_store.py",
                    snippet=(
                        "state: State = dict(initial)\n"
                        "for event in history:\n"
                        "    handler = handlers.get(event.event_type)\n"
                        "    if handler is None:\n"
                        "        raise UnknownEventTypeError(\n"
                        "            f\"no handler for event type {event.event_type!r} (event \"\n"
                        "            f\"{event.event_id!r}, version {event.version})\"\n"
                        "        )\n"
                        "    state = handler(state, event)\n"
                        "return state"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-es-concurrency-pitch",
                    text=(
                        "The write side is one invariant: OPTIMISTIC "
                        "concurrency. A writer states which version it "
                        "believes the stream is at; if the stream moved "
                        "on, the append is refused with a VersionConflict "
                        "and — because the check runs before anything is "
                        "minted — the losing write stores NOTHING, not "
                        "half a batch. No locks anywhere: a lost race is "
                        "simply told it lost, and the writer's recovery "
                        "is the pattern's own medicine (re-read the "
                        "stream, re-fold, retry with a fresh belief):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-es-adapter-quote",
                    language="py",
                    caption=(
                        "The adapter's whole write discipline: check "
                        "first, totally — a conflict means nothing was "
                        "stored."
                    ),
                    source="server/guide/data/patterns/memory_event_store.py",
                    snippet=(
                        "current = len(self._streams.get(stream, ()))\n"
                        "believed_empty = expected_version == EXPECT_EMPTY\n"
                        "if (believed_empty and current != 0) or (\n"
                        "    not believed_empty and expected_version != current\n"
                        "):\n"
                        "    raise VersionConflict(stream=stream, expected=expected_version, actual=current)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-es-demo-pitch",
                    text=(
                        "The demo drives the real port end to end: five "
                        "facts about one post's lifecycle are appended "
                        "with dense versions and stamped clocks; the "
                        "current state is folded back out ONE FACT AT A "
                        "TIME (each fold step is its own evidence row — "
                        "watch the title change, the tags accumulate, "
                        "the status flip); a SECOND store instance "
                        "re-appends the same drafts and folds to a state "
                        "checked equal against the first — the replay "
                        "promise executed, not asserted; and a stale "
                        "writer holding a three-versions-old belief is "
                        "refused by the conflict check with the log "
                        "length unchanged."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="arch:eventstore",
                    title="Event store: append, fold, rebuild, conflict",
                    description=(
                        "The real EventStore port: five appended facts, the "
                        "state folded event by event, a second store proving "
                        "replay determinism, and a stale write refused "
                        "totally."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-es-kinship-pitch",
                    text=(
                        "The repo's nearest relative to an event store "
                        "predates this topic and has been live since the "
                        "data phase: audit_log, the append-only table "
                        "migration 0001 created, written inside the SAME "
                        "transaction as the change it records (topic 16's "
                        "audit demo proved the rollback half — a rolled "
                        "back transaction leaves no audit row). The "
                        "difference is the direction of truth: audit_log "
                        "is a side-band record BESIDE mutable rows, "
                        "written for forensics; event sourcing makes the "
                        "log itself the source of truth and the mutable "
                        "row its derived projection. Both keep history; "
                        "only one trusts it enough to rebuild from it."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-es-audit-quote",
                    language="sql",
                    caption=(
                        "The in-repo relative: audit_log — append-only, "
                        "sequence-identified, JSONB facts, written in the "
                        "same transaction as the change."
                    ),
                    source="server/alembic/versions/0001_guide_schema.py",
                    snippet=(
                        "op.create_table(\n"
                        "    \"audit_log\",\n"
                        "    sa.Column(\n"
                        "        \"id\",\n"
                        "        sa.BigInteger(),\n"
                        "        server_default=sa.text(\"nextval('audit_log_id_seq'::regclass)\"),\n"
                        "        nullable=False,\n"
                        "    ),\n"
                        "    -- …\n"
                        "    sa.Column(\"actor\", sa.Text(), nullable=False),\n"
                        "    sa.Column(\"action\", sa.Text(), nullable=False),\n"
                        "    sa.Column(\"table_name\", sa.Text(), nullable=False),\n"
                        "    sa.Column(\"row_pk\", sa.Text(), nullable=False),"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-es-outbox-kinship",
                    text=(
                        "The last kinship completes the circle the topic "
                        "opened with: the outbox table (migration 0004) IS "
                        "a durable event store with one job — carrying "
                        "committed facts out of one transactional boundary "
                        "to everyone else. A production event-sourced "
                        "aggregate in this stack would be an outbox-shaped "
                        "table per aggregate family: append-only rows, "
                        "dense versions under a unique key, and the "
                        "consumer side folding projections — the in-memory "
                        "adapter the demo drove is exactly that contract "
                        "with the durability dial turned down for the "
                        "classroom."
                    ),
                ),
            ],
        ),
        # ── 8. tracing across boundaries ─────────────────────────────────
        Section(
            id="tracing-across-boundaries",
            title="Tracing across boundaries",
            lead="One id that survives every hop — request, process, and log.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="aa-tr-pitch",
                    text=(
                        "Every pattern in this topic FAILS SILENTLY unless "
                        "one thing exists: an identifier that survives "
                        "every boundary an operation crosses. A request "
                        "that fans through middleware, a dependency tree, "
                        "a repository, an outbox relay, a stream consumer, "
                        "and a worker process produces log lines in six "
                        "places; without a shared id they are six "
                        "unrelated stories, and 'which logs belong to the "
                        "order that failed?' becomes archaeology. "
                        "Distributed tracing as a discipline (spans, "
                        "context propagation, the W3C traceparent header) "
                        "generalizes this; its minimal, indispensable core "
                        "is the CORRELATION ID — and this repo has built "
                        "that core for real, twice."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-tr-middleware-quote",
                    language="py",
                    caption=(
                        "The id's whole life cycle: accept the inbound "
                        "header or mint one, bind it to a contextvar, and "
                        "stamp it on the response — every boundary in one "
                        "middleware."
                    ),
                    source="server/guide/core/request_context.py",
                    snippet=(
                        "request_id = _assign_request_id(_inbound_id(scope))\n"
                        "token = _request_id.set(request_id)\n"
                        "_mirror_into_scope(scope, request_id)\n"
                        "# …\n"
                        "if message[\"type\"] == \"http.response.start\":\n"
                        "    MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id\n"
                        "await send(message)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-tr-roundtrip",
                    text=(
                        "The request-id half (topic 8, deepened by 28 and "
                        "33) is the HTTP boundary's correlation: one id "
                        "per exchange, accepted from the inbound "
                        "x-request-id header or minted fresh, echoed on "
                        "the response so the CALLER learns it, bound to "
                        "a contextvar so every structlog line anywhere "
                        "in the call stack carries it with zero "
                        "parameter-passing, and mirrored into the ASGI "
                        "scope so even the outermost 500 handler can "
                        "recover it. The envelope joins in: every error "
                        "body carries the same requestId the header "
                        "carries, which is how a user's screenshot maps "
                        "to exact log lines. A client that generates its "
                        "own id per user action and sends it inbound — "
                        "the browser client does this — has already "
                        "built the first rung of end-to-end tracing."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-tr-events",
                    text=(
                        "The second half crosses the boundaries requests "
                        "never see. Events carry their event_id from the "
                        "outbox through the stream to the idempotent "
                        "consumer's processed-set — the SAME id that "
                        "makes deduplication safe makes the delivery "
                        "traceable: a duplicate in a consumer's log is "
                        "correlated to the relay crash that caused it by "
                        "the id they share. Jobs carry the same shape "
                        "one process over: the arq trails (topic 29) "
                        "record every attempt of a run under the run's "
                        "id, so a retried-then-dead-lettered job reads "
                        "as one story across worker restarts. And the "
                        "observability topic (33) assembled the pieces "
                        "into the correlation you can watch live: its "
                        "trace demo fans one inbound id across header, "
                        "envelope, and log rows of three real internal "
                        "rounds. When this repo eventually adopts full "
                        "span-based tracing, it will not be adding the "
                        "correlation — only the TIMING around it."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-tr-coda",
                    text=(
                        "That is the closing symmetry of the guide: the "
                        "consistency map said WHERE each guarantee lives; "
                        "the vocabulary sections said what the pieces are "
                        "CALLED; the pattern sections — saga, CQRS, event "
                        "sourcing — said how the pieces COOPERATE across "
                        "the boundaries a single transaction cannot "
                        "cross; and tracing is what makes any of it "
                        "OPERABLE once it runs. Advanced architecture is "
                        "not more boxes on a diagram — it is the same "
                        "disciplines this guide has practiced at every "
                        "scale, applied at the scale where the network "
                        "gets a vote: explicit contracts at every "
                        "boundary, honesty about failure modes, "
                        "constraints owned by the mechanism that can "
                        "actually enforce them, and an id that survives "
                        "the whole trip."
                    ),
                ),
            ],
        ),
        # ── 9. terminal companion ────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead=(
                "The capstone from a shell: both demos on the running "
                "stack, their proofs checked field by field."
            ),
            blocks=[
                TextBlock(
                    kind="text",
                    id="aa-terminal-intro",
                    text=(
                        "Six stops, all against the live stack: the saga "
                        "panel's two runs (the committed one, then the "
                        "compensated one with its reversed undo), the "
                        "balance proof that the undo undid, the event "
                        "store's appended history, the fold and the "
                        "rebuild equality, the refused stale write, and "
                        "this final topic's own shape through both ports."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-terminal-saga-runs",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the saga's two lives: committed, then compensated\n"
                        "curl -s localhost:8000/api/demo/arch/saga | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for run in (panel[\"happyRun\"], panel[\"failureRun\"]):\n"
                        "    print(run[\"label\"], \"->\", run[\"outcome\"])\n"
                        "    for e in run[\"entries\"]:\n"
                        "        print(\"  \", e[\"at\"], e[\"phase\"], e[\"step\"], \"|\", e[\"evidence\"][:58])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-terminal-saga-proof",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the undo proof: compensation order reversed, balances net zero\n"
                        "curl -s localhost:8000/api/demo/arch/saga | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "f = panel[\"failureRun\"]\n"
                        "print(\"failed at:\", f[\"failureStep\"])\n"
                        "print(\"undo order:\", \" -> \".join(f[\"compensationOrder\"]))\n"
                        "for b in panel[\"balances\"]:\n"
                        "    print(\"%-20s %s -> %s (happy) -> %s (failed): %s\"\n"
                        "          % (b[\"metric\"], b[\"before\"], b[\"afterHappy\"], b[\"afterFailure\"], b[\"verdict\"][:40]))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-terminal-es-append",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the event store's history: five facts, dense versions, minted ids\n"
                        "curl -s localhost:8000/api/demo/arch/eventstore | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for e in panel[\"appended\"]:\n"
                        "    print(\"v%d %-14s %-34s %s %s\"\n"
                        "          % (e[\"version\"], e[\"eventType\"], e[\"payload\"][:32], e[\"eventId\"][:8], e[\"occurredAt\"]))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-terminal-es-fold",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the fold, event by event, and the rebuild equality\n"
                        "curl -s localhost:8000/api/demo/arch/eventstore | python3 -c '\n"
                        "import json, sys\n"
                        "panel = json.load(sys.stdin)\n"
                        "for s in panel[\"foldSteps\"]:\n"
                        "    print(\"after v%d %-14s %s\" % (s[\"afterVersion\"], s[\"eventType\"], s[\"stateNow\"][:60]))\n"
                        "print(\"rebuild matches:\", panel[\"rebuild\"][\"matches\"])\n"
                        "print(\"current state:\", json.dumps(panel[\"currentState\"]))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-terminal-es-conflict",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the stale write refused totally, and the panels through the proxy\n"
                        "curl -s localhost:8000/api/demo/arch/eventstore | python3 -c '\n"
                        "import json, sys\n"
                        "c = json.load(sys.stdin)[\"concurrency\"]\n"
                        "print(\"expected v%d vs actual v%d -> stored still %d\"\n"
                        "      % (c[\"expectedVersion\"], c[\"actualVersion\"], c[\"storedEventsAfter\"]))'\n"
                        "curl -s -o /dev/null -w 'proxy saga: %{http_code}\\n' localhost:5174/api/demo/arch/saga\n"
                        "curl -s -o /dev/null -w 'proxy eventstore: %{http_code}\\n' localhost:5174/api/demo/arch/eventstore"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aa-terminal-shape",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — the curriculum complete: 43 topics, this page's shape, the receipt\n"
                        "curl -s localhost:8000/api/content | python3 -c '\n"
                        "import json, sys\n"
                        "index = json.load(sys.stdin)\n"
                        "print(len(index[\"topics\"]), \"topics /\", len(index[\"groups\"]), \"groups\")'\n"
                        "curl -s localhost:8000/api/content/advanced-architecture | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'\n"
                        "curl -s -o /dev/null -w 'health: %{http_code} in %{time_total}s\\n' localhost:8000/api/health"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aa-terminal-coda",
                    text=(
                        "Stops 1–2 are the saga's whole argument in two "
                        "payloads: a committed run, then a failed run "
                        "whose compensations ran newest-first and left "
                        "the ledger exactly where it started. Stops 3–5 "
                        "are event sourcing's: facts appended once and "
                        "never rewritten, state folded out of them, the "
                        "same facts rebuilt in a second store to the "
                        "same answer, and a stale writer refused without "
                        "a scratch on the log. Stop 6 closes the guide "
                        "the way every topic closed — the shape of the "
                        "thing you just read, served by the stack that "
                        "was the subject all along."
                    ),
                ),
            ],
        ),
    ],
)
