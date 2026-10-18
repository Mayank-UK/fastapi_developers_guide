"""Topic 22 — Messaging (Redis Streams + the transactional outbox).

Topic 21 gave the guide a cache; this topic gives it NERVES — events
that travel between the request that caused them and the work that
reacts to them. The topic builds two real substrates and teaches
through them: a Redis Stream with a consumer group (the lab's healthy
and poison consumers make delivery bookkeeping visible — read, ack,
pending, reclaim), and a transactional outbox spanning PostgreSQL and
Redis (a post and its event commit in ONE transaction; a relay delivers
at-least-once; an idempotent consumer turns that into an exactly-once
EFFECT). Both demos are inline in the sections that teach them, and the
terminal companion walks every endpoint with curl.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="messaging",
    title="Messaging",
    subtitle=(
        "Why work goes asynchronous, logs vs queues, delivery guarantees, "
        "pending entries and XAUTOCLAIM, the transactional outbox, and "
        "idempotent consumers — built real over Redis Streams and PostgreSQL."
    ),
    group="state-auth",
    order=22,
    sections=[
        # ── 1. Why asynchronous work exists ────────────────────────────────
        Section(
            id="why-asynchronous-work",
            title="Why asynchronous work exists",
            blocks=[
                TextBlock(
                    kind="text",
                    id="why-pitch",
                    text=(
                        "Every request-scoped call you have written so far shares one "
                        "shape: the caller WAITS — the database query, the cache read, "
                        "even the gRPC round trip all hold the request open until the "
                        "answer lands. Asynchronous messaging exists for the work that "
                        "must NOT hold anyone open: the confirmation email after signup, "
                        "the thumbnail render after upload, the search re-index after a "
                        "post changes. The request commits the INTENT (\"this happened\") "
                        "and returns; separate machinery reacts to the intent whenever "
                        "it runs. That flip — from \"do the work now\" to \"record that "
                        "the work is due\" — is the entire subject of this topic, and "
                        "everything else here is the price of making it honest."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-three-wins",
                    text=(
                        "The flip buys three distinct things, and it is worth naming "
                        "them separately because they fail separately:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="why-three-list",
                    ordered=False,
                    items=[
                        "Decoupling — the writer names WHAT happened (post.created) "
                        "and never knows who cares; a new subscriber joins without the "
                        "publisher changing a line, and teams ship features against "
                        "events they did not coordinate.",
                        "Absorption — a broker is a shock absorber between uneven "
                        "rates: a traffic spike queues as backlog and consumers drain "
                        "it at their own pace, instead of the spike propagating into "
                        "every downstream system at once.",
                        "Failure isolation — the consumer being down no longer fails "
                        "the request that caused the work; delivery retries on the "
                        "broker's clock, and the failure surfaces where it can be "
                        "handled (the consumer, its alerts) rather than in the user's "
                        "response.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="why-price",
                    text=(
                        "The price is that three questions with trivial answers in a "
                        "request-response world become design decisions: DID the "
                        "message get there (delivery guarantees), WHO is working on it "
                        "right now (ownership and pending state), and WHAT HAPPENS IF "
                        "IT ARRIVES TWICE (idempotence). A synchronous call answers all "
                        "three with its return value; an event answers none of them by "
                        "existing. The rest of this topic builds those answers for "
                        "real: section two gives the log its read side, section three "
                        "names the guarantees, section four recovers from dead "
                        "consumers, and sections five and six make the write side "
                        "atomic and the read side exactly-once-in-effect."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-not",
                    text=(
                        "And the discipline of when NOT to flip: synchronous stays the "
                        "default. If the caller needs the answer — the read path, the "
                        "validation verdict, anything a response is incomplete without "
                        "— an event cannot help you, because events do not RETURN. "
                        "Going asynchronous earns its complexity only when the "
                        "reaction may be SLOW (rendering, third-party calls), "
                        "UNRELIABLE in a way the request should not inherit "
                        "(a flaky email provider), or NUMEROUS in a way request "
                        "workers should not absorb (a thousand thumbnails from one "
                        "upload). The test this guide uses: would the correct user "
                        "response change if the reaction ran ten seconds later? If "
                        "yes, it belongs in the request; if no, it is an event "
                        "waiting to be modeled — and topic 29 will place plain "
                        "background JOBS, which have no event semantics at all, "
                        "on the other side of that same line."
                    ),
                ),
            ],
        ),
        # ── 2. Logs vs queues ──────────────────────────────────────────────
        Section(
            id="logs-vs-queues",
            title="Logs vs queues",
            lead="This section carries the topic's first demo — the stream lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="log-models",
                    text=(
                        "Two mental models compete for the word \"queue\", and picking "
                        "the wrong one quietly decides your architecture. The classic "
                        "QUEUE is destructive: a consumer takes a message, the message "
                        "leaves, and the next consumer sees the rest — great for work "
                        "distribution, terrible for replay, audit, or a second reader. "
                        "The LOG is append-only: producers XADD entries, nobody's read "
                        "moves anybody else's position, and each reader holds a CURSOR "
                        "into the same immutable history. Redis Streams (this topic's "
                        "substrate), Kafka, and Event Hubs are logs; RabbitMQ queues "
                        "and SQS are queues. The difference is not which is better — "
                        "it is that a log can always SIMULATE a queue (a consumer "
                        "group with acknowledgement is a durable work queue), while a "
                        "queue can never simulate a log (the taken message is gone)."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="log-groups-pitch",
                    text=(
                        "The consumer group is the bridge: one named group over one "
                        "stream, where each entry is delivered to exactly one consumer "
                        "IN the group (load balancing), while independent groups each "
                        "see every entry (fan-out). Delivery is tracked per entry in "
                        "the group's pending entries list — the PEL — and "
                        "acknowledgement is what removes an entry from it. The whole "
                        "read side of this topic's substrate is one domain port:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="log-port",
                    language="py",
                    caption="The consumer-group lifecycle as a port — ensure, read new, ack.",
                    source="server/guide/domain/messaging/ports.py",
                    snippet=(
                        "@runtime_checkable\n"
                        "class StreamConsumer(Protocol):\n"
                        '    """The consumer-group lifecycle over a stream — the log\'s read side."""\n'
                        "\n"
                        "    async def ensure_group(self, stream: str, group: str) -> None:\n"
                        '        """Create the group idempotently (an existing group is not an error)."""\n'
                        "        ...\n"
                        "\n"
                        "    async def read_new(\n"
                        "        self, stream: str, group: str, consumer: str, count: int\n"
                        "    ) -> list[StreamEntryRow]:\n"
                        '        """Deliver entries never delivered to this group (XREADGROUP ``>``)."""\n'
                        "        ...\n"
                        "\n"
                        "    async def ack(self, stream: str, group: str, entry_ids: Sequence[str]) -> int:\n"
                        '        """Acknowledge delivered entries; answer how many left the PEL."""\n'
                        "        ..."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="log-personas",
                    text=(
                        "The lab's two consumer personas are the entire delivery model "
                        "in one comparison. The healthy consumer reads with XREADGROUP "
                        "and then ACKS — acknowledgement is the work-done signal, and "
                        "until it fires the entries belong to that consumer. The "
                        "poison consumer reads and never acks: identical delivery, "
                        "zero completion — which is exactly what a crashed or stuck "
                        "worker looks like from the broker's point of view:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="log-consume",
                    language="py",
                    caption="One read round: the persona decides whether acknowledgement happens.",
                    source="server/guide/domain/messaging/stream_service.py",
                    snippet=(
                        "        await self.ensure_ready()\n"
                        "        consumer = HEALTHY_CONSUMER if request.mode == \"healthy\" else POISON_CONSUMER\n"
                        "        delivered = await self._consumer.read_new(STREAM_KEY, GROUP, consumer, request.count)\n"
                        "        acked = 0\n"
                        "        if request.mode == \"healthy\" and delivered:\n"
                        "            acked = await self._consumer.ack(STREAM_KEY, GROUP, [row.id for row in delivered])"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="log-ordering",
                    text=(
                        "Ordering falls out of the entry id, not out of bookkeeping: "
                        "XADD mints ids of the form milliseconds-dash-sequence, so the "
                        "log's id order IS arrival order, XRANGE walks it start to "
                        "finish, and a consumer group created at 0-0 (this lab's "
                        "choice) replays the whole history — the property that makes a "
                        "log an audit trail and a rebuild mechanism, not just a pipe. "
                        "The adapter below is the real redis-py call; note that '>' "
                        "means \"only entries never delivered to this group\", the "
                        "half of XREADGROUP that makes consumer groups a work queue:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="log-read-adapter",
                    language="py",
                    caption="XREADGROUP '>' over the shared client — the adapter's honest shapes.",
                    source="server/guide/data/messaging/redis_streams.py",
                    snippet=(
                        "        with _map_messaging_failures(\"read_new\"):\n"
                        "            reply = cast(\n"
                        "                \"list[tuple[str, list[ReplyPair]]] | None\",\n"
                        "                await self._client.xreadgroup(group, consumer, {stream: \">\"}, count=count),\n"
                        "            )\n"
                        "            pairs: list[ReplyPair] = []\n"
                        "            for reply_stream, reply_entries in reply or []:\n"
                        "                if reply_stream == stream:\n"
                        "                    pairs = reply_entries\n"
                        "            return [_decode(str(entry_id), fields) for entry_id, fields in pairs]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="log-anatomy",
                    text=(
                        "An entry's anatomy is deliberately boring: the id, plus a "
                        "FLAT string-to-string field dictionary — no nesting, no "
                        "types, no broker-side schema. This guide encodes every event "
                        "as three fields (event_id, type, payload) with the payload a "
                        "canonical JSON string, so the producer's bytes and the "
                        "consumer's bytes are the same bytes and the log never "
                        "interprets what it carries — the same canonical-serialization "
                        "discipline the cache and webhook topics used, now across a "
                        "broker. One more log fact the demos make visible by omission: "
                        "a log GROWS. Production trims (XADD accepts an approximate "
                        "MAXLEN, or XRANGE-plus-XDEL for exact windows), and trimming "
                        "interacts with pending state — reclaiming an entry whose "
                        "place in the log was trimmed away is why XAUTOCLAIM also "
                        "answers with the ids it CLEARED; the adapter's comment "
                        "marks exactly where that third reply element is handled."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="log-demo-pitch",
                    text=(
                        "Try it: produce two notes and watch the entry ids' "
                        "millisecond prefixes order themselves; consume as the "
                        "healthy worker and watch the ack clear the backlog; consume "
                        "as the poison worker instead and watch the SAME entries land "
                        "in the pending list with their owner named; then hand the "
                        "backlog to section four's reclaim. The panel shows the log "
                        "in order, its length, its last id, and the pending count — "
                        "all read live from the stream."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="msg:stream",
                    title="The stream lab",
                    description=(
                        "One Redis Stream (guide_demo:msg:stream), one consumer "
                        "group, two personas over the REAL adapter: produce XADDs a "
                        "UUIDv7-keyed note; consume reads as healthy-worker (XREADGROUP "
                        "then XACK) or poison-worker (reads, never acks — entries land "
                        "in the group's pending list); the pending panel lists owner, "
                        "idle milliseconds, and delivery count from XPENDING; reclaim "
                        "moves stale entries back with XAUTOCLAIM and finishes them; "
                        "the roster shows the whole log in id order with length and "
                        "last id."
                    ),
                ),
            ],
        ),
        # ── 3. Delivery guarantees ─────────────────────────────────────────
        Section(
            id="delivery-guarantees",
            title="Delivery guarantees",
            blocks=[
                TextBlock(
                    kind="text",
                    id="guarantees-pitch",
                    text=(
                        "Once a message leaves the request that produced it, \"did it "
                        "arrive?\" stops having one answer and starts having a "
                        "CONTRACT. Every broker sells one of three, and the differences "
                        "are not marketing — they are statements about which failure "
                        "windows the broker is willing to close for you:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="guarantees-list",
                    ordered=False,
                    items=[
                        "At-most-once — fire and forget: a send that fails, or a "
                        "delivery the consumer drops, is simply LOST; no retries, no "
                        "record. Cheap, fast, and right only for data whose loss is "
                        "boring (metrics samples, cache warming hints).",
                        "At-least-once — the workhorse: the broker stores, the "
                        "consumer acknowledges AFTER processing, and anything "
                        "unacknowledged (timeout, crash, rejected) is redelivered; "
                        "the cost is that duplicates are a normal, expected event.",
                        "Exactly-once — the broker promise that is really two "
                        "promises bolted together: at-least-once delivery PLUS "
                        "idempotent (transactional) processing on the consumer side; "
                        "no mainstream system delivers it without that second half.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="guarantees-mechanics",
                    text=(
                        "The mechanics matter more than the labels. WHEN the consumer "
                        "acknowledges is the whole contract in one decision: ack "
                        "BEFORE processing and a crash between ack and work loses the "
                        "message (at-most-once sneaks in through the back door); ack "
                        "AFTER processing and a crash between work and ack guarantees "
                        "a redelivery — a duplicate, which is survivable, instead of a "
                        "loss, which is not. Redis Streams default to at-least-once "
                        "with explicit XACK; the pending machinery in section four is "
                        "precisely the bookkeeping that makes the redelivery half "
                        "real. This guide's outbox relay (section five) publishes "
                        "at-least-once ON PURPOSE, and the whole of section six exists "
                        "to absorb the duplicates that decision produces."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="guarantees-substrate",
                    text=(
                        "This topic's substrate takes the workhorse contract, and its "
                        "commands ARE the contract's moving parts: XREADGROUP is the "
                        "delivery (recorded in the PEL), XACK is the completion (the "
                        "only thing that erases a PEL entry), and a consumer that "
                        "dies between the two is exactly the case section four's "
                        "reclaim exists to finish. The lab's personas act out the "
                        "ack-placement decision physically — the healthy consumer "
                        "acks after its work, the poison consumer never does, and "
                        "the difference between their pending panels is the entire "
                        "content of this section rendered in broker state. Watch the "
                        "delivery counts in that panel climb after a reclaim round "
                        "and you are watching at-least-once keeping count of how "
                        "many chances an entry has had."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="guarantees-honesty",
                    text=(
                        "A sentence of honesty about \"exactly-once\" marketing: even "
                        "systems that advertise it (Kafka's transactional producer, "
                        "commercial brokers' once-mode) implement it as at-least-once "
                        "delivery plus de-duplication or transactional writes INSIDE a "
                        "bounded scope — same producer, same partition, same session. "
                        "Across a database write in your handler and a broker offset "
                        "in someone else's storage, no single system can see both "
                        "halves atomically, and the honest architecture plans for "
                        "duplicates everywhere the scope ends. Design at-least-once, "
                        "dedupe deliberately, and \"exactly-once\" becomes an EFFECT "
                        "you engineered rather than a checkbox you trusted."
                    ),
                ),
            ],
        ),
        # ── 4. Pending entries and XAUTOCLAIM ──────────────────────────────
        Section(
            id="pending-entries-and-xautoclaim",
            title="Pending entries and XAUTOCLAIM",
            blocks=[
                TextBlock(
                    kind="text",
                    id="pending-pitch",
                    text=(
                        "The pending entries list is where at-least-once keeps its "
                        "promises: every XREADGROUP delivery records entry id, owning "
                        "consumer, delivery count, and idle time, and the entry STAYS "
                        "recorded until its owner acks it. A healthy consumer's "
                        "pending entries are simply work in flight; a dead one's are "
                        "a backlog with an owner who will never finish. XPENDING is "
                        "the inspection command — the lab's pending panel is its "
                        "range form, and the adapter maps redis's reply into the "
                        "domain's honest row:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pending-adapter",
                    language="py",
                    caption="XPENDING's range form — owner, idle milliseconds, delivery count.",
                    source="server/guide/data/messaging/redis_streams.py",
                    snippet=(
                        "        with _map_messaging_failures(\"pending\"):\n"
                        "            raw = await self._client.xpending_range(\n"
                        "                stream, group, min=\"-\", max=\"+\", count=count\n"
                        "            )\n"
                        "            return [\n"
                        "                PendingRow(\n"
                        "                    entry_id=str(row[\"message_id\"]),\n"
                        "                    consumer=str(row[\"consumer\"]),\n"
                        "                    idle_ms=int(row[\"time_since_delivered\"]),\n"
                        "                    deliveries=int(row[\"times_delivered\"]),\n"
                        "                )\n"
                        "                for row in raw\n"
                        "            ]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pending-claim-pitch",
                    text=(
                        "Reclaim is where ownership transfers: XAUTOCLAIM takes any "
                        "pending entry whose idle time has passed a threshold and "
                        "moves it to a HEALTHY consumer, in one server-side "
                        "operation. The threshold is a visibility timeout — entries "
                        "younger than it are presumed still being worked on, and "
                        "stealing them would create a duplicate worker; entries older "
                        "are presumed abandoned. The claim itself only changes "
                        "ownership; the claiming consumer still has to DO the work "
                        "and ack, which is why the engine claims and then acks as one "
                        "round:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pending-reclaim",
                    language="py",
                    caption="The reclaim round: claim the stale, finish the work, ack.",
                    source="server/guide/domain/messaging/stream_service.py",
                    snippet=(
                        "        claimed = await self._consumer.claim(\n"
                        "            STREAM_KEY, GROUP, HEALTHY_CONSUMER, request.min_idle_ms, RECLAIM_COUNT\n"
                        "        )\n"
                        "        acked = 0\n"
                        "        if claimed:\n"
                        "            acked = await self._consumer.ack(STREAM_KEY, GROUP, [row.id for row in claimed])"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pending-claim-adapter",
                    language="py",
                    caption="XAUTOCLAIM behind the port — the command with the threshold in it.",
                    source="server/guide/data/messaging/redis_streams.py",
                    snippet=(
                        "        with _map_messaging_failures(\"claim\"):\n"
                        "            reply = await self._client.xautoclaim(\n"
                        "                stream, group, consumer, min_idle_time=min_idle_ms, count=count\n"
                        "            )\n"
                        "            pairs = cast(\"list[ReplyPair]\", reply[1])\n"
                        "            return [_decode(entry_id, fields) for entry_id, fields in pairs]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pending-xclaim",
                    text=(
                        "Redis offers the older XCLAIM for the same job — move a "
                        "specific pending id to a consumer — and the difference is "
                        "the bookkeeping you would otherwise write yourself: XCLAIM "
                        "wants you to already know the ids, while XAUTOCLAIM walks "
                        "the pending list server-side, applies the idle threshold "
                        "for you, increments each claimed entry's delivery counter "
                        "(so poison detection keeps working across reclaims), and "
                        "answers with a CURSOR for lists longer than one round — "
                        "a production reclaimer loops that cursor until it wraps to "
                        "zero, while the lab's single bounded round keeps the demo "
                        "honest about doing one page of work per button press. "
                        "Either way the ownership change is instant and the WORK "
                        "is not: claiming an entry nobody is processing is safe, "
                        "claiming one somebody still holds past their visibility "
                        "timeout is how duplicate workers happen — the threshold, "
                        "not the command, is the actual design decision."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pending-read",
                    text=(
                        "Three production notes the lab makes physical. First, the "
                        "delivery count is your poison detector: an entry redelivered "
                        "many times is not unlucky — it is probably unprocessable, and "
                        "the right move is a dead-letter path (ack it OUT of the "
                        "pending list into a failure stream a human can inspect and "
                        "replay — topic 14 built exactly that shape for webhooks, and "
                        "topic 29's job queues formalize it). Second, the threshold "
                        "must exceed your slowest legitimate handler, or reclaim "
                        "duplicates live work. Third, the lab's poison persona is a "
                        "CONTROLLED version of the worst case — a consumer that "
                        "reads and never finishes; every real backlog you will ever "
                        "debug looks exactly like its pending panel."
                    ),
                ),
            ],
        ),
        # ── 5. The transactional outbox ────────────────────────────────────
        Section(
            id="transactional-outbox",
            title="The transactional outbox",
            lead="This section carries the topic's second demo — the outbox lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="outbox-dual-write",
                    text=(
                        "The hardest problem in this topic is not reading — it is "
                        "WRITING to two stores atomically. The business saves a post "
                        "to PostgreSQL and should announce post.created to the "
                        "stream; done as two separate calls, every failure between "
                        "them corrupts the system — save-then-publish-fails loses the "
                        "announcement forever (a phantom post nobody reacts to), "
                        "publish-then-save-fails announces a post that does not "
                        "exist. No transaction can span PostgreSQL and Redis, so the "
                        "DUAL WRITE cannot be made atomic by trying harder. The "
                        "transactional outbox dissolves the problem: the business "
                        "transaction writes the post AND an event row into the SAME "
                        "PostgreSQL commit — one database, one transaction, trivially "
                        "atomic — and a separate relay delivers the row to the stream "
                        "later. This guide's outbox is a real migration, not a "
                        "diagram:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="outbox-migration",
                    language="py",
                    caption="Migration 0004 — the outbox table, UUIDv7 event ids, published_at NULL as the work queue.",
                    source="server/alembic/versions/0004_outbox.py",
                    snippet=(
                        "    op.create_table(\n"
                        "        \"outbox\",\n"
                        "        sa.Column(\n"
                        "            \"id\",\n"
                        "            sa.BigInteger(),\n"
                        "            server_default=sa.text(\"nextval('outbox_id_seq'::regclass)\"),\n"
                        "            nullable=False,\n"
                        "        ),\n"
                        "        sa.Column(\"event_id\", postgresql.UUID(), nullable=False),\n"
                        "        sa.Column(\"event_type\", sa.Text(), nullable=False),\n"
                        "        sa.Column(\"aggregate\", sa.Text(), nullable=False),\n"
                        "        sa.Column(\"payload\", postgresql.JSONB(), nullable=False),\n"
                        "        sa.Column(\n"
                        "            \"created_at\",\n"
                        "            postgresql.TIMESTAMP(timezone=True),\n"
                        "            server_default=sa.text(\"now()\"),\n"
                        "            nullable=False,\n"
                        "        ),\n"
                        "        sa.Column(\"published_at\", postgresql.TIMESTAMP(timezone=True), nullable=True),\n"
                        "        sa.PrimaryKeyConstraint(\"id\", name=op.f(\"pk_outbox\")),\n"
                        "        sa.UniqueConstraint(\"event_id\", name=op.f(\"uq_outbox_event_id\")),\n"
                        "    )\n"
                        "    op.execute(\n"
                        "        sa.text(\n"
                        "            \"CREATE INDEX ix_outbox_unpublished ON outbox (id) \"\n"
                        "            \"WHERE published_at IS NULL\"\n"
                        "        )\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="outbox-one-tx",
                    text=(
                        "The business write is then one ordinary transaction with an "
                        "extra INSERT in it — the event rides the post's commit, and "
                        "the atomicity the dual write could never buy across two "
                        "stores comes free inside one. The partial index above is the "
                        "relay's entire work queue: only unpublished rows, in "
                        "insertion order, shrinking as the relay catches up. The "
                        "adapter mints the event's UUIDv7 ONCE at write time — the "
                        "stable identity a redelivered event will still carry in "
                        "section six:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="outbox-write",
                    language="py",
                    caption="The one-transaction dual write: the post INSERT and the outbox INSERT, one commit.",
                    source="server/guide/data/messaging/outbox_store.py",
                    snippet=(
                        "                async with self._engine.begin() as connection:\n"
                        "                    author_name = await connection.scalar(\n"
                        "                        sa.select(authors.c.name).where(authors.c.id == DEMO_AUTHOR_ID)\n"
                        "                    )\n"
                        "                    if author_name is None:\n"
                        "                        raise AppError(FailureKind.SERVICE_UNAVAILABLE, SEED_MISSING_MESSAGE)\n"
                        "\n"
                        "                    inserted = await connection.execute(\n"
                        "                        sa.insert(posts)\n"
                        "                        .values(\n"
                        "                            author_id=DEMO_AUTHOR_ID,\n"
                        "                            slug=slug,\n"
                        "                            title=draft.title,\n"
                        "                            body=draft.body,\n"
                        "                            status=\"published\",\n"
                        "                        )\n"
                        "                        .returning(posts.c.id, posts.c.created_at)\n"
                        "                    )\n"
                        "                    post = inserted.one()\n"
                        "                    # …\n"
                        "                    stamped = await connection.execute(\n"
                        "                        sa.insert(outbox)\n"
                        "                        .values(\n"
                        "                            event_id=event_id,\n"
                        "                            event_type=EVENT_TYPE,\n"
                        "                            aggregate=f\"posts:{post.id}\",\n"
                        "                            payload=payload,\n"
                        "                        )\n"
                        "                        .returning(outbox.c.created_at)\n"
                        "                    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="outbox-relay-pitch",
                    text=(
                        "The relay closes the loop, and its GAPS are the lesson: it "
                        "polls unpublished rows, XADDs each to the stream, and only "
                        "then marks the row published. Publish and mark cannot be "
                        "atomic across two stores — a relay that dies between them "
                        "leaves a delivered-but-unmarked row, and the next cycle "
                        "publishes it AGAIN. That duplicate is not a defect to "
                        "engineer away; it is at-least-once delivery keeping its "
                        "promise, and the demo's crash button opens the window on "
                        "purpose so the next section's consumer can absorb it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="outbox-relay",
                    language="py",
                    caption="The relay cycle: poll, publish each, mark — with the crash window between.",
                    source="server/guide/domain/messaging/outbox_service.py",
                    snippet=(
                        "        async with self._relay_lock:\n"
                        "            self._cycle += 1\n"
                        "            discovered = await self._outbox.unpublished(request.batch)\n"
                        "            published: list[PublishedEntryRow] = []\n"
                        "            for row in discovered:\n"
                        "                entry_id = await self._producer.append(\n"
                        "                    OUTBOX_STREAM,\n"
                        "                    EventDraft(\n"
                        "                        event_id=row.event_id,\n"
                        "                        event_type=row.event_type,\n"
                        "                        payload=row.payload,\n"
                        "                    ),\n"
                        "                )\n"
                        "                # …\n"
                        "            crashed = request.crash_before_mark and bool(published)\n"
                        "            if crashed:\n"
                        "                self._crashes += 1"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="outbox-variants",
                    text=(
                        "The relay itself has three honest implementations, and this "
                        "guide chose the first. A POLLING relay (this substrate): a "
                        "loop or a cron-triggered cycle SELECTs unpublished rows and "
                        "publishes them — seconds of latency at worst, zero extra "
                        "infrastructure, and entirely sufficient for most workloads. "
                        "A CDC relay (Debezium and kin): reads PostgreSQL's write-"
                        "ahead log and turns outbox INSERTs into stream entries — "
                        "millisecond latency and no polling load, at the price of "
                        "another deployed system with its own operational story. "
                        "And the variant to refuse: publishing from inside the "
                        "business transaction with \"transactional\" client APIs — "
                        "the atomicity they offer ends at their own broker and "
                        "leaves the dual-write problem exactly where it was. "
                        "Whatever relays, two properties must hold: delivery ORDER "
                        "follows the outbox id (the poll's ORDER BY), and the mark "
                        "happens only after the publish — the relay's lock in the "
                        "quoted cycle keeps concurrent triggers from doubling the "
                        "backlog beyond what the crash window already teaches."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="outbox-demo-pitch",
                    text=(
                        "Try it: create a post-with-event and read the response — "
                        "both rows, one transaction, the event still unpublished. "
                        "Relay with the crash window open: the event lands on the "
                        "stream, the row stays unpublished, the payload says exactly "
                        "that. Relay again normally: the SAME row is rediscovered, "
                        "republished (the stream now holds a duplicate), and marked. "
                        "Consume: the idempotent walk processes the event once and "
                        "SKIPS the duplicate — the counts are the exactly-once "
                        "effect. The panel tracks table counts, recent rows with "
                        "their published stamps, stream entries, and the demo's "
                        "counters."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="msg:outbox",
                    title="The outbox lab",
                    description=(
                        "PostgreSQL and Redis bridged for real: POST /outbox/posts "
                        "commits a post AND its outbox event in ONE transaction "
                        "(UUIDv7 event id, JSONB payload); POST /outbox/relay runs "
                        "the cycle poll → XADD → mark over the 0004 partial index, "
                        "with crashBeforeMark opening the publish-then-die window; "
                        "POST /outbox/consume walks the stream through the "
                        "processed-set dedupe and reports processed vs skipped — "
                        "after a crash round the numbers prove the exactly-once "
                        "EFFECT; GET /outbox shows table counts, recent rows, "
                        "stream entries, and telemetry."
                    ),
                ),
            ],
        ),
        # ── 6. Idempotent consumers ────────────────────────────────────────
        Section(
            id="idempotent-consumers",
            title="Idempotent consumers",
            blocks=[
                TextBlock(
                    kind="text",
                    id="idem-pitch",
                    text=(
                        "At-least-once delivery means every consumer WILL see some "
                        "events more than once, and the exactly-once experience is "
                        "built on the consuming side: remember what you have "
                        "handled, and skip the repeats. The event id is the anchor "
                        "— the UUIDv7 minted once at outbox-write time and carried "
                        "unchanged through every redelivery, so \"have I seen this "
                        "BEFORE\" is one set lookup, not a heuristic over payloads. "
                        "The store behind the memory is one small port, and the "
                        "adapter implements it as a Redis SET under the demo "
                        "namespace:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="idem-port",
                    language="py",
                    caption="The processed-set port — one membership question, one remember call.",
                    source="server/guide/domain/messaging/ports.py",
                    snippet=(
                        "@runtime_checkable\n"
                        "class ProcessedEventStore(Protocol):\n"
                        '    """The idempotent consumer\'s processed-set — event ids already handled."""\n'
                        "\n"
                        "    async def seen(self, set_key: str, event_id: str) -> bool:\n"
                        '        """True when ``event_id`` was already processed (the set remembers)."""\n'
                        "        ...\n"
                        "\n"
                        "    async def remember(self, set_key: str, event_id: str) -> None:\n"
                        '        """Record ``event_id`` as processed — AFTER the work, not before."""\n'
                        "        ..."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="idem-order",
                    text=(
                        "The order of the two calls is the whole design, and it is a "
                        "deliberate trade rather than a detail: check BEFORE the "
                        "work, remember AFTER it. Remembering before the work would "
                        "make a mid-work crash LOSE the event forever (at-most-once "
                        "creeping back in); remembering after it means a crash "
                        "between work and remember replays the work once on "
                        "redelivery — a duplicate effect, which is auditable, "
                        "instead of a silent loss, which is not. The engine's one "
                        "docstring line states the contract the suite pins:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="idem-note",
                    language="py",
                    caption="The ordering decision, stated once where the suite can find it.",
                    source="server/guide/domain/messaging/idempotence.py",
                    snippet=(
                        "REMEMBER_ORDER_NOTE: Final = (\n"
                        "    \"the processed-set is checked before the work and remembered after it — \"\n"
                        "    \"crashes may replay work, never lose it\"\n"
                        ")"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="idem-walk",
                    language="py",
                    caption="The walk: ordered awaits, first sightings work, repeats skip.",
                    source="server/guide/domain/messaging/idempotence.py",
                    snippet=(
                        "        processed: list[str] = []\n"
                        "        skipped_duplicates: list[str] = []\n"
                        "        for entry in entries:\n"
                        "            if await self._store.seen(self._set_key, entry.event_id):\n"
                        "                skipped_duplicates.append(entry.event_id)\n"
                        "                continue\n"
                        "            await self._store.remember(self._set_key, entry.event_id)\n"
                        "            processed.append(entry.event_id)\n"
                        "        return DedupeWalk(processed=processed, skipped_duplicates=skipped_duplicates)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="idem-read",
                    text=(
                        "Two honest limits keep this from being a magic wand. The "
                        "set GROWS: a production processed-set needs a retirement "
                        "story — a TTL past any conceivable redelivery window, or "
                        "persistence keyed so old ids age out — because an "
                        "unbounded set is a slow leak. And dedupe-by-id only makes "
                        "the DELIVERY once; the handler itself should still be "
                        "safe to run twice for the crash-before-remember window "
                        "(an upsert, not an insert; a counter keyed by event id, "
                        "not a blind increment). The demo's numbers make the "
                        "combined effect concrete: after one crash round the "
                        "stream holds two entries for one event, and the walk "
                        "answers processed one, skipped one — exactly-once as an "
                        "engineered effect, on top of two stores that each only "
                        "promised at-least-once."
                    ),
                ),
            ],
        ),
        # ── 7. Kafka and RabbitMQ ──────────────────────────────────────────
        Section(
            id="kafka-and-rabbitmq",
            title="Kafka and RabbitMQ",
            blocks=[
                TextBlock(
                    kind="text",
                    id="survey-pitch",
                    text=(
                        "This topic built on Redis Streams because the guide already "
                        "runs Redis and the concepts transfer unchanged — but the "
                        "wider ecosystem has two canonical shapes worth knowing "
                        "honestly, neither of which you should reach for by default. "
                        "The positioning below is about what each system IS, not "
                        "which is fashionable:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="survey-list",
                    ordered=False,
                    items=[
                        "Kafka — a distributed LOG first: partitions for parallelism, "
                        "retention in time rather than per-consumer, consumer groups "
                        "and rebalancing built in; its strength is high-throughput "
                        "event pipelines and replayable history, and its weight is "
                        "operational (brokers, ZooKeeper/KRaft, tuning) that a "
                        "single FastAPI service rarely owes.",
                        "RabbitMQ — a distributed QUEUE first: flexible routing "
                        "(exchanges, bindings, topics), per-message acknowledgement "
                        "and dead-lettering, excellent at complex WORK distribution "
                        "at moderate throughput; messages are not a replayable "
                        "history, and throughput ceilings arrive sooner than a log's.",
                        "Redis Streams — the log shape embedded in a store you may "
                        "already run: consumer groups, pending lists, XAUTOCLAIM "
                        "(everything this topic used), single-node scale; right up "
                        "to the point where volume or durability requirements "
                        "outgrow a cache's SLA.",
                        "Cloud queues (SQS, Pub/Sub, EventBridge) — managed "
                        "at-least-once queues with visibility timeouts doing what "
                        "section four taught; the outbox pattern in front of them is "
                        "unchanged, because the dual-write problem does not care "
                        "which broker follows it.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="survey-choosing",
                    text=(
                        "The choosing heuristic this guide recommends: start with "
                        "what you already operate — for most FastAPI services that "
                        "is PostgreSQL plus maybe Redis, and sections five and six "
                        "just proved that pair delivers durable, atomic, "
                        "exactly-once-in-effect messaging with no new moving parts. "
                        "Add Kafka when REPLAY and volume are the product (event "
                        "pipelines, analytics feeds, many independent consumers of "
                        "one history); add RabbitMQ when ROUTING is the product "
                        "(one incoming event fanned to differing queues by rules, "
                        "classic task distribution). And whichever broker you "
                        "choose, the two patterns that made this topic work — "
                        "write the event in the business transaction, dedupe by "
                        "stable event id on the consumer — stay exactly the same, "
                        "because they answer problems the broker cannot see: your "
                        "database and your handler."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="survey-jobs",
                    text=(
                        "One boundary worth drawing before the shell tour: an event "
                        "broker is not a JOB RUNNER. Events here are facts with "
                        "consumers; jobs (send this email at 09:00, retry this "
                        "render five times with backoff, run this report nightly) "
                        "need scheduling, per-task retry policies, and dead-letter "
                        "queues owned by the TASK — topic 29 builds exactly that "
                        "over worker queues, and it is no accident that its "
                        "reliability vocabulary (attempts, backoff, dead-letter) is "
                        "the one topic 14's webhooks and this topic's pending "
                        "machinery kept reusing. The outbox hands an event to the "
                        "world; a job queue hands a TASK to a worker. Systems that "
                        "conflate the two end up encoding cron expressions as "
                        "stream entries, and nobody deserves that."
                    ),
                ),
            ],
        ),
        # ── 8. Terminal companion ──────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole topic, from a shell — real deliveries, real pending, real counts.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Eight stops: the stream roster, the produce-then-ack round, "
                        "the poison read with its pending list, the XAUTOCLAIM "
                        "reclaim, the outbox's one-transaction create, the crash "
                        "window and its redelivery, the idempotent counts, and the "
                        "topic payload itself. The stack is up; every command "
                        "answers with real broker bookkeeping."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-roster",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the stream roster: the log in order, its pending backlog\n"
                        "curl -s localhost:8000/api/demo/msg/stream | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "print(\"stream:\", b[\"stream\"], \"· group:\", b[\"group\"])\n"
                        "print(\"length:\", b[\"length\"], \"· last:\", b[\"lastId\"], \"· pending:\", b[\"pendingCount\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-round",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the happy round: produce two, consume healthy, watch the ack\n"
                        "curl -s -X POST -H 'content-type: application/json' -d '{\"note\":\"tour one\"}' \\\n"
                        "  localhost:8000/api/demo/msg/stream/produce | python3 -c 'import json,sys; print(\"entry:\", json.load(sys.stdin)[\"entryId\"])'\n"
                        "curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"mode\":\"healthy\",\"count\":5}' localhost:8000/api/demo/msg/stream/consume \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"delivered:\", len(b[\"delivered\"]), \"· acked:\", b[\"acked\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-poison",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the poison read: delivered, never acked, pending grows\n"
                        "curl -s -X POST -H 'content-type: application/json' -d '{\"note\":\"stuck\"}' \\\n"
                        "  localhost:8000/api/demo/msg/stream/produce > /dev/null\n"
                        "curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"mode\":\"poison\",\"count\":5}' localhost:8000/api/demo/msg/stream/consume \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"poison delivered:\", len(b[\"delivered\"]), \"· acked:\", b[\"acked\"])'\n"
                        "curl -s localhost:8000/api/demo/msg/stream/pending \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"pending:\", [(e[\"consumer\"], e[\"deliveries\"]) for e in b[\"entries\"]])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-reclaim",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — XAUTOCLAIM: the healthy consumer takes the stale backlog back\n"
                        "curl -s -X POST -H 'content-type: application/json' -d '{\"minIdleMs\":0}' \\\n"
                        "  localhost:8000/api/demo/msg/stream/reclaim \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"claimed:\", len(b[\"claimed\"]), \"· acked:\", b[\"acked\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-outbox-create",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the outbox write: post + event, ONE transaction\n"
                        "curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"title\":\"The outbox pattern, from a shell\",\"body\":\"both rows or neither\"}' \\\n"
                        "  localhost:8000/api/demo/msg/outbox/posts \\\n"
                        "  | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "print(\"committed:\", b[\"committed\"], \"· post:\", b[\"post\"][\"id\"])\n"
                        "print(\"event:\", b[\"event\"][\"eventId\"], \"· published:\", b[\"event\"][\"publishedAt\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-crash",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — the crash window, then the redelivery it guarantees\n"
                        "curl -s -X POST -H 'content-type: application/json' -d '{\"crashBeforeMark\":true}' \\\n"
                        "  localhost:8000/api/demo/msg/outbox/relay \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"crashed:\", b[\"crashed\"], \"· published:\", len(b[\"published\"]), \"· marked:\", b[\"marked\"])'\n"
                        "curl -s -X POST -H 'content-type: application/json' -d '{}' \\\n"
                        "  localhost:8000/api/demo/msg/outbox/relay \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(\"rediscovered:\", b[\"discovered\"], \"· marked:\", b[\"marked\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-dedupe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 7 — the exactly-once EFFECT: one event, two entries, one processed\n"
                        "curl -s -X POST localhost:8000/api/demo/msg/outbox/consume \\\n"
                        "  | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "print(f\"{b[\"entries\"]} entries -> processed {b[\"processed\"]}, skipped {b[\"skippedDuplicates\"]}\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-topic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 8 — this topic: eight sections, two demos inline where they teach\n"
                        "curl -s localhost:8000/api/content/messaging | python3 -c '\n"
                        "import json, sys\n"
                        "t = json.load(sys.stdin)\n"
                        "print(\"sections:\", len(t[\"sections\"]))\n"
                        "for s in t[\"sections\"]:\n"
                        "    demos = [b[\"id\"] for b in s[\"blocks\"] if b[\"kind\"] == \"demo\"]\n"
                        "    print(\" \", s[\"id\"], (\"· demo: \" + \", \".join(demos)) if demos else \"\")'\n"
                        "# the namespace, from the store's own mouth\n"
                        "docker exec fastapi_developers_guide_redis_dev \\\n"
                        "  redis-cli --scan --pattern 'guide_demo:msg:*'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stops 2 through 4 are the read side's whole story — ack as "
                        "work-done, pending as the honest backlog, reclaim as the "
                        "recovery. Stops 5 through 7 are the write side's whole "
                        "story: one transaction for post and event, a crash window "
                        "that must be survivable, and counts that prove it was. The "
                        "state-and-auth group now has caching and messaging; the "
                        "next topic puts IDENTITY on this same stack, and every "
                        "pattern here — durable writes, at-least-once, dedupe by "
                        "stable id — keeps earning its keep in it."
                    ),
                ),
            ],
        ),
    ],
)
