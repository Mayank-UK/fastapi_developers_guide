"""Topic 17 — databases and SQL (second topic of the Data group).

Topic 16 built the schema; this topic OPENS the database. Six demos run
real SQL against the live dev PostgreSQL through the guide's first
repository: the parameterized-filter safety probe, the transactional
migration rehearsal (a mid-sequence failure rolled back atomically),
the sql-lab exhibits (CTEs, windows, recursion), full-text search over
migration 0002's generated tsvector with both EXPLAIN plans, the
deterministic lost-update race vs SELECT … FOR UPDATE, and the
in-transaction audit proof. Sections walk the working order: drivers
and layers, the DAO pattern and parameterization, transactions, what an
ORM would add, hand-written SQL worth knowing, reading EXPLAIN ANALYZE,
full-text search, isolation and locking, and audit in the same
transaction.

Every must-source code block quotes a real repo file (the ratchet
verifies it): the engine factory, the repository's SQL constants, the
migration rehearsal, the race choreography, the audit scenario,
migration 0002, and the search query.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="databases-sql",
    title="Databases and SQL",
    subtitle=(
        "Opening the database for real — drivers, the DAO pattern, "
        "transactions, hand-written SQL, EXPLAIN, full-text search, "
        "isolation, and audit."
    ),
    group="data",
    order=17,
    sections=[
        # ── 1. Drivers and layers ──────────────────────────────────────────
        Section(
            id="drivers-and-layers",
            title="Drivers and layers",
            blocks=[
                TextBlock(
                    kind="text",
                    id="drivers-pitch",
                    text=(
                        "Topic 16 left the database as a schema — tables, "
                        "constraints, a migration chain. This topic makes "
                        "the application TALK to it, and the first decision "
                        "is which layer to talk through. In the Python "
                        "world the stack has three floors, and every "
                        "choice trades control for convenience:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="drivers-layers-list",
                    ordered=False,
                    items=[
                        "The driver — asyncpg (or psycopg): speaks the "
                        "PostgreSQL wire protocol, owns sockets and "
                        "types. Fastest, closest to the metal, SQL in and "
                        "rows out.",
                        "SQLAlchemy Core — a thin layer over the driver: "
                        "a shared SQL expression language, connection "
                        "pooling, and composable table metadata, while "
                        "you still think in tables and SQL.",
                        "SQLAlchemy ORM — the top floor: mapped Python "
                        "objects, a session with an identity map, "
                        "relationship loading, unit-of-work flushes. "
                        "Convenient, and the furthest from the SQL you "
                        "sent.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="drivers-choice",
                    text=(
                        "This guide's data phase sits deliberately on "
                        "Core over asyncpg: the engine URL names the "
                        "driver, and everything above it is SQLAlchemy. "
                        "That choice is not a ranking — asyncpg alone is "
                        "perfectly production-ready, and topic 18 gives "
                        "the ORM a full topic of its own — it is a "
                        "teaching position: you should write and read "
                        "real SQL, transactions, and query plans BEFORE "
                        "an ORM starts generating them for you. The one "
                        "piece of infrastructure every floor shares is "
                        "the engine, and the guide owns exactly one "
                        "factory for it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="drivers-engine",
                    language="py",
                    caption="One config rail, one engine: every DB-touching adapter in the guide shares this.",
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
                    id="drivers-engine-read",
                    text=(
                        "Two details earn their keep immediately. "
                        "pool_pre_ping checks a pooled connection before "
                        "handing it out, so a database restart between "
                        "requests becomes a clean reconnect rather than a "
                        "stale-socket error — the cheapest reliability "
                        "line in the whole stack. And the engine is LAZY: "
                        "constructing it opens nothing, which is why the "
                        "app boots even with PostgreSQL down (topic 16's "
                        "optional-service discipline — every demo in this "
                        "topic reports the honest 503 envelope until the "
                        "database returns). One engine per process, many "
                        "short-lived connections drawn from its pool: "
                        "never a connection per request made by hand, "
                        "never a global connection shared across "
                        "requests."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="drivers-seed",
                    text=(
                        "One more thing every demo in this topic needs: "
                        "DATA. The schema shipped empty; the demos share "
                        "an idempotent seed step — the first DB-backed "
                        "request inserts three authors, twelve posts, and "
                        "sixteen comments (the same roster the in-memory "
                        "substrate of topic 11 served, now with bodies "
                        "worth full-text searching), and every later "
                        "request skips it with a single COUNT. The seed "
                        "runs as a FastAPI dependency the demo routers "
                        "share, so 'the data exists' is a wiring fact, "
                        "not a README instruction someone forgot to run."
                    ),
                ),
            ],
        ),
        # ── 2. The DAO pattern + parameterized queries ────────────────────
        Section(
            id="dao-and-parameterized-queries",
            title="The DAO pattern and parameterized queries",
            lead="This section carries the topic's first demo — the SQL safety probe.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dao-pitch",
                    text=(
                        "Where does SQL live? Not in routers (they parse "
                        "and map), not sprinkled through use cases (they "
                        "orchestrate), but in ONE place per area: a "
                        "repository — the classic name is DAO, data "
                        "access object — that owns every statement "
                        "touching a table. The guide's is "
                        "guide/data/db/repository.py: a class implementing "
                        "the domain's GuideRepository port, taking the "
                        "shared engine, exposing one method per query the "
                        "demos need. Routers resolve it through "
                        "dependency injection and never see a connection; "
                        "the domain defines the port and the row models "
                        "that cross it; tests can fake the whole thing by "
                        "registering another adapter. That seam is the "
                        "pattern's entire value."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dao-parameterization-pitch",
                    text=(
                        "The repository's first rule is non-negotiable: "
                        "every query that carries caller input uses bind "
                        "parameters. The demo's filter query is the "
                        "canonical shape — a placeholder in the SQL "
                        "text, the value handed over SEPARATELY, the "
                        "driver (here through SQLAlchemy's text()) "
                        "sending them as protocol-level parameters:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dao-filter-sql",
                    language="sql",
                    caption="The safety demo's filter, exactly as the repository runs it.",
                    source="server/guide/data/db/repository.py",
                    snippet=(
                        "SELECT p.id, p.slug, p.title, p.status\n"
                        "FROM posts AS p\n"
                        "WHERE p.title ILIKE :pattern\n"
                        "ORDER BY p.id"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dao-parameterization-read",
                    text=(
                        "Read :pattern as a hole punched in the statement "
                        "BEFORE the value exists. PostgreSQL parses the "
                        "statement once — the plan knows there is a "
                        "title ILIKE comparison against one text value — "
                        "and the value is then matched against that "
                        "shape as pure data. A caller who sends a quote "
                        "cannot close the string literal, because there "
                        "IS no string literal to close; a semicolon "
                        "cannot start a second statement, because the "
                        "value is never parsed as SQL. The contrast is "
                        "the naive twin, rendered (never executed) by "
                        "the demo's pure builder:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dao-unsafe",
                    language="py",
                    caption="The interpolated twin: rendered as display text only — never executed.",
                    source="server/guide/domain/demos/sql_safety.py",
                    snippet=(
                        "UNSAFE_TEMPLATE = (\n"
                        "    \"SELECT id, slug, title, status FROM posts WHERE title ILIKE '%{value}%' ORDER BY id\"\n"
                        ")\n"
                        "# …\n"
                        "def render_unsafe_sql(template: str, filter_value: str) -> str:\n"
                        "    \"\"\"The statement string interpolation would produce — pure text.\n"
                        "\n"
                        "    This is exactly what ``f\"... ILIKE '%{value}%'\"`` builds; nothing\n"
                        "    here ever reaches a database connection.\n"
                        "    \"\"\"\n"
                        "    return template.format(value=filter_value)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dao-unsafe-read",
                    text=(
                        "Feed that template the classic payload '; DROP "
                        "TABLE posts; -- and the rendered text stops "
                        "being one query: the quote closes the literal, "
                        "DROP TABLE becomes a second statement, the "
                        "comment marker eats the trailing quote. The "
                        "demo's default input IS that payload — the safe "
                        "card shows it really executed as data (it "
                        "matches zero rows, because no title literally "
                        "contains it), while the unsafe card shows the "
                        "spliced text with executed: false. One input, "
                        "two meanings; the difference is only WHERE the "
                        "value entered the statement."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dao-honest-limits",
                    text=(
                        "Two honest footnotes the demo carries with it. "
                        "First, parameterization stops SQL injection, "
                        "not LIKE semantics: % and _ inside the VALUE "
                        "still act as wildcards in the pattern, so a "
                        "caller can widen a match — escape wildcards or "
                        "use equality when that matters. Second, "
                        "parameterized does not mean fast-by-default: "
                        "a fresh statement text each request forfeits "
                        "prepared-statement reuse, which is one more "
                        "reason SQL lives in a repository, where the "
                        "same handful of constant texts run forever."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dao-demo-pitch",
                    text=(
                        "Try it: change the filter input and watch the "
                        "safe side stay boring — the wildest input is "
                        "just a pattern that matches fewer or more "
                        "titles — while the rendered card changes shape "
                        "with every quote you add."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="db:sql-safety",
                    title="The SQL safety probe",
                    description=(
                        "GET /api/demo/db/sql-safety?filter=… runs the "
                        "SAME title filter two ways. The safe card is "
                        "REAL: the parameterized query executed against "
                        "the live posts with your input as the :pattern "
                        "bind parameter — the default input is '; DROP "
                        "TABLE posts; --, and it matches zero rows as "
                        "pure data. The unsafe card renders the "
                        "string-interpolated statement the naive code "
                        "would have produced (shown and explained, "
                        "executed: false). Plus the honest boundary: "
                        "bind parameters stop injection, not "
                        "LIKE-wildcard semantics."
                    ),
                ),
            ],
        ),
        # ── 3. Transactions ────────────────────────────────────────────────
        Section(
            id="transactions",
            title="Transactions",
            lead="This section carries the topic's second demo — the migration rehearsal.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="tx-pitch",
                    text=(
                        "A transaction is the database's unit of trust: "
                        "everything inside it commits together or "
                        "vanishes together — the ACID A and I doing "
                        "their quiet work. In SQLAlchemy the shape is a "
                        "context manager: engine.begin() opens a "
                        "connection AND its transaction, and the block "
                        "leaving normally commits while any exception "
                        "rolls back. The property is oldest news in "
                        "database theory and still the one developers "
                        "trust least, so this topic's second demo proves "
                        "it live, with DDL — the statement kind people "
                        "assume is special."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tx-ddl",
                    text=(
                        "PostgreSQL is nearly alone among production "
                        "databases in taking CREATE TABLE and ALTER "
                        "TABLE transactionally: a failed migration "
                        "leaves NO half-applied schema. Alembic leans on "
                        "exactly this (its env.py wraps each migration "
                        "in begin), and the demo rehearses the story "
                        "with a scratch sequence whose third step "
                        "deliberately fails:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tx-failing-steps",
                    language="py",
                    caption="Three steps; the third is the classic NOT-NULL-without-default trap.",
                    source="server/guide/data/db/repository.py",
                    snippet=(
                        "FAILING_STEPS: Final = (\n"
                        "    (\n"
                        "        \"create the scratch table\",\n"
                        "        f\"CREATE TABLE {SCRATCH_TABLE} (id bigint PRIMARY KEY, label text NOT NULL)\",\n"
                        "    ),\n"
                        "    (\"seed one row\", f\"INSERT INTO {SCRATCH_TABLE} (id, label) VALUES (1, 'seeded by step two')\"),\n"
                        "    (\n"
                        "        \"add a NOT NULL column to a non-empty table — fails\",\n"
                        "        f\"ALTER TABLE {SCRATCH_TABLE} ADD COLUMN size integer NOT NULL\",\n"
                        "    ),\n"
                        ")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tx-failing-read",
                    text=(
                        "Step three trips PostgreSQL's guard rail — a "
                        "NOT NULL column with no default cannot be added "
                        "to a table that already has rows, because the "
                        "existing row would need a value that does not "
                        "exist. The error is real and the demo surfaces "
                        "it verbatim; what matters is what happens NEXT. "
                        "The rehearsal runs the steps inside one "
                        "engine.begin() block and simply catches the "
                        "failure:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="tx-rehearse",
                    language="py",
                    caption="One transaction, N steps: the DBAPIError rolls the whole block back.",
                    source="server/guide/data/db/repository.py",
                    snippet=(
                        "        failure: str | None = None\n"
                        "        applied = 0\n"
                        "        try:\n"
                        "            async with self._engine.begin() as connection:\n"
                        "                for _, sql in steps:\n"
                        "                    await connection.execute(sa.text(sql))\n"
                        "                    applied += 1\n"
                        "        except sa.exc.DBAPIError as exc:\n"
                        "            failure = str(exc.orig) if exc.orig is not None else str(exc)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tx-proof",
                    text=(
                        "After the catch, the demo verifies with a fresh "
                        "connection: to_regclass finds no scratch table, "
                        "no row, nothing — CREATE TABLE rolled back with "
                        "the failed ALTER, which is transactional DDL "
                        "doing precisely what 'migrations run at app "
                        "startup' (topic 16's strategy) depends on. The "
                        "second half of the payload runs the FIXED "
                        "sequence (the same ALTER with DEFAULT 0, plus a "
                        "backfill) and commits: the verification now "
                        "finds the table with its row. Same code path, "
                        "two endings, and the demo drops the scratch "
                        "table afterwards so it can repeat from zero."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="tx-discipline",
                    text=(
                        "The working disciplines that fall out of this "
                        "mechanism are few and strict:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="tx-discipline-list",
                    ordered=False,
                    items=[
                        "Short transactions — hold a transaction across "
                        "I/O you control (statements), not calls you "
                        "don't (external APIs, user think-time).",
                        "Fail whole, not half — when a multi-step change "
                        "breaks midway, ROLL BACK; never 'finish the "
                        "rest and hope'.",
                        "Nest by composition — SQLAlchemy's begin_nested "
                        "(SAVEPOINT) marks inner units that can fail "
                        "without dooming the outer work.",
                        "Test the rollback — the suite asserts the "
                        "absence (no table) as firmly as the presence; "
                        "a rollback you never exercised is a rumor.",
                    ],
                ),
                DemoBlock(
                    kind="demo",
                    id="db:migrations",
                    title="The migration rehearsal",
                    description=(
                        "GET /api/demo/db/migrations runs a scratch "
                        "migration sequence inside one transaction, "
                        "twice. The failing run applies two steps, then "
                        "PostgreSQL refuses the NOT NULL ALTER — and the "
                        "rollback takes the CREATE TABLE and INSERT with "
                        "it (verification: the table does not exist). "
                        "The succeeding run adds the column WITH a "
                        "DEFAULT, backfills, commits — verification "
                        "finds the table and its row. Every step's SQL "
                        "and outcome, the real error text, and both "
                        "verifications ride in the payload; the demo "
                        "cleans up its scratch table so it can repeat."
                    ),
                ),
            ],
        ),
        # ── 4. ORM comparison ──────────────────────────────────────────────
        Section(
            id="orm-comparison",
            title="ORM comparison: what Core gives, what an ORM adds",
            blocks=[
                TextBlock(
                    kind="text",
                    id="orm-pitch",
                    text=(
                        "You have now seen every primitive an ORM would "
                        "wrap: tables as metadata, queries as "
                        "expressions, changes inside transactions. So "
                        "what would SQLAlchemy's ORM layer actually add "
                        "on top of the Core this topic uses? The honest "
                        "inventory:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="orm-adds-list",
                    ordered=False,
                    items=[
                        "Mapped classes — a Post dataclass-like type per "
                        "table; rows arrive as objects instead of "
                        "mappings you reshape by hand.",
                        "The Session — a unit of work: it tracks every "
                        "object you touched and flushes exactly the "
                        "changed columns as one transaction.",
                        "Identity map — one row loaded twice in a "
                        "session is ONE object; accidental duplicates "
                        "become impossible within a unit of work.",
                        "Relationships — post.author traverses the "
                        "foreign key as an attribute, with lazy/eager "
                        "loading strategies behind it.",
                        "Inheritance and polymorphism — entity "
                        "hierarchies over single tables, when your "
                        "model genuinely has them.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="orm-costs",
                    text=(
                        "And the costs, equally honest: a session is "
                        "stateful machinery you must keep straight "
                        "(topic 18 spends a whole section on its "
                        "lifecycle); relationship loading hides queries "
                        "— the N+1 problem is an ORM-native disease; "
                        "generated SQL drifts from what you meant as "
                        "queries grow complex; and every ORM abstraction "
                        "leaks exactly when the database does something "
                        "interesting (locking, partial indexes, "
                        "tsvector). The guide's position for THIS topic: "
                        "Core is the layer where the SQL you send is "
                        "still the SQL you read. Here is the seed's "
                        "insert loop, in Core, from the repository you "
                        "have been quoting all topic:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="orm-core-insert",
                    language="py",
                    caption="Core in the repository: explicit inserts over the metadata tables.",
                    source="server/guide/data/db/repository.py",
                    snippet=(
                        "                for post in SEED_POSTS:\n"
                        "                    await connection.execute(\n"
                        "                        sa.insert(posts).values(updated_at=post[\"created_at\"], **post)\n"
                        "                    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="orm-verdict",
                    text=(
                        "sa.insert(posts) is a Core expression: the "
                        "table object carries the column list, values "
                        "fill them, the engine renders dialect-correct "
                        "SQL for asyncpg. An ORM would express the same "
                        "intent as session.add(Post(**post)) and flush "
                        "later — terser, and one step further from the "
                        "wire. Neither is wrong; they are different "
                        "points on the control/convenience dial, and "
                        "topic 18 turns that dial fully so you can feel "
                        "the session, the identity map, N+1, and the "
                        "eager-loading cures on this same schema. What "
                        "STAYS constant at every dial position is "
                        "everything this topic taught: the repository "
                        "seam, bind parameters, transactions, and plans "
                        "you can read."
                    ),
                ),
            ],
        ),
        # ── 5. SQL by hand: CTEs and window functions ──────────────────────
        Section(
            id="sql-by-hand",
            title="SQL by hand: CTEs and window functions",
            lead="This section carries the topic's third demo — the SQL lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="hand-pitch",
                    text=(
                        "Some questions are not 'rows where…' but shapes "
                        "ACROSS rows: rank each author's posts, accumulate "
                        "a timeline, walk a chain. The two SQL features "
                        "built for those shapes are common table "
                        "expressions and window functions, and they are "
                        "worth writing by hand at least once a year even "
                        "in an ORM shop — they move per-row Python loops "
                        "into one statement the database executes "
                        "natively. A CTE (WITH name AS (…)) names a "
                        "subquery so a query reads in stages; a window "
                        "function computes OVER a window of rows while "
                        "every row stays in the output. The lab's second "
                        "exhibit shows both in one statement — a running "
                        "total of comments across the whole post "
                        "timeline:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="hand-window",
                    language="sql",
                    caption="The running-total exhibit: SUM and AVG over an ordered frame, one pass.",
                    source="server/guide/data/db/repository.py",
                    snippet=(
                        "SELECT p.id AS post_id,\n"
                        "       p.title AS title,\n"
                        "       p.created_at AS created_at,\n"
                        "       COUNT(c.id) AS comments,\n"
                        "       SUM(COUNT(c.id)) OVER (\n"
                        "           ORDER BY p.created_at\n"
                        "           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW\n"
                        "       ) AS running_comments,\n"
                        "       ROUND(\n"
                        "           AVG(COUNT(c.id)) OVER (\n"
                        "               ORDER BY p.created_at\n"
                        "               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW\n"
                        "           ), 2\n"
                        "       ) AS avg_comments_so_far\n"
                        "FROM posts AS p\n"
                        "LEFT JOIN comments AS c ON c.post_id = p.id\n"
                        "GROUP BY p.id, p.title, p.created_at\n"
                        "ORDER BY p.created_at"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="hand-window-read",
                    text=(
                        "Read the frame clause as the definition: for "
                        "each row, the window is every row from the "
                        "start of the ordering up to and including it, "
                        "and SUM aggregates THAT — so the column "
                        "accumulates down the result. Without the "
                        "window, a running total needs a correlated "
                        "self-join or a Python loop; with it, one scan. "
                        "The same syntax family gives you moving "
                        "averages (BETWEEN 6 PRECEDING AND CURRENT ROW), "
                        "month-over-month deltas (LAG), and share-of-"
                        "total (SUM OVER the whole partition). The "
                        "lab's first exhibit pairs a CTE with TWO "
                        "windows: a per-post comment count aggregated "
                        "once in the CTE, then ROW_NUMBER() OVER "
                        "(PARTITION BY author ORDER BY created_at) "
                        "numbering each author's posts oldest-first and "
                        "RANK() ordering everyone globally by comments."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="hand-recursive-pitch",
                    text=(
                        "The third shape is RECURSION. WITH RECURSIVE "
                        "lets a CTE refer to ITSELF: an anchor query "
                        "seeds it, and a recursive term keeps consuming "
                        "the previous round's rows until it produces "
                        "nothing new. The lab's thread exhibit walks "
                        "one post's comment thread link by link — "
                        "anchor on the thread's first comment, then "
                        "each hop joins LATERAL to the NEXT comment by "
                        "id, with depth counting the hops:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="hand-thread",
                    language="sql",
                    caption="The recursive exhibit: an anchor, a UNION ALL step, and a depth counter.",
                    source="server/guide/data/db/repository.py",
                    snippet=(
                        "WITH RECURSIVE thread AS (\n"
                        "    SELECT c.id AS id, c.author AS author, c.body AS body, 1 AS depth\n"
                        "    FROM comments AS c\n"
                        "    WHERE c.post_id = :post_id\n"
                        "      AND c.id = (SELECT MIN(c2.id) FROM comments AS c2\n"
                        "                  WHERE c2.post_id = :post_id)\n"
                        "    UNION ALL\n"
                        "    SELECT nxt.id, nxt.author, nxt.body, thread.depth + 1\n"
                        "    FROM thread\n"
                        "    JOIN LATERAL (\n"
                        "        SELECT c3.id, c3.author, c3.body\n"
                        "        FROM comments AS c3\n"
                        "        WHERE c3.post_id = :post_id AND c3.id > thread.id\n"
                        "        ORDER BY c3.id\n"
                        "        LIMIT 1\n"
                        "    ) AS nxt ON TRUE\n"
                        ")\n"
                        "SELECT depth, id, author, body\n"
                        "FROM thread\n"
                        "ORDER BY depth"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="hand-recursive-read",
                    text=(
                        "The anchor is the WHERE id = (SELECT MIN …) row; "
                        "the recursive term reads the previous round "
                        "from thread and produces each next comment "
                        "(LATERAL + ORDER BY + LIMIT 1 = 'the next "
                        "one'), depth incrementing per hop; UNION ALL "
                        "accumulates; the walk ends when there is no "
                        "next comment. Swap the next-by-id rule for "
                        "parent_id = id and this is a comment tree or "
                        "an org chart — the same five lines. Two "
                        "safety habits with recursion: UNION ALL (UNION "
                        "dedupes every round and costs accordingly), "
                        "and a depth guard in real systems (WHERE "
                        "depth < 50) so a cycle in the data cannot "
                        "walk forever."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="db:sql-lab",
                    title="The SQL lab",
                    description=(
                        "GET /api/demo/db/sql-lab?exhibit=ranked|window|"
                        "thread executes one exhibit against the seeded "
                        "posts and comments and shows the SQL verbatim "
                        "with its real results: ranked (per-author "
                        "ROW_NUMBER + global RANK by comments), window "
                        "(running total and running average across the "
                        "timeline — the last row's total equals the "
                        "table's comment count), and thread (a "
                        "recursive CTE walking the most-commented "
                        "post's five comments, depth 1..5, via a "
                        "LATERAL next-by-id hop)."
                    ),
                ),
            ],
        ),
        # ── 6. EXPLAIN ANALYZE ─────────────────────────────────────────────
        Section(
            id="explain-analyze",
            title="EXPLAIN ANALYZE: reading what the planner did",
            blocks=[
                TextBlock(
                    kind="text",
                    id="explain-pitch",
                    text=(
                        "Every statement you send is a PLAN in disguise: "
                        "PostgreSQL's planner picks scan strategies, join "
                        "orders, and algorithms from statistics it keeps "
                        "about your tables. EXPLAIN shows the plan; "
                        "EXPLAIN ANALYZE EXECUTES the statement and shows "
                        "the plan annotated with real timings and row "
                        "counts — the difference between a guess and a "
                        "measurement. This is the skill that turns 'the "
                        "query is slow' into a sentence with a subject: "
                        "which node, how many rows, how long."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="explain-anatomy",
                    text=(
                        "A plan reads outside-in as a tree: each "
                        "indented node feeds the one above it, and the "
                        "reading discipline is short:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="explain-anatomy-list",
                    ordered=True,
                    items=[
                        "Find the slowest node — every line carries "
                        "(actual time=start..end rows=N loops=M); the "
                        "biggest end time is your suspect.",
                        "Check rows against expectations — a node that "
                        "returns 100k rows the planner guessed would "
                        "return 10 is a statistics problem (ANALYZE the "
                        "table).",
                        "Name the scan kind — Seq Scan on a big table "
                        "under an equality filter means a missing index; "
                        "Bitmap Index Scan means an index fed a heap "
                        "fetch; Index Scan means direct index walking.",
                        "Watch the sort — 'Sort Method: external merge' "
                        "spilled to disk; work_mem or a better index is "
                        "the fix.",
                        "Read loops carefully — a nested loop's inner "
                        "time is PER LOOP; multiply before you panic.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="explain-real-plans",
                    text=(
                        "The search demo captures both of this topic's "
                        "plans live, and they are worth reading here in "
                        "full. First the no-index shape — the planner "
                        "has no tsvector column, so it recomputes one "
                        "for EVERY row it scans (this is EXACTLY what "
                        "the demo runs; the filter line is the tell):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="explain-naive-output",
                    language="text",
                    caption="Real EXPLAIN ANALYZE output from the live dev PostgreSQL (naive, no index).",
                    source=None,
                    snippet=(
                        "Seq Scan on posts p (actual time=0.061..0.323 rows=3 loops=1)\n"
                        "  Filter: (to_tsvector('english'::regconfig, ((COALESCE(title, ''::text) || ' '::text) || COALESCE(body, ''::text))) @@ '''error'' & ''envelop'''::tsquery)\n"
                        "  Rows Removed by Filter: 9\n"
                        "Planning Time: 0.018 ms\n"
                        "Execution Time: 0.326 ms"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="explain-indexed-pitch",
                    text=(
                        "And the indexed shape over migration 0002's "
                        "column — a bitmap index scan feeding a heap "
                        "fetch, the stems matched inside the index, "
                        "the filter gone (captured with seq scans "
                        "disabled for the session, because on twelve "
                        "rows the planner honestly prefers the scan — "
                        "at real table sizes it flips on its own):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="explain-indexed-output",
                    language="text",
                    caption="The same query through the GIN index: bitmap scan, no per-row stemming.",
                    source=None,
                    snippet=(
                        "Bitmap Heap Scan on posts p (actual time=0.018..0.020 rows=3 loops=1)\n"
                        "  Recheck Cond: (search_vector @@ '''error'' & ''envelop'''::tsquery)\n"
                        "  Heap Blocks: exact=2\n"
                        "  ->  Bitmap Index Scan on ix_posts_search_vector (actual time=0.014..0.014 rows=7 loops=1)\n"
                        "        Index Cond: (search_vector @@ '''error'' & ''envelop'''::tsquery)\n"
                        "Planning Time: 0.033 ms"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="explain-coda",
                    text=(
                        "Same question, two plans, 10x apart on twelve "
                        "rows and far more at scale — and every claim "
                        "above is visible in the annotations: rows=3 "
                        "kept, 9 removed, the recheck condition named. "
                        "Two habits close the section: always ANALYZE "
                        "(the keyword, or EXPLAIN without it) on data "
                        "shaped like production — tiny dev tables make "
                        "planners lie politely — and never index on "
                        "theory: write the query, read its plan, add "
                        "the index the plan asks for, read the plan "
                        "again. The next section does exactly that, "
                        "for search."
                    ),
                ),
            ],
        ),
        # ── 7. Full-text search ────────────────────────────────────────────
        Section(
            id="full-text-search",
            title="Full-text search with tsvector",
            lead="This section carries the topic's fourth demo — the search lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="fts-pitch",
                    text=(
                        "LIKE '%word%' finds substrings; search finds "
                        "MEANING. PostgreSQL's full-text stack maps "
                        "every document to a tsvector — a sorted set of "
                        "LEXEMES (stemmed words: 'errors' and 'error' "
                        "both fold to 'error', 'envelope' to 'envelop') "
                        "with positions — and maps user input to a "
                        "tsquery of AND/OR'd lexemes. The @@ operator "
                        "matches query against vector, and that is the "
                        "whole engine. The guide's migration 0002 "
                        "(this topic's own change) adds the storage: a "
                        "GENERATED column, derived from title and body "
                        "on every write so it can never drift from its "
                        "row, plus the GIN index that makes @@ an "
                        "index operation:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="fts-migration",
                    language="py",
                    caption="Migration 0002: a stored generated column and a GIN index over it.",
                    source="server/alembic/versions/0002_posts_search_vector.py",
                    snippet=(
                        "def upgrade() -> None:\n"
                        "    op.add_column(\n"
                        "        \"posts\",\n"
                        "        sa.Column(\n"
                        "            \"search_vector\",\n"
                        "            postgresql.TSVECTOR(),\n"
                        "            sa.Computed(SEARCH_VECTOR_EXPRESSION, persisted=True),\n"
                        "            nullable=False,\n"
                        "        ),\n"
                        "    )\n"
                        "    op.create_index(\n"
                        "        \"ix_posts_search_vector\",\n"
                        "        \"posts\",\n"
                        "        [\"search_vector\"],\n"
                        "        unique=False,\n"
                        "        postgresql_using=\"gin\",\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="fts-migration-read",
                    text=(
                        "Every design choice there is a lesson: STORED "
                        "means the vector is materialized in the row "
                        "(the alternative, an index over an expression, "
                        "recomputes nothing but can only serve the "
                        "index); GENERATED ALWAYS means no writer can "
                        "sneak a hand-maintained vector past the "
                        "expression; the expression concatenates title "
                        "and body with coalesce so NULLs cannot blank "
                        "the vector; and GIN — the inverted index — "
                        "is what turns section 6's seq-scan-plus-"
                        "recompute into the bitmap scan. The demo's "
                        "query then does the asking:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="fts-search-sql",
                    language="sql",
                    caption="The search demo's ranked query: match, rank, headline.",
                    source="server/guide/data/db/repository.py",
                    snippet=(
                        "SELECT p.id, p.slug, p.title,\n"
                        "       ts_rank(p.search_vector, query) AS rank,\n"
                        "       ts_headline('english', p.title || ': ' || p.body, query,\n"
                        "                   'StartSel=<b>, StopSel=</b>, MaxFragments=2') AS headline\n"
                        "FROM posts AS p, plainto_tsquery('english', :query) AS query\n"
                        "WHERE p.search_vector @@ query\n"
                        "ORDER BY rank DESC, p.id"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="fts-search-read",
                    text=(
                        "Three functions carry the weight. "
                        "plainto_tsquery parses free user text safely — "
                        "quotes and semicolons dissolve into lexemes, "
                        "AND-ed together (to_tsquery is the power-user "
                        "form that accepts explicit & | ! operators; "
                        "websearch_to_tsquery accepts quoted phrases). "
                        "ts_rank scores each match so 'error envelope' "
                        "puts the post about the error envelope above "
                        "one that merely mentions errors — the demo "
                        "shows real scores an order of magnitude apart. "
                        "ts_headline renders the match context with "
                        "markers around the hits, running only on the "
                        "rows that matched. And the FROM-clause trick "
                        "(…, plainto_tsquery(:query) AS query) names "
                        "the parsed query once and reuses it in all "
                        "three places — still one bind parameter, "
                        "still injection-proof."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="db:search",
                    title="The search lab",
                    description=(
                        "GET /api/demo/db/search?q=… runs the ranked "
                        "full-text query over the live posts: the "
                        "parsed tsquery (watch stemming — 'error "
                        "envelope' becomes 'error' & 'envelop'), "
                        "ranked matches with ts_rank scores and "
                        "ts_headline context, and BOTH EXPLAIN plans "
                        "captured live — the GIN bitmap index scan vs "
                        "the no-index seq scan that recomputes the "
                        "vector per row. Try q=error, q=errors (same "
                        "stem), a quoted phrase, or gibberish (zero "
                        "matches is data, not an error)."
                    ),
                ),
            ],
        ),
        # ── 8. Isolation, locking, and races ───────────────────────────────
        Section(
            id="isolation-locking-races",
            title="Isolation, locking, and races",
            lead="This section carries the topic's fifth demo — the race lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="iso-pitch",
                    text=(
                        "Transactions promise isolation, but isolation "
                        "is a DIAL. PostgreSQL's levels, from the "
                        "default up:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="iso-levels",
                    ordered=False,
                    items=[
                        "READ COMMITTED (the default) — every statement "
                        "sees rows committed before IT started: fresh "
                        "per statement, but two statements in one "
                        "transaction can see different worlds.",
                        "REPEATABLE READ — one snapshot per "
                        "transaction; a concurrent change mid-"
                        "transaction stays invisible, and conflicting "
                        "writes abort with 'could not serialize'.",
                        "SERIALIZABLE — the planner proves the "
                        "transaction's reads and writes could have run "
                        "serially; otherwise it aborts and you retry.",
                        "The forgotten baseline — autocommit (no "
                        "transaction) makes every statement its own "
                        "world; read-modify-write logic cannot live "
                        "there at all.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="iso-lost-update",
                    text=(
                        "Here is the classic failure under READ "
                        "COMMITTED, the one this topic's demo "
                        "choreographs for real: two transactions both "
                        "COUNT a post's comments (both read 2), both "
                        "insert 'comment number 3', both commit. No "
                        "error, no warning — and the comment number 4 "
                        "that should have existed was never assigned. "
                        "The lost update is invisible precisely because "
                        "every individual statement succeeded; the "
                        "bug is in the GAP between two statements. "
                        "The demo's unlocked run IS this code, "
                        "statement by statement:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="iso-unlocked",
                    language="py",
                    caption="The unlocked race: both counts complete before either insert starts.",
                    source="server/guide/data/db/repository.py",
                    snippet=(
                        "        async with _two_connections(self._engine) as (conn_a, conn_b):\n"
                        "            tx_a = await conn_a.begin()\n"
                        "            tx_b = await conn_b.begin()\n"
                        "            try:\n"
                        "                count_a = await self._comment_count(conn_a, post_id)\n"
                        "                count_b = await self._comment_count(conn_b, post_id)\n"
                        "                await self._insert_slot(conn_a, post_id, RACE_AUTHOR_A, count_a + 1, \"unlocked\")\n"
                        "                await self._insert_slot(conn_b, post_id, RACE_AUTHOR_B, count_b + 1, \"unlocked\")\n"
                        "                await tx_a.commit()\n"
                        "                await tx_b.commit()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="iso-determinism",
                    text=(
                        "Note what makes it deterministic — the "
                        "demo-ware discipline: every statement is "
                        "awaited in a fixed order (both counts settle "
                        "before either insert begins), so the lost "
                        "update happens EVERY run, not on Tuesdays. "
                        "Real races are rare exactly because they are "
                        "random; a demo that taught probabilistically "
                        "would teach nothing. The fix comes in two "
                        "flavors, and the demo runs the first: "
                        "SELECT … FOR UPDATE takes ROW LOCKS, so the "
                        "second transaction BLOCKS at its lock request "
                        "until the first commits — its count then runs "
                        "after the first insert is visible, and every "
                        "number is really assigned. The demo's locked "
                        "run even awaits the blocked lock as a task, "
                        "the way a real connection pool would."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="iso-choosing",
                    text=(
                        "Choosing between the fixes is an engineering "
                        "judgment, not a style pick:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="iso-choosing-list",
                    ordered=False,
                    items=[
                        "Pessimistic (FOR UPDATE / SELECT FOR NO KEY "
                        "UPDATE) — lock first, wait, then compute: "
                        "right for short transactions under real "
                        "contention; throughput pays for the waiting.",
                        "Optimistic (version column or REPEATABLE READ "
                        "retry) — compute, then verify nothing changed; "
                        "right when contention is rare and retrying is "
                        "cheap (the webhooks topic's retry engine is "
                        "the shape).",
                        "Atomic single statement — UPDATE … SET n = n + "
                        "1 or INSERT … SELECT WHERE NOT EXISTS: no gap "
                        "exists at all when read and write are one "
                        "statement; always the first thing to reach "
                        "for.",
                        "Advisory locks — pg_advisory_xact_lock for "
                        "application-level mutexes (one backfill "
                        "running at a time); rarely right, unbeatable "
                        "when they are.",
                    ],
                ),
                DemoBlock(
                    kind="demo",
                    id="db:race",
                    title="The race lab",
                    description=(
                        "GET /api/demo/db/race choreographs two "
                        "concurrent transactions over the same post's "
                        "comment count, twice — deterministically "
                        "(ordered awaits, no sleeps). The unlocked run "
                        "loses an update: both transactions read the "
                        "same count and both write 'slot #3' (the "
                        "timeline shows every step). The locked run "
                        "takes SELECT … FOR UPDATE first: B blocks "
                        "until A commits, then computes from a fresh "
                        "read — slots #3 and #4 both exist. Both final "
                        "states side by side, with verdicts computed "
                        "from the evidence."
                    ),
                ),
            ],
        ),
        # ── 9. Audit in the same transaction ───────────────────────────────
        Section(
            id="audit-in-the-transaction",
            title="Audit in the same transaction",
            lead="This section carries the topic's sixth demo — the audit proof.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="audit-pitch",
                    text=(
                        "Topic 16 designed the audit-logging pattern and "
                        "proved it in tests; with transactions now in "
                        "your hands, the pattern's load-bearing line "
                        "deserves its live proof. An audit row written "
                        "on the change's OWN connection is not 'nearby' "
                        "— it is IN the transaction: one commit, one "
                        "rollback, no change without its trail. The "
                        "demo runs both halves against a real post, "
                        "and the committed half is three statements:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="audit-scenario",
                    language="py",
                    caption="Change, audit, commit — one engine.begin() block, one fate.",
                    source="server/guide/data/db/repository.py",
                    snippet=(
                        "            # The committed half: change + audit row, one transaction.\n"
                        "            status_after = \"published\" if status_before == \"draft\" else \"draft\"\n"
                        "            change_note = f\"status: {status_before} -> {status_after}\"\n"
                        "            async with self._engine.begin() as connection:\n"
                        "                await connection.execute(\n"
                        "                    sa.update(posts).where(posts.c.id == post_id).values(status=status_after)\n"
                        "                )\n"
                        "                await record_audit(\n"
                        "                    connection,\n"
                        "                    AuditEvent(\n"
                        "                        actor=\"demo:db-audit\",\n"
                        "                        action=\"update\",\n"
                        "                        table_name=\"posts\",\n"
                        "                        row_pk=str(post_id),\n"
                        "                        changes={\"status\": change_note},\n"
                        "                    ),\n"
                        "                )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="audit-read",
                    text=(
                        "record_audit is topic 16's writer, untouched — "
                        "it takes the CALLER's connection and INSERTs "
                        "the event's values into audit_log, so the "
                        "UPDATE and the audit row commit in the same "
                        "engine.begin() block. The rolled-back half "
                        "then runs the same shape with a poisoned "
                        "third step: the audit INSERT succeeds, an "
                        "UPDATE to a 200-character title trips the "
                        "ck_posts_title_length CHECK, and the block "
                        "exits by exception — both rows vanish. The "
                        "proof is arithmetic, not assertion: the demo "
                        "counts audit rows for the post BEFORE the "
                        "attempt and AFTER, and the difference is "
                        "zero."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="audit-history",
                    text=(
                        "Watch the payload's history card: it lists "
                        "every audit row the post has ever collected, "
                        "and it grows by exactly one row per run — "
                        "this demo audits itself. That is the "
                        "pattern's quiet superpower: because the trail "
                        "rides the transaction, it is always exactly "
                        "as complete as the data it describes, and "
                        "queries by row_pk, actor, or occurred_at are "
                        "one index away when the volume ever demands "
                        "one."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="db:audit",
                    title="The audit proof",
                    description=(
                        "GET /api/demo/db/audit runs both halves live "
                        "on a seeded post: the committed half flips "
                        "draft/published and reads its audit row back "
                        "from audit_log (change visible, row present); "
                        "the rolled-back half writes an audit row and "
                        "then trips the title CHECK in the SAME "
                        "transaction — audit rows added: 0, change "
                        "visible: false, the real constraint error "
                        "included. The post's full audit history grows "
                        "by one row per run."
                    ),
                ),
            ],
        ),
        # ── 10. Terminal companion ─────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="Nine real stops: all six demos, the topic itself, the migration bookkeeping, the curriculum.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-honesty",
                    text=(
                        "Everything in this topic runs against the live "
                        "stack, so the tour is unusually direct: stops "
                        "1–6 hit the six demos in curriculum order with "
                        "meaningful inputs (watch the injection payload "
                        "come back as data, the rollback find no table, "
                        "the recursive CTE count depth, the plans "
                        "disagree, the race lose and then keep an "
                        "update, the audit add zero rows); stop 7 reads "
                        "the topic; stop 8 checks the migration "
                        "bookkeeping this topic extended; stop 9 "
                        "watches the curriculum grow. If the server "
                        "was restarted, the first stop also seeds the "
                        "database for you."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-safety",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the safety probe: an injection payload, executed as DATA\n"
                        "curl -s 'localhost:8000/api/demo/db/sql-safety' | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "print(\"safe rows:\", b[\"safe\"][\"rowCount\"], \"· bind:\", b[\"safe\"][\"parameterValue\"])\n"
                        "print(\"unsafe executed:\", b[\"unsafe\"][\"executed\"])\n"
                        "print(b[\"unsafe\"][\"renderedSql\"][:90], \"…\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-migrations",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the rehearsal: the failed run rolls back CREATE TABLE itself\n"
                        "curl -s localhost:8000/api/demo/db/migrations | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "f, s = b[\"failing\"], b[\"succeeding\"]\n"
                        "print(\"failing committed:\", f[\"committed\"], \"· table exists:\", f[\"tableExistsAfter\"])\n"
                        "print(\"error:\", f[\"failure\"][:70])\n"
                        "print(\"succeeding committed:\", s[\"committed\"], \"· rows:\", s[\"rowCountAfter\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-lab",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — the SQL lab: all three exhibits (a recursive thread walk)\n"
                        "for exhibit in ranked window thread; do\n"
                        "  curl -s \"localhost:8000/api/demo/db/sql-lab?exhibit=$exhibit\" | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "print(b[\"exhibit\"], \"· rows:\", b[\"rowCount\"])\n"
                        "print(\"  first:\", b[\"rows\"][0] if b[\"rows\"] else None)'\n"
                        "done"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-search",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — search: stemming, ranks, and the plan that uses the GIN index\n"
                        "curl -s 'localhost:8000/api/demo/db/search?q=error%20envelope' | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "print(\"parsed:\", b[\"parsedQuery\"])\n"
                        "for m in b[\"matches\"]:\n"
                        "    print(f\"  {m[\\\"rank\\\"]:.4f}\", m[\"title\"])\n"
                        "print(\"indexed:\", b[\"indexedPlan\"][0])\n"
                        "print(\"naive:  \", b[\"naivePlan\"][0])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-race",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the race: lost update vs FOR UPDATE, verdicts from evidence\n"
                        "curl -s localhost:8000/api/demo/db/race | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "print(\"baseline comments:\", b[\"baselineComments\"])\n"
                        "for run in (\"unlocked\", \"locked\"):\n"
                        "    print(run, \"->\", [s[\"body\"] for s in b[run][\"finalSlots\"]])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-audit",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — the audit proof: zero rows added by the rolled-back half\n"
                        "curl -s localhost:8000/api/demo/db/audit | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "c, r = b[\"committed\"], b[\"rolledBack\"]\n"
                        "print(\"committed:\", c[\"statusBefore\"], \"->\", c[\"statusAfter\"],\n"
                        "      \"· audit row id\", c[\"auditRow\"][\"id\"])\n"
                        "print(\"rolled back added:\", r[\"auditRowsAdded\"], \"· visible:\", r[\"changeVisible\"])\n"
                        "print(\"history rows:\", b[\"historyCount\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-topic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 7 — the topic itself: ten sections, six demos inline\n"
                        "curl -s localhost:8000/api/content/databases-sql | python3 -c '\n"
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
                    id="terminal-alembic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 8 — this topic's migration, in the bookkeeping table and the schema\n"
                        "docker exec fastapi_developers_guide_postgres_dev \\\n"
                        "  psql -U postgres -d guide -c 'SELECT * FROM alembic_version;' \\\n"
                        "  -c '\\d posts' | grep -E 'search_vector|0002' "
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-curriculum",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 9 — seventeen topics now, and the Data group filling up\n"
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
                        "Stop 5 is the whole topic in one payload: the "
                        "same two transactions, run unlocked and then "
                        "locked, over the same row — the only variable "
                        "is whether anyone was allowed to compute while "
                        "the row was contested. Everything else you "
                        "toured (bind parameters, transactional DDL, "
                        "windows and recursion, plans, stems, the audit "
                        "trail) exists to make that payload boring in "
                        "production. Topic 18 climbs the last layer — "
                        "the ORM session — over this same schema, and "
                        "finally meets the N+1 problem it spent this "
                        "topic preparing you to diagnose."
                    ),
                ),
            ],
        ),
    ],
)
