"""Topic 20 — Redis and the in-memory store (fifth and final topic of the
Data group).

Topics 16–19 built the data phase around access patterns: relational
PostgreSQL as the system of record, MongoDB as the optional document
citizen. This topic adds the third and last store this guide runs — the
in-memory one. It teaches what Redis actually is (a data-structures server,
not a cache with extra steps), the optional-service discipline applied a
third time (port and adapter, degrade to 503, boot without it), the five
core structures through redis-py's asyncio client (with the topic's demo
inline: a real playground over the live Redis), TTL and expiry as a
first-class storage property, pub/sub with a real round-trip, and the
when-a-second-store decision framework grounded in a repo that now runs
PostgreSQL, MongoDB, AND Redis — so every comparison is a decision this
codebase actually made.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="redis",
    title="Redis",
    subtitle=(
        "The in-memory data-structures server — five core structures, TTL "
        "expiry, pub/sub, and when a second (or third) store earns its place."
    ),
    group="data",
    order=20,
    sections=[
        # ── 1. What Redis is ────────────────────────────────────────────────
        Section(
            id="what-redis-is",
            title="What Redis is",
            blocks=[
                TextBlock(
                    kind="text",
                    id="what-pitch",
                    text=(
                        "Redis — REmote DIctionary Server — is not a database "
                        "with caching bolted on; it is a SERVER FOR DATA "
                        "STRUCTURES. You hand it a key and one of a handful "
                        "of structure types, and it owns that value in RAM: "
                        "reading, writing, and updating it with commands "
                        "whose cost is microseconds because nothing ever "
                        "touches a disk before the answer. The whole design "
                        "follows from one bet: memory is the primary "
                        "storage, and everything else — persistence, "
                        "replication, expiry — is a policy layered on top. "
                        "Where PostgreSQL answers 'what is true and "
                        "consistent?', Redis answers 'what is FAST?' — and "
                        "the structures it offers are the vocabulary every "
                        "answer is built from."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="what-structures-pitch",
                    text=(
                        "The command set is small enough to know cold, "
                        "because each structure comes with a tiny verb "
                        "family of its own — this topic's playground demo "
                        "walks all five against the live store:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="what-structures-list",
                    ordered=False,
                    items=[
                        "String — one value under one key (bytes or a "
                        "number), plus atomic arithmetic: INCR/DECR turn a "
                        "string into a lock-free counter.",
                        "Hash — field-value pairs under one key: a small "
                        "record (session, profile) read whole with HGETALL "
                        "or field-by-field with HGET.",
                        "List — an ordered sequence pushed at either end "
                        "(LPUSH/RPUSH), read in windows with LRANGE: feeds, "
                        "timelines, cheap queues.",
                        "Set — unique members with O(1) membership tests "
                        "(SISMEMBER) and set algebra (SINTER/SUNION): tags, "
                        "presence, dedup.",
                        "Sorted set — members carrying a score, kept in "
                        "score order by the structure itself: leaderboards, "
                        "priority queues, sliding windows.",
                        "Streams and pub/sub — append-only logs with "
                        "consumer groups, and fire-and-forget channels — "
                        "topic 22's material, previewed in section five.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="what-model",
                    text=(
                        "Under the hood the execution model is refreshingly "
                        "simple, and it explains most of Redis's famous "
                        "properties at once. A client opens one TCP "
                        "connection and speaks a tiny text protocol (RESP); "
                        "the server runs command EXECUTION essentially "
                        "single-threaded — one command at a time, to "
                        "completion — which is exactly why INCR needs no "
                        "lock: there is no concurrent execution to race. "
                        "Modern versions move network I/O onto helper "
                        "threads, but the atomicity story is unchanged, "
                        "and the practical consequences are the ones you "
                        "would guess: every individual command is fast "
                        "and safe, commands that would scan or sort large "
                        "ranges are dangerous (KEYS over a big keyspace "
                        "is the classic outage), and batch work belongs "
                        "in pipelines or the structure-native commands, "
                        "not in many round trips."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="what-memory",
                    text=(
                        "The honest costs come with the RAM bet. Capacity "
                        "is bounded by memory, which makes Redis the most "
                        "expensive bytes-per-dollar store in this stack; "
                        "persistence is a TUNABLE, not a guarantee — "
                        "snapshotting (RDB) and append-only files (AOF) "
                        "exist, but both trade durability windows against "
                        "throughput, and an in-memory store holding the "
                        "ONLY copy of a fact is a design smell. That is "
                        "why this guide's posture is strict: PostgreSQL "
                        "(topics 16–18) owns every durable fact, MongoDB "
                        "(topic 19) owns optional documents, and Redis "
                        "owns things whose VALUE is speed or expiry — "
                        "caches, counters, ephemeral state. Topic 21 puts "
                        "the first real cache on it; this topic builds the "
                        "wiring and the discipline."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="what-where",
                    text=(
                        "Redis has run in this guide's dev stack since "
                        "Phase 0 — the compose file's redis service was "
                        "there before any code talked to it, waiting under "
                        "the optional-service deal: present when up, "
                        "harmless when down. Nothing in topics 1–19 needed "
                        "it. Now something does, and the very first "
                        "engineering question is the one topic 19 asked "
                        "before it: what happens when it is DOWN?"
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
                        "Third store, same rule, and by now it is muscle "
                        "memory: the app must BOOT with Redis absent, serve "
                        "every feature that does not touch it, and degrade "
                        "only the redis demos — to the honest 503 envelope, "
                        "fast, never a hang, never a crash. The compose "
                        "stack deliberately wires no depends_on from the "
                        "server to redis; the healthcheck exists for humans, "
                        "not for orchestration. Everything in this section "
                        "is topic 19's mongo discipline reapplied — which "
                        "is exactly the point: a second store must not "
                        "change the SHAPE of anything, only add one more "
                        "optional citizen."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="optional-config-pitch",
                    text=(
                        "The wiring starts with one config rail, present "
                        "since Phase 0, defaulting to localhost so the app "
                        "boots anywhere with zero setup:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="optional-config",
                    language="py",
                    caption="The redis URL rail — same shape as database_url and mongo_url beside it.",
                    source="server/guide/core/config.py",
                    snippet=(
                        "    redis_url: str = \"redis://localhost:6379\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="optional-timeout-pitch",
                    text=(
                        "Degradation must also be FAST, and laziness is "
                        "what makes it cheap: ``Redis.from_url`` connects "
                        "to nothing, exactly like SQLAlchemy's engine "
                        "(topic 16) and motor's client (topic 19), so the "
                        "composition root builds the client unconditionally "
                        "and only the first COMMAND pays the connection. "
                        "When the URL points at nothing, redis-py's default "
                        "timeouts would let a request hang far too long — "
                        "the factory bounds both halves of every round-trip "
                        "to two seconds:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="optional-timeout",
                    language="py",
                    caption="Timeout policy lives in exactly one place: the client factory.",
                    source="server/guide/data/redis/client.py",
                    snippet=(
                        "SOCKET_CONNECT_TIMEOUT_S: Final = 2.0\n"
                        "# …\n"
                        "def create_redis_client(config: AppConfig) -> Redis:\n"
                        "    # …\n"
                        "    return Redis.from_url(\n"
                        "        config.redis_url,\n"
                        "        decode_responses=True,\n"
                        "        socket_connect_timeout=SOCKET_CONNECT_TIMEOUT_S,\n"
                        "        socket_timeout=SOCKET_TIMEOUT_S,\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="optional-decode",
                    text=(
                        "One factory decision carries more weight than its "
                        "one line suggests: ``decode_responses=True``. "
                        "Redis speaks bytes on the wire; without this flag "
                        "every GET, HGETALL, and pub/sub payload arrives as "
                        "``b\"...\"`` and the whole adapter decodes by hand. "
                        "With it, the CLIENT edge decodes once and every "
                        "reply is a ``str`` — the display rows and the wire "
                        "model speak strings only, and the boundary stays "
                        "where topic 2 taught defensive parsing to live. "
                        "The failure side is the one-contextmanager "
                        "discipline the other two stores use:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="optional-mapping",
                    language="py",
                    caption="Optional-service discipline, third store, same shape: RedisError becomes service_unavailable.",
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
                        "        # …\n"
                        "        raise AppError(\n"
                        "            FailureKind.SERVICE_UNAVAILABLE,\n"
                        "            \"Redis is unreachable or unusable — this demo runs real commands \"\n"
                        "            \"against the live store and refuses to serve stale facts.\",\n"
                        "        ) from exc"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="optional-proof-pitch",
                    text=(
                        "And the behavior is PROVEN, not asserted — by the "
                        "same unreachable-URL trick, never by stopping a "
                        "shared container. The suite wires an app whose "
                        "redis URL points at a port nothing will ever "
                        "answer on, then checks both halves of the "
                        "discipline in one test:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="optional-proof",
                    language="py",
                    caption="The boot-without-redis proof: everything else serves; only the demo degrades.",
                    source="server/tests/demo/test_redis_playground_endpoint.py",
                    snippet=(
                        "    monkeypatch.setenv(\"FDG_REDIS_URL\", UNREACHABLE_REDIS_URL)\n"
                        "    get_config.cache_clear()\n"
                        "    app = create_app()\n"
                        "    get_config.cache_clear()\n"
                        "    with TestClient(app) as client:\n"
                        "        assert client.get(\"/api/health\").status_code == 200\n"
                        "        content = client.get(\"/api/content\")\n"
                        "        assert content.status_code == 200\n"
                        "        assert len(content.json()[\"topics\"]) >= 20\n"
                        "        degraded = client.get(REDIS_PLAYGROUND_PATH)\n"
                        "        assert degraded.status_code == 503\n"
                        "        assert degraded.json()[\"error\"][\"code\"] == \"service_unavailable\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="optional-read",
                    text=(
                        "The adapter test pins the SPEED too: a playground "
                        "run against port 1 must raise the 503 AppError in "
                        "well under the six-second bound the suite allows "
                        "— connection-refused is instant, and the socket "
                        "timeouts are the ceiling for anything slower. "
                        "One fine print differs from topic 19's motor: "
                        "redis-py's asyncio client is loop-native (its "
                        "connections are asyncio objects created lazily on "
                        "the serving loop), so there is no measured "
                        "event-loop pinning gotcha — one client per app is "
                        "still the wiring, but by construction rather than "
                        "by defensive policy."
                    ),
                ),
            ],
        ),
        # ── 3. redis-asyncio structures ────────────────────────────────────
        Section(
            id="redis-asyncio-structures",
            title="redis-asyncio structures",
            lead="This section carries the topic's demo — the playground.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="structures-client-pitch",
                    text=(
                        "The dependency this topic adds is one package: "
                        "``redis`` (redis-py), whose ``redis.asyncio`` "
                        "module is a FIRST-CLASS asyncio client — not a "
                        "thread-pool skin over a sync driver like motor, "
                        "but await-colored commands over native "
                        "connections. Every method you will meet in this "
                        "section — set, get, incr, hset, hgetall, lpush, "
                        "lrange, sadd, smembers, zadd, zrange, ttl, "
                        "publish, subscribe — is one awaited call. The "
                        "domain sees none of them: the port speaks result "
                        "rows, the adapter owns every redis-py import, "
                        "same as topics 17–19:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="structures-port",
                    language="py",
                    caption="The domain port: one method, plain rows, no driver vocabulary.",
                    source="server/guide/domain/db/ports.py",
                    snippet=(
                        "@runtime_checkable\n"
                        "class RedisPlaygroundRunner(Protocol):\n"
                        "    # …\n"
                        "    async def run_playground(self, tag: str) -> RedisPlaygroundRun:\n"
                        "        \"\"\"Run the playground; ``tag`` is woven into the keys and values.\"\"\"\n"
                        "        ..."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="structures-roundtrip",
                    text=(
                        "One mechanical fact is worth internalizing before "
                        "the structures: EVERY awaited method is a network "
                        "round trip — set, then get, then two incrs is "
                        "four exchanges, each microseconds but each a "
                        "real crossing. That cost is why redis-py offers "
                        "pipelining (batch many commands into one "
                        "crossing) and why structure choice is really a "
                        "ROUND-TRIP choice: the hash that HGETALLs a "
                        "whole record in one call beats three string "
                        "keys fetched in sequence, and the sorted set "
                        "that answers 'rank' from its maintained order "
                        "beats sorting in the application on every read. "
                        "The playground keeps its calls un-pipelined on "
                        "purpose — each row should show one real "
                        "command, one real answer."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="structures-keys-pitch",
                    text=(
                        "Redis has one FLAT keyspace — no databases inside "
                        "the process you would want to rely on, no "
                        "collections, no schemas: every key is a global "
                        "name, so NAMING is the only isolation you get. "
                        "The discipline is a dedicated namespace prefix "
                        "per purpose, the same rule that gave MongoDB's "
                        "demos the ``guide_demo`` database. One playground "
                        "run touches only keys it owns, deletes them "
                        "before writing and after finishing — so calls are "
                        "idempotent and nothing accumulates:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="structures-namespace",
                    language="py",
                    caption="The namespace every demo key lives under — the whole topic owns it.",
                    source="server/guide/data/redis/playground.py",
                    snippet=(
                        "NAMESPACE: Final = \"guide_demo:redis:\"\n"
                        "NAMESPACE_DISPLAY: Final = \"guide_demo:redis:*\"\n"
                        "\"\"\"The demos' dedicated key namespace — the whole topic owns it.\"\"\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="structures-string-pitch",
                    text=(
                        "The string walk is the workhorse pattern: SET a "
                        "number, GET it back, then INCR it twice and GET "
                        "it again. The teaching point is what INCR is NOT "
                        "— it is not read-modify-write. The server parses, "
                        "increments, and stores atomically, and each call "
                        "ANSWERS with the new value, which is why counters "
                        "built this way need no lock even under concurrent "
                        "requests (topic 17 raced the SQL equivalent; "
                        "topic 25's rate limiter will lean on exactly "
                        "this property):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="structures-string",
                    language="py",
                    caption="The atomic counter: each INCR returns the value it wrote — no lock, no race.",
                    source="server/guide/data/redis/playground.py",
                    snippet=(
                        "        await self._client.set(key, \"1\")\n"
                        "        initial = await self._client.get(key)\n"
                        "        first_incr = int(await self._client.incr(key))\n"
                        "        second_incr = int(await self._client.incr(key))\n"
                        "        final = await self._client.get(key)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="structures-hash-set",
                    text=(
                        "Hash and set need less ceremony but carry their "
                        "own semantics. A hash is the record shape: one "
                        "HSET with a mapping plants three fields, one "
                        "HGETALL answers the whole record back — the "
                        "profile a session store would cache, no JOIN and "
                        "no second query. A set is the uniqueness shape: "
                        "SADD answers how many members it actually ADDED, "
                        "so re-adding an existing member honestly returns "
                        "0 — dedup is the structure's job, not the "
                        "application's. The playground weaves your tag "
                        "into both (the hash carries it as a field, the "
                        "set as a member) so different callers visibly "
                        "write different state."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="structures-list-pitch",
                    text=(
                        "The list walk stages a small inversion worth "
                        "seeing once: LPUSH adds at the HEAD, so pushing "
                        "\"third\" then \"second\" then \"first\" leaves "
                        "\"first\" at index 0 — newest-first for free, "
                        "which is precisely what a feed wants. LRANGE "
                        "0 -1 reads the whole window (ranges are "
                        "inclusive, -1 means the last element):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="structures-list",
                    language="py",
                    caption="Push order vs read order: LPUSH prepends, LRANGE 0 -1 reads left-to-right.",
                    source="server/guide/data/redis/playground.py",
                    snippet=(
                        "        pushed = int(\n"
                        "            await self._client.lpush(key, f\"third:{tag}\", f\"second:{tag}\", f\"first:{tag}\")\n"
                        "        )\n"
                        "        items = [str(item) for item in await self._client.lrange(key, 0, -1)]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="structures-zset-pitch",
                    text=(
                        "The sorted set is the structure with no cheap "
                        "SQL sibling: members carry scores, and the "
                        "structure ITSELF maintains score order — ZRANGE "
                        "is not sorting anything, it is reading an order "
                        "that already exists, which is why leaderboards "
                        "update in place at memory speed. WITHSCORES "
                        "returns member/score pairs in score order (the "
                        "two casts carry ``decode_responses=True``'s str "
                        "guarantee across redis-py's bytes-typed "
                        "signatures — the guarantee section two put in "
                        "the factory):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="structures-zset",
                    language="py",
                    caption="ZADD plants score-member pairs; ZRANGE WITHSCORES reads the maintained order.",
                    source="server/guide/data/redis/playground.py",
                    snippet=(
                        "        added = cast(\"int\", await self._client.zadd(key, dict(LEADERBOARD)))\n"
                        "        scored = cast(\n"
                        "            \"list[tuple[str, float]]\",\n"
                        "            await self._client.zrange(key, 0, -1, withscores=True),\n"
                        "        )\n"
                        "        pairs = [(str(member), float(score)) for member, score in scored]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="structures-router-pitch",
                    text=(
                        "The endpoint is a thin router like every demo "
                        "before it — validate the tag at the edge, one "
                        "port call, one pure payload builder — and the "
                        "tag is the caller's handle on freshness: it "
                        "names the key family (``guide_demo:redis:"
                        "<tag>:*``), so switching tags is switching to "
                        "untouched keys:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="structures-router",
                    language="py",
                    caption="The router: tag validated at the edge, then port + builder.",
                    source="server/guide/presentation/routers/demo/redis.py",
                    snippet=(
                        "async def read_redis_playground(\n"
                        "    runner: Annotated[RedisPlaygroundRunner, Depends(get_redis_playground)],\n"
                        "    tag: Annotated[\n"
                        "        str, Query(min_length=1, max_length=24, pattern=REDIS_TAG_PATTERN)\n"
                        "    ] = DEFAULT_REDIS_TAG,\n"
                        ") -> RedisPlaygroundPayload:\n"
                        "    \"\"\"The whole scripted playground against the live Redis: five structures\n"
                        "    with real results, an honest TTL expiry proof, and a real pub/sub\n"
                        "    round-trip — the tag names the key family, so repeats are fresh.\"\"\"\n"
                        "    run = await runner.run_playground(tag)\n"
                        "    return build_redis_playground_payload(run, tag)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="structures-demo-pitch",
                    text=(
                        "Try it: one request walks all five structures "
                        "with the real commands and their real read-backs "
                        "— the counter's 1 → 3, the hash's whole record, "
                        "the list's newest-first inversion, the set's "
                        "sorted members, the sorted set's score-ordered "
                        "ranks — then proves TTL expiry (section four) "
                        "and closes a real pub/sub round-trip (section "
                        "five) in the same payload. Change the tag and "
                        "every key is fresh."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="redis:playground",
                    title="The redis playground",
                    description=(
                        "GET /api/demo/redis/playground?tag=… runs the "
                        "whole scripted walk against the live Redis: "
                        "string SET/GET with two atomic INCRs, hash "
                        "HSET/HGETALL, list LPUSH/LRANGE with the "
                        "push-order inversion, set SADD/SMEMBERS with "
                        "honest duplicate refusal, sorted set ZADD/ZRANGE "
                        "WITHSCORES in score order — plus an honest TTL "
                        "expiry proof (the live clock, then the key's "
                        "absence) and a real pub/sub round-trip reported "
                        "from both sides of the wire."
                    ),
                ),
            ],
        ),
        # ── 4. TTL and expiry ──────────────────────────────────────────────
        Section(
            id="ttl-and-expiry",
            title="TTL and expiry",
            blocks=[
                TextBlock(
                    kind="text",
                    id="ttl-pitch",
                    text=(
                        "Every key in Redis can carry a countdown. SET with "
                        "an expiry — the inline EX this demo uses, the modern form of "
                        "the old SETEX shorthand — "
                        "plants the key AND its deadline in one atomic "
                        "command; TTL reads the seconds remaining; PERSIST "
                        "removes the deadline; EXPIRE attaches one to a "
                        "key that already exists. When the countdown "
                        "reaches zero the key is GONE — sessions, "
                        "verification codes, cache entries, and rate-limit "
                        "windows all become 'the store deletes it for me' "
                        "instead of 'a cron job remembers to'. This is "
                        "expiry as a first-class storage property — the "
                        "same idea topic 19 met as Mongo's TTL index, but "
                        "per-key and instant to set."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ttl-mechanics",
                    text=(
                        "Under the hood the eviction is honest but "
                        "two-phase, and knowing the phases prevents "
                        "surprises. Accessing an expired key removes it "
                        "lazily on the spot; between accesses, a "
                        "background cycle samples keys with countdowns "
                        "and evicts the ones past zero — so an expired "
                        "key may briefly still occupy memory, but it can "
                        "never be READ again: GET answers nil the "
                        "microsecond the deadline passes, regardless of "
                        "when the memory is reclaimed. Two semantics "
                        "matter to writers: setting a key again RESETS "
                        "its countdown only if you set one again (a bare "
                        "SET clears the old deadline entirely), and all "
                        "TTL commands are integer-seconds granular "
                        "(PTTL/PEXPIRE are the millisecond variants)."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ttl-flags",
                    text=(
                        "Two refinements matter in practice. SET takes "
                        "its expiry inline — ``SET key value EX 30`` is "
                        "SETEX without the separate command — and the "
                        "conditional flags compose with it: ``NX`` makes "
                        "the write succeed only when the key does NOT "
                        "exist, which is how the classic distributed-lock "
                        "idiom is one command (``SET lock holder NX EX "
                        "10``), and ``XX`` inverts the condition to "
                        "existing keys only. Neither flag appears in the "
                        "playground because neither is what it teaches, "
                        "but topic 21's cache-aside writes and topic 25's "
                        "rate limiter windows are both EX-compositions "
                        "away."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ttl-proof-pitch",
                    text=(
                        "The playground proves expiry honestly rather "
                        "than drawing a picture of it: SET with a "
                        "two-second EX deadline, TTL immediately after (the "
                        "live clock, not a claim), then a bounded wait "
                        "PAST the deadline and a GET that answers nil. "
                        "The constants make the proof deterministic — "
                        "asyncio sleeps AT LEAST the requested time, so "
                        "2.25 seconds can never race a 2-second expiry:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="ttl-constants",
                    language="py",
                    caption="Short enough to teach, long enough that no run ever races the deadline.",
                    source="server/guide/data/redis/playground.py",
                    snippet=(
                        "TTL_SECONDS: Final = 2\n"
                        "TTL_WAIT_S: Final = 2.25\n"
                        "\"\"\"Sleep past the expiry so the absence proof is deterministic: asyncio\n"
                        "sleeps AT LEAST the requested time, so the key is guaranteed gone.\"\"\""
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="ttl-walk",
                    language="py",
                    caption="The honest proof: set, read the clock, wait past the deadline, answer nil.",
                    source="server/guide/data/redis/playground.py",
                    snippet=(
                        "        await self._client.set(key, value, ex=TTL_SECONDS)\n"
                        "        ttl_first_read = int(await self._client.ttl(key))\n"
                        "        started = time.monotonic()\n"
                        "        await asyncio.sleep(TTL_WAIT_S)\n"
                        "        absent_after_expiry = await self._client.get(key) is None\n"
                        "        waited_ms = round((time.monotonic() - started) * 1000)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ttl-read",
                    text=(
                        "The payload reports every number the run "
                        "measured: the configured seconds, the TTL "
                        "answer (1 or 2 — the suite pins the honest "
                        "range), the milliseconds actually waited, and "
                        "the absence as a boolean the store produced, "
                        "not one the code assumed. That last distinction "
                        "is the section's whole lesson: expiry claims "
                        "are cheap, expiry PROOFS are an observable "
                        "absence — and the same discipline will make "
                        "topic 21's cache invalidation measurable "
                        "instead of hopeful."
                    ),
                ),
            ],
        ),
        # ── 5. Pub/sub ─────────────────────────────────────────────────────
        Section(
            id="pub-sub",
            title="Pub/sub",
            blocks=[
                TextBlock(
                    kind="text",
                    id="pubsub-pitch",
                    text=(
                        "Pub/sub is Redis's decoupling primitive: PUBLISH "
                        "sends a payload to a channel NAME; every "
                        "connection currently SUBSCRIBEd to that channel "
                        "receives it, and PUBLISH's return value is the "
                        "RECEIVER COUNT — the only acknowledgment that "
                        "exists. There is no persistence (a message "
                        "published with no subscriber is gone), no "
                        "replay, no per-consumer state: it is "
                        "fire-and-forget broadcast, the vocabulary of "
                        "chat fan-out, cache invalidation hints, and "
                        "live 'something changed' nudges. When a "
                        "workload needs those guarantees instead — "
                        "retention, consumer groups, at-least-once — "
                        "that is Redis Streams, topic 22's subject and "
                        "deliberately not this one."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pubsub-choreography-pitch",
                    text=(
                        "The playground performs a REAL round-trip, "
                        "choreographed so every step is bounded: "
                        "subscribe (the awaited call returns after the "
                        "server confirms), start a listener task on the "
                        "subscription's message stream, PUBLISH once, "
                        "and await the listener's message with a "
                        "timeout. Both sides end up in the payload — "
                        "what PUBLISH answered, and what the listener "
                        "actually collected:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pubsub-choreography",
                    language="py",
                    caption="One real round-trip: bounded listener, one PUBLISH, both sides reported.",
                    source="server/guide/data/redis/playground.py",
                    snippet=(
                        "        pubsub = self._client.pubsub()\n"
                        "        try:\n"
                        "            await pubsub.subscribe(channel)\n"
                        "            listener = asyncio.ensure_future(self._first_message(pubsub))\n"
                        "            try:\n"
                        "                receivers = int(await self._client.publish(channel, payload))\n"
                        "                message = await asyncio.wait_for(listener, timeout=PUBSUB_WAIT_S)\n"
                        "            finally:\n"
                        "                # No-op once the wait completed; a hard bound on any leak path.\n"
                        "                listener.cancel()\n"
                        "        finally:\n"
                        "            await pubsub.aclose()"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pubsub-listener-pitch",
                    text=(
                        "The listener itself is a filtered walk over the "
                        "subscription's stream — listen() yields EVERY "
                        "event type, and the subscription confirmation "
                        "arrives first, so the filter on 'message' is "
                        "what skips the bookkeeping and returns only "
                        "what a PUBLISH produced:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pubsub-listener",
                    language="py",
                    caption="Consume the stream until the first real message — confirmations filtered out.",
                    source="server/guide/data/redis/playground.py",
                    snippet=(
                        "    @staticmethod\n"
                        "    async def _first_message(pubsub: PubSub) -> str | None:\n"
                        "        \"\"\"Consume the pub/sub stream until the first real message.\n"
                        "\n"
                        "        ``listen()`` yields every event type — the subscription confirmation\n"
                        "        first — so the filter on ``type == \"message\"`` is what skips the\n"
                        "        bookkeeping and returns the PUBLISHed payload.\n"
                        "        \"\"\"\n"
                        "        async for message in pubsub.listen():\n"
                        "            if message.get(\"type\") == \"message\":\n"
                        "                data: Any = message.get(\"data\")\n"
                        "                return str(data)\n"
                        "        return None"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pubsub-read",
                    text=(
                        "Two production notes hide in that choreography. "
                        "First, leaks: a pub/sub connection holds a "
                        "server-side subscription and a client-side "
                        "task — the nested finally blocks guarantee "
                        "``listener.cancel()`` (a no-op when the wait "
                        "already completed) and ``pubsub.aclose()`` run "
                        "on EVERY path, success or failure, so the demo "
                        "can never bleed a dangling task or a stuck "
                        "connection into the serving loop. Second, "
                        "topology: a subscriber needs a connection of "
                        "its OWN (it blocks reading), which is why the "
                        "client pools per-command connections but "
                        "pubsub hands back a dedicated object — and "
                        "why, at more than one app instance, every "
                        "instance's subscriber still sees the message: "
                        "channels are server-global. Topic 28 will "
                        "stand this exact shape up again for "
                        "WebSockets; topic 22 replaces the forget half "
                        "with Streams' remember."
                    ),
                ),
            ],
        ),
        # ── 6. When a second store ─────────────────────────────────────────
        Section(
            id="when-a-second-store",
            title="When a second store",
            blocks=[
                TextBlock(
                    kind="text",
                    id="second-pitch",
                    text=(
                        "This repo now runs THREE stores, and that is the "
                        "right number to reason with because no two of "
                        "them were added for the same reason. The three "
                        "config rails sitting side by side ARE the "
                        "architecture decision, made three times:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="second-rails",
                    language="py",
                    caption="Three stores, three rails: PostgreSQL the record, mongo the documents, redis the clock.",
                    source="server/guide/core/config.py",
                    snippet=(
                        "    database_url: str = \"postgresql+asyncpg://postgres:guide@localhost:5432/guide\"\n"
                        "    redis_url: str = \"redis://localhost:6379\"\n"
                        "    mongo_url: str = \"mongodb://localhost:27017\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="second-grounded",
                    text=(
                        "Ground the framework in what this codebase "
                        "actually decided. PostgreSQL owns every fact "
                        "that must survive: the authors, posts, and "
                        "comments behind migrations 0001–0003, the audit "
                        "log a regulation would ask about, the version "
                        "numbers optimistic locking depends on. MongoDB "
                        "owns exactly one thing — the ``guide_demo`` "
                        "console documents, read-shaped teaching records "
                        "whose loss would cost a demo run, nothing more. "
                        "Redis owns nothing yet but namespace and "
                        "promises: the playground's structures vanish at "
                        "run's end, and that disposability is the point "
                        "— when topic 21 caches a post list, the cache "
                        "entry's death by TTL must be a non-event while "
                        "the same post in PostgreSQL is the business. "
                        "Three stores, three durability contracts, "
                        "deliberately different."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="second-grounds-pitch",
                    text=(
                        "The decision framework the data phase has been "
                        "building, stated once: a second store earns its "
                        "place ONLY when a workload's access pattern "
                        "outgrows the store you have — never because the "
                        "new one is fashionable. The questions that "
                        "matter, in the order worth asking them:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="second-grounds-list",
                    ordered=True,
                    items=[
                        "Shape of the data and queries — normalized "
                        "relational facts joined ad hoc (topics 16–18) vs "
                        "self-contained read-shaped documents (topic 19) "
                        "vs structures addressed by key with "
                        "microsecond updates (this topic).",
                        "Durability semantics — which facts must survive "
                        "anything (PostgreSQL's disk-first transactions), "
                        "which are conveniences (documents), which are "
                        "ephemeral BY DESIGN (counters, caches, "
                        "countdowns — losing them is the plan, not a "
                        "failure).",
                        "Consistency needs — read-your-writes across "
                        "joins is SQL's default; a cache that briefly "
                        "serves yesterday's answer is a policy decision "
                        "(topic 21's invalidation conversation).",
                        "Operation cost — every store is another "
                        "container to run, back up, monitor, and "
                        "UPGRADE; three optional services triple the "
                        "degradation matrix you must test (this topic's "
                        "503 proofs exist per store).",
                        "Team knowledge — a store nobody on call "
                        "understands is an outage waiting for a "
                        "schedule; the boring choice you know beats the "
                        "fast choice you don't.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="second-wiring-pitch",
                    text=(
                        "And when one clears the bar, it enters the way "
                        "all three entered here — optional, behind a "
                        "port, wired once at the composition root, "
                        "degraded honestly when absent. The redis wiring "
                        "is three lines, exactly as unceremonious as "
                        "mongo's was:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="second-wiring",
                    language="py",
                    caption="The composition root: one lazy client, one adapter, one app.state seam.",
                    source="server/guide/main.py",
                    snippet=(
                        "    redis_client = create_redis_client(config)\n"
                        "    app.state.redis_client = redis_client\n"
                        "    app.state.redis_playground = RedisPlaygroundRepository(redis_client)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="second-verdict",
                    text=(
                        "The honest verdict for most systems, this "
                        "guide's included: ONE relational store carries "
                        "you further than the internet implies — "
                        "PostgreSQL alone served topics 11–15 and could "
                        "serve everything else. Add a second store when "
                        "a MEASURED workload demands it: documents whose "
                        "shape is the payload (mongo), or speed and "
                        "expiry as the product (redis). The two "
                        "anti-patterns to name out loud are symmetric: "
                        "reaching for a second store before measuring "
                        "the first, and reaching for the relational "
                        "default when the workload is genuinely "
                        "ephemeral — a session countdown in PostgreSQL "
                        "is a cron job wearing a tie. The data phase "
                        "closes here: three stores, one architecture, "
                        "zero special cases — topic 21 immediately puts "
                        "the newest one to work."
                    ),
                ),
            ],
        ),
        # ── 7. Terminal companion ──────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole topic, from a shell — real structures, real clocks, real messages.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Six stops: the five structures with their real "
                        "results, the TTL and pub/sub proofs up close, a "
                        "fresh tag family, this topic's payload, the "
                        "curriculum it completes, and the degradation "
                        "proof plus the redis-cli detour. The stack is "
                        "up; every command answers with real data."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-structures",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the five structures, each with its real read-back\n"
                        "curl -s 'localhost:8000/api/demo/redis/playground' | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "for s in b[\"structures\"]:\n"
                        "    print(f\"{s[\\\"kind\\\"]:7} {s[\\\"key\\\"]}\")\n"
                        "    print(\"   \", s[\"outcome\"])\n"
                        "    for v in s[\"values\"]:\n"
                        "        print(f\"    {v[\\\"label\\\"]} = {v[\\\"value\\\"]}\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-proofs",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the honest TTL proof and the real pub/sub round-trip\n"
                        "curl -s 'localhost:8000/api/demo/redis/playground' | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "t = b[\"ttl\"]\n"
                        "print(f\"ttl: configured {t[\\\"ttlSeconds\\\"]}s, clock read {t[\\\"ttlFirstRead\\\"]}s, \"\n"
                        "      f\"waited {t[\\\"waitedMs\\\"]}ms, absent after expiry: {t[\\\"absentAfterExpiry\\\"]}\")\n"
                        "p = b[\"pubsub\"]\n"
                        "print(f\"pubsub: publish answered {p[\\\"receivers\\\"]} receiver(s), \"\n"
                        "      f\"listener matched: {p[\\\"matched\\\"]}\")'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-tag",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — a fresh tag = a fresh key family, woven into keys and values\n"
                        "curl -s 'localhost:8000/api/demo/redis/playground?tag=tour' | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "print(\"tag:\", b[\"tag\"])\n"
                        "print(\"keys:\", [s[\"key\"] for s in b[\"structures\"]])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-topic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — this topic: seven sections, the demo inline in section three\n"
                        "curl -s localhost:8000/api/content/redis | python3 -c '\n"
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
                        "# stop 5 — the curriculum this closes: twenty topics, the Data group complete\n"
                        "curl -s localhost:8000/api/content | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "data = [t[\"id\"] for t in b[\"topics\"] if t[\"group\"] == \"data\"]\n"
                        "print(\"topics:\", len(b[\"topics\"]), \"· data group:\", \" \".join(data))'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-degradation",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — the degradation proof (unreachable URL, no containers harmed)\n"
                        "docker exec fastapi_developers_guide_dev bash -lc \\\n"
                        "  'cd /workspaces/fastapi_developers_guide/server && uv run pytest -q \\\n"
                        "   tests/demo/test_redis_playground_endpoint.py -k \"boots or unreachable\"'\n"
                        "# and the store's own mouth: the namespace is empty after every run\n"
                        "docker exec fastapi_developers_guide_redis_dev \\\n"
                        "  redis-cli --scan --pattern 'guide_demo:redis:*'\n"
                        "# (no output — the playground DELs its stage first and after)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stop 1 is the topic in one payload: five "
                        "structures, each read back with the commands "
                        "that really ran. Stop 2 shows the two proofs "
                        "that make this demo more than a tour — a "
                        "countdown observed and an absence measured, a "
                        "message received as well as sent. Stop 6 is "
                        "the discipline: the app boots and serves with "
                        "Redis gone, and the store's own scanner "
                        "confirms the demo left nothing behind. The "
                        "Data group closes here — topic 21 opens the "
                        "next phase by putting Redis to its most "
                        "classic work, the cache."
                    ),
                ),
            ],
        ),
    ],
)
