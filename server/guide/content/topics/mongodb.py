"""Topic 19 — MongoDB and document stores (fourth topic of the Data group).

Topics 16–18 built the relational half of the data phase; this topic
opens the NoSQL half with the store this guide actually runs besides
PostgreSQL. It teaches document thinking (BSON, embedding, flexible
schema as a managed choice), the optional-service discipline that lets
the app boot and serve with MongoDB down, the motor async client (with
the event-loop fine print this guide measured), validation in the
application layer (pydantic as the only schema), queries, indexes with
explain() and TTL indexes, where a document store sits in this
architecture (ports and adapters, same as everything else), an honest
SQL-vs-Mongo comparison grounded in a repo that uses both, and a prose
survey of the wider NoSQL landscape. One demo, inline in the section
that teaches queries: a real console over the live MongoDB.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="mongodb",
    title="MongoDB and document stores",
    subtitle=(
        "Documents over rows — BSON, the optional-service discipline, "
        "motor, pydantic as the only schema, indexes and TTL, and an "
        "honest SQL-vs-Mongo ledger."
    ),
    group="data",
    order=19,
    sections=[
        # ── 1. Document thinking ────────────────────────────────────────────
        Section(
            id="document-thinking",
            title="Document thinking",
            blocks=[
                TextBlock(
                    kind="text",
                    id="doc-pitch",
                    text=(
                        "Everything topics 16 through 18 taught assumed the "
                        "relational shape: rows of a fixed column set, joined "
                        "by keys, normalized to keep one fact in one place. A "
                        "document store makes a different bet. The unit of "
                        "storage is the DOCUMENT — a self-describing tree of "
                        "fields, arrays, and subdocuments, serialized as BSON "
                        "(JSON's binary cousin with real dates, 64-bit "
                        "integers, and ObjectIds) — and a COLLECTION holds "
                        "documents the way a folder holds files: related by "
                        "convention, not by a declared shape. MongoDB is the "
                        "document store this guide runs, and the same six "
                        "authors-and-notes world the SQL topics used maps "
                        "onto it without a single CREATE TABLE."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="doc-seed-pitch",
                    text=(
                        "Here is one of the console demo's seed documents — a "
                        "plain pydantic model in the adapter, dumped straight "
                        "into the collection. No migration wrote its shape; "
                        "the model IS the shape:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="doc-seed-note",
                    language="py",
                    caption="One seed note: the whole record is one value, stored as one BSON document.",
                    source="server/guide/data/mongo/console.py",
                    snippet=(
                        "SEED_NOTES: Final[tuple[ConsoleNoteDraft, ...]] = (\n"
                        "    ConsoleNoteDraft(\n"
                        "        key=\"mongo-note-documents\",\n"
                        "        author=\"Grace Hopper\",\n"
                        "        title=\"A document is the unit\",\n"
                        "        body=\"No rows, no joins over foreign keys — the whole record is one addressable value.\",\n"
                        "        tags=[\"modeling\"],\n"
                        "        status=\"published\",\n"
                        "        created_at=datetime(2026, 10, 1, 9, 0, tzinfo=UTC),\n"
                        "    ),\n"
                        "    # …\n"
                        ")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="doc-modeling-pitch",
                    text=(
                        "The mental shift is in the tags field. In PostgreSQL "
                        "a multi-valued fact demanded a second table or a "
                        "column type (topic 16 chose an array with a GIN "
                        "index); here an array is just data, queried with the "
                        "same filter syntax as a scalar — ``{tags: \"indexes\"}`` "
                        "matches any document whose tags array CONTAINS the "
                        "value. That generalizes to the design rule: embed "
                        "what you read together. A document that carries its "
                        "list page — title, author, tags, date — is ONE read; "
                        "the relational equivalent was a join or the ORM's "
                        "selectin trickery from topic 18. The costs arrive "
                        "on the write side and in the consistency rules:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="doc-modeling-list",
                    ordered=False,
                    items=[
                        "Denormalization is the default — the same fact may "
                        "live in many documents (the author's name on every "
                        "note), so updates fan out and 'one fact one place' "
                        "becomes an application promise, not a schema "
                        "guarantee.",
                        "No joins across collections — MongoDB has "
                        "$lookup, but it is heavier than a relational join "
                        "and late to the party; embedding is the primary "
                        "tool, references (store the key, query again) the "
                        "fallback.",
                        "Flexible schema cuts both ways — a missing field "
                        "and a null and a differently-typed field are all "
                        "storable, so schema drift is a discipline problem "
                        "the application layer must own (section four).",
                        "Transactions exist but are the exception — "
                        "multi-document ACID transactions arrived in MongoDB "
                        "4.0 and cost more than single-document atomicity, "
                        "which is already guaranteed: one insert or replace "
                        "is atomic because the document IS the row.",
                        "ObjectId, not sequences — the default _id is a "
                        "12-byte value embedding a timestamp (roughly "
                        "sortable, topic 16's UUIDv7 argument in miniature); "
                        "any unique field can serve as _id instead.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="doc-read",
                    text=(
                        "Hold the framing for the whole topic: MongoDB is not "
                        "'SQL with different syntax' and it is not a "
                        "replacement — it is a storage engine whose unit of "
                        "locality is the aggregate your reads want. This "
                        "guide keeps PostgreSQL as the system of record and "
                        "treats the document store as a second, optional "
                        "citizen — which raises the very first engineering "
                        "question: what happens when it is DOWN?"
                    ),
                ),
            ],
        ),
        # ── 2. The optional-service discipline ─────────────────────────────
        Section(
            id="the-optional-service-discipline",
            title="The optional-service discipline",
            blocks=[
                TextBlock(
                    kind="text",
                    id="optional-pitch",
                    text=(
                        "The dev stack runs mongo in the same compose file as "
                        "the server, with no depends_on — deliberately. A "
                        "second store is a SECOND dependency, and every "
                        "dependency you add multiplies the failure modes of "
                        "every request that touches it. The family rule this "
                        "guide formalized in topic 16 (PostgreSQL down must "
                        "not stop the boot) extends unchanged: the app must "
                        "come up, serve content, answer health checks, and "
                        "run every non-mongo feature with MongoDB absent — "
                        "and the mongo demos must degrade to an honest 503 "
                        "envelope, never a hang, never a crash."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="optional-config-pitch",
                    text=(
                        "The wiring starts where all configuration does — one "
                        "rail in AppConfig, defaulting to localhost so the "
                        "app boots anywhere with zero setup:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="optional-config",
                    language="py",
                    caption="The mongo URL rail, same shape as the database and redis rails.",
                    source="server/guide/core/config.py",
                    snippet=(
                        "    mongo_url: str = \"mongodb://localhost:27017\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="optional-timeout-pitch",
                    text=(
                        "Degradation must also be FAST. A request that waits "
                        "out the driver's 30-second default server-selection "
                        "timeout is a hung worker, not a degraded feature, so "
                        "the client factory bounds it explicitly — two "
                        "seconds to find a server, two to connect:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="optional-timeout",
                    language="py",
                    caption="Timeout policy lives in exactly one place: the client factory.",
                    source="server/guide/data/mongo/client.py",
                    snippet=(
                        "SERVER_SELECTION_TIMEOUT_MS: Final = 2_000\n"
                        "# …\n"
                        "def create_mongo_client(config: AppConfig) -> AsyncIOMotorClient[dict[str, Any]]:\n"
                        "    # …\n"
                        "    return AsyncIOMotorClient(\n"
                        "        config.mongo_url,\n"
                        "        serverSelectionTimeoutMS=SERVER_SELECTION_TIMEOUT_MS,\n"
                        "        connectTimeoutMS=CONNECT_TIMEOUT_MS,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="optional-proof-pitch",
                    text=(
                        "And the behavior is PROVEN, not asserted. The suite "
                        "wires an app whose mongo URL points at a port nothing "
                        "will ever answer on, then checks the two halves of "
                        "the discipline in one test:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="optional-proof",
                    language="py",
                    caption="The boot-without-mongo proof: everything else serves; only the demo degrades.",
                    source="server/tests/demo/test_mongo_console_endpoint.py",
                    snippet=(
                        "    monkeypatch.setenv(\"FDG_MONGO_URL\", UNREACHABLE_MONGO_URL)\n"
                        "    # …\n"
                        "    with TestClient(app) as client:\n"
                        "        assert client.get(\"/api/health\").status_code == 200\n"
                        "        content = client.get(\"/api/content\")\n"
                        "        assert content.status_code == 200\n"
                        "        assert len(content.json()[\"topics\"]) >= 19\n"
                        "        degraded = client.get(MONGO_CONSOLE_PATH)\n"
                        "        assert degraded.status_code == 503\n"
                        "        assert degraded.json()[\"error\"][\"code\"] == \"service_unavailable\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="optional-read",
                    text=(
                        "Note what the test does NOT do: stop the real mongo "
                        "container. Proving degradation by tearing down a "
                        "shared dev service would make the suite hostile to "
                        "the machine it runs on; an unreachable URL is the "
                        "same code path (server selection fails, the adapter "
                        "maps it) without the collateral damage. The "
                        "envelope's request id, the logged warning with the "
                        "operation name, the 503 status — all of it is the "
                        "one error taxonomy from topic 30's preview, doing "
                        "exactly what it exists for."
                    ),
                ),
            ],
        ),
        # ── 3. The motor async client ──────────────────────────────────────
        Section(
            id="the-motor-async-client",
            title="The motor async client",
            blocks=[
                TextBlock(
                    kind="text",
                    id="motor-pitch",
                    text=(
                        "The Python driver story has two layers: pymongo is "
                        "the synchronous driver that speaks MongoDB's wire "
                        "protocol, and motor is a thin async skin over it — "
                        "await-colored methods that run the same pymongo "
                        "calls on a shared thread-pool executor, so nothing "
                        "blocks the event loop. You get the identical API "
                        "surface (clients, databases, collections, cursors) "
                        "with await in front, plus this guide's whole async "
                        "discipline from topic 2 applies verbatim: the "
                        "blocking work happens off-loop, futures hop back "
                        "on. Motor is the only new dependency this topic "
                        "adds — one ``uv add motor``, pymongo rides along."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="motor-lazy-pitch",
                    text=(
                        "Construction is lazy — building a client connects "
                        "to nothing, exactly like SQLAlchemy's engine in "
                        "topic 16. That laziness is what makes the "
                        "optional-service discipline cheap: the composition "
                        "root builds the client unconditionally, and only "
                        "the first OPERATION pays the connection cost:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="motor-wiring",
                    language="py",
                    caption="One lazy client per app, wired beside the engine — the composition root.",
                    source="server/guide/main.py",
                    snippet=(
                        "    mongo_client = create_mongo_client(config)\n"
                        "    app.state.mongo_client = mongo_client\n"
                        "    app.state.mongo_console = MongoConsoleRepository(mongo_client)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="motor-loop-pitch",
                    text=(
                        "One fine print matters enough to teach precisely, "
                        "because this guide measured it rather than "
                        "believing folklore: motor binds its event loop "
                        "LAZILY — at the first operation, not at "
                        "construction. Build a client, use it on loop A, "
                        "and it is pinned to A forever; a second use from "
                        "loop B raises 'Event loop is closed'. The guide's "
                        "wiring is therefore one client PER APP: under "
                        "uvicorn the first request pins the serving loop, "
                        "and in tests each app's client pins that test's "
                        "loop. A module-level shared client is the bug this "
                        "rule prevents — under --reload or across test "
                        "apps, one stale pin poisons every later use."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="motor-read",
                    text=(
                        "From there the driver surface is small and stable: "
                        "``client[\"guide_demo\"]`` is a database, "
                        "``database[\"console_notes\"]`` a collection, and "
                        "every method you will see in this topic's console "
                        "— insert_one, find, update_one, count_documents, "
                        "delete_one, create_index, command — is an awaited "
                        "motor method over the exact pymongo signature. "
                        "WriteConcern defaults to acknowledging the primary; "
                        "the demo keeps those defaults and says so, because "
                        "durability tuning is topic 39's conversation, not "
                        "a console's."
                    ),
                ),
            ],
        ),
        # ── 4. Validation in the application layer ─────────────────────────
        Section(
            id="validation-in-the-application-layer",
            title="Validation in the application layer",
            blocks=[
                TextBlock(
                    kind="text",
                    id="validation-pitch",
                    text=(
                        "Insert a dict into a collection and MongoDB will "
                        "store it — missing fields, wrong types, surprise "
                        "fields, all of it, forever. (There IS an optional "
                        "$jsonSchema validator per collection; this guide "
                        "does not use it, and the honest reason is that the "
                        "boundary already exists one layer up.) Topic 5 "
                        "established pydantic as the edge of the "
                        "application; a document store makes that choice "
                        "load-bearing, because the model is the ONLY schema "
                        "the data will ever have. The console's boundary "
                        "model is one pydantic class:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="validation-draft",
                    language="py",
                    caption="The whole schema: one pydantic model — extra fields forbidden.",
                    source="server/guide/domain/db/ports.py",
                    snippet=(
                        "class ConsoleNoteDraft(CamelModel):\n"
                        "    model_config = ConfigDict(extra=\"forbid\")\n"
                        "\n"
                        "    key: str = Field(min_length=3, max_length=64, pattern=r\"^[a-z0-9-]+$\")\n"
                        "    author: str = Field(min_length=2, max_length=80)\n"
                        "    title: str = Field(min_length=3, max_length=120)\n"
                        "    body: str = Field(min_length=1, max_length=2000)\n"
                        "    tags: list[Annotated[str, Field(min_length=1, max_length=40)]] = Field(\n"
                        "        min_length=1, max_length=8\n"
                        "    )\n"
                        "    status: Literal[\"draft\", \"published\", \"archived\"]\n"
                        "    created_at: datetime"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="validation-refusal-pitch",
                    text=(
                        "The console demo runs the boundary through its "
                        "paces on every request: first a deliberately bad "
                        "payload (empty title, empty tags, unknown status) "
                        "is model_validate'd and REFUSED — pydantic "
                        "collects all three field errors and no I/O of any "
                        "kind happens — then the valid draft is dumped and "
                        "inserted:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="validation-refusal",
                    language="py",
                    caption="Refusal first: the ValidationError is the whole exhibit — MongoDB never sees this document.",
                    source="server/guide/data/mongo/console.py",
                    snippet=(
                        "    try:\n"
                        "        ConsoleNoteDraft.model_validate(INVALID_DRAFT_PAYLOAD)\n"
                        "    except ValidationError as exc:\n"
                        "        errors = [\n"
                        "            f\"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}\"\n"
                        "            for error in exc.errors()\n"
                        "        ]\n"
                        "        return RefusalRow(\n"
                        "            attempted={field: str(value) for field, value in INVALID_DRAFT_PAYLOAD.items()},\n"
                        "            errors=errors,\n"
                        "        )"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="validation-insert",
                    language="py",
                    caption="Acceptance second: what crosses into the store is the VALIDATED dump.",
                    source="server/guide/data/mongo/console.py",
                    snippet=(
                        "        result = await console.insert_one(draft.model_dump())\n"
                        "        stored = {\"_id\": result.inserted_id, **draft.model_dump()}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="validation-read",
                    text=(
                        "Two details in that insert carry the whole "
                        "discipline. ``model_dump()`` without arguments is "
                        "python-mode: created_at stays a datetime, so BSON "
                        "stores a real date (sortable, TTL-able) rather "
                        "than a string that merely looks like one — the "
                        "same distinction topic 17's parameter binding "
                        "made about types. And the ``_id`` MongoDB mints "
                        "is an ObjectId, which never crosses the HTTP "
                        "boundary raw: the adapter renders documents to "
                        "display strings (dates ISO, ObjectId str) because "
                        "the wire model speaks rows, not BSON — the "
                        "client's DTO would reject a stray ObjectId "
                        "exactly as topic 2's defensive parsing taught."
                    ),
                ),
            ],
        ),
        # ── 5. Queries ─────────────────────────────────────────────────────
        Section(
            id="queries",
            title="Queries",
            lead="This section carries the topic's demo — the mongo console.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="queries-pitch",
                    text=(
                        "MongoDB's query language is operators over JSON "
                        "shapes: a filter document selects, an optional "
                        "projection document trims, a sort specification "
                        "orders. The console demo runs the full read-write "
                        "lifecycle against the live guide_demo database, "
                        "and every row in its payload is what the store "
                        "actually answered. The read that carries the most "
                        "teaching is the find — filter, projection, and "
                        "sort in one line:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="queries-find",
                    language="py",
                    caption="Filter on an array field, project the fat fields away, sort newest-first.",
                    source="server/guide/data/mongo/console.py",
                    snippet=(
                        "        query = {\"tags\": tag}\n"
                        "        cursor = console.find(query, FIND_PROJECTION).sort([(\"created_at\", DESCENDING)])\n"
                        "        found = await cursor.to_list(length=None)\n"
                        "        outcome = (\n"
                        "            f\"{len(found)} document(s) match tags={tag!r}\"\n"
                        "            + (\"\" if found else \" — an empty cursor is the honest answer, not an error\")\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="queries-verbs-pitch",
                    text=(
                        "The rest of the lifecycle uses one method per "
                        "verb, each with a crisp contract worth knowing by "
                        "name:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="queries-verbs-list",
                    ordered=False,
                    items=[
                        "replace_one + upsert — the keyed-write idiom: match "
                        "on a natural key, replace wholesale, insert if "
                        "absent; the seed uses it so re-runs are idempotent "
                        "(matched 6, upserted 0 on a warm database).",
                        "update_one + $set — operator updates change named "
                        "fields in place without read-modify-write; matched "
                        "and modified are SEPARATE counts (1/1 here; 1/0 "
                        "when the value already matched).",
                        "count_documents — a server-side count over any "
                        "filter the find accepts; the console runs it over "
                        "the SAME filter so the totals visibly agree.",
                        "delete_one / delete_many — removal by filter, "
                        "answering deletedCount; the console deletes its "
                        "own demo document so every run ends back at the "
                        "seed.",
                        "command — the escape hatch: explain, ping, "
                        "aggregate, anything the server speaks; section six "
                        "uses it for explain() output.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="queries-empty-pitch",
                    text=(
                        "One honest-edge worth its own sentence: a filter "
                        "that matches nothing is NOT an error. The console "
                        "accepts any tag query parameter, and asking for a "
                        "tag no note carries returns an empty cursor, a "
                        "zero count, and a payload that says so — the same "
                        "'empty is an answer' stance topic 11 gave REST "
                        "collections. Try it in the demo with a made-up "
                        "tag."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="queries-router-pitch",
                    text=(
                        "The endpoint itself stays a thin router, exactly "
                        "like every db demo before it — parse the tag, one "
                        "port call, one pure builder:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="queries-router",
                    language="py",
                    caption="The router: tag validated at the edge, then port + builder.",
                    source="server/guide/presentation/routers/demo/db.py",
                    snippet=(
                        "async def read_mongo_console(\n"
                        "    runner: Annotated[MongoConsoleRunner, Depends(get_mongo_console)],\n"
                        "    tag: Annotated[\n"
                        "        str, Query(min_length=1, max_length=40, pattern=MONGO_TAG_PATTERN)\n"
                        "    ] = DEFAULT_MONGO_TAG,\n"
                        ") -> MongoConsolePayload:\n"
                        "    # …\n"
                        "    run = await runner.run_console(tag)\n"
                        "    return build_mongo_console_payload(run, tag)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="queries-demo-pitch",
                    text=(
                        "Try it: the console reruns end-to-end on every "
                        "request and shows each operation's mongosh-shaped "
                        "command, its real outcome, and the documents it "
                        "touched — the refused insert with its three field "
                        "errors, the accepted insert's ObjectId, the find's "
                        "projected rows newest-first, update's matched/"
                        "modified split, the agreeing count, and the "
                        "delete that resets the stage."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="db:mongo-console",
                    title="The mongo console",
                    description=(
                        "GET /api/demo/db/mongo-console?tag=… runs the "
                        "whole scripted console against the live MongoDB: "
                        "an idempotent keyed seed, one pydantic refusal "
                        "(three field errors, zero I/O) and one accepted "
                        "insert, find with filter + projection + sort "
                        "(empty tag results are honest empties), update "
                        "one with matched/modified counts, an agreeing "
                        "count_documents, delete — plus the index exhibit "
                        "(COLLSCAN vs IXSCAN explains over the same "
                        "query) and a real TTL index with its definition."
                    ),
                ),
            ],
        ),
        # ── 6. Indexes and TTL ─────────────────────────────────────────────
        Section(
            id="indexes-and-ttl",
            title="Indexes and TTL",
            blocks=[
                TextBlock(
                    kind="text",
                    id="indexes-pitch",
                    text=(
                        "Every topic-16 lesson about indexes transfers, "
                        "because MongoDB's indexes are the same data "
                        "structure: B-trees over field values, maintained "
                        "on write, chosen by the planner per query. The "
                        "console's seed step creates two — a unique index "
                        "on the natural key (making the keyed upsert safe "
                        "under concurrency) and a descending index on "
                        "created_at (serving the find's sort) — "
                        "idempotently, since re-creating an identical "
                        "index is a no-op:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="indexes-seed",
                    language="py",
                    caption="Idempotent index creation at seed time: uniqueness + the sort key.",
                    source="server/guide/data/mongo/console.py",
                    snippet=(
                        "        key_index = await console.create_index([(\"key\", ASCENDING)], unique=True)\n"
                        "        sort_index = await console.create_index([(\"created_at\", DESCENDING)])"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="indexes-explain-pitch",
                    text=(
                        "And the proof discipline transfers too: claims "
                        "about plans are measured with explain(). The "
                        "demo's index exhibit drops its own scratch "
                        "collection, inserts eight documents, explains a "
                        "title filter (the plan says COLLSCAN — every "
                        "document examined), creates the index, and "
                        "explains the SAME query again:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="indexes-explain",
                    language="py",
                    caption="explain() through the command escape hatch, with executionStats for the counts.",
                    source="server/guide/data/mongo/console.py",
                    snippet=(
                        "        explained = await database.command(\n"
                        "            {\"explain\": {\"find\": collection, \"filter\": dict(query)}, \"verbosity\": \"executionStats\"}\n"
                        "        )"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="indexes-stage",
                    language="py",
                    caption="Walking the winning plan to its access stage: COLLSCAN or IXSCAN.",
                    source="server/guide/data/mongo/console.py",
                    snippet=(
                        "def _access_stage(plan: Mapping[str, Any]) -> tuple[str, str | None]:\n"
                        "    # …\n"
                        "    stage = plan\n"
                        "    name = str(stage.get(\"stage\", \"\"))\n"
                        "    while \"inputStage\" in stage:\n"
                        "        stage = stage[\"inputStage\"]\n"
                        "        name = str(stage.get(\"stage\", name))\n"
                        "    index_name = str(stage[\"indexName\"]) if name == \"IXSCAN\" and \"indexName\" in stage else None\n"
                        "    return name, index_name"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="indexes-explain-read",
                    text=(
                        "The second explain's arithmetic is the payoff the "
                        "payload shows: totalKeysExamined 1, "
                        "totalDocsExamined 1, winning plan FETCH fed by "
                        "IXSCAN on title_1 — against the scan's 0 keys and "
                        "8 documents. That is the same story topic 17's "
                        "EXPLAIN ANALYZE told with seq scan vs bitmap heap "
                        "scan, in the document store's dialect."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ttl-pitch",
                    text=(
                        "One index kind has no SQL counterpart and earns "
                        "its own exhibit: the TTL index. Create a normal "
                        "index on a DATE field with expireAfterSeconds and "
                        "mongod's background TTL monitor — a thread that "
                        "wakes roughly every 60 seconds — deletes documents "
                        "whose value is older than the grace period. "
                        "Sessions, cache entries, verification codes: "
                        "expiry becomes a storage-layer property instead "
                        "of a cron job:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="ttl-create",
                    language="py",
                    caption="A real TTL index: ten seconds of grace on the scratch collection.",
                    source="server/guide/data/mongo/console.py",
                    snippet=(
                        "        await stage.create_index(\n"
                        "            [(\"expires_at\", ASCENDING)], expireAfterSeconds=TTL_EXPIRE_AFTER_SECONDS\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ttl-read",
                    text=(
                        "The console then shows the definition exactly as "
                        "list_indexes returns it — ``{v: 2, key: "
                        "{expires_at: 1}, name: expires_at_1, "
                        "expireAfterSeconds: 10}`` — and two scratch "
                        "documents, one expiring in ten seconds and one "
                        "durable for an hour. What it deliberately does "
                        "not do is WAIT for eviction: the sweeper's ~60 s "
                        "cadence would make the demo slow and flaky, and "
                        "the suite pins the provable part instead (the "
                        "index exists, with the configured expiry, over a "
                        "BSON date). Honest teaching beats theater — the "
                        "mechanics are real, the wait is not worth your "
                        "attention."
                    ),
                ),
            ],
        ),
        # ── 7. Layering: where a store sits ────────────────────────────────
        Section(
            id="layering-where-a-store-sits",
            title="Layering: where a store sits",
            blocks=[
                TextBlock(
                    kind="text",
                    id="layering-pitch",
                    text=(
                        "Topic 32 will say this in full, but the data phase "
                        "already proves it: a second store changes NOTHING "
                        "about the architecture. The domain declares a "
                        "port — a Protocol speaking result rows, never "
                        "motor types — the data layer implements it, the "
                        "composition root wires one adapter to one port, "
                        "and routers stay thin. Here is the whole mongo "
                        "port:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="layering-port",
                    language="py",
                    caption="The domain port: one method, plain rows, no driver vocabulary.",
                    source="server/guide/domain/db/ports.py",
                    snippet=(
                        "@runtime_checkable\n"
                        "class MongoConsoleRunner(Protocol):\n"
                        "    # …\n"
                        "    async def run_console(self, tag: str) -> MongoConsoleRun:\n"
                        "        \"\"\"Run the scripted console; ``tag`` is the find filter's value.\"\"\"\n"
                        "        ..."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="layering-failure-pitch",
                    text=(
                        "The adapter owns every motor and pymongo import "
                        "in the guide — and every failure mapping. The "
                        "same one-contextmanager discipline topics 16–18 "
                        "used turns unreachable MongoDB into the family "
                        "envelope:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="layering-failure",
                    language="py",
                    caption="Optional-service discipline, third store, same shape.",
                    source="server/guide/data/mongo/console.py",
                    snippet=(
                        "@contextmanager\n"
                        "def _map_mongo_failures(operation: str) -> Iterator[None]:\n"
                        "    \"\"\"Optional-service discipline: MongoDB trouble becomes service_unavailable.\"\"\"\n"
                        "    try:\n"
                        "        yield\n"
                        "    except AppError:\n"
                        "        raise\n"
                        "    except (PyMongoError, OSError) as exc:\n"
                        "        # …\n"
                        "        raise AppError(\n"
                        "            FailureKind.SERVICE_UNAVAILABLE,\n"
                        "            \"MongoDB is unreachable or unusable — this demo runs real operations \"\n"
                        "            \"against the live document store and refuses to serve stale facts.\",\n"
                        "        ) from exc"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="layering-read",
                    text=(
                        "The payoff is composability. The demo's payload "
                        "builder in ``guide.domain.demos`` is PURE — it "
                        "shapes the run's rows and derives its reasoning "
                        "sentence from measured counts, so it is unit-"
                        "tested without a database; the adapter test pins "
                        "the store behavior; the endpoint test pins the "
                        "wire; and a fake ``MongoConsoleRunner`` wired via "
                        "dependency_overrides (topic 6) would drive the "
                        "client with zero infrastructure. Swap motor for "
                        "another driver, or MongoDB for FerretDB, and the "
                        "port is the only seam that knows the difference — "
                        "exactly the property the posts substrate bought "
                        "in topic 11."
                    ),
                ),
            ],
        ),
        # ── 8. SQL vs Mongo ────────────────────────────────────────────────
        Section(
            id="sql-vs-mongo",
            title="SQL vs Mongo",
            blocks=[
                TextBlock(
                    kind="text",
                    id="sql-vs-mongo-pitch",
                    text=(
                        "This guide runs BOTH stores, so the comparison is "
                        "not hypothetical — it is the decision the "
                        "codebase itself made. PostgreSQL (topics 16–18) "
                        "is the system of record: the schema is declared, "
                        "migrated, and checked; writes are transactional "
                        "across many tables; queries join and aggregate "
                        "across the whole normalized world. MongoDB (this "
                        "topic) is the second citizen: schema-light, "
                        "read-shaped, optional. The honest ledger behind "
                        "that split:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="sql-vs-mongo-list",
                    ordered=False,
                    items=[
                        "Schema — SQL's is enforced by the engine "
                        "(types, FKs, CHECKs — topic 16); Mongo's is "
                        "whatever the application validates, so discipline "
                        "lives in pydantic models and drift is a code "
                        "review problem.",
                        "Joins vs embedding — normalization vs "
                        "denormalization: SQL keeps one fact in one place "
                        "and joins on read; Mongo embeds aggregates and "
                        "accepts fanned-out writes (or $lookup, slower and "
                        "clunkier).",
                        "Transactions — SQL's are the default and cheap; "
                        "Mongo gives single-document atomicity for free, "
                        "multi-document ACID since 4.0 at real cost — so "
                        "document design IS transaction design.",
                        "Ad-hoc query power — SQL is a 50-year language "
                        "for asking anything of anything (topic 17's CTEs "
                        "and windows); Mongo filters well within a "
                        "collection and reaches for the aggregation "
                        "pipeline beyond it.",
                        "Consistency model — PostgreSQL serves strong "
                        "read-your-writes; MongoDB's default replication "
                        "is asynchronous, so a secondary can trail — a "
                        "real consideration once reads fan out.",
                        "Operations — both are containers in this stack, "
                        "but sizing stories differ: SQL's pain is "
                        "migrations and VACUUM; Mongo's is working sets "
                        "and replica-set ops.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="sql-vs-mongo-verdict",
                    text=(
                        "The decision rule this guide lands on: default to "
                        "the relational store — its constraints are "
                        "boring in the best way — and reach for a document "
                        "store when the SHAPE of the data is the payload: "
                        "self-contained aggregates read as a whole, "
                        "polymorphic siblings a fixed table fits badly, "
                        "or a second workload you want isolated from the "
                        "system of record. When you do add one, it enters "
                        "as this topic's mongo did: optional, behind a "
                        "port, degraded honestly when absent. The one "
                        "anti-pattern to name out loud: using schema "
                        "freedom to avoid a schema DECISION — the shape "
                        "still exists, the only question is whether "
                        "anything enforces it."
                    ),
                ),
            ],
        ),
        # ── 9. The NoSQL survey ────────────────────────────────────────────
        Section(
            id="the-nosql-survey",
            title="The NoSQL survey",
            blocks=[
                TextBlock(
                    kind="text",
                    id="survey-intro",
                    text=(
                        "\"NoSQL\" is a label of omission — not-SQL — "
                        "coined at a 2009 meetup about stores that traded "
                        "relational guarantees for particular strengths. "
                        "MongoDB is one member of a wide family this guide "
                        "touches across its run (redis arrives next "
                        "topic), and the honest way to survey the rest is "
                        "by the access pattern each was built around, not "
                        "by marketing categories."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="survey-redis",
                    text=(
                        "Redis is a data-structures server: strings, "
                        "hashes, lists, sets, sorted sets, streams — all "
                        "in memory, all with sub-millisecond operations, "
                        "optionally persisted. Nothing models a domain; "
                        "everything answers FAST. Caches, rate limiters, "
                        "session stores, leaderboards, and pub/sub live "
                        "here naturally. The costs are the ones topic 21 "
                        "will weigh in full: memory is the budget, "
                        "persistence is a tunable trade-off rather than a "
                        "guarantee, and an in-memory store holding the "
                        "ONLY copy of a fact is a design smell."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="survey-kafka",
                    text=(
                        "Kafka is a distributed LOG, not a database: "
                        "append-only, ordered per partition, retained for "
                        "a window (or forever), replayed by consumers at "
                        "their own pace. It is the backbone choice when "
                        "many systems must see the same events — analytics "
                        "pipelines, event-driven microservices, audit "
                        "feeds — and its log semantics (offsets, consumer "
                        "groups) are exactly topic 22's vocabulary. The "
                        "costs: operational weight (brokers, ZooKeeper/"
                        "KRaft, partitioning discipline) and a hard rule "
                        "that consumers must be idempotent, because "
                        "at-least-once delivery is the contract."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="survey-cassandra",
                    text=(
                        "Cassandra (and its cousins ScyllaDB) is a wide-"
                        "column store built for write-heavy scale and "
                        "tiered storage across many nodes. The model is "
                        "partitioned rows with sparse columns — you "
                        "declare the partition key, and EVERY query must "
                        "lead with it, which makes data modeling query-"
                        "first to an degree SQL never demanded. Time "
                        "series, telemetry, and messaging backlogs fit; "
                        "ad-hoc joins and cross-partition scans do not, "
                        "and tunable consistency (ONE vs QUORUM reads) is "
                        "an application decision on every table."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="survey-dynamodb",
                    text=(
                        "DynamoDB is AWS's key-value and document "
                        "hybrid: single-digit-millisecond lookups at any "
                        "scale, capacity on demand, item-level atomic "
                        "operations. It is spectacular for access patterns "
                        "known at design time — a partition/sort key is "
                        "the whole query surface (plus secondary indexes "
                        "with their own bills) — and hostile to "
                        "exploration. Its cost model (per read/write "
                        "capacity unit) and its eventual-consistency "
                        "defaults are the two surprises engineers meet "
                        "first; the DynamoDB paper's original insight — "
                        "give the application owner the key, never guess "
                        "it — is the design discipline it demands."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="survey-elasticsearch",
                    text=(
                        "Elasticsearch inverts the index: documents go in, "
                        "an inverted index makes full-text search over "
                        "millions of them fast, and relevance scoring is a "
                        "first-class citizen (BM25 where topic 17 met "
                        "ts_rank). Product search, log aggregation (its "
                        "Kibana pairing), and anything users query in "
                        "natural language are its home turf. It is not a "
                        "system of record — mappings can drift, updates "
                        "are near-real-time (the famous one-second "
                        "refresh), and cluster state management is its own "
                        "craft — so the usual architecture is a pipeline: "
                        "store of record feeds the search index, and "
                        "reindexing is an operational fact of life."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="survey-close",
                    text=(
                        "The family resemblance across all of them: pick "
                        "the access pattern first, accept the consistency "
                        "and modeling constraints it implies, and let the "
                        "store do the one job it was built for. Relational "
                        "remains the general-purpose default; everything "
                        "in this survey is a specialist. A specialist "
                        "earned its place only when a workload measurably "
                        "outgrew the default — the same bar MongoDB had to "
                        "clear to appear in this guide at all."
                    ),
                ),
            ],
        ),
        # ── 10. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole topic, from a shell — real documents, real plans, honest degradation.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Six stops: the console's real results, the two "
                        "exhibits up close, this topic's payload, the "
                        "curriculum it joins, the degradation proof, and "
                        "the optional mongosh detour. The stack is up; "
                        "every command answers with real data."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-console",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the console: seed, refusal, find, update, count, delete\n"
                        "curl -s 'localhost:8000/api/demo/db/mongo-console?tag=indexes' | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "print(\"seed:\", b[\"seed\"][\"upserted\"], \"fresh /\", b[\"seed\"][\"totalAfter\"], \"total\")\n"
                        "print(\"refused:\", len(b[\"refusal\"][\"errors\"]), \"field errors\")\n"
                        "for op in b[\"operations\"]:\n"
                        "    print(f\"  {op[\\\"op\\\"]:6} {op[\\\"outcome\\\"]}\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-exhibits",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the exhibits: COLLSCAN → IXSCAN, and the TTL definition\n"
                        "curl -s 'localhost:8000/api/demo/db/mongo-console' | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "for e in b[\"indexShowcase\"][\"explains\"]:\n"
                        "    print(f\"{e[\\\"label\\\"]:14} {e[\\\"stage\\\"]:8} keys={e[\\\"keysExamined\"]} docs={e[\\\"docsExamined\"]}\")\n"
                        "print(\"ttl:\", b[\"ttlShowcase\"][\"indexDefinition\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-empty",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — an honest empty: a tag nothing carries\n"
                        "curl -s 'localhost:8000/api/demo/db/mongo-console?tag=missing' | python3 -c '\n"
                        "import json, sys\n"
                        "ops = json.load(sys.stdin)[\"operations\"]\n"
                        "print(ops[1][\"outcome\"])\n"
                        "print(ops[3][\"outcome\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-topic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — this topic: ten sections, the demo inline in section five\n"
                        "curl -s localhost:8000/api/content/mongodb | python3 -c '\n"
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
                    id="terminal-degradation",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the degradation proof (unreachable URL, no containers harmed)\n"
                        "docker exec fastapi_developers_guide_dev bash -lc \\\n"
                        "  'cd /workspaces/fastapi_developers_guide/server && uv run pytest -q \\\n"
                        "   tests/demo/test_mongo_console_endpoint.py -k \"boots or unreachable\"'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-mongosh",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — optional: the same collection through mongosh itself\n"
                        "docker exec fastapi_developers_guide_mongo_dev \\\n"
                        "  mongosh --quiet guide_demo --eval \\\n"
                        "  'db.console_notes.countDocuments()'\n"
                        "# 6 — the seed, exactly; the demo document cleaned up after itself"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stop 1 is the topic in one payload: a boundary "
                        "that refused before any I/O, a keyed seed that "
                        "never duplicates, reads shaped by filter and "
                        "projection, and a lifecycle that cleans up after "
                        "itself. Stops 2 and 6 show the same facts from "
                        "the store's own mouth — plans and counts from "
                        "explain(), six documents from mongosh. Topic 20 "
                        "stays in the NoSQL half for redis: same "
                        "optional-service deal, same ports-and-adapters "
                        "seam, one very different data model."
                    ),
                ),
            ],
        ),
    ],
)
