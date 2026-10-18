"""Topic 16 — SQL schema design (first topic of the Data group).

The data phase begins where every database-backed service must: the
SCHEMA. This topic teaches relational thinking on the guide's own real
tables — the dev PostgreSQL now carries authors, posts, comments, and
an audit_log, created by this topic's Alembic setup (which later data
topics inherit). Sections walk the discipline in order: how relations
model the posts substrate from topic 11, PostgreSQL's types and
constraints, keys and foreign keys, normalization against deliberate
denormalization, indexes (with the live schema-explorer demo INLINE),
the Alembic history that owns the schema as code, the UUIDv7-vs-
sequential identity decision (with the uuid lab demo INLINE), and the
audit-logging pattern that closes the loop on "who changed what".

Every code block quotes a real repo file (the snippet ratchet verifies
it): the Core schema module, the initial migration, the async env.py,
the tolerant startup migration, the in-repo UUIDv7 implementation, the
audit writer and its rollback-proof test, and the introspection SQL
the explorer itself runs.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="sql-schema",
    title="SQL schema design",
    subtitle=(
        "Tables as contracts — PostgreSQL types, keys, constraints, "
        "indexes, Alembic history, and the id strategy underneath."
    ),
    group="data",
    order=16,
    sections=[
        # ── 1. Relational thinking ─────────────────────────────────────────
        Section(
            id="relational-thinking",
            title="Relational thinking",
            blocks=[
                TextBlock(
                    kind="text",
                    id="relational-pitch",
                    text=(
                        "Topics 11 through 15 served the posts substrate from "
                        "an in-memory repository: twelve seeded posts, honest "
                        "CRUD semantics, and a hard ceiling — pull the plug "
                        "and every write evaporates. The Data group replaces "
                        "that substrate's storage with PostgreSQL, and this "
                        "topic builds the foundation everything else in the "
                        "group stands on: the SCHEMA, the declared shape of "
                        "the data. Relational thinking means modeling your "
                        "domain as TABLES of identically shaped ROWS, where "
                        "each table holds one kind of thing (authors, posts, "
                        "comments), each row is one instance with the same "
                        "columns, and relationships between things become "
                        "REFERENCES from one table's column to another "
                        "table's key. The shape is not documentation — it is "
                        "an enforced contract the database itself upholds "
                        "for every writer, whether that writer is this "
                        "FastAPI app, a psql session, or next year's batch job."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="relational-bargain",
                    text=(
                        "That bargain — declare the shape once, in one place "
                        "— buys the properties that keep data trustworthy "
                        "for years after the original authors move on:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="relational-properties",
                    ordered=False,
                    items=[
                        "Declared integrity — constraints live in the "
                        "database and bind EVERY writer, not just the app "
                        "that happened to validate first.",
                        "One home per fact — each piece of truth is stored "
                        "once and referenced everywhere else by key, so "
                        "contradictions cannot accumulate.",
                        "Set-at-a-time queries — SQL answers questions "
                        "across thousands of rows in one statement, where "
                        "in-memory loops paid per row.",
                        "Transactions — multi-step changes commit or vanish "
                        "as a unit (the property topic 17 leans on).",
                        "Independence — the schema outlives any one process, "
                        "client, or programming language talking to it.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="relational-mapping",
                    text=(
                        "The guide's schema models the same vocabulary topic "
                        "11 designed: authors get their own table (name, "
                        "email, bio), posts reference an author by key and "
                        "carry the fields you already know from the REST "
                        "resource — slug, title, body, tags, status, "
                        "timestamps — and comments hang off posts the same "
                        "way posts hang off authors. A fourth table, "
                        "audit_log, records who changed what; section 8 "
                        "gives it a full treatment. None of this is "
                        "hypothetical: the migration this topic lands "
                        "created these four tables in the live dev "
                        "PostgreSQL before you read this sentence, and "
                        "both demos in the topic read their facts back out "
                        "of that real database."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="relational-roadmap",
                    text=(
                        "The chapter order is the working order of a real "
                        "schema review: types and constraints first (the "
                        "columns), then keys and references (identity and "
                        "relationships), then the normalization judgment "
                        "calls, then indexes (the performance contract), "
                        "then the migration machinery that makes the whole "
                        "thing reproducible, then the primary-key strategy, "
                        "and finally the audit pattern that observes every "
                        "change. Topic 17 writes the SQL that reads and "
                        "writes these tables; topic 18 maps ORM classes "
                        "onto them. Here the tables themselves are the "
                        "product."
                    ),
                ),
            ],
        ),
        # ── 2. PostgreSQL types and constraints ────────────────────────────
        Section(
            id="pg-types-and-constraints",
            title="PostgreSQL types and constraints",
            blocks=[
                TextBlock(
                    kind="text",
                    id="types-pitch",
                    text=(
                        "A column's TYPE is its first constraint: it says "
                        "what kind of value can live there and what "
                        "operations make sense on it. PostgreSQL's native "
                        "vocabulary is rich enough that you rarely invent "
                        "your own, and this schema deliberately samples the "
                        "kinds you will actually use — uuid for keys "
                        "minted anywhere, bigint for sequence-backed "
                        "counters, text for names and bodies (PostgreSQL "
                        "text has no length ceiling; VARCHAR(n) is a "
                        "constraint, not a different type), timestamp with "
                        "time zone for instants (always the tz-aware "
                        "spelling — naive timestamps are a bug factory), "
                        "jsonb for structured payloads you deliberately do "
                        "not normalize, and text[] arrays for small "
                        "list-valued facts. Constraints then narrow types "
                        "to business truth on the same axis pydantic "
                        "narrowed JSON in topic 10 — but at rest, for "
                        "every writer."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="types-naming",
                    text=(
                        "Before the constraints, one piece of engineering "
                        "hygiene that pays for itself the first time a "
                        "constraint fires: constraint NAMES. When an "
                        "INSERT violates a rule, the error you get names "
                        "the constraint — PostgreSQL's defaults "
                        "(posts_pkey, posts_status_check) are readable "
                        "enough for one table and useless across fifty. "
                        "The guide's schema declares a naming convention "
                        "so every constraint gets a deterministic, "
                        "searchable name:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="types-convention",
                    language="py",
                    caption="One convention, every constraint named — the rule lives with the schema.",
                    source="server/guide/data/db/schema.py",
                    snippet=(
                        "NAMING_CONVENTION: dict[str, str] = {\n"
                        "    \"ix\": \"ix_%(table_name)s_%(column_0_name)s\",\n"
                        "    \"uq\": \"uq_%(table_name)s_%(column_0_name)s\",\n"
                        "    \"ck\": \"ck_%(table_name)s_%(constraint_name)s\",\n"
                        "    \"fk\": \"fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s\",\n"
                        "    \"pk\": \"pk_%(table_name)s\",\n"
                        "}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="types-authors",
                    text=(
                        "Now the authors table as it really exists in the "
                        "dev database — the smallest complete example of "
                        "every idea in this section in one place:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="types-authors-code",
                    language="py",
                    caption="The authors table: uuid key with a server default, unique email, defaulted timestamps.",
                    source="server/guide/data/db/schema.py",
                    snippet=(
                        "authors = Table(\n"
                        "    \"authors\",\n"
                        "    metadata,\n"
                        "    sa.Column(\n"
                        "        \"id\",\n"
                        "        postgresql.UUID(),\n"
                        "        primary_key=True,\n"
                        "        server_default=sa.text(\"gen_random_uuid()\"),\n"
                        "    ),\n"
                        "    sa.Column(\"name\", sa.Text(), nullable=False),\n"
                        "    sa.Column(\"email\", sa.Text(), nullable=False, unique=True),\n"
                        "    sa.Column(\"bio\", sa.Text(), nullable=False, server_default=\"\"),\n"
                        "    sa.Column(\n"
                        "        \"created_at\",\n"
                        "        postgresql.TIMESTAMP(timezone=True),\n"
                        "        nullable=False,\n"
                        "        server_default=sa.text(\"now()\"),\n"
                        "    ),\n"
                        ")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="types-read",
                    text=(
                        "Read it line by line. id is a UUID primary key whose "
                        "server_default lets PostgreSQL mint a uuid4 when a "
                        "writer omits it (gen_random_uuid() is built into "
                        "modern PostgreSQL) — the app may also supply its "
                        "own id, which section 7 will make interesting. "
                        "email is NOT NULL and UNIQUE: two authors cannot "
                        "share one address, enforced by a unique INDEX "
                        "PostgreSQL builds automatically (named uq_authors_email by the "
                        "convention). bio carries an empty-string default so "
                        "writers omit it freely. created_at is timestamptz "
                        "defaulting to now() — the database's clock, not the "
                        "app's. The remaining constraint kinds show up on "
                        "posts, where the business rules live:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="types-posts-checks",
                    language="py",
                    caption="The posts rules as the migration states them: a default, then two named CHECK domains.",
                    source="server/alembic/versions/0001_guide_schema.py",
                    snippet=(
                        "        sa.Column(\"status\", sa.Text(), server_default=\"draft\", nullable=False),\n"
                        "        # …\n"
                        "        sa.CheckConstraint(\n"
                        "            \"status IN ('draft', 'published')\", name=op.f(\"ck_posts_status_domain\")\n"
                        "        ),\n"
                        "        sa.CheckConstraint(\n"
                        "            \"char_length(title) BETWEEN 1 AND 120\", name=op.f(\"ck_posts_title_length\")\n"
                        "        ),"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="types-kinds",
                    text=(
                        "Those lines are the four constraint kinds every "
                        "schema is built from, each doing one job:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="types-kinds-list",
                    ordered=False,
                    items=[
                        "NOT NULL — the column must carry a value; absence "
                        "is a lie, not a state.",
                        "CHECK — a boolean expression every row must "
                        "satisfy (status IN (...), char_length(title) "
                        "BETWEEN 1 AND 120).",
                        "UNIQUE — no two rows may repeat the value; "
                        "enforced through an index, so it also speeds "
                        "lookups.",
                        "DEFAULT — the value used when a writer omits the "
                        "column; a server default is one the database "
                        "itself fills in.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="types-coda",
                    text=(
                        "Notice the layering against topic 10: the API "
                        "validates a PostCreate body and answers 422 "
                        "politely; the schema re-checks the same rules "
                        "blindly and answers with a constraint violation. "
                        "That redundancy is deliberate defense in depth — "
                        "the edge gives clients readable errors, the "
                        "database guarantees the invariant even for "
                        "writers that never saw the edge. A schema whose "
                        "constraints merely repeat the app is doing it "
                        "right."
                    ),
                ),
            ],
        ),
        # ── 3. Primary keys and foreign keys ───────────────────────────────
        Section(
            id="primary-and-foreign-keys",
            title="Primary keys and foreign keys",
            blocks=[
                TextBlock(
                    kind="text",
                    id="keys-pitch",
                    text=(
                        "A PRIMARY KEY is a table's identity contract: the "
                        "column (or columns) whose value names exactly one "
                        "row, forever. Every table here has a single-column "
                        "PK with a deterministic name (pk_posts, pk_authors "
                        "…) — and a PK is not just a label, it comes with "
                        "two enforced properties: uniqueness and a "
                        "NOT NULL. PostgreSQL implements the PK's unique "
                        "half as a real index, which is why the schema "
                        "explorer later lists pk_posts among the table's "
                        "indexes: a key you cannot look up by would be "
                        "decoration. What kind of value should BE the key "
                        "is its own decision with real consequences — "
                        "section 7 gives it a full section, and the schema "
                        "deliberately shows both answers: uuid for authors, "
                        "bigint sequences for posts, comments, and the "
                        "audit log."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="keys-fk-pitch",
                    text=(
                        "A FOREIGN KEY is the reference that turns separate "
                        "tables into a relational model: posts.author_id "
                        "must contain a value that EXISTS as authors.id — "
                        "PostgreSQL checks every INSERT and UPDATE against "
                        "it, so a post cannot point at a vanished author. "
                        "The other half of the contract is the DELETE "
                        "side: what happens to referencing rows when the "
                        "referenced row goes away? The vocabulary is small "
                        "and worth memorizing, because choosing per "
                        "relationship is the actual design work:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="keys-on-delete",
                    ordered=False,
                    items=[
                        "NO ACTION — refuse the delete if references remain "
                        "(the default; checked at statement end).",
                        "RESTRICT — same refusal, checked immediately; the "
                        "guide spells it explicitly to say \"authors are "
                        "protected\" out loud.",
                        "CASCADE — delete the referencing rows too; "
                        "comments have no meaning without their post.",
                        "SET NULL — keep the referencing row, null its "
                        "reference (requires a nullable FK column).",
                        "SET DEFAULT — set the reference back to its "
                        "default value; rare, and usually a smell.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="keys-fk-code-intro",
                    text=(
                        "Both of this schema's foreign keys come straight "
                        "from the initial migration, each with its ON "
                        "DELETE behavior chosen on purpose:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="keys-fk-code",
                    language="py",
                    caption="The schema's two relationships: RESTRICT protects authors, CASCADE sweeps comments.",
                    source="server/alembic/versions/0001_guide_schema.py",
                    snippet=(
                        "        sa.ForeignKeyConstraint(\n"
                        "            [\"author_id\"],\n"
                        "            [\"authors.id\"],\n"
                        "            name=op.f(\"fk_posts_author_id_authors\"),\n"
                        "            ondelete=\"RESTRICT\",\n"
                        "        ),\n"
                        "        # …\n"
                        "        sa.ForeignKeyConstraint(\n"
                        "            [\"post_id\"],\n"
                        "            [\"posts.id\"],\n"
                        "            name=op.f(\"fk_comments_post_id_posts\"),\n"
                        "            ondelete=\"CASCADE\",\n"
                        "        ),"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="keys-fk-read",
                    text=(
                        "The asymmetry is the lesson. Deleting an author "
                        "with posts fails loudly (RESTRICT): silently "
                        "destroying someone's writing is never what a "
                        "caller meant. Deleting a post takes its comments "
                        "along (CASCADE): a comment is owned by its post "
                        "in every sense, and an orphaned comment is "
                        "garbage. These choices live in the database, so "
                        "they hold for every writer — the same "
                        "defense-in-depth argument as section 2, now for "
                        "relationships. One PostgreSQL fact that surprises "
                        "everyone: the database checks FKs but does NOT "
                        "index the referencing column for you, so "
                        "\"find this author's posts\" scans the whole "
                        "posts table until you add an index yourself — "
                        "which is exactly where the next section begins."
                    ),
                ),
            ],
        ),
        # ── 4. Normalization → denormalization ─────────────────────────────
        Section(
            id="normalization-to-denormalization",
            title="Normalization to denormalization",
            blocks=[
                TextBlock(
                    kind="text",
                    id="norm-pitch",
                    text=(
                        "Normalization is the discipline of storing each "
                        "fact ONCE and referencing it everywhere else. The "
                        "schema already obeys the core move: an author's "
                        "name lives in authors, and posts carry "
                        "author_id — not a copied name. The payoff is "
                        "update-in-one-place: rename the author, and every "
                        "query sees the new name; the denormalized "
                        "alternative (name copied onto every post) would "
                        "need a thousand-row UPDATE and would still "
                        "drift. The formal normal forms (1NF through 5NF) "
                        "codify this intuition with increasing rigor, but "
                        "for working schema design three habits cover "
                        "the ground:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="norm-habits",
                    ordered=False,
                    items=[
                        "One kind of thing per table — a table describes "
                        "exactly one entity shape, never a blend.",
                        "Facts by reference — repeat nothing you can "
                        "reference; keys are cheap, copies drift.",
                        "Attributes belong to their owner — a post's "
                        "title lives on posts, an author's email on "
                        "authors, never both.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="norm-tags-problem",
                    text=(
                        "The interesting cases are the ones where the "
                        "discipline has a price. The substrate's posts "
                        "carry tags — a LIST-valued fact. Strict "
                        "normalization says a list is a relationship: a "
                        "post_tags table of (post_id, tag) pairs, one row "
                        "per tag, giving you per-tag constraints, cheap "
                        "renames, and set operations. This schema chose "
                        "the PostgreSQL array instead — a deliberate, "
                        "documented denormalization:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="norm-tags-code",
                    language="py",
                    caption="tags as a text[] column: the list lives on the row, one fact, one place.",
                    source="server/alembic/versions/0001_guide_schema.py",
                    snippet=(
                        "        sa.Column(\n"
                        "            \"tags\",\n"
                        "            postgresql.ARRAY(sa.Text()),\n"
                        "            server_default=sa.text(\"'{}'\"),\n"
                        "            nullable=False,\n"
                        "        ),"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="norm-tags-reasoning",
                    text=(
                        "Why the array wins HERE: the guide never queries "
                        "across tags relationally — it filters posts by "
                        "one tag and shows a post's tags with the post, "
                        "both of which the array serves with no join, no "
                        "second write, and no identity question (is the "
                        "tag 'http' on this post the SAME tag as 'http' "
                        "on that one? here: no such thing). The moment "
                        "tags need to be entities — renamed, described, "
                        "counted globally, owned — the join table stops "
                        "being optional. That is denormalization's "
                        "honest shape: not a vice you apologize for, but "
                        "a trade — cheaper reads and simpler writes "
                        "TODAY, bought with the cost of migrating later "
                        "when a query needs the normalized shape."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="norm-coda",
                    text=(
                        "The same reasoning scale applies to computed "
                        "facts: a post's comment COUNT is derivable from "
                        "comments, so it is not stored — a counter column "
                        "would be a denormalization you buy only when "
                        "counting on read gets measured as too slow. The "
                        "working rule this guide follows: normalize by "
                        "default, denormalize on evidence, and when you "
                        "denormalize, write down what evidence would "
                        "reverse the decision — the migration history of "
                        "section 6 is where that record lives."
                    ),
                ),
            ],
        ),
        # ── 5. Indexes ─────────────────────────────────────────────────────
        Section(
            id="indexes",
            title="Indexes",
            lead="This section carries the topic's first demo — the schema explorer.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="indexes-pitch",
                    text=(
                        "Without an index, every lookup is a full table "
                        "scan — read every row, keep the matches. An "
                        "index is a side data structure the database "
                        "maintains so it can FIND rows without scanning: "
                        "PostgreSQL's default is the B-tree, a sorted "
                        "tree whose whole personality is that equality "
                        "and range lookups on the indexed column(s) "
                        "become a short walk instead of a sweep. Indexes "
                        "answer three questions for every table: which "
                        "lookups are common (index those columns), what "
                        "uniqueness must hold (unique indexes ENFORCE "
                        "it — PKs and UNIQUE constraints are indexes "
                        "under the hood), and what the maintenance cost "
                        "is (every INSERT and UPDATE must also update "
                        "each index — more indexes, slower writes)."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="indexes-fk-need",
                    text=(
                        "Section 3 ended on the trap: PostgreSQL does not "
                        "index foreign keys for you. The reference CHECK "
                        "works without an index, but every \"posts by "
                        "this author\" and every RESTRICT/CASCADE "
                        "cleanup scans the referencing table. This "
                        "schema's rule is one b-tree per foreign key — "
                        "ix_posts_author_id and ix_comments_post_id — "
                        "plus one deliberately FANCY index worth a close "
                        "read:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="indexes-partial",
                    language="py",
                    caption="A partial index: only published posts are covered — drafts never enter the tree.",
                    source="server/alembic/versions/0001_guide_schema.py",
                    snippet=(
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
                    id="indexes-partial-read",
                    text=(
                        "That WHERE makes it a PARTIAL index — a b-tree "
                        "over only the rows matching the predicate. The "
                        "guide's real feed query is \"published posts, "
                        "newest first\"; drafts (the majority, in a "
                        "writing app) are invisible to that query, so the "
                        "index simply excludes them: the tree is smaller, "
                        "fits in more cache, and updates to drafts never "
                        "touch it. Partial indexes are the sharpest tool "
                        "in the box for read-shaped tables: unique-among-"
                        "a-subset (one ACTIVE subscription per user), "
                        "sparse facts (index only where deleted_at IS "
                        "NULL), hot slices (index only recent rows). The "
                        "cost is the same as any index plus one rule: a "
                        "query only uses it when the planner can PROVE "
                        "the query's predicate implies the index's "
                        "predicate — status = 'published' queries match, "
                        "status = 'draft' cannot."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="indexes-introspect",
                    text=(
                        "You should never trust a schema diagram over "
                        "the database itself — so this demo does not "
                        "have one. The explorer endpoint introspects the "
                        "LIVE schema through PostgreSQL's own catalogs: "
                        "information_schema for the standard questions "
                        "(tables, columns) and pg_catalog for the ones "
                        "the standard does not carry (index kind, "
                        "partial WHERE, primary-ness). This is the query "
                        "behind the demo's index cards — real SQL, read "
                        "against your running database:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="indexes-sql",
                    language="sql",
                    caption="How the explorer sees indexes: pg_index joined to the catalogs, one row per index.",
                    source="server/guide/data/db/introspection.py",
                    snippet=(
                        "SELECT ic.relname AS index_name,\n"
                        "       tn.relname AS table_name,\n"
                        "       am.amname AS kind,\n"
                        "       ix.indisunique AS is_unique,\n"
                        "       ix.indisprimary AS is_primary,\n"
                        "       pg_get_expr(ix.indpred, ix.indrelid) AS where_clause,"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="indexes-demo-pitch",
                    text=(
                        "Use it right now: the roster lists every public "
                        "table with its fact counts, and clicking a table "
                        "drills into its full anatomy — columns with "
                        "types, nullability, and raw defaults (look for "
                        "posts.id's nextval(...) — the sequence default "
                        "bigserial really uses), the primary key, foreign "
                        "keys with their ON DELETE behavior, CHECK "
                        "definitions verbatim, and every index with kind, "
                        "uniqueness, and partial WHERE. Everything you "
                        "just read about this schema, the explorer is "
                        "reading about the real one."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="db:schema-explorer",
                    title="The schema explorer",
                    description=(
                        "GET /api/demo/db/schema-explorer introspects the "
                        "LIVE dev PostgreSQL via information_schema and "
                        "pg_catalog — nothing hard-coded: the table roster "
                        "with column/FK/CHECK/index counts, and "
                        "?table=posts drills into one table's full anatomy "
                        "(columns with types, nullable flags, raw defaults "
                        "like nextval('posts_id_seq'); primary key; "
                        "foreign keys with ON DELETE behaviors; CHECK "
                        "definitions as pg_get_constraintdef renders them; "
                        "every index with kind, uniqueness, and partial "
                        "WHERE clause). An unknown table answers the "
                        "honest 404 envelope; unreachable PostgreSQL "
                        "answers the 503 one."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="indexes-coda",
                    text=(
                        "A closing note on restraint: each index is a "
                        "small tax on every write, so the discipline is "
                        "to index for the queries you actually run — the "
                        "foreign keys (joins and delete checks), the "
                        "uniques (identity), and the one read path the "
                        "product lives on (the published feed). Topic 17 "
                        "shows how to CHECK that discipline with "
                        "EXPLAIN ANALYZE, where you can watch an index "
                        "being used — or ignored."
                    ),
                ),
            ],
        ),
        # ── 6. Alembic history ─────────────────────────────────────────────
        Section(
            id="alembic-history",
            title="Alembic history",
            blocks=[
                TextBlock(
                    kind="text",
                    id="alembic-pitch",
                    text=(
                        "A schema created by hand — one CREATE TABLE "
                        "session, remembered by nobody — is a liability: "
                        "the second environment (staging, a colleague's "
                        "laptop, tomorrow's prod) gets a slightly "
                        "different database and nobody knows which is "
                        "right. Alembic turns the schema into CODE WITH "
                        "HISTORY: an ordered chain of migration files in "
                        "server/alembic/versions/, each one a Python "
                        "program whose upgrade() moves the database "
                        "FORWARD one step and whose downgrade() can walk "
                        "it back. The database carries a tiny "
                        "alembic_version table recording which revision "
                        "it is at; upgrading means \"run every migration "
                        "after the recorded one\" — so the same command "
                        "brings ANY environment to ANY point in the "
                        "chain. The schema this topic teaches is "
                        "revision 0001 — later topics grow the chain "
                        "from it (0002 adds full-text search)."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="alembic-layout",
                    text=(
                        "This repo's Alembic setup is the foundation for "
                        "every later data topic, so its wiring deserves a "
                        "close read. alembic.ini holds only PATHS and "
                        "logging — never a database URL. The URL comes "
                        "from the app's own config rail at runtime: "
                        "alembic/env.py (the program Alembic runs around "
                        "each migration) builds an async engine on "
                        "asyncpg from the SAME pydantic-settings "
                        "configuration the app uses — so migrations and "
                        "application can never disagree about which "
                        "database they target:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="alembic-env",
                    language="py",
                    caption="env.py's URL rule: the caller's injection wins; the app config rail is the default.",
                    source="server/alembic/env.py",
                    snippet=(
                        "# The URL comes from the app config rail UNLESS the caller already\n"
                        "# injected one into the Config (the lifespan and tests do — they may\n"
                        "# target a different database than the ambient FDG_ environment).\n"
                        "if not config.get_main_option(\"sqlalchemy.url\"):\n"
                        "    config.set_main_option(\"sqlalchemy.url\", get_config().database_url)\n"
                        "\n"
                        "target_metadata = metadata"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="alembic-target-metadata",
                    text=(
                        "That target_metadata is the second load-bearing "
                        "line: it points at the SQLAlchemy Core tables in "
                        "guide/data/db/schema.py, making those definitions "
                        "the schema's single source of truth. New tables "
                        "are added THERE, then ``alembic revision "
                        "--autogenerate`` writes the migration by "
                        "diffing the metadata against the live database — "
                        "and a test in the suite runs ``alembic check`` "
                        "after every upgrade to refuse drift between the "
                        "two. Autogeneration is a draft, not a verdict: "
                        "it never sees SEQUENCEs, so 0001's three "
                        "create_sequence calls and nextval defaults were "
                        "finished by hand — which is exactly why "
                        "migrations are reviewed code, committed and "
                        "versioned like any other."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="alembic-strategy",
                    text=(
                        "The remaining decision is WHEN migrations run. "
                        "This guide's strategy: the app's lifespan runs "
                        "``alembic upgrade head`` AT STARTUP — "
                        "idempotently (an up-to-date database costs one "
                        "version-table read), so every environment "
                        "converges on the schema without a deploy-time "
                        "orchestration step, and the same command works "
                        "from a terminal for humans. Alembic's command "
                        "API is synchronous, so the lifespan runs it "
                        "through asyncio.to_thread — and true to the "
                        "optional-service discipline, a failed migration "
                        "(PostgreSQL down) logs a warning and the app "
                        "still boots:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="alembic-lifecycle",
                    language="py",
                    caption="The lifespan's best-effort migration: apply at boot, log the skip, stay up.",
                    source="server/guide/data/db/lifecycle.py",
                    snippet=(
                        "async def upgrade_database_on_startup(database_url: str) -> None:\n"
                        "    \"\"\"Best-effort startup migration: apply, or log the skip and continue.\"\"\"\n"
                        "    try:\n"
                        "        await asyncio.to_thread(upgrade_database_to_head, database_url)\n"
                        "    except Exception as exc:\n"
                        "        logger.warning(\n"
                        "            \"db_migrations_skipped\",\n"
                        "            error=type(exc).__name__,\n"
                        "            detail=str(exc),\n"
                        "            hint=\"PostgreSQL may be down — the app stays up; DB-backed \"\n"
                        "            \"features will report service_unavailable until it returns.\",\n"
                        "        )\n"
                        "    else:\n"
                        "        logger.info(\"db_migrations_applied\", target=\"head\")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="alembic-workflow",
                    text=(
                        "The day-to-day workflow this sets up for the "
                        "rest of the guide (and for your own projects) "
                        "is a loop with review built in:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="alembic-workflow-list",
                    ordered=True,
                    items=[
                        "Declare the change — edit the Core tables in "
                        "schema.py (the source of truth).",
                        "Draft the migration — alembic revision "
                        "--autogenerate diffs metadata against the live "
                        "database.",
                        "Review and adjust — autogenerate misses "
                        "sequences, data migrations, and intent; fix the "
                        "draft like any code under review.",
                        "Apply — alembic upgrade head (or just restart "
                        "the app; the lifespan does it).",
                        "Commit both — schema.py and the migration file "
                        "travel together in one change, and alembic "
                        "check keeps them honest.",
                    ],
                ),
            ],
        ),
        # ── 7. UUIDv7 vs sequential ────────────────────────────────────────
        Section(
            id="uuid7-vs-sequential",
            title="UUIDv7 vs sequential",
            lead="This section carries the topic's second demo — the UUID lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="uuid-pitch",
                    text=(
                        "Section 3 deferred the primary-key VALUE "
                        "decision; here it is, because it interacts with "
                        "everything — especially section 5's indexes. A "
                        "B-tree loves appends: new rows whose key sorts "
                        "AFTER everything present land on the right "
                        "edge, one page at a time. Keys that sort "
                        "RANDOMLY scatter inserts across the whole tree "
                        "— every insert a different page, the cache "
                        "never warming. So the id strategy is really an "
                        "index-locality strategy, and the three standard "
                        "candidates trade exactly that:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="uuid-strategies",
                    ordered=False,
                    items=[
                        "Sequence (bigserial/identity) — the database "
                        "counts 1, 2, 3…; perfect locality, but ids "
                        "leak volume and timing, collide across tables, "
                        "and sort terribly as text ('10' before '2').",
                        "UUIDv4 — 122 random bits mintable anywhere with "
                        "zero coordination; hopeless locality (random "
                        "inserts) and no ordering at all.",
                        "UUIDv7 — 48 bits of Unix-milliseconds up front, "
                        "then version, then randomness and a counter: "
                        "mint-anywhere like v4, but time-ordered, so "
                        "inserts cluster near the right edge and the "
                        "ids SORT — including as plain strings.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="uuid-implementation",
                    text=(
                        "Python 3.13's uuid module has no uuid7 — so this "
                        "repo implements it, for real, in the domain "
                        "layer. The construction is the whole lesson: "
                        "128 bits placed field by field, version and "
                        "variant stamped by the assembler so no caller "
                        "can forge another layout:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="uuid-parts",
                    language="py",
                    caption="guide.domain.db.ids.uuid7_from_parts: the RFC 9562 layout, field by field.",
                    source="server/guide/domain/db/ids.py",
                    snippet=(
                        "def uuid7_from_parts(unix_ms: int, rand_a: int, rand_b: int) -> UUID:\n"
                        "    \"\"\"Assemble a UUIDv7 from its three fields (each taken mod its width).\n"
                        "\n"
                        "    The version and variant bits are written here and only here — callers\n"
                        "    cannot forge another layout through this seam.\n"
                        "    \"\"\"\n"
                        "    if unix_ms < 0:\n"
                        "        raise ValueError(f\"unix_ms must be non-negative, got {unix_ms}\")\n"
                        "    value = (unix_ms & _UNIX_MS_MASK) << 80\n"
                        "    value |= UUID7_VERSION << 76\n"
                        "    value |= (rand_a & _RAND_A_MASK) << 64\n"
                        "    value |= 0b10 << 62\n"
                        "    value |= rand_b & _RAND_B_MASK\n"
                        "    return UUID(int=value)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="uuid-layout-read",
                    text=(
                        "Read the shifts as the layout: unix_ms occupies "
                        "the leftmost 48 bits (bits 127..80), the version "
                        "nibble 7 sits at bits 79..76, rand_a gets 12 "
                        "bits at 75..64, the variant marker 10 claims "
                        "the top of bits 63..62, and rand_b fills the "
                        "remaining 62. Because time is the LEFTMOST "
                        "field, comparing two UUIDv7s — even as strings "
                        "— compares their creation times first: that is "
                        "the entire sortability claim. The one hazard is "
                        "two ids minted in the SAME millisecond, and "
                        "the mint's answer is the RFC's recommended "
                        "monotonic method — a counter in rand_b's top "
                        "bits:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="uuid-mint",
                    language="py",
                    caption="Uuid7Mint.mint: same-millisecond calls advance the counter, so every mint sorts after the last.",
                    source="server/guide/domain/db/ids.py",
                    snippet=(
                        "    def mint(self) -> UUID:\n"
                        "        \"\"\"One fresh UUIDv7, greater than every previous mint from here.\"\"\"\n"
                        "        now_ms = self._clock()\n"
                        "        if now_ms > self._last_ms:\n"
                        "            self._last_ms = now_ms\n"
                        "            self._counter = 0\n"
                        "            self._rand_a_base = secrets.randbelow(_RAND_A_MASK + 1)\n"
                        "        else:\n"
                        "            self._counter += 1\n"
                        "        rand_b = (self._counter << _RANDOM_BITS) | secrets.randbelow(1 << _RANDOM_BITS)\n"
                        "        return uuid7_from_parts(self._last_ms, self._rand_a_base, rand_b)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="uuid-mint-read",
                    text=(
                        "A new millisecond resets the counter and redraws "
                        "rand_a's random base; within the millisecond the "
                        "counter grows — 42 bits of headroom, four "
                        "million ids per millisecond from one mint — and "
                        "a clock that runs backwards is HELD at the last "
                        "seen millisecond rather than obeyed, because "
                        "monotonicity is the contract. The property "
                        "suite pins all of it: version and variant bits, "
                        "timestamp round-trip (uuid7_timestamp_ms reads "
                        "the time back out), a thousand same-millisecond "
                        "mints coming out distinct AND sorted, and the "
                        "backwards clock refusing to regress."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="uuid-demo-pitch",
                    text=(
                        "The lab below runs the comparison live: twelve "
                        "ids per strategy, minted the moment you load "
                        "it. The sortRanks fact is the proof — for each "
                        "generated value, its rank in lexicographic "
                        "sort order. UUIDv7's ranks read 0, 1, 2, … "
                        "(generation order IS sort order); uuid4's are "
                        "shuffled; the sequence's ranks look sorted too — "
                        "until you notice the values column and that "
                        "'10' and '11' sort before '2' as text. The "
                        "layout card dissects one real UUIDv7 into its "
                        "five fields, hex slice by hex slice, with the "
                        "timestamp read back out beside it."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="db:uuid",
                    title="The UUID lab",
                    description=(
                        "GET /api/demo/db/uuid mints three runs of twelve "
                        "ids each — uuid4, UUIDv7 (this repo's own "
                        "implementation, all minted inside one "
                        "millisecond), and a bigserial-style sequence — "
                        "and proves the ordering facts: per-run sortRanks "
                        "(uuid7 reads 0..11, uuid4 shuffles, the "
                        "sequence falls into the '10' before '2' "
                        "string-sort trap), the shared hex prefix of "
                        "same-millisecond uuid7s, one UUIDv7 dissected "
                        "into its five RFC 9562 fields with the "
                        "timestamp read back out, and the three "
                        "strategies' trade-off cards (locality, "
                        "randomness, coordination, timing leakage)."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="uuid-coda",
                    text=(
                        "So what did the schema choose? Both answers, on "
                        "purpose: authors.id is a UUID the application "
                        "can mint (uuid7 in new code — client-side "
                        "generation with server-default fallback), while "
                        "posts, comments, and audit_log use bigint "
                        "sequences — high-volume, database-owned tables "
                        "where the database is the natural single "
                        "minter. That split is the practical answer most "
                        "systems land on: coordinate nothing you don't "
                        "have to, and know WHICH property (freedom to "
                        "mint, or append-only order) each table's "
                        "traffic actually needs."
                    ),
                ),
            ],
        ),
        # ── 8. The audit-logging pattern ───────────────────────────────────
        Section(
            id="audit-logging-pattern",
            title="The audit-logging pattern",
            blocks=[
                TextBlock(
                    kind="text",
                    id="audit-pitch",
                    text=(
                        "Schema design's last question is not how rows "
                        "are shaped but how they CHANGE — who set a "
                        "post from draft to published, when, and what "
                        "was it before? Application logs answer none of "
                        "that durably; a full history table answers it "
                        "for every row. The audit-logging pattern is an "
                        "append-only table that records one row per "
                        "meaningful change, and the guide's schema "
                        "ships it as real DDL — topic 17's SQL and "
                        "topic 18's ORM sessions will write through it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="audit-ddl",
                    language="py",
                    caption="audit_log from the initial migration: append-only facts, jsonb payload, database clock.",
                    source="server/alembic/versions/0001_guide_schema.py",
                    snippet=(
                        "    op.create_table(\n"
                        "        \"audit_log\",\n"
                        "        # …\n"
                        "        sa.Column(\"actor\", sa.Text(), nullable=False),\n"
                        "        sa.Column(\"action\", sa.Text(), nullable=False),\n"
                        "        sa.Column(\"table_name\", sa.Text(), nullable=False),\n"
                        "        sa.Column(\"row_pk\", sa.Text(), nullable=False),\n"
                        "        sa.Column(\n"
                        "            \"changes\",\n"
                        "            postgresql.JSONB(),\n"
                        "            server_default=sa.text(\"'{}'::jsonb\"),\n"
                        "            nullable=False,\n"
                        "        ),"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="audit-ddl-read",
                    text=(
                        "The shape is deliberately query-first: actor "
                        "(who — a user id or system label), action "
                        "(insert/update/delete — the closed vocabulary "
                        "lives in the domain's AuditEvent), table_name + "
                        "row_pk (what — a stable address across ANY "
                        "table, which is why row_pk is text: uuid or "
                        "bigint both stringify), changes as jsonb (the "
                        "field-by-field before/after, queryable in SQL), "
                        "and occurred_at defaulting to now() — the "
                        "database's clock, same argument as section 2. "
                        "Append-only is enforced by DISCIPLINE, not DDL "
                        "(PostgreSQL has no read-only table): the "
                        "domain offers only the insert path, and the "
                        "writer's contract is two lines long:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="audit-writer",
                    language="py",
                    caption="record_audit: the INSERT joins the CALLER'S transaction — that line is the pattern.",
                    source="server/guide/data/db/audit.py",
                    snippet=(
                        "async def record_audit(connection: AsyncConnection, event: AuditEvent) -> None:\n"
                        "    \"\"\"Write one audit row on the caller's connection (same transaction).\"\"\"\n"
                        "    await connection.execute(sa.insert(audit_log).values(**audit_row_values(event)))"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="audit-in-tx",
                    text=(
                        "The load-bearing word is the parameter: the "
                        "CALLER'S connection. An audit row written on a "
                        "separate connection after the fact can arrive "
                        "without its change (the process died between) "
                        "or its change without the audit (nobody wrote "
                        "it) — an audit log with holes is worse than "
                        "none, because you TRUST it. Taking the "
                        "business change's own connection makes both "
                        "rows one transaction: they commit together "
                        "and roll back together, always. The domain "
                        "side keeps the payload pure — "
                        "audit_row_values(event) builds exactly the "
                        "table's columns — and the test suite proves "
                        "the atomicity both ways:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="audit-proof",
                    language="py",
                    caption="The rollback proof: the change fails after the audit write — both rows vanish.",
                    source="server/tests/data/test_audit_writer.py",
                    snippet=(
                        "            try:\n"
                        "                async with connection.begin():\n"
                        "                    await connection.execute(\n"
                        "                        sa.insert(authors).values(name=\"Grace\", email=email)\n"
                        "                    )\n"
                        "                    await record_audit(connection, _an_event(email))\n"
                        "                    raise RuntimeError(\"the business change failed after the audit write\")\n"
                        "            except RuntimeError:\n"
                        "                pass"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="audit-coda",
                    text=(
                        "After that block, the test counts rows: zero "
                        "authors, zero audit entries — the failed "
                        "change left no orphaned audit trail, and the "
                        "sibling test commits the same pair and finds "
                        "both. That pair of tests is the pattern's "
                        "whole contract. Two honest limits close it "
                        "out: this writer records what the APPLICATION "
                        "does — a rogue psql session bypasses it (a "
                        "database trigger is the stronger, noisier "
                        "alternative); and changes jsonb is only as "
                        "deep as the diff you build. Queries come free "
                        "with the shape: by row_pk for a row's "
                        "biography, by actor for a person's trail, by "
                        "occurred_at for an incident window — each one "
                        "just an index away if the volume ever demands "
                        "it."
                    ),
                ),
            ],
        ),
        # ── 9. Terminal companion ──────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="Eight real stops: the topic, the live schema, one drill-down each, a 404, the id lab, the group.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-honesty",
                    text=(
                        "This topic's tour is unusually satisfying "
                        "because everything it touches is live: the "
                        "schema sits in the running PostgreSQL, the "
                        "explorer reads it fresh on every request, and "
                        "psql itself is one docker exec away when you "
                        "want to go past what the explorer shows. Stops "
                        "1–2 read the topic and the whole-table roster; "
                        "stop 3 drills into posts and reads back every "
                        "constraint this chapter taught; stop 4 checks "
                        "the audit table's anatomy; stop 5 earns the "
                        "honest 404; stop 6 runs the id lab; stop 7 "
                        "peeks at the migration bookkeeping table "
                        "psql-style; stop 8 watches the Data group "
                        "open."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-topic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the topic itself: nine sections, both demos inline (§5 and §7)\n"
                        "curl -s localhost:8000/api/content/sql-schema | python3 -c '\n"
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
                    id="terminal-roster",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the live roster: every public table with its fact counts\n"
                        "curl -s localhost:8000/api/demo/db/schema-explorer | python3 -c '\n"
                        "import json, sys\n"
                        "r = json.load(sys.stdin)\n"
                        "print(\"database:\", r[\"databaseName\"], \"· tables:\", r[\"tableCount\"])\n"
                        "for t in r[\"tables\"]:\n"
                        "    print(f\"  {t['name']:15} {t['columnCount']} cols · {t['indexCount']} idx · \"\n"
                        "          f\"{t['foreignKeyCount']} fk · {t['checkCount']} checks\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-posts",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — posts under the microscope: types, defaults, FK, checks, the partial index\n"
                        "curl -s 'localhost:8000/api/demo/db/schema-explorer?table=posts' | python3 -c '\n"
                        "import json, sys\n"
                        "f = json.load(sys.stdin)[\"focus\"]\n"
                        "for c in f[\"columns\"]:\n"
                        "    print(f\"  {c['name']:12} {c['type']:26} null={c['nullable']} default={c['default']}\")\n"
                        "print(\"pk:\", f[\"primaryKey\"], \"· fk:\", f[\"foreignKeys\"][0][\"onDelete\"])\n"
                        "print(\"checks:\", [c[\"name\"] for c in f[\"checks\"]])\n"
                        "for i in f[\"indexes\"]:\n"
                        "    print(f\"  index {i['name']:34} {i['kind']} unique={i['unique']} where={i['where']}\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-audit",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the audit table's anatomy: jsonb payload, database clock\n"
                        "curl -s 'localhost:8000/api/demo/db/schema-explorer?table=audit_log' | python3 -c '\n"
                        "import json, sys\n"
                        "f = json.load(sys.stdin)[\"focus\"]\n"
                        "print(\"columns:\", [c[\"name\"] for c in f[\"columns\"]])\n"
                        "print(\"changes column:\", next(c for c in f[\"columns\"] if c[\"name\"] == \"changes\")[\"type\"])\n"
                        "print(\"occurred_at default:\", next(c for c in f[\"columns\"] if c[\"name\"] == \"occurred_at\")[\"default\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-404",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the honest 404: a table the live schema does not have\n"
                        "curl -s 'localhost:8000/api/demo/db/schema-explorer?table=no_such_table' | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-uuid",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — the id lab: ordering proofs for uuid4, uuid7, and the sequence\n"
                        "curl -s localhost:8000/api/demo/db/uuid | python3 -c '\n"
                        "import json, sys\n"
                        "r = json.load(sys.stdin)\n"
                        "for run in r[\"runs\"]:\n"
                        "    print(f\"  {run['kind']:9} sortable={str(run['sortable']):5} ranks={run['sortRanks']}\")\n"
                        "print(\"shared prefix:\", r[\"sharedPrefixHex\"])\n"
                        "print(\"first uuid7:\", r[\"layout\"][\"value\"], \"-> timestamp\", r[\"layout\"][\"unixMs\"], \"ms\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-alembic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 7 — psql-style: the migration bookkeeping itself (which revision is live)\n"
                        "docker exec fastapi_developers_guide_postgres_dev \\\n"
                        "  psql -U postgres -d guide -c 'SELECT * FROM alembic_version;' \\\n"
                        "  -c '\\d posts' | head -20"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-curriculum",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 8 — the Data group opens: sixteen topics, five groups\n"
                        "curl -s localhost:8000/api/content | python3 -c '\n"
                        "import json, sys\n"
                        "body = json.load(sys.stdin)\n"
                        "print(\"groups:\", [g[\"id\"] for g in body[\"groups\"]])\n"
                        "print(\"topics total:\", len(body[\"topics\"]))\n"
                        "print(\"first data topic:\", next(t[\"id\"] for t in body[\"topics\"] if t[\"group\"] == \"data\"))'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stop 3 is the chapter in one screen: the "
                        "nextval default of section 7, the RESTRICT "
                        "foreign key of section 3, the named CHECKs of "
                        "section 2, and the partial WHERE of section 5 "
                        "— every claim this topic made, read back out "
                        "of the database that enforces it. And stop 7 "
                        "shows the one table this topic did not design: "
                        "alembic_version, two columns, the whole "
                        "migration story in a single row. The schema is "
                        "in place; topic 17 opens the database for "
                        "real — drivers, transactions, and the SQL that "
                        "earns it all."
                    ),
                ),
            ],
        ),
    ],
)
