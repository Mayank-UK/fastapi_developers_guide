"""Topic 21 — Caching (first topic of the State & auth group).

The data phase left the guide with three stores and a promise: Redis
owns "things whose value is speed or expiry." This topic keeps that
promise — it builds the guide's first REAL cache, end to end, on the
posts substrate topics 11–18 built. Two caching worlds are kept
deliberately distinct: HTTP caching (validators, revalidation, the 304)
where the CLIENT and shared proxies are the cache, and application
caching (cache-aside, TTL, invalidation, single-flight) where YOUR
process is. The topic's one lab demo is inline in the section that
teaches cache-aside, and everything it shows is real: keys, TTL,
telemetry, invalidation, and coalescing all run against the live Redis
— only the origin's cost is simulated (and labeled as such), because
the in-memory posts substrate would otherwise make every miss
indistinguishable from every hit.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="caching",
    title="Caching",
    subtitle=(
        "The two caching worlds — HTTP validators and 304s on one side, "
        "cache-aside, invalidation, and single-flight on the other — built "
        "real over the posts substrate."
    ),
    group="state-auth",
    order=21,
    sections=[
        # ── 1. Two worlds ───────────────────────────────────────────────────
        Section(
            id="two-worlds",
            title="Two worlds",
            blocks=[
                TextBlock(
                    kind="text",
                    id="worlds-pitch",
                    text=(
                        "Caching is remembering an answer so the next question is "
                        "free, and the single most useful thing to hold in your "
                        "head before writing any of it is that there are TWO "
                        "disjoint caching worlds, with different owners, different "
                        "mechanisms, and different failure modes. HTTP caching is "
                        "the protocol's own: response headers (Cache-Control, "
                        "ETag) let the browser, a proxy, or a CDN remember a "
                        "representation and later REVALIDATE it — your server "
                        "participates but stores nothing. Application caching is "
                        "yours: your process (or your Redis) remembers the result "
                        "of expensive work between requests, with keys, TTLs, and "
                        "invalidation as your own responsibility. They compose "
                        "beautifully — this topic builds both, then a lab that "
                        "shows them answering in the same round trip."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="worlds-contrast-pitch",
                    text=(
                        "The two worlds differ along every axis that matters, "
                        "which is why a caching strategy that ignores the "
                        "distinction always half-works:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="worlds-contrast-list",
                    ordered=False,
                    items=[
                        "Owner — HTTP caches belong to the CLIENT and shared "
                        "proxies (browsers, CDNs); an application cache belongs "
                        "to YOUR deployment and lives in your process or Redis.",
                        "Unit — HTTP caches store REPRESENTATIONS (the exact "
                        "bytes of one response, with its validators); an "
                        "application cache stores whatever YOU choose (a JSON "
                        "string, a counter, a computed object).",
                        "Freshness — HTTP freshness is negotiated (max-age, then "
                        "revalidation with If-None-Match); application freshness "
                        "is yours to enforce (TTL expiry, explicit invalidation, "
                        "versioned keys).",
                        "Cost model — a 304 saves the BODY but still crosses the "
                        "network; an application hit saves the ORIGIN work "
                        "(database, computation) and never leaves your process.",
                        "Failure mode — a mis-set Cache-Control serves stale "
                        "bytes to clients you cannot reach; a mis-keyed "
                        "application cache serves the WRONG answer to the next "
                        "request you fully control.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="worlds-chain",
                    text=(
                        "Zoom out and the two worlds are really a CHAIN of "
                        "caches a request may cross before your code runs at "
                        "all: the browser's HTTP cache (and possibly a service "
                        "worker in front of it), a shared proxy or CDN edge, "
                        "then finally your process — where the application "
                        "cache and the origin wait. Every hop independently "
                        "decides whether to answer or forward, which is why "
                        "caching bugs are so disorienting to debug: the fix "
                        "that 'sometimes works' usually depends on WHICH hop "
                        "answered, and the first diagnostic question for any "
                        "stale-data report is 'whose copy is stale?' — client, "
                        "edge, or process. The headers from section two are "
                        "how you discipline the hops you do not control; the "
                        "keys and TTLs from section three are how you "
                        "discipline the one you do."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="worlds-why-both",
                    text=(
                        "This guide runs both, really. The application half is a "
                        "cache-aside service over the posts use cases — the same "
                        "substrate /api/posts serves — storing canonical page "
                        "JSON under one versioned Redis key, with the "
                        "optional-service discipline topic 20 established (Redis "
                        "down degrades the lab to the 503 envelope; the app keeps "
                        "serving everything else). The HTTP half is a REAL "
                        "conditional endpoint this topic adds: it computes an "
                        "ETag over the exact bytes it serves, honors "
                        "If-None-Match, and answers 304 with an empty body. Read "
                        "them as one sentence: the application cache saves your "
                        "database, the conditional round trip saves your "
                        "bandwidth — and the last section's curl tour shows both "
                        "cashing out in a single command."
                    ),
                ),
            ],
        ),
        # ── 2. HTTP caching — validators and the 304 ───────────────────────
        Section(
            id="http-caching-and-304",
            title="HTTP caching and the 304",
            blocks=[
                TextBlock(
                    kind="text",
                    id="http-validators",
                    text=(
                        "An HTTP cache needs two answers from your response: HOW "
                        "LONG the representation may be reused without asking "
                        "(Cache-Control), and HOW to ask whether the thing it "
                        "remembered is still current (validators). The validators "
                        "are the ETag — an opaque string naming one "
                        "representation — and the modification date; this topic "
                        "uses ETags exclusively because they are exact: an ETag "
                        "is a fingerprint of the BYTES, not a guess about when "
                        "they changed. The endpoint computes it with a pure "
                        "domain helper over the payload string it is about to "
                        "serve, so the validator can never disagree with the "
                        "body:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="http-etag",
                    language="py",
                    caption="The ETag is a quoted SHA-256 prefix over the exact served bytes.",
                    source="server/guide/domain/caching/conditionals.py",
                    snippet=(
                        "def compute_etag(payload: str) -> str:\n"
                        '    """A strong ETag over the payload\'s exact bytes: quoted SHA-256 prefix."""\n'
                        "    digest = hashlib.sha256(payload.encode(\"utf-8\")).hexdigest()[:ETAG_HEX_LENGTH]\n"
                        '    return f\'\"{digest}\"\''
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="http-revalidation",
                    text=(
                        "Revalidation is the part that feels like magic the "
                        "first time: a cache that holds a representation sends "
                        "its ETag back in an If-None-Match request header, and "
                        "if the server's current ETag matches, the answer is 304 "
                        "Not Modified — the SAME validators, NO body. The client "
                        "keeps its copy; the network carried headers only. The "
                        "matching rules come from RFC 9110 and have edges worth "
                        "nailing down in a pure function (several candidates "
                        "comma-separated, weak-comparison W/ prefixes, and the "
                        "match-anything star), because a wrong matcher either "
                        "refuses valid clients or 304s stale data:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="http-matcher",
                    language="py",
                    caption="If-None-Match matching, per RFC 9110: weak comparison, candidates, star.",
                    source="server/guide/domain/caching/conditionals.py",
                    snippet=(
                        "    if if_none_match is None:\n"
                        "        return False\n"
                        "    header = if_none_match.strip()\n"
                        '    if header == "*":\n'
                        "        return True\n"
                        '    candidates = (candidate.strip().removeprefix("W/") for candidate in header.split(","))\n'
                        "    return any(candidate == etag for candidate in candidates)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="http-cache-control",
                    text=(
                        "Cache-Control is the policy half, and this endpoint's "
                        "choice is deliberate: no-cache. Despite the name it "
                        "does not disable caching — it forbids REUSE without "
                        "revalidation: store freely, but every use must ask "
                        "'still current?' and If-None-Match is what makes that "
                        "question cost zero body bytes. That is the right "
                        "default for API JSON whose freshness matters; max-age "
                        "(and its shared-cache sibling s-maxage) allows serving "
                        "WITHOUT asking for a stated window — the right choice "
                        "only when a stale window is acceptable, and section six "
                        "shows exactly where that is (fingerprinted static "
                        "assets)."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="http-policy",
                    language="py",
                    caption="The endpoint's freshness policy: store, but always revalidate.",
                    source="server/guide/domain/caching/conditionals.py",
                    snippet=(
                        'RESPONSE_CACHE_CONTROL: Final = "no-cache"\n'
                        '"""The conditional endpoint\'s policy: store freely, but ALWAYS revalidate.'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="http-endpoint-pitch",
                    text=(
                        "The endpoint itself applies those helpers as a thin "
                        "router: one port call serves the page (through the "
                        "application cache — section three), the response "
                        "carries the ETag, the policy, and the telemetry headers "
                        "the lab and the curl tour read (x-cache naming what "
                        "served it, elapsed milliseconds, age, and the hit and "
                        "origin counters), and a matching If-None-Match turns "
                        "the whole answer into a bodyless 304:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="http-endpoint",
                    language="py",
                    caption="The real conditional endpoint: same validators either way, body only when needed.",
                    source="server/guide/presentation/routers/demo/caching.py",
                    snippet=(
                        "    row = await service.fetch_page()\n"
                        "    headers = {\n"
                        '        "etag": row.etag,\n'
                        '        "cache-control": RESPONSE_CACHE_CONTROL,\n'
                        "        **_telemetry_headers(row),\n"
                        "    }\n"
                        '    if etag_matches(request.headers.get("if-none-match"), row.etag):\n'
                        "        return Response(status_code=304, headers=headers)\n"
                        '    return Response(content=row.payload, media_type="application/json", headers=headers)'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="http-validator-kinds",
                    text=(
                        "Validator vocabulary, briefly, so the choices do not "
                        "look arbitrary. HTTP knows two validator kinds: "
                        "Last-Modified (a timestamp — cheap, but second-"
                        "granular and ambiguous when clocks or rewrite orders "
                        "differ) and ETag (a fingerprint — exact, and the only "
                        "honest choice when a representation can change twice "
                        "in one second or stay byte-identical across a "
                        "rewrite). ETags themselves come in two strengths: a "
                        "STRONG etag (unquoted W/) promises byte-identical "
                        "bodies, a WEAK one (W/ prefix) promises semantic "
                        "equivalence — same meaning, possibly different bytes. "
                        "This endpoint computes a strong one because its cache "
                        "stores the literal response string: byte-identical is "
                        "the only equivalence it can actually verify, and the "
                        "matcher above still accepts weak candidates from "
                        "clients because RFC 9110 requires weak comparison on "
                        "GET revalidation."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="http-read",
                    text=(
                        "Two honest notes. First, 304 semantics: the response "
                        "MUST NOT carry a body, and it repeats the validators so "
                        "the client's copy stays labeled with the right ETag — "
                        "the test suite pins both. Second, note what the 304 "
                        "does and does not save: it saves the body and the "
                        "client's parse of it, but the request still crosses the "
                        "network and your process still runs — which is exactly "
                        "why the x-cache header rides along on the 304 too. A "
                        "304 with x-cache: hit means BOTH worlds saved you: the "
                        "application cache skipped the origin, and the "
                        "conditional saved the transfer. The lab's conditional "
                        "console makes that combination visible with two clicks."
                    ),
                ),
            ],
        ),
        # ── 3. Cache-aside ─────────────────────────────────────────────────
        Section(
            id="cache-aside-and-decorators",
            title="Cache-aside and decorators",
            lead="This section carries the topic's demo — the lab.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="aside-pitch",
                    text=(
                        "Application caching has one dominant pattern, and its "
                        "name is its algorithm: cache-aside. The cache sits "
                        "BESIDE the origin, not in front of it — every reader "
                        "asks the cache first and only the owner of a miss goes "
                        "to the origin, writes the answer back with a deadline, "
                        "and serves it. Nothing else changes: the origin stays "
                        "the system of record (PostgreSQL behind the posts use "
                        "cases), the cache is disposable by design, and a cache "
                        "that vanished tomorrow would cost latency, never "
                        "correctness. The pattern's whole store contract is four "
                        "verbs, and that contract is a domain port:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aside-port",
                    language="py",
                    caption="The cache-aside store contract: get, set-with-TTL, delete, TTL.",
                    source="server/guide/domain/caching/ports.py",
                    snippet=(
                        "@runtime_checkable\n"
                        "class CacheStore(Protocol):\n"
                        '    """What every cache adapter must do; keys arrive fully formed."""\n'
                        "\n"
                        "    async def get(self, key: str) -> str | None:\n"
                        '        """The value under ``key``, or None when absent (or expired)."""\n'
                        "        ...\n"
                        "\n"
                        "    async def set(self, key: str, value: str, ttl_seconds: int) -> None:\n"
                        '        """Store ``value`` under ``key`` with an expiry — the safety net."""\n'
                        "        ..."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aside-read-path",
                    text=(
                        "The read path is where all the decisions live. One GET "
                        "answers a hit. A miss takes a per-key lock and "
                        "RE-CHECKS the store inside it — that double-check is "
                        "what makes concurrent misses cheap (section five makes "
                        "it prove itself) — and only a second miss pays the "
                        "origin. The fill is written with its TTL before the "
                        "lock releases, so no concurrent reader can observe a "
                        "half-filled state; the cached value is the page's "
                        "canonical JSON STRING, exactly the bytes the endpoint "
                        "serves, which is why the ETag over it cannot drift from "
                        "any body a client ever receives:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aside-read",
                    language="py",
                    caption="Cache-aside's read path: check, lock, double-check, fill, write with TTL.",
                    source="server/guide/domain/caching/service.py",
                    snippet=(
                        "        started = time.monotonic()\n"
                        "        cached = await self._store.get(CACHE_KEY)\n"
                        "        if cached is not None:\n"
                        "            return await self._serve_from_store(cached, started, coalesced=False)\n"
                        "        async with self._lock_for(CACHE_KEY):\n"
                        "            cached = await self._store.get(CACHE_KEY)\n"
                        "            if cached is not None:\n"
                        "                # Single-flight did its job: another request filled the\n"
                        "                # entry while this one waited on the lock — serve it warm.\n"
                        "                return await self._serve_from_store(cached, started, coalesced=True)\n"
                        "            payload = await self._fetch_origin()\n"
                        "            await self._store.set(CACHE_KEY, payload, TTL_SECONDS)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aside-origin",
                    text=(
                        "One label in this substrate must be read honestly: the "
                        "ORIGIN here is an in-memory repository that answers in "
                        "microseconds, so a flat simulated cost stands in for "
                        "the database and I/O latency a real origin pays — "
                        "without it, a miss and a hit would be indistinguishable "
                        "to the eye. The sleep is the simulation; the use case "
                        "call and its canonical serialization are the real "
                        "substrate:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aside-cost",
                    language="py",
                    caption="The simulated origin cost — labeled as such; the caching around it is real.",
                    source="server/guide/domain/caching/service.py",
                    snippet=(
                        "ORIGIN_COST_MS: Final = 120\n"
                        '"""SIMULATED origin cost — a flat stand-in for real database/IO latency."""\n'
                        "\n"
                        "ORIGIN_COST_NOTE: Final = (\n"
                        '    f"simulated — the real substrate answers in microseconds; the flat "\n'
                        '    f"{ORIGIN_COST_MS} ms stands in for database/IO time so hit-vs-miss is visible"\n'
                        ")"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="aside-origin-call",
                    language="py",
                    caption="The expensive path: simulated cost first, then the real use case, canonical JSON out.",
                    source="server/guide/domain/caching/service.py",
                    snippet=(
                        "        await asyncio.sleep(ORIGIN_COST_MS / 1000)\n"
                        "        result = self._posts.list_posts.execute(ORIGIN_QUERY)\n"
                        "        if isinstance(result, Err):\n"
                        "            raise result.failure\n"
                        "        return result.value.model_dump_json(by_alias=True)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aside-decorators",
                    text=(
                        "Where are the decorators, then? In many codebases "
                        "cache-aside arrives as one — a @cached(prefix, ttl) "
                        "wrapper that memoizes any async function's result by "
                        "its arguments, and the shape is worth knowing: hash the "
                        "arguments into a key, GET, on miss await the wrapped "
                        "call, SET with TTL, return. This guide's service uses "
                        "the explicit method instead, deliberately: a decorator "
                        "hides the cache from the call site (and from the "
                        "reader), its silently-generated keys are exactly the "
                        "kind section four warns about, and the teaching artifact "
                        "wants every step visible. The rule of thumb holds for "
                        "both shapes: cache-aside wrapping a function you could "
                        "also call directly, where the ONLY change on a hit is "
                        "how long the call takes."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="aside-demo-pitch",
                    text=(
                        "Try it: the lab is the whole topic in one panel. Fetch "
                        "the real conditional endpoint twice and watch x-cache "
                        "flip from miss (about 120 ms, simulated origin) to hit "
                        "(single-digit milliseconds); read the key, its TTL "
                        "countdown, and the hit/miss/coalesced/invalidation "
                        "counters; run the conditional console to send the ETag "
                        "back and watch the 304 land with an empty body; "
                        "invalidate and watch the next fetch refill; or fire a "
                        "stampede and watch eight concurrent cold requests "
                        "produce exactly one origin fetch."
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="caching:lab",
                    title="The caching lab",
                    description=(
                        "One panel over the real cache-aside service: GET "
                        "/api/demo/caching/posts is a REAL conditional endpoint "
                        "(ETag, Cache-Control: no-cache, x-cache telemetry, "
                        "If-None-Match → 304); the state panel shows the "
                        "versioned key, its live TTL, and the hit/miss/"
                        "coalesced/invalidation counters; buttons invalidate "
                        "explicitly and run a cold 8-request stampede pinned to "
                        "exactly one origin fetch by single-flight. Origin cost "
                        "is simulated at 120 ms and labeled as such — the "
                        "caching is real."
                    ),
                ),
            ],
        ),
        # ── 4. Invalidation ────────────────────────────────────────────────
        Section(
            id="invalidation-ttl-versioned-keys",
            title="Invalidation, TTL, versioned keys",
            blocks=[
                TextBlock(
                    kind="text",
                    id="invalidation-pitch",
                    text=(
                        "There are only two hard problems in caching, and this "
                        "is one of them: the entry says yesterday. The honest "
                        "framework is three mechanisms, ordered by how much "
                        "they promise. Explicit invalidation is the strongest: "
                        "the code that CHANGES the origin deletes the affected "
                        "key, the next read misses and refills — the lab's "
                        "invalidate button is exactly that delete, and the "
                        "adapter's DEL answers how many entries actually died, "
                        "which is the difference between 'I invalidated' and "
                        "'there was something to invalidate':"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="invalidation-delete",
                    language="py",
                    caption="Explicit invalidation: delete the key, count what died, report the refill.",
                    source="server/guide/domain/caching/service.py",
                    snippet=(
                        "        deleted = await self._store.delete(CACHE_KEY)\n"
                        "        if deleted > 0:\n"
                        "            self._invalidations += 1"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="invalidation-ttl",
                    text=(
                        "TTL is the safety net, never the strategy: every entry "
                        "this lab writes carries a two-second EX inline in its "
                        "SET — topic 20 taught the mechanics (lazy plus sampled "
                        "eviction, never readable past zero) — so worst case, a "
                        "forgotten invalidation goes stale for at most one TTL "
                        "window. The short window is a DEMO choice; production "
                        "picks it per workload as 'how stale can this answer be "
                        "before anyone is hurt.' The store adapter translates "
                        "redis's two special TTL answers into the port's honest "
                        "contract (absent and no-deadline both become None), "
                        "which is the whole reason a state panel can render a "
                        "countdown without learning redis conventions:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="invalidation-ttl-adapter",
                    language="py",
                    caption="The adapter's TTL translation: redis's -2/-1 specials become the port's None.",
                    source="server/guide/data/caching/redis_store.py",
                    snippet=(
                        "    async def ttl(self, key: str) -> int | None:\n"
                        '        """TTL — seconds remaining, or None when absent or without deadline."""\n'
                        '        with _map_cache_failures("ttl"):\n'
                        "            raw = int(await self._client.ttl(key))\n"
                        "            return None if raw in (TTL_ABSENT, TTL_IMMORTAL) else raw"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="invalidation-versioned",
                    text=(
                        "Versioned keys are the third mechanism and the "
                        "cleanest one in production: instead of deleting an "
                        "obsolete entry, CHANGE THE KEY so the obsolete one is "
                        "never read again and expires on its own clock. This "
                        "lab's one key carries its version segment for exactly "
                        "that teaching — a payload projection change becomes "
                        "posts:v2, every reader starts missing immediately, and "
                        "no delete was ever needed:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="invalidation-key",
                    language="py",
                    caption="The versioned key: bump the segment and the old entry is unreachable, then expired.",
                    source="server/guide/domain/caching/service.py",
                    snippet=(
                        'CACHE_KEY: Final = f"{NAMESPACE}posts:v1"\n'
                        '"""The one key this lab caches: the posts list page, payload-version v1.\n'
                        "\n"
                        "The version segment is the invalidation strategy taught in section four:\n"
                        "a new payload shape becomes ``posts:v2`` and the old entry is never read\n"
                        'again — it simply expires. Bump it when the cached projection changes."""\n'
                        "\n"
                        "TTL_SECONDS: Final = 2\n"
                        '"""The safety-net expiry: short enough to demo, long enough to see hits."""'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="invalidation-read",
                    text=(
                        "The discipline that binds the three: invalidation must "
                        "be keyed by CAUSE, not by guess. A post is created or "
                        "replaced, therefore the page that would show it is "
                        "stale, therefore delete (or bump) that key — ideally in "
                        "the same code path that committed the change, the way "
                        "topic 22's transactional outbox will make "
                        "cross-service versions of this reliable. What you may "
                        "NOT do is shrug and shorten the TTL until complaints "
                        "stop: that is tuning a bug, not designing freshness. "
                        "The lab makes the full lifecycle observable — "
                        "invalidate, watch the miss, watch the refill, then "
                        "wait out the TTL and watch the entry expire on the "
                        "store's own clock with no code running at all."
                    ),
                ),
            ],
        ),
        # ── 5. Stampedes ───────────────────────────────────────────────────
        Section(
            id="stampedes-and-single-flight",
            title="Stampedes and single-flight",
            blocks=[
                TextBlock(
                    kind="text",
                    id="stampede-pitch",
                    text=(
                        "Every entry expires; sometimes they all expire "
                        "together (a deploy restarts every process, a popular "
                        "page's TTL ends) — and then N concurrent requests all "
                        "miss, all go to the origin, and the origin experiences "
                        "the very load the cache existed to prevent: a cache "
                        "stampede. The fix this lab implements is single-flight, "
                        "also called request coalescing: on a miss, take a "
                        "per-key lock, RE-CHECK the cache inside it, and let "
                        "exactly ONE request fetch while every other waiter "
                        "blocks on the lock — then reads the fill that landed "
                        "while it waited. The double-check from section three "
                        "was this mechanism all along:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="stampede-lock",
                    language="py",
                    caption="The per-key single-flight lock — in-process, deterministic, one lock per key.",
                    source="server/guide/domain/caching/service.py",
                    snippet=(
                        "    def _lock_for(self, key: str) -> asyncio.Lock:\n"
                        '        """The per-key single-flight lock (this lab has exactly one key)."""\n'
                        "        lock = self._origin_locks.get(key)\n"
                        "        if lock is None:\n"
                        "            lock = asyncio.Lock()\n"
                        "            self._origin_locks[key] = lock\n"
                        "        return lock"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="stampede-round",
                    language="py",
                    caption="The stampede round: cold-start, gather N concurrent reads, count the fills.",
                    source="server/guide/domain/caching/service.py",
                    snippet=(
                        "        await self._store.delete(CACHE_KEY)\n"
                        "        started = time.monotonic()\n"
                        "        fetched = await asyncio.gather(*(self.fetch_page() for _ in range(requests)))\n"
                        "        wall_ms = self._elapsed_ms(started)\n"
                        "        rounds = [\n"
                        "            StampedeRequestRow(index=index, outcome=row.outcome, elapsed_ms=row.elapsed_ms)\n"
                        "            for index, row in enumerate(fetched)\n"
                        "        ]\n"
                        '        origin_fetches = sum(1 for row in fetched if row.outcome == "miss")\n'
                        "        served_warm = requests - origin_fetches"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="stampede-determinism",
                    text=(
                        "The proof's determinism deserves a sentence, because "
                        "'it usually works' is not a cache guarantee. The "
                        "counts are pinned by the LOCK, not by timing: every "
                        "concurrent request misses its first GET, queues on the "
                        "per-key lock, and the first holder fills and writes "
                        "BEFORE releasing — so no waiter's re-check can miss, "
                        "and exactly one origin fetch happens no matter how the "
                        "event loop interleaves them. The lab's stampede button "
                        "fires eight concurrent cold requests and the suite "
                        "pins the result: one origin fetch, seven served warm "
                        "(reported as coalesced), wall time one origin cost — "
                        "not eight. The same test discipline as topic 17's race "
                        "lab applies: ordered awaits, no sleeps pretending to "
                        "be synchronizers."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="stampede-beyond",
                    text=(
                        "Two production refinements this lab deliberately does "
                        "NOT implement, because they trade determinism for "
                        "scale. Early expiry plus jitter: instead of waiting "
                        "for the deadline, the first reader a moment BEFORE "
                        "expiry (say, at 90 percent of the TTL, offset by a "
                        "random jitter per request so callers do not align) "
                        "refreshes the entry in the background while everyone "
                        "else keeps serving the old one — the stampede never "
                        "happens, at the cost of a background task and a "
                        "deliberate near-stale serve. Distributed locking: an "
                        "asyncio.Lock coalesces within ONE process, but the "
                        "guide's own deployment story (topic 37) runs replicas "
                        "— the cross-process form is a lock KEY in Redis "
                        "acquired with SET NX EX (topic 20 taught the exact "
                        "command shape), where the winner fills and the losers "
                        "poll briefly for the fill; it works, it is standard, "
                        "and every moving part (TTL on the lock itself, "
                        "crash-recovery, fencing) is why this lab teaches the "
                        "deterministic in-process version first."
                    ),
                ),
            ],
        ),
        # ── 6. CDN and hashed filenames ────────────────────────────────────
        Section(
            id="cdn-and-hashed-filenames",
            title="CDN and hashed filenames",
            blocks=[
                TextBlock(
                    kind="text",
                    id="cdn-pitch",
                    text=(
                        "A CDN is HTTP caching at planetary scale: edge servers "
                        "in front of your origin that answer clients from the "
                        "nearest hop, using the SAME Cache-Control and "
                        "validator vocabulary section two taught — s-maxage "
                        "governs the shared edge, max-age the private browser, "
                        "and a 304 from your origin still refreshes an edge "
                        "entry. Nothing new to learn, one giant new cache. What "
                        "a CDN fixes is distance and origin load for cacheable "
                        "responses; what it does NOT fix is everything else — "
                        "uncacheable per-request API work, POSTs and other "
                        "non-safe methods, cookies that strip shared "
                        "cacheability, and TLS-adjacent misconfigurations. Put "
                        "the CDN where the cacheable bytes are, never in front "
                        "of an API that cannot answer from a copy."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cdn-fingerprint-pitch",
                    text=(
                        "The cacheable bytes in a SPA are its build artifacts, "
                        "and this repo's production client ships exactly that "
                        "shape: Vite builds content-HASHED filenames (an "
                        "asset's name embeds a digest of its content — the "
                        "dist/ directory carries names like "
                        "app_info_demo-vEIz86L3.js), nginx serves them, and a "
                        "changed asset is a NEW filename by construction. That "
                        "inversion is what makes aggressive caching safe:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="cdn-fingerprint-list",
                    ordered=True,
                    items=[
                        "Build hashes the content — every asset filename embeds "
                        "a digest of its own bytes, so any edit changes the "
                        "name.",
                        "index.html references the new names — the one "
                        "uncacheable document; served fresh, it points clients "
                        "at the new world.",
                        "Assets answer immutable — same name means same bytes "
                        "forever, so Cache-Control: public, max-age=31536000, "
                        "immutable is provably safe for them.",
                        "Old names age out — the previous build's files simply "
                        "stop being referenced; a CDN's and browser's copies "
                        "harmlessly expire.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="cdn-build-pitch",
                    text=(
                        "The real pipeline, quoted from this repo's production "
                        "client image — Vite emits the hashed assets in Node, "
                        "nginx receives the whole dist/ tree:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cdn-build",
                    language="dockerfile",
                    caption="Hashed assets are born in the build stage and land in nginx's static root.",
                    source=".docker/client/Dockerfile.prod",
                    snippet=(
                        "FROM node:22-bookworm AS build\n"
                        "# …\n"
                        "COPY client/ ./\n"
                        "RUN npm run build\n"
                        "\n"
                        "FROM nginx:1.27-alpine\n"
                        "COPY .docker/client/nginx.conf /etc/nginx/conf.d/default.conf\n"
                        "COPY --from=build /app/dist /usr/share/nginx/html"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cdn-nginx",
                    language="nginx",
                    caption="The static root that serves the hashed tree; /api stays proxied, never edge-cached.",
                    source=".docker/client/nginx.conf",
                    snippet=(
                        "    root   /usr/share/nginx/html;\n"
                        "    index  index.html;\n"
                        "\n"
                        "    # Proxy API calls to the FastAPI server (compose service name).\n"
                        "    location /api/ {\n"
                        "        # …\n"
                        "    }\n"
                        "\n"
                        "    # SPA history fallback: unknown paths serve the app, which renders the 404 view.\n"
                        "    location / {\n"
                        "        try_files $uri $uri/ /index.html;\n"
                        "    }"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cdn-read",
                    text=(
                        "One honest gap, visible by reading that config: this "
                        "nginx does not yet set Cache-Control on static "
                        "responses, so browsers fall back to heuristic "
                        "freshness — correct but timid. The production upgrade "
                        "is one location block: for /assets/ (the hashed tree), "
                        "add expires 1y plus Cache-Control immutable; for "
                        "index.html, add Cache-Control no-cache — the document "
                        "must always revalidate precisely BECAUSE it is the "
                        "only thing naming the immutable assets. That pairing "
                        "(an eternally-cacheable everything, one always-"
                        "revalidated pointer) is the CDN-era refinement of "
                        "section two's policy choice, and it is exactly what "
                        "the hashed filenames make safe."
                    ),
                ),
            ],
        ),
        # ── 7. What NOT to cache ───────────────────────────────────────────
        Section(
            id="what-not-to-cache",
            title="What not to cache",
            blocks=[
                TextBlock(
                    kind="text",
                    id="not-pitch",
                    text=(
                        "The second hard problem in caching is caching the "
                        "wrong thing — a cache is an amplifier, and it "
                        "amplifies mistakes as reliably as it amplifies "
                        "savings. The test is not 'is this slow?' but 'is a "
                        "slightly-old, possibly-shared copy of this answer "
                        "harmless?' — and for a large, security-shaped family "
                        "of answers the honest reply is no. The classic "
                        "outages are not cache misses; they are cached AUTH "
                        "DECISIONS still saying yes after the truth changed:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="not-list",
                    ordered=False,
                    items=[
                        "Auth decisions — a cached 'this token is valid' or "
                        "'this user may write' outlives its revocation; "
                        "authorization must be evaluated per request (topic 24 "
                        "builds it as a dependency precisely so it cannot be "
                        "skipped).",
                        "Per-user data — a shared cache keyed without the user "
                        "hands one person another person's page; when user A's "
                        "data is cached at all, the user is part of the key, "
                        "and section two's shared-cache headers must stay "
                        "private.",
                        "Un-validated writes — caching a response computed "
                        "from input that was never validated (topic 10's "
                        "boundary) canonizes garbage and serves it at cache "
                        "speed to everyone who shares the key.",
                        "Anything you cannot afford stale — inventory counts, "
                        "balances, quota windows: if a stale window costs real "
                        "money, the correct tool is the origin's transaction, "
                        "not a TTL race.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="not-positive",
                    text=(
                        "The mirror image is worth stating too, because a "
                        "topic of don'ts can scare you off the savings: the "
                        "safely-cacheable category is large. Public, read-only "
                        "aggregates (this lab's newest-posts page), expensive "
                        "PURE derivations (a computed ranking, a rendered "
                        "digest) where inputs change rarely relative to reads, "
                        "reference data that changes on deploy cadence, and "
                        "the fingerprinted static assets of section six — all "
                        "of these are sharing-friendly, staleness-tolerant by "
                        "design, and trivially invalidated by cause. The "
                        "discipline is not 'cache less'; it is 'cache the "
                        "answers whose old copies are boring.'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="not-rails",
                    text=(
                        "This topic's own lab honors the list by construction: "
                        "it caches one PUBLIC, read-only page (the newest "
                        "posts) under a key with no user in it — the only "
                        "category where sharing is the point — and its "
                        "conditional endpoint sends no-cache so no shared "
                        "proxy ever serves stale-but-unservable bytes without "
                        "revalidating. When you extend the pattern, keep the "
                        "checklist order: WHO is the answer for (key it), HOW "
                        "stale is acceptable (TTL it), WHAT invalidates it "
                        "(delete or bump on that cause), and MAY a shared "
                        "cache hold it at all (private beats public the "
                        "moment a user appears). A cache that fails all four "
                        "questions is still correct — it is just slow; the "
                        "danger is the cache that answers all four with "
                        "guesses."
                    ),
                ),
            ],
        ),
        # ── 8. Terminal companion ──────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion",
            lead="The whole topic, from a shell — real headers, real 304s, real counts.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-intro",
                    text=(
                        "Seven stops: the miss-then-hit round trip with its "
                        "telemetry headers, the 304 with an empty body, "
                        "explicit invalidation, the TTL safety net expiring on "
                        "the store's own clock, the stampede pinned to one "
                        "origin fetch, the lab and topic payloads, and the "
                        "degradation proof plus the namespace check. The stack "
                        "is up; every command answers with real headers."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-hitmiss",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — first read pays the simulated origin (miss), second is warm (hit)\n"
                        "curl -sD - -o /dev/null localhost:8000/api/demo/caching/posts \\\n"
                        "  | grep -iE '^(x-cache|x-cache-elapsed-ms|etag)'\n"
                        "curl -sD - -o /dev/null localhost:8000/api/demo/caching/posts \\\n"
                        "  | grep -iE '^(x-cache|x-cache-elapsed-ms|etag)'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-304",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the conditional round trip: send the ETag back, get a bodyless 304\n"
                        "etag=$(curl -sD - -o /dev/null localhost:8000/api/demo/caching/posts \\\n"
                        "  | grep -i '^etag' | tr -d '\\r' | cut -d' ' -f2)\n"
                        "echo \"etag: $etag\"\n"
                        "curl -sD - -o /dev/null -H \"If-None-Match: $etag\" \\\n"
                        "  localhost:8000/api/demo/caching/posts | grep -iE '^(HTTP|x-cache|etag|content-length)'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-invalidate",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — explicit invalidation: the delete, then the next read refills\n"
                        "curl -s -X POST localhost:8000/api/demo/caching/invalidate \\\n"
                        "  | python3 -c 'import json,sys; b=json.load(sys.stdin); print(b[\"detail\"])'\n"
                        "curl -sD - -o /dev/null localhost:8000/api/demo/caching/posts \\\n"
                        "  | grep -i '^x-cache'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-ttl",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the TTL safety net: wait out the 2 s expiry, watch it miss again\n"
                        "sleep 2.25\n"
                        "curl -sD - -o /dev/null localhost:8000/api/demo/caching/posts \\\n"
                        "  | grep -iE '^(x-cache|x-cache-elapsed-ms)'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-stampede",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the stampede: 8 concurrent cold requests, exactly 1 origin fetch\n"
                        "curl -s -X POST -H 'content-type: application/json' \\\n"
                        "  -d '{\"requests\": 8}' localhost:8000/api/demo/caching/stampede \\\n"
                        "  | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "r, o, w, s = b[\"requests\"], b[\"originFetches\"], b[\"wallMs\"], b[\"servedWarm\"]\n"
                        "print(f\"requests {r} -> origin {o}, served warm {s}, wall {w}ms\")\n"
                        "print(b[\"proof\"])'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-topic",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 6 — the lab roster + this topic: the demo inline in section three\n"
                        "curl -s localhost:8000/api/demo/caching/lab | python3 -c '\n"
                        "import json, sys\n"
                        "b = json.load(sys.stdin)\n"
                        "s = b[\"state\"]\n"
                        "print(\"key:\", s[\"key\"], \"· ttl:\", s[\"ttlSeconds\"], \"s · present:\", s[\"present\"])\n"
                        "print(\"telemetry:\", s[\"telemetry\"])\n"
                        "print(\"origin:\", b[\"originCostMs\"], \"ms (\" + b[\"originCostNote\"] + \")\")'\n"
                        "curl -s localhost:8000/api/content/caching | python3 -c '\n"
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
                        "# stop 7 — degradation proof + the store's own mouth (no containers harmed)\n"
                        "docker exec fastapi_developers_guide_dev bash -lc \\\n"
                        "  'cd /workspaces/fastapi_developers_guide/server && uv run pytest -q \\\n"
                        "   tests/demo/test_caching_lab_endpoint.py -k \"unreachable or boots\"'\n"
                        "# the namespace self-cleans: every key carries the 2 s TTL\n"
                        "docker exec fastapi_developers_guide_redis_dev \\\n"
                        "  redis-cli --scan --pattern 'guide_demo:caching:*'\n"
                        "# (no output within 2 s of the last lab touch — the TTL is the janitor)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stop 1 is the whole application half in two commands: "
                        "the same URL answering miss at 120-plus milliseconds "
                        "then hit in single digits. Stop 2 is the HTTP half: "
                        "the validator sent home, the body that never crossed "
                        "the wire. Stops 3 and 4 are the invalidation chapter "
                        "acted out — the delete you can see, the expiry that "
                        "runs itself — and stop 5 is the guarantee under load: "
                        "eight requests, one origin fetch. The topic closes "
                        "the data phase's promise and opens the state and "
                        "auth group: the next topics put MESSAGES and then "
                        "IDENTITY on this same stack, and caching discipline "
                        "keeps earning its keep in every one of them."
                    ),
                ),
            ],
        ),
    ],
)
