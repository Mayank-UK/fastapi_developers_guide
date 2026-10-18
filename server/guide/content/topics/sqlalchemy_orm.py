"""Topic 18 — the SQLAlchemy ORM (third topic of the Data group).

Topic 17 ran SQL by hand through Core; this topic climbs the last
layer: mapped objects, the session's identity map and dirty checking,
relationship loading (lazy, joinedload, selectinload) with REAL query
counts from an engine-level recorder, the N+1 problem that follows,
projections and DTOs, async sessions, optimistic versioning (migration
0003's counter column), pagination (offset vs keyset), and the
guide-wide Testcontainers wiring — the tests that prove the whole stack
on a clean throwaway PostgreSQL.

Every must-source code block quotes a real repo file (the ratchet
verifies it): the ORM models mapped onto topic 16's Core tables, the
session factory, the query recorder, the probe adapter's strategies and
proofs, migration 0003, the pagination queries, and the testcontainers
test module. One demo, inline in the section that teaches loading.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="sqlalchemy-orm",
    title="The SQLAlchemy ORM",
    subtitle=(
        "Objects over the schema — sessions, identity maps, relationship "
        "loading, N+1, projections, async, optimistic versioning, "
        "pagination, and Testcontainers."
    ),
    group="data",
    order=18,
    sections=[
        # ── 1. What an ORM does and what it costs ───────────────────────────
        Section(
            id="what-an-orm-does",
            title="What an ORM does and what it costs",
            blocks=[
                TextBlock(
                    kind="text",
                    id="orm-pitch",
                    text=(
                        "Topic 17's repository built every statement by hand "
                        "and it earned that control: you saw the SQL, the "
                        "bind parameters, the plans. An object-relational "
                        "mapper trades some of that visibility for a "
                        "different working surface — you manipulate Python "
                        "objects and the library generates the SQL. "
                        "SQLAlchemy's ORM is the layer almost every "
                        "production FastAPI service sits on, and this "
                        "guide's position is the same as its data-phase "
                        "split: learn the SQL first (topic 17), then let "
                        "the ORM write it for you, because the only way to "
                        "use a query generator responsibly is to know what "
                        "it should have generated."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="orm-mapping-pitch",
                    text=(
                        "The first decision is who owns the schema. The "
                        "wrong answer — and it is the common one — is to "
                        "declare tables inside ORM classes and let the ORM "
                        "metadata become the source of truth by accident. "
                        "This guide keeps topic 16's Core ``Table`` objects "
                        "as the single definition and MAPS the ORM classes "
                        "onto them, so there is exactly one spelling of "
                        "every column, constraint, and index, and "
                        "``alembic check`` keeps guarding the agreement "
                        "between the metadata and the applied database:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="orm-mapping-registry",
                    language="py",
                    caption="The ORM registry binds to the Core metadata; classes claim existing tables.",
                    source="server/guide/data/db/orm/models.py",
                    snippet=(
                        "orm_registry = registry(metadata=metadata)\n"
                        "# …\n"
                        "class Base(DeclarativeBase, AsyncAttrs):\n"
                        "    # …\n"
                        "    registry = orm_registry"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="orm-mapping-post",
                    language="py",
                    caption="Post maps onto the same posts table migration 0001 created — no column redeclared.",
                    source="server/guide/data/db/orm/models.py",
                    snippet=(
                        "class Post(Base):\n"
                        "    # …\n"
                        "    __table__ = posts\n"
                        "    __mapper_args__ = {\"version_id_col\": posts.c.version}\n"
                        "\n"
                        "    id: Mapped[int]\n"
                        "    # …\n"
                        "    author: Mapped[\"Author\"] = relationship(back_populates=\"posts\")\n"
                        "    comments: Mapped[list[\"Comment\"]] = relationship(back_populates=\"post\")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="orm-mapping-read",
                    text=(
                        "Read that as a claim, not a declaration: "
                        "``__table__ = posts`` says this class IS the "
                        "existing table, ``Mapped[]`` annotations type the "
                        "attributes the table already carries, and only "
                        "``relationship()`` is new wiring — the FK-driven "
                        "edges between classes that Core deliberately "
                        "lacks. The ``version_id_col`` line is this "
                        "topic's addition to the schema (migration 0003, "
                        "section seven) and the relationships load LAZY by "
                        "default — a decision section three measures. What "
                        "you get back is a ``Post`` whose attributes are "
                        "row values and whose attribute access can quietly "
                        "be a query."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="orm-hybrid",
                    text=(
                        "The hybrid pays off mechanically: because the "
                        "mapper's metadata IS topic 16's metadata, "
                        "``alembic check`` still diffs one schema "
                        "definition against the live database, and the "
                        "Core statements topic 17 wrote keep working "
                        "beside ORM queries over the same engine — the "
                        "migration rehearsal, the race demo, and this "
                        "topic's probe share pool and pre-ping policy "
                        "without knowing about each other. Teams that "
                        "let the ORM declare its own tables discover the "
                        "cost of two metadata sources the day autogenerate "
                        "proposes dropping a column the other half of the "
                        "codebase still selects; one schema, two APIs "
                        "over it, is the arrangement that survives."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="orm-costs-pitch",
                    text=(
                        "So what does the abstraction buy, and what does it "
                        "charge? The honest ledger, learned the hard way by "
                        "every team that skipped learning it:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="orm-costs-list",
                    ordered=False,
                    items=[
                        "Unit of work — the session tracks every loaded "
                        "object, diffs your changes, and flushes the "
                        "minimal UPDATE/INSERT/DELETE set in dependency "
                        "order at commit.",
                        "Identity map — one row equals one Python object "
                        "per session; two loads of post #4 are the "
                        "SAME instance, so in-memory consistency is "
                        "structural, not discipline.",
                        "Relationships — traversal reads like objects "
                        "(``post.author.name``) while the library emits "
                        "joins or follow-up SELECTs; convenient, and the "
                        "door N+1 walks through.",
                        "Portability — one query language across dialects; "
                        "worth little when you run exactly one database "
                        "(this guide: PostgreSQL only), never zero.",
                        "Distance from SQL — the generated statement is a "
                        "consequence of your options, not your intent; "
                        "without instrumentation you are guessing what ran "
                        "(this topic's recorder exists for exactly that).",
                        "Leaky async boundaries — mapped objects are "
                        "sync-flavored; using them inside async code has "
                        "sharp edges section six names precisely.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="orm-costs-verdict",
                    text=(
                        "The verdict this guide lands on: use the ORM for "
                        "the 90% of writes and simple reads where the unit "
                        "of work genuinely helps, keep Core (or raw SQL, "
                        "as in topic 17's lab) for the gnarly reads, and "
                        "never let either hide what the database actually "
                        "received. Everything from here is that last "
                        "clause made practical."
                    ),
                ),
            ],
        ),
        # ── 2. Session, identity map, and dirty checking ───────────────────
        Section(
            id="session-identity-map-dirty-checking",
            title="Session, identity map, and dirty checking",
            blocks=[
                TextBlock(
                    kind="text",
                    id="session-pitch",
                    text=(
                        "The Session is the ORM's unit of work, and three "
                        "of its jobs run simultaneously inside one object: "
                        "it is the transaction boundary (commit or roll "
                        "back on exit), the identity map (a per-session "
                        "dictionary keyed by mapper and primary key), and "
                        "the change tracker that diffs your objects "
                        "against their loaded state. The guide owns one "
                        "factory for sessions, built at the composition "
                        "root right beside the engine, so pooling policy "
                        "and unit-of-work policy each live in exactly one "
                        "place:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="session-factory",
                    language="py",
                    caption="One session factory per process, beside the engine.",
                    source="server/guide/data/db/orm/sessions.py",
                    snippet=(
                        "def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:\n"
                        "    \"\"\"Build the process's session factory over the shared engine.\n"
                        "\n"
                        "    The factory is called without arguments — ``sessions()`` — and\n"
                        "    yields an ``AsyncSession`` whose context manager commits on normal\n"
                        "    exit and rolls back on any exception, so no code path leaks a\n"
                        "    transaction. Sessions are cheap; transactions are not.\n"
                        "    \"\"\"\n"
                        "    return async_sessionmaker(engine, expire_on_commit=False)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="session-identity-pitch",
                    text=(
                        "The identity map is the property developers trust "
                        "least and demonstrations settle fastest. Ask one "
                        "session for the same primary key twice: the first "
                        "``get`` is a cache miss and emits a SELECT, the "
                        "second is answered from the map — zero SQL, and "
                        "the SAME Python object comes back, provable with "
                        "``is``. The probe adapter runs this proof with "
                        "the recorder attached, so the count is a "
                        "measurement:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="session-identity-proof",
                    language="py",
                    caption="The identity-map proof: two gets, one SELECT, one object.",
                    source="server/guide/data/db/orm/probe.py",
                    snippet=(
                        "            post_id = await self._anchor_post_id()\n"
                        "            async with self._sessions() as session:\n"
                        "                with record_sql(self._engine) as recorder:\n"
                        "                    first = await session.get(Post, post_id)\n"
                        "                    second = await session.get(Post, post_id)\n"
                        "                    same_object = first is not None and first is second\n"
                        "                return IdentityMapProof(\n"
                        "                    post_id=post_id,\n"
                        "                    select_count=recorder.count(\"SELECT\"),\n"
                        "                    same_object=same_object,\n"
                        "                    statements=list(recorder.statements),\n"
                        "                )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="session-identity-read",
                    text=(
                        "Two consequences worth internalizing. First, the "
                        "map is PER SESSION — two sessions loading the "
                        "same row hold two objects, and section seven "
                        "builds its conflict proof on exactly that gap. "
                        "Second, ``get`` checks the map BEFORE the "
                        "database, which is why re-reading something you "
                        "already hold is free; the many-to-one lazy "
                        "loader consults it too, and the N+1 arithmetic "
                        "in section four comes out lower than the naive "
                        "1+N exactly because of it."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="session-dirty-pitch",
                    text=(
                        "Dirty checking is the quieter superpower: mutate "
                        "an attribute — nothing happens, no SQL, no "
                        "save() call — and the next ``flush()`` diffs the "
                        "session's objects against their loaded snapshots "
                        "and emits exactly the UPDATE the change requires, "
                        "one row, one column, plus the version counter "
                        "this topic adds. The probe proves it and rolls "
                        "back, so the demo can repeat on the same seed:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="session-dirty-proof",
                    language="py",
                    caption="One field mutated, one UPDATE flushed, then rolled back.",
                    source="server/guide/data/db/orm/probe.py",
                    snippet=(
                        "                post = await session.get(Post, post_id)\n"
                        "                assert post is not None\n"
                        "                before = post.status\n"
                        "                after = \"published\" if before == \"draft\" else \"draft\"\n"
                        "                post.status = after\n"
                        "                with record_sql(self._engine) as recorder:\n"
                        "                    await session.flush()\n"
                        "                await session.rollback()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="session-dirty-read",
                    text=(
                        "Flush versus commit is the distinction to hold "
                        "onto: flush sends pending SQL inside the current "
                        "transaction (the recorder sees it), commit ends "
                        "the transaction and makes it visible. The proof "
                        "flushes so the UPDATE is measurable, then rolls "
                        "back so the seed stays untouched — the same "
                        "discipline topic 17's race and audit demos used, "
                        "now at the object layer. What the recorder "
                        "captured is one statement whose WHERE clause "
                        "already carries this topic's next idea: "
                        "``WHERE posts.id = $3 AND posts.version = $4``."
                    ),
                ),
            ],
        ),
        # ── 3. Relationship loading: lazy, eager, selectin ─────────────────
        Section(
            id="relationship-loading",
            title="Relationship loading: lazy, eager, selectin",
            lead="This section carries the topic's demo — the ORM probe.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="loading-pitch",
                    text=(
                        "A relationship is a promise that touching an "
                        "attribute will be satisfied somehow — today, or "
                        "later, or never if you do not look. SQLAlchemy "
                        "offers a small set of strategies and the choice "
                        "is PER QUERY (``.options()`` on the select), not "
                        "a lifelong marriage baked into the mapping. The "
                        "probe runs the canonical access pattern — load "
                        "five published posts, touch each post's author "
                        "and comments — under all three strategies, with "
                        "a fresh session and a recorder window each time:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="loading-recorder",
                    language="py",
                    caption="The recorder: one engine listener, attached for the block, no longer.",
                    source="server/guide/data/db/orm/query_counter.py",
                    snippet=(
                        "@contextmanager\n"
                        "def record_sql(engine: AsyncEngine) -> Iterator[SqlRecorder]:\n"
                        "    # …\n"
                        "    recorder = SqlRecorder()\n"
                        "\n"
                        "    # …\n"
                        "    def before_cursor_execute(\n"
                        "        conn: object,\n"
                        "        cursor: object,\n"
                        "        statement: str,\n"
                        "        parameters: object,\n"
                        "        context: object,\n"
                        "        executemany: bool,\n"
                        "    ) -> None:\n"
                        "        recorder.statements.append(statement)\n"
                        "\n"
                        "    sync_engine = engine.sync_engine\n"
                        "    event.listen(sync_engine, \"before_cursor_execute\", before_cursor_execute)\n"
                        "    try:\n"
                        "        yield recorder\n"
                        "    finally:\n"
                        "        event.remove(sync_engine, \"before_cursor_execute\", before_cursor_execute)"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="loading-strategies",
                    language="py",
                    caption="The same select, three option sets — the strategy is a query-time choice.",
                    source="server/guide/data/db/orm/probe.py",
                    snippet=(
                        "            rows: list[StrategyRow] = []\n"
                        "            for strategy in STRATEGIES:\n"
                        "                async with self._sessions() as session:\n"
                        "                    with record_sql(self._engine) as recorder:\n"
                        "                        started = time.perf_counter()\n"
                        "                        statement = (\n"
                        "                            select(Post)\n"
                        "                            .where(Post.status == \"published\")\n"
                        "                            .order_by(Post.id)\n"
                        "                            .limit(post_count)\n"
                        "                        )\n"
                        "                        if strategy == \"joinedload\":\n"
                        "                            statement = statement.options(\n"
                        "                                joinedload(Post.author), joinedload(Post.comments)\n"
                        "                            )\n"
                        "                        elif strategy == \"selectinload\":\n"
                        "                            statement = statement.options(\n"
                        "                                selectinload(Post.author), selectinload(Post.comments)\n"
                        "                            )\n"
                        "                        posts = (await session.scalars(statement)).unique().all()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="loading-touch",
                    text=(
                        "Touching happens through ``awaitable_attrs`` — the "
                        "async-honest access for a possibly-unloaded "
                        "attribute (already-loaded resolves instantly, "
                        "lazy emits the awaited SELECT; section six "
                        "explains why plain attribute access is a trap in "
                        "async code). Every strategy executes the same "
                        "loop, so the only variable is the loading "
                        "strategy:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="loading-touch-code",
                    language="py",
                    caption="Identical touching code for all three strategies.",
                    source="server/guide/data/db/orm/probe.py",
                    snippet=(
                        "                        authors: list[str] = []\n"
                        "                        comment_total = 0\n"
                        "                        for post in posts:\n"
                        "                            author = await post.awaitable_attrs.author\n"
                        "                            comments = await post.awaitable_attrs.comments\n"
                        "                            authors.append(author.name)\n"
                        "                            comment_total += len(comments)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="loading-results",
                    text=(
                        "Against the live seed the counts come out 9, 1, "
                        "and 3 statements: lazy pays one SELECT for the "
                        "posts, three for the DISTINCT authors the "
                        "identity map does not already hold (five posts, "
                        "two of them repeat Grace Hopper — deduped), and "
                        "five for the comments collections; joinedload "
                        "pays exactly one statement with two LEFT OUTER "
                        "JOINs; selectinload pays one SELECT per table, "
                        "the follow-ups batched with ``IN`` over the "
                        "loaded ids. All three return identical authors "
                        "and identical comment totals — the payload "
                        "checks, so 'which is best' is purely a query-"
                        "shape question, never a correctness one."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="loading-demo-pitch",
                    text=(
                        "Try it: the demo reruns the whole probe on click, "
                        "shows each strategy's statement list verbatim "
                        "with per-strategy counts and timings, and the two "
                        "session proofs beside them — the identity map "
                        "(two gets, one SELECT) and dirty checking (one "
                        "field, one UPDATE, rolled back). Change the post "
                        "count and watch lazy's count grow with N while "
                        "the eager strategies stay flat."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="db:orm-probe",
                    title="The ORM probe",
                    description=(
                        "GET /api/demo/db/orm-probe?posts=… runs the same "
                        "access pattern under lazy, joinedload, and "
                        "selectinload with REAL query counting: per-"
                        "strategy SQL counts, the captured statements, "
                        "timings, and an identical-results check across "
                        "strategies. Plus the session's two proofs: "
                        "identity map (two gets → ONE SELECT, same object) "
                        "and dirty checking (mutate one field → flush "
                        "emits exactly one UPDATE, then rollback keeps "
                        "the demo repeatable)."
                    ),
                ),
            ],
        ),
        # ── 4. The N+1 problem ─────────────────────────────────────────────
        Section(
            id="the-n-plus-one-problem",
            title="The N+1 problem",
            blocks=[
                TextBlock(
                    kind="text",
                    id="nplus-pitch",
                    text=(
                        "N+1 is what lazy loading does when a loop meets a "
                        "relationship: one query for the collection, then "
                        "one more per row for the thing each row points "
                        "at. It is the single most common ORM performance "
                        "bug in production, and its cruelty is that it "
                        "never shows up in development — five extra "
                        "SELECTs on a five-row page cost nothing until "
                        "the page is fifty rows and the database is a "
                        "network hop away. Here is the lazy strategy's "
                        "captured statement list from the probe, exactly "
                        "as the engine emitted it (posts=5):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="nplus-transcript",
                    language="text",
                    caption="The lazy run's nine statements, captured live (abridged to the shapes).",
                    source=None,
                    snippet=(
                        "1  SELECT posts.id, …, posts.version FROM posts\n"
                        "   WHERE posts.status = $1 ORDER BY posts.id LIMIT $2\n"
                        "2  SELECT authors.id, authors.name, … FROM authors\n"
                        "   WHERE authors.id = $1                        -- Grace\n"
                        "3  SELECT comments.id, … FROM comments\n"
                        "   WHERE $1 = comments.post_id                  -- post 1's comments\n"
                        "4  SELECT comments.id, … FROM comments\n"
                        "   WHERE $1 = comments.post_id                  -- post 2's comments\n"
                        "5  SELECT authors.id, … FROM authors\n"
                        "   WHERE authors.id = $1                        -- Alan (Grace deduped)\n"
                        "6  SELECT comments.id, … FROM comments WHERE $1 = comments.post_id\n"
                        "7  SELECT comments.id, … FROM comments WHERE $1 = comments.post_id\n"
                        "8  SELECT authors.id, … FROM authors\n"
                        "   WHERE authors.id = $1                        -- Barbara\n"
                        "9  SELECT comments.id, … FROM comments WHERE $1 = comments.post_id"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="nplus-arithmetic",
                    text=(
                        "The arithmetic: 1 + A + N where N is posts and A "
                        "the DISTINCT authors the identity map cannot "
                        "answer — 1+3+5 here, and 1+N+N in the general "
                        "case where every row's related objects are "
                        "unseen. Note what saved two statements: the "
                        "many-to-one loader consulted the identity map "
                        "before emitting, so Grace Hopper's second and "
                        "third posts cost no author SELECT. That mercy "
                        "runs out immediately for collections — every "
                        "``post.comments`` is its own query — and for "
                        "any relationship the session has not loaded."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="nplus-fixes-pitch",
                    text=(
                        "The fixes are the two eager strategies from "
                        "section three, and they trade differently:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="nplus-fixes-list",
                    ordered=False,
                    items=[
                        "selectinload — one extra SELECT per relationship, "
                        "batched with IN over the parent ids; keeps result "
                        "sets flat and is usually the right default for "
                        "lists (3 statements in the probe run).",
                        "joinedload — everything in ONE statement via "
                        "outer joins; no round trips at all, but rows "
                        "multiply across joined collections (posts × "
                        "comments) and payload width grows with every "
                        "relationship.",
                        "Lazy, kept deliberately — for a single entity "
                        "where you touch relationships only sometimes, "
                        "lazy avoids paying for what you never read; the "
                        "bug is lazy inside a loop, not lazy per se.",
                        "Raise-N guardrails — SQLAlchemy's "
                        "``enable_eagerloads(False)`` / ``lazy=\"raise\"`` "
                        "option turns an accidental lazy load into an "
                        "immediate exception in tests, the cheapest way "
                        "to keep N+1 out of a codebase.",
                        "Measure, always — the recorder exists because "
                        "counts are claims until captured; any query "
                        "review that cannot show the statements is a "
                        "vibes review.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="nplus-read",
                    text=(
                        "The GraphQL chapter of topic 13 met the same "
                        "problem in resolver clothing and solved it with "
                        "dataloaders — batching by key. Same disease, "
                        "different layer: whenever object traversal "
                        "drives query emission per object, the cure is to "
                        "restructure access around SETS of keys, whether "
                        "by a load option or a loader."
                    ),
                ),
            ],
        ),
        # ── 5. Projections and DTOs ────────────────────────────────────────
        Section(
            id="projections-and-dtos",
            title="Projections and DTOs",
            blocks=[
                TextBlock(
                    kind="text",
                    id="projection-pitch",
                    text=(
                        "An ORM entity carries every column — load a "
                        "``Post`` and you paid for body, tags, timestamps, "
                        "the generated tsvector's slot in the row header, "
                        "even when the caller wanted a title for a list "
                        "page. A projection selects only the columns you "
                        "need; the ORM expression language makes it a "
                        "one-line change and returns lightweight rows "
                        "instead of tracked objects:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="projection-query",
                    language="py",
                    caption="A list page's query: two columns, no entity tracking, no N+1.",
                    source="server/guide/data/db/orm/probe.py",
                    snippet=(
                        "                        offset_statement = (\n"
                        "                            select(Post.id, Post.title)\n"
                        "                            .where(Post.status == \"published\")\n"
                        "                            .order_by(Post.id)\n"
                        "                            .offset(page_index * page_size)\n"
                        "                            .limit(page_size)\n"
                        "                        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="projection-when",
                    text=(
                        "Rule of thumb: SELECT entities when the unit of "
                        "work matters (you will mutate and commit), "
                        "project columns when it does not (reads, lists, "
                        "reports). SQLAlchemy also has a middle path — "
                        "``load_only()`` loads a partial entity that can "
                        "still lazy-load the rest — useful but easy to "
                        "abuse, since the deferred columns turn into "
                        "surprise queries on touch. The projection above "
                        "cannot surprise you: a row of two values has no "
                        "relationships to walk."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dto-pitch",
                    text=(
                        "The projection hands the adapter two values per "
                        "row; what crosses the HTTP boundary is a DTO — "
                        "the same discipline the guide has enforced since "
                        "topic 11's posts substrate: mapped objects and "
                        "driver rows NEVER leave the data layer, wire "
                        "models shaped for the client do. The pagination "
                        "probe's row is two fields:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dto-row",
                    language="py",
                    caption="The wire-side row: two fields, camelCase on the wire, frozen.",
                    source="server/guide/domain/db/ports.py",
                    snippet=(
                        "class PageEntry(CamelModel):\n"
                        "    \"\"\"One projected page row: just the id and title the client needs.\"\"\"\n"
                        "\n"
                        "    id: int\n"
                        "    title: str"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dto-read",
                    text=(
                        "Pydantic at the edge, SQLAlchemy inside, an "
                        "explicit mapping between them in the adapter — "
                        "that is the whole contract. It also keeps the "
                        "dependency rule intact: the domain port speaks "
                        "``PageEntry``, never ``Post``; routers and "
                        "client code cannot reach the ORM even by "
                        "accident, and the demo's payload builder stays "
                        "pure data-shaping that tests can run without a "
                        "database."
                    ),
                ),
            ],
        ),
        # ── 6. Async sessions ──────────────────────────────────────────────
        Section(
            id="async-sessions",
            title="Async sessions",
            blocks=[
                TextBlock(
                    kind="text",
                    id="async-pitch",
                    text=(
                        "AsyncSession wraps the sync ORM engine in await-"
                        "colored methods — but the objects it hands back "
                        "are still sync-flavored, and that mismatch is "
                        "the number-one async ORM bug. Touching an "
                        "UNLOADED lazy attribute from async code needs "
                        "IO, and attribute access cannot await: "
                        "SQLAlchemy detects the attempt and raises "
                        "``MissingGreenletError`` instead of silently "
                        "blocking the event loop. You will meet this "
                        "error; the design answer is to make loads "
                        "EXPLICIT — options at query time, or the "
                        "``awaitable_attrs`` accessor the guide's mapped "
                        "classes inherit:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="async-base",
                    language="py",
                    caption="AsyncAttrs on the base: every mapped attribute gains an async-honest access.",
                    source="server/guide/data/db/orm/models.py",
                    snippet=(
                        "class Base(DeclarativeBase, AsyncAttrs):\n"
                        "    \"\"\"Declarative base for every mapped class in the guide.\n"
                        "\n"
                        "    ``AsyncAttrs`` adds the ``awaitable_attrs`` accessor every mapped\n"
                        "    attribute gains in async code — the async-honest way to touch a\n"
                        "    relationship that may still need loading (see the probe's strategy\n"
                        "    runs: a lazy attribute access from an async context without it is\n"
                        "    an error, not a pause).\n"
                        "    \"\"\"\n"
                        "\n"
                        "    registry = orm_registry"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="async-discipline-pitch",
                    text=(
                        "The working disciplines that fall out of the "
                        "async wrapper are few and strict:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="async-discipline-list",
                    ordered=False,
                    items=[
                        "One session per unit of work — open it from the "
                        "factory inside a context manager; the block "
                        "commits on normal exit, rolls back on any "
                        "exception, and nothing leaks across requests.",
                        "Load eagerly, touch freely — put "
                        "selectinload/joinedload options on the query so "
                        "attribute access afterwards is pure memory.",
                        "awaitable_attrs for the rest — when a lazy load "
                        "is genuinely fine (single entity, occasional "
                        "traversal), await it explicitly instead of "
                        "letting attribute access pretend to be free.",
                        "expire_on_commit=False — a committed object that "
                        "refreshes itself on next touch is another hidden "
                        "lazy load; the guide's factory disables expiry "
                        "so post-commit reads stay in memory.",
                        "Never block the loop — the sync-side APIs "
                        "(Alembic's runner, heavy DDL) go through "
                        "``asyncio.to_thread``, exactly as topic 16's "
                        "startup migration does.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="async-wiring",
                    text=(
                        "Wiring is one line at the composition root: the "
                        "factory sits beside the engine on app.state, "
                        "adapters resolve it through dependency "
                        "injection, and routers stay as thin as ever — "
                        "they never see a session at all:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="async-root",
                    language="py",
                    caption="The composition root: engine, session factory, and the probe adapter.",
                    source="server/guide/main.py",
                    snippet=(
                        "    db_engine = create_db_engine(config)\n"
                        "    app.state.db_engine = db_engine\n"
                        "    # …\n"
                        "    orm_sessions = create_session_factory(db_engine)\n"
                        "    app.state.orm_session_factory = orm_sessions\n"
                        "    app.state.orm_probe = OrmProbeRepository(db_engine, orm_sessions)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="async-read",
                    text=(
                        "The payoff of holding this line: the async "
                        "boundary is invisible in the domain. Ports speak "
                        "plain rows, adapters speak sessions, and neither "
                        "side's vocabulary leaks into the other — the "
                        "same ports→adapters seam every topic since "
                        "eleven has used, now with a database behind it."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="async-per-request",
                    text=(
                        "One lifecycle question remains: where do sessions "
                        "come from per REQUEST? The guide's answer keeps "
                        "them adapter-internal — the demo router resolves "
                        "the probe runner, which opens a session per proof "
                        "— but the equally idiomatic FastAPI shape is a "
                        "yield dependency (topic 6): a ``get_session`` "
                        "dependency yields one session, the handler runs "
                        "inside it, and the dependency's teardown commits "
                        "or rolls back. Either shape satisfies the rule "
                        "that matters: never a session shared across "
                        "requests, never a transaction spanning user "
                        "think-time, and never a session outliving the "
                        "request that opened it."
                    ),
                ),
            ],
        ),
        # ── 7. Optimistic versioning ───────────────────────────────────────
        Section(
            id="optimistic-versioning",
            title="Optimistic versioning",
            blocks=[
                TextBlock(
                    kind="text",
                    id="versioning-pitch",
                    text=(
                        "Topic 17 fixed the lost update with SELECT … FOR "
                        "UPDATE — a lock held across the read-modify-"
                        "write. Locks are right when contention is real "
                        "and transactions are short; for the long tail of "
                        "'two edits race occasionally', optimistic "
                        "versioning is cheaper: NO lock, but every UPDATE "
                        "proves it saw the latest row. The recipe is one "
                        "integer column the ORM maintains for you:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="versioning-migration",
                    language="py",
                    caption="Migration 0003: the counter column, backfilled to 1 by the server default.",
                    source="server/alembic/versions/0003_posts_version_counter.py",
                    snippet=(
                        "def upgrade() -> None:\n"
                        "    op.add_column(\n"
                        "        \"posts\",\n"
                        "        sa.Column(\"version\", sa.Integer(), server_default=sa.text(\"1\"), nullable=False),\n"
                        "    )"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="versioning-mapper",
                    language="py",
                    caption="One line of mapping: the column becomes an optimistic lock.",
                    source="server/guide/data/db/orm/models.py",
                    snippet=(
                        "    __table__ = posts\n"
                        "    __mapper_args__ = {\"version_id_col\": posts.c.version}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="versioning-mechanics",
                    text=(
                        "From there the machinery is automatic. On INSERT "
                        "the row starts at version 1 (the server default "
                        "the migration set); on every UPDATE the session "
                        "writes the NEXT integer and guards the WHERE "
                        "clause with the version it LOADED — you saw this "
                        "statement in the dirty-check proof, and now the "
                        "last two predicates have a reason to exist:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="versioning-update",
                    language="text",
                    caption="The dirty-check proof's captured UPDATE — the version guard is the last predicate.",
                    source=None,
                    snippet=(
                        "UPDATE posts SET status=$1::VARCHAR, version=$2::INTEGER\n"
                        "WHERE posts.id = $3::BIGINT AND posts.version = $4::INTEGER"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="versioning-conflict-pitch",
                    text=(
                        "If another transaction committed first, the "
                        "guard matches ZERO rows; SQLAlchemy expects "
                        "exactly one and raises ``StaleDataError`` at "
                        "flush — the write is refused, out loud, before "
                        "it can clobber anyone. The adapter's proof is "
                        "the whole story in miniature: two sessions load "
                        "a throwaway post, the winner commits a status "
                        "flip (1 → 2), the loser edits its stale copy:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="versioning-conflict",
                    language="py",
                    caption="The conflict proof: winner commits, loser is refused with StaleDataError.",
                    source="server/guide/data/db/orm/probe.py",
                    snippet=(
                        "        async with self._sessions() as winner:\n"
                        "            winner_post = await winner.get(Post, post_id)\n"
                        "            assert winner_post is not None\n"
                        "            stale_version = winner_post.version\n"
                        "            async with self._sessions() as loser:\n"
                        "                loser_post = await loser.get(Post, post_id)\n"
                        "                assert loser_post is not None\n"
                        "                # The winner commits first: version 1 -> 2.\n"
                        "                winner_post.status = \"published\"\n"
                        "                await winner.commit()\n"
                        "                committed_version = winner_post.version\n"
                        "                # The loser edits its STALE copy and tries to commit.\n"
                        "                loser_post.body = loser_post.body + \" (the loser's edit)\"\n"
                        "                try:\n"
                        "                    await loser.commit()\n"
                        "                except StaleDataError as exc:\n"
                        "                    return VersionConflictProof(\n"
                        "                        # …\n"
                        "                    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="versioning-read",
                    text=(
                        "The real error, captured live: ``StaleDataError: "
                        "UPDATE statement on table 'posts' expected to "
                        "update 1 row(s); 0 were matched.`` The HTTP "
                        "mapping is the family's 409 conflict — the "
                        "client re-reads and retries on the fresh version "
                        "(exactly what topic 17's comment thread "
                        "recommended over holding locks). The suite pins "
                        "this behavior three ways: the adapter proof "
                        "above, a bare-session reproduction, and the "
                        "clean-database round-trip in section nine — the "
                        "version column must exist from migration 0003 "
                        "onward, because the ORM will reference it."
                    ),
                ),
            ],
        ),
        # ── 8. Pagination ──────────────────────────────────────────────────
        Section(
            id="pagination",
            title="Pagination",
            blocks=[
                TextBlock(
                    kind="text",
                    id="pagination-pitch",
                    text=(
                        "Topic 11 designed pagination as part of a "
                        "resource's identity; the ORM chapter's job is "
                        "the query mechanics. Offset pagination asks for "
                        "rows k..k+n; keyset pagination asks for 'rows "
                        "after the last one I saw'. The probe walks the "
                        "published posts both ways with the same page "
                        "size and compares, and the two statements it "
                        "captures are the whole lesson:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pagination-offset-sql",
                    language="text",
                    caption="Captured page two of three, offset style.",
                    source=None,
                    snippet=(
                        "SELECT posts.id, posts.title\n"
                        "FROM posts\n"
                        "WHERE posts.status = $1 ORDER BY posts.id\n"
                        " LIMIT $2 OFFSET $3"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pagination-keyset-sql",
                    language="text",
                    caption="Captured page two of three, keyset style.",
                    source=None,
                    snippet=(
                        "SELECT posts.id, posts.title\n"
                        "FROM posts\n"
                        "WHERE posts.status = $1 AND posts.id > $2 ORDER BY posts.id\n"
                        " LIMIT $3"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pagination-tradeoffs-pitch",
                    text=(
                        "Both produce identical pages on a quiet database "
                        "— the probe checks — and diverge in exactly two "
                        "ways that matter:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="pagination-tradeoffs-list",
                    ordered=False,
                    items=[
                        "Cost — OFFSET makes the database produce and "
                        "discard k rows before your page; keyset seeks "
                        "into the index at the cursor and reads exactly "
                        "the page (page 10,000 is the difference between "
                        "a scan and a seek).",
                        "Stability — a row inserted before your offset "
                        "window shifts every later page (duplicates at "
                        "page boundaries); a keyset cursor pins your "
                        "position in the ordering, immune to inserts "
                        "before it.",
                        "Cursor choice — the cursor must be the ordering "
                        "key (here the id; for 'newest first' a "
                        "tie-broken timestamp), immutable, and indexed — "
                        "the same care topic 16 spent on choosing primary "
                        "keys.",
                        "Interface cost — offsets give free page numbers "
                        "('page 7 of 40'); cursors give a token the "
                        "client passes back opaquely, which is why real "
                        "APIs often serve both, cursor-first.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="pagination-code-pitch",
                    text=(
                        "In the ORM the keyset page is one extra WHERE on "
                        "the same projected select — the adapter threads "
                        "the last seen id through the walk:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pagination-keyset-code",
                    language="py",
                    caption="The keyset statement: WHERE id > last seen, same projection, same order.",
                    source="server/guide/data/db/orm/probe.py",
                    snippet=(
                        "                        keyset_statement = (\n"
                        "                            select(Post.id, Post.title)\n"
                        "                            .where(Post.status == \"published\")\n"
                        "                            .where(Post.id > (last_seen_id or 0))\n"
                        "                            .order_by(Post.id)\n"
                        "                            .limit(page_size)\n"
                        "                        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pagination-read",
                    text=(
                        "A detail easy to miss: the probe projects ``id`` "
                        "and ``title`` only, so the page query doubles as "
                        "section five's projection exhibit — pagination "
                        "and projection compose naturally because both "
                        "are just shapes of the same select. The suite "
                        "asserts the agreement (``agree: true``) and that "
                        "the keyset statement really carries no OFFSET, "
                        "so the lesson cannot silently rot."
                    ),
                ),
            ],
        ),
        # ── 9. Testcontainers ──────────────────────────────────────────────
        Section(
            id="testcontainers",
            title="Testcontainers",
            blocks=[
                TextBlock(
                    kind="text",
                    id="tc-pitch",
                    text=(
                        "Every database test so far ran against the "
                        "long-lived dev PostgreSQL — shared state, "
                        "pre-applied migrations, someone's leftover rows. "
                        "That is fine for demos and fast feedback, but it "
                        "cannot answer the question that actually matters "
                        "before a release: does the FULL stack — "
                        "migrations from zero, the ORM mapping, the "
                        "session factory — work on a CLEAN database? "
                        "Testcontainers answers it by spinning a real "
                        "throwaway PostgreSQL in Docker for the test's "
                        "lifetime: no fixture files, no 'refresh your "
                        "local DB' README, no cross-test pollution."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tc-wiring-pitch",
                    text=(
                        "The guide's wiring has one honest wrinkle: the "
                        "dev/verify container has NO docker socket, so "
                        "Testcontainers cannot run there. The rule this "
                        "guide standardized: those tests are MARKED, and "
                        "they skip with a stated reason when no Docker is "
                        "reachable — never silently pass:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tc-probe",
                    language="py",
                    caption="The honest probe: is there a usable Docker endpoint in THIS environment?",
                    source="server/tests/data/test_orm_testcontainers.py",
                    snippet=(
                        "def _docker_reachable() -> tuple[bool, str]:\n"
                        "    # …\n"
                        "    raw = os.environ.get(\"DOCKER_HOST\", \"unix:///var/run/docker.sock\")\n"
                        "    if raw.startswith(\"unix://\"):\n"
                        "        path = raw.removeprefix(\"unix://\")\n"
                        "        if not os.path.exists(path):\n"
                        "            return False, f\"no Docker socket at {path} (dev/verify containers have none)\"\n"
                        "        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\n"
                        "        probe.settimeout(DOCKER_PROBE_TIMEOUT)\n"
                        "        try:\n"
                        "            probe.connect(path)\n"
                        "        except OSError as exc:\n"
                        "            return False, f\"Docker socket {path} unreachable: {exc}\"\n"
                        "        finally:\n"
                        "            probe.close()\n"
                        "        return True, \"\""
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tc-marker",
                    language="py",
                    caption="One marker; skips state the reason; the fallback run selects the marker.",
                    source="server/tests/data/test_orm_testcontainers.py",
                    snippet=(
                        "DOCKER_OK, DOCKER_SKIP_REASON = _docker_reachable()\n"
                        "\n"
                        "pytestmark = [\n"
                        "    pytest.mark.testcontainers,\n"
                        "    pytest.mark.skipif(not DOCKER_OK, reason=DOCKER_SKIP_REASON),\n"
                        "]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tc-fixture-pitch",
                    text=(
                        "The fixture is one context manager: start the "
                        "container, hand back a URL. testcontainers "
                        "defaults to a psycopg2-style URL, so the fixture "
                        "retags it for the guide's asyncpg driver — one "
                        "``replace``, the same engine stack as production "
                        "code:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tc-fixture",
                    language="py",
                    caption="One throwaway PostgreSQL per test; the URL is the whole fixture.",
                    source="server/tests/data/test_orm_testcontainers.py",
                    snippet=(
                        "@pytest.fixture\n"
                        "def container_url() -> Iterator[str]:\n"
                        "    \"\"\"One throwaway PostgreSQL; its asyncpg URL is the whole fixture.\"\"\"\n"
                        "    with PostgresContainer(POSTGRES_IMAGE) as postgres:\n"
                        "        # testcontainers hands out a psycopg2 URL; the guide speaks asyncpg.\n"
                        "        yield postgres.get_connection_url().replace(\"+psycopg2\", \"+asyncpg\")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tc-roundtrip-pitch",
                    text=(
                        "Then the point itself: against that empty "
                        "database, run the migration chain to head and "
                        "exercise the ORM round-trip — create, eager "
                        "load, commit a version bump, refuse a stale "
                        "write. The first half of the fixture does the "
                        "migrating; the test does the proving:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tc-roundtrip",
                    language="py",
                    caption="Migrations to head on a clean database, then the ORM round-trip.",
                    source="server/tests/data/test_orm_testcontainers.py",
                    snippet=(
                        "@pytest.fixture\n"
                        "async def engine(container_url: str) -> AsyncEngine:\n"
                        "    \"\"\"Engine over the throwaway container, migrations applied to head.\"\"\"\n"
                        "    await asyncio.to_thread(upgrade_database_to_head, container_url)\n"
                        "    engine = create_async_engine(container_url, pool_pre_ping=True)\n"
                        "    try:\n"
                        "        yield engine\n"
                        "    finally:\n"
                        "        await engine.dispose()"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tc-create",
                    language="py",
                    caption="The round-trip's first act: objects in, version 1 out, cascade wired.",
                    source="server/tests/data/test_orm_testcontainers.py",
                    snippet=(
                        "    async with sessions() as session:\n"
                        "        author = Author(name=\"Clean Db\", email=\"clean@guide.dev\", bio=\"\")\n"
                        "        post = Post(\n"
                        "            author=author,\n"
                        "            slug=\"clean-database-round-trip\",\n"
                        "            title=\"The clean-database round trip\",\n"
                        "            body=\"Created by the testcontainers test; dies with its container.\",\n"
                        "            tags=[\"orm\"],\n"
                        "            status=\"draft\",\n"
                        "        )\n"
                        "        session.add(post)\n"
                        "        await session.commit()\n"
                        "        post_id, author_id = post.id, author.id\n"
                        "        assert post.version == 1  # migration 0003's server default"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tc-runs",
                    text=(
                        "Where the tests actually RUN is the wiring's "
                        "second half. In the dev container they skip (the "
                        "reason above prints in the report); on the host "
                        "they run for real, selected by the registered "
                        "marker, inside a one-shot uv container that "
                        "mounts the Docker socket and the host-override "
                        "so the throwaway PostgreSQL is reachable:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tc-fallback",
                    language="bash",
                    caption="The host-run fallback: sock + override mounted, only the marked tests.",
                    source=None,
                    snippet=(
                        "docker run --rm -v \"$PWD\":/repo -w /repo/server \\\n"
                        "  -v fdg-uv:/root/.cache/uv \\\n"
                        "  -v /var/run/docker.sock:/var/run/docker.sock \\\n"
                        "  -e TESTCONTAINERS_HOST_OVERRIDE=host.docker.internal \\\n"
                        "  ghcr.io/astral-sh/uv:python3.13-bookworm \\\n"
                        "  bash -lc 'flock /repo/server/.verify.lock \\\n"
                        "    bash -c \"uv sync --locked && uv run pytest -q -m testcontainers\"'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tc-read",
                    text=(
                        "Both paths stay green by design: the in-"
                        "container full suite exits zero with the skips "
                        "visible and explained, and the fallback run "
                        "shows the same tests PASSED against real "
                        "containers. The marker is registered in "
                        "pyproject.toml so an unregistered-marker warning "
                        "can never hide a typo, and the pattern is now "
                        "the guide's standing recipe — topic 19 and 20's "
                        "optional stores, and any future adapter, get "
                        "their clean-database proofs the same way."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tc-costs",
                    text=(
                        "The honest costs: a throwaway container costs "
                        "seconds of startup per test (the image caches "
                        "after the first pull, and testcontainers' own "
                        "ryuk sidecar reaps anything a crashed run left "
                        "behind), so the suite keeps them MARKED and "
                        "separate rather than paying that tax on every "
                        "red-green loop — the fast path still runs against "
                        "the shared dev PostgreSQL, and the clean-database "
                        "run is the release gate that proves migrations "
                        "and models agree from zero. That split — fast "
                        "shared-state tests for iteration, slow hermetic "
                        "tests for proof — is the testing chapter's "
                        "pyramid (topic 34) in miniature, and the reason "
                        "this wiring exists at all."
                    ),
                ),
            ],
        ),
        # ── 10. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole topic, from a shell — measured counts, refused stale writes, and a clean database.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Six stops: the probe's measured strategy counts, "
                        "the suite's version-conflict and pagination "
                        "proofs, the migration bookkeeping, the "
                        "clean-database run, this topic's payload, and "
                        "the curriculum it joins. The stack is up; every "
                        "command answers with real data."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-probe",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the probe: lazy 9, selectin 3, joined 1 — measured\n"
                        "curl -s 'localhost:8000/api/demo/db/orm-probe?posts=5' | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "for s in b[\"strategies\"]:\n"
                        "    print(f\"{s[\\\"strategy\\\"]:11} {s[\\\"sqlCount\\\"]} stmts  {s[\\\"elapsedMs\\\"]:.1f} ms\")\n"
                        "print(\"results match:\", b[\"resultsMatch\"])\n"
                        "print(\"identity map:\", b[\"identityMap\"][\"selectCount\"], \"SELECT, same object:\",\n"
                        "      b[\"identityMap\"][\"sameObject\"])\n"
                        "print(\"dirty check:\", b[\"dirtyCheck\"][\"updateCount\"], \"UPDATE, committed:\",\n"
                        "      b[\"dirtyCheck\"][\"committed\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-proofs",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the proofs the payload does not carry: conflict + pagination\n"
                        "docker exec fastapi_developers_guide_dev bash -lc \\\n"
                        "  'cd /workspaces/fastapi_developers_guide/server && uv run pytest -q \\\n"
                        "   tests/data/test_orm_probe_repository.py -k \"conflict or stale or paginate\"'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-alembic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — migration 0003 in the bookkeeping table and the column it added\n"
                        "docker exec fastapi_developers_guide_postgres_dev \\\n"
                        "  psql -U postgres -d guide -c 'SELECT * FROM alembic_version;' \\\n"
                        "  -c '\\d posts' | grep -E '0003|version'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-testcontainers",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the clean-database run: throwaway PostgreSQL, migrations from zero\n"
                        "# (needs Docker on the host; skips with a reason inside the dev container)\n"
                        "docker run --rm -v \"$PWD\":/repo -w /repo/server \\\n"
                        "  -v fdg-uv:/root/.cache/uv -v /var/run/docker.sock:/var/run/docker.sock \\\n"
                        "  -e TESTCONTAINERS_HOST_OVERRIDE=host.docker.internal \\\n"
                        "  ghcr.io/astral-sh/uv:python3.13-bookworm \\\n"
                        "  bash -lc 'flock /repo/server/.verify.lock \\\n"
                        "    bash -c \"uv sync --locked && uv run pytest -q -m testcontainers\"'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-topic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — this topic: ten sections, the demo inline in section three\n"
                        "curl -s localhost:8000/api/content/sqlalchemy-orm | python3 -c '\n"
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
                    id="terminal-curriculum",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — eighteen topics now; the Data group is one short of full\n"
                        "curl -s localhost:8000/api/content | python3 -c '\n"
                        "import json, sys\n"
                        "body = json.load(sys.stdin)\n"
                        "print(\"topics total:\", len(body[\"topics\"]))\n"
                        "print(\"data topics:\", [t[\"id\"] for t in body[\"topics\"] if t[\"group\"] == \"data\"])'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stop 1 is the topic compressed into one payload: "
                        "the same objects, the same touching code, three "
                        "wildly different query bills — and two session "
                        "proofs that cost the database one SELECT and one "
                        "rolled-back UPDATE. Everything else you toured "
                        "exists to keep those numbers honest at scale: "
                        "version guards that refuse stale writes, cursors "
                        "that do not drift, and a clean-database run that "
                        "proves the stack from migration one. Topic 19 "
                        "leaves the relational world for MongoDB — and "
                        "keeps every discipline this one established: "
                        "optional-service, ports and adapters, measured "
                        "proofs."
                    ),
                ),
            ],
        ),
    ],
)
