"""Topic 01 — python-language (the EXEMPLAR topic module).

Teaches the language this server is written in, using the server's own
code as every example: why Python · python basics (control flow, loops,
functions, classic classes) · data structures and strings · type hints +
mypy · dataclasses vs pydantic · None discipline · modules and imports ·
exceptions and context managers · comprehensions and generators · types
at runtime (with the topic's inline live demo) · the terminal companion.

Authoring pattern lives in ``topics/__init__.py``; this module is its
reference implementation. Every code block below quotes a real repo file
(the snippet ratchet verifies it) — including the yield dependency the
context-manager section quotes: the repo's real request-span instrument,
grown up with topic 06 (which retires the teaching exhibit this section
once needed).
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="python-language",
    title="The Python language",
    subtitle=(
        "The language tour this server actually uses — from type hints to what "
        "the interpreter really does with them."
    ),
    group="foundations",
    order=1,
    sections=[
        # ── 1. Why Python on the server ─────────────────────────────────────
        Section(
            id="why-python",
            title="Why Python on the server",
            blocks=[
                TextBlock(
                    kind="text",
                    id="why-python-pitch",
                    text=(
                        "Python is a dynamically typed, bytecode-compiled language whose "
                        "server-side pitch is iteration speed and ecosystem depth. An endpoint "
                        "is a screen of code, and the batteries are installed: FastAPI for the "
                        "web layer, pydantic for validation, SQLAlchemy for the ORM, uvicorn "
                        "for the ASGI server, structlog for logging. This guide's entire server "
                        "runs on five runtime dependencies — quoted below from the manifest, "
                        "because that number is the honest advertisement."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-python-caveat",
                    text=(
                        "The honest caveat is dynamism. Untyped Python refactors badly at scale, "
                        "fails at runtime where typed languages fail at compile time, and pays "
                        "the GIL tax on CPU-bound work — one thread executes Python bytecode at "
                        "a time, and the free-threaded interpreter shipping experimentally in "
                        "3.13 is not what this repo runs. What made Python survivable on the "
                        "server is gradual typing: PEP 484 made annotations part of the "
                        "language without changing execution at all, then the syntax got "
                        "cheap — builtin generics like dict[str, Topic] in 3.9, unions "
                        "written X | None in 3.10, the modern generic syntax in 3.12. This "
                        "repo requires Python 3.13, annotates everything, checks it with "
                        "mypy in strict mode, and validates with pydantic exactly where "
                        "data enters."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-python-gradual",
                    text=(
                        "\"Gradual\" is the operative word, and it is why the migration story "
                        "worked: annotation coverage is adoptable file by file, so large "
                        "untyped codebases move over incrementally — new code fully annotated, "
                        "the checker's strictness ratcheted up as coverage grows. Starting "
                        "strict, this repo's choice, is dramatically cheaper than "
                        "retrofitting: every line is born checked, and the annotations pay "
                        "their own way immediately in editor tooling — jump-to-definition, "
                        "rename refactoring, and signature help all read the same types mypy "
                        "does."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="why-python-stack",
                    language="toml",
                    caption="The whole server, dependency-wise.",
                    source="server/pyproject.toml",
                    snippet=(
                        "[project]\n"
                        "name = \"guide\"\n"
                        "version = \"0.1.0\"\n"
                        "description = \"FastAPI Developers Guide server: the typed content API that is the guide\"\n"
                        "requires-python = \">=3.13\"\n"
                        "dependencies = [\n"
                        "    \"fastapi>=0.115\",\n"
                        "    \"pydantic>=2.9\",\n"
                        "    \"pydantic-settings>=2.6\",\n"
                        "    \"structlog>=24.4\",\n"
                        "    \"uvicorn[standard]>=0.30\",\n"
                        "]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-python-tradeoffs",
                    text=(
                        "Where Python is the wrong tool, stated plainly:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="why-python-wrong-tool-list",
                    ordered=False,
                    items=[
                        "Sustained CPU-bound number crunching in pure Python loops — "
                        "interpreter overhead plus the GIL; reach for NumPy-native code, a "
                        "compiled extension, or another language.",
                        "Hard real-time constraints — the garbage collector pauses "
                        "unpredictably.",
                        "Very large refactors across untyped legacy code — though that "
                        "last one is exactly what the type-hints section ahead exists to "
                        "prevent.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="why-python-io-bound",
                    text=(
                        "For I/O-bound API servers, where a request "
                        "arrives, the handler waits on PostgreSQL or Redis, and a response "
                        "leaves, CPython's per-request cost is negligible — and the async "
                        "runtime (topic 02) makes the waiting cheap too."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-python-tour-map",
                    text=(
                        "The rest of this topic is the language tour in the order this server "
                        "uses it: the bare-language basics — control flow, loops, functions, "
                        "classes — then the core data structures and strings, type hints, "
                        "the dataclass/pydantic split, None discipline, the module system, "
                        "exceptions with context managers, comprehensions with generators — "
                        "and then the punchline: what those types actually "
                        "are at runtime, which is the subject of this topic's live demo."
                    ),
                ),
            ],
        ),
        # ── 2. Python basics: control flow, loops, functions, classes ───────
        Section(
            id="python-basics",
            title="Python basics: control flow, loops, functions, classes",
            lead="The tour assumes no prior Python — every mechanic below is one this server actually uses.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="basics-pitch",
                    text=(
                        "Control flow first. An ``if`` takes a condition and a colon, and "
                        "the indented block underneath is the branch — indentation IS the "
                        "block structure in Python, there are no braces, and mixing "
                        "indentation widths is a syntax error, not a style nit. ``elif`` "
                        "chains further conditions, ``else`` catches everything left; an "
                        "honest chain reads ``if status >= 500: ... elif status >= 400: "
                        "... else: ...``. Conditions need no parentheses, and truthiness "
                        "follows fixed rules: empty containers, 0, \"\", and None are all "
                        "falsy — though for None specifically this repo tests identity "
                        "(``is None``), a discipline the None section formalizes. The "
                        "ternary expression folds a two-way branch into a value — "
                        "``a if cond else b``, read in exactly that order — and because it "
                        "is an expression it slots into a return or an assignment. Python "
                        "3.10 added ``match``: structural pattern matching that destructures "
                        "as it selects — ``match command: case (\"get\", key): ...`` binds "
                        "the parts of a tuple while choosing the branch, and literals, "
                        "classes, and mapping patterns compose the same way. It is a "
                        "richer switch, not an if-replacement: this server's decisions are "
                        "two-way, so its branching is honestly if-based and ``match`` "
                        "appears here in prose only — you will meet it across modern 3.10+ "
                        "codebases:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="basics-control-flow",
                    language="py",
                    caption="A real branch: exact match first, a ternary for the leftover split.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "def kind_for_http_status(status: int) -> FailureKind:\n"
                        "    # …\n"
                        "    exact = _KIND_BY_HTTP_STATUS.get(status)\n"
                        "    if exact is not None:\n"
                        "        return exact\n"
                        "    return FailureKind.NOT_FOUND if status < 500 else FailureKind.INTERNAL"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="basics-loops",
                    text=(
                        "Python's ``for`` is a foreach: ``for x in xs:`` runs the body once "
                        "per element of ANY iterable — a list, a dict (keys), a string "
                        "(characters), a generator. There is no C-style three-part header; "
                        "the loop tools, in one place:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="basics-loop-tools-list",
                    ordered=False,
                    items=[
                        "``enumerate(xs)`` — the idiom when you need indices; yields "
                        "(index, item) pairs — the quote below numbers snippet lines from "
                        "one because its failure reasons are for humans.",
                        "``range(start, stop)`` — produces the half-open integer sequence "
                        "on demand — the streaming demo's ``range(1, item_count + 1)`` "
                        "walks 1 through item_count inclusive.",
                        "``zip(a, b)`` — walks two iterables in lockstep and stops at the "
                        "shorter; nothing here zips yet, so it lives in prose.",
                        "``while cond:`` — repeats until the condition falsifies — the "
                        "tool when the trip count is not knowable up front, like advancing "
                        "a scan position.",
                        "``break`` / ``continue`` — inside any body, ``break`` exits the "
                        "loop and ``continue`` jumps to the next iteration.",
                        "``else`` on a loop — the rarely-known truth: it runs only when "
                        "the loop finished WITHOUT ``break`` — it is the completed-search "
                        "idiom (``for ... : if hit: break`` / ``else: report absence``), "
                        "not an error path.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="basics-loops-no-break",
                    text=(
                        "This repo contains "
                        "no ``break`` at all — its loops return early instead, like the "
                        "scan below — so it never needs loop-``else`` either; read the "
                        "keyword as no-break or it will masquerade as if/else:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="basics-loops-scan",
                    language="py",
                    caption="for + enumerate + while in one real two-pointer scan.",
                    source="server/guide/content/snippet_matcher.py",
                    snippet=(
                        "    position = 0\n"
                        "    for number, line in enumerate(snippet_lines, start=1):\n"
                        "        while position < len(source_lines) and source_lines[position] != line:\n"
                        "            position += 1\n"
                        "        if position == len(source_lines):\n"
                        "            return SnippetMatch(\n"
                        "                ok=False,\n"
                        "                reason=(\n"
                        "                    f\"snippet line {number} not found in source (in order): \"\n"
                        "                    f\"{_short(line)!r}\"\n"
                        "                ),\n"
                        "            )\n"
                        "        position += 1\n"
                        "    return SnippetMatch(ok=True, reason=None)"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="basics-loops-range",
                    language="py",
                    caption="range over the half-open bounds — one tick per loop turn.",
                    source="server/guide/domain/demos/runtime_streaming.py",
                    snippet=(
                        "    for index in range(1, item_count + 1):\n"
                        "        await asyncio.sleep(tick)  # the simulated I/O between yields\n"
                        "        yield _encode(\n"
                        "            StreamChunk(\n"
                        "                seq=index,\n"
                        "                kind=\"item\",\n"
                        "                label=f\"loop-tick-{index}\",\n"
                        "                detail=f\"yielded after {tick * 1000:.0f}ms of simulated io\",\n"
                        "            )\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="basics-functions",
                    text=(
                        "A function is ``def name(parameters) -> return_type:`` plus an "
                        "indented body; ``return`` hands back a value, and falling off "
                        "the end returns None. Parameters may carry defaults — "
                        "``capacity: int = SPAN_LOG_CAPACITY`` below — which makes them "
                        "optional, and keyword call syntax (``append(event=\"setup\")``) "
                        "keeps call sites self-documenting. One trap earns its own "
                        "paragraph: defaults evaluate ONCE, at definition time. A mutable "
                        "default — ``def add(item, items=[])`` — is a single list shared "
                        "by every call; appends leak between invocations. The classic fix "
                        "is the None sentinel (default to None, build the container "
                        "inside), and this repo's discipline is stronger still: every "
                        "default in it is an immutable constant, and the class that owns "
                        "a list creates it in __init__, once per instance — quoted below. "
                        "``*args`` and ``**kwargs`` collect surplus positional and keyword "
                        "arguments into a tuple and a dict; you will read them throughout "
                        "library code, but never in this server — a typed codebase wants "
                        "fixed, checked, honestly-named signatures. The bare ``*`` "
                        "separator marks the parameters after it keyword-only (``def f(a, "
                        "*, b)`` forces ``b=...`` at call sites) and ``/`` dually marks "
                        "positional-only — readability guards the standard library uses "
                        "heavily and this repo's small signatures don't yet need. Lambdas "
                        "are single-expression anonymous functions — ``lambda group: "
                        "group.order`` — and their honest scope is exactly the next "
                        "block's: sort keys and one-shot callbacks. The moment a function "
                        "needs a statement, an annotation, or a name, def it."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="basics-functions-lambda",
                    language="py",
                    caption="The repo's only lambdas: both sorted() key functions.",
                    source="server/guide/presentation/routers/content.py",
                    snippet=(
                        "@router.get(\"\", response_model=ContentListResponse, response_model_exclude_none=True)\n"
                        "def list_content(\n"
                        "    registry: Annotated[ContentRegistry, Depends(get_content_registry)],\n"
                        ") -> ContentListResponse:\n"
                        "    \"\"\"Serve the whole topic index: groups then topics, each sorted by order.\"\"\"\n"
                        "    return ContentListResponse(\n"
                        "        version=CONTENT_API_VERSION,\n"
                        "        groups=sorted(registry.groups(), key=lambda group: group.order),\n"
                        "        topics=sorted(registry.summaries(), key=lambda summary: summary.order),\n"
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="basics-classes",
                    text=(
                        "Classic class syntax: ``class Name:`` with a docstring, then "
                        "``__init__`` — the initializer every construction calls, so "
                        "``RequestSpan(log)`` invokes ``__init__(self, log)``. ``self`` is "
                        "the instance, passed explicitly as the first parameter of every "
                        "method, and attribute assignment (``self.span_id = ...``) is how "
                        "fields come to exist. A leading underscore is private-by-"
                        "convention — Python enforces no privacy, only adults. Methods "
                        "are functions defined on the class and called on instances. "
                        "``@property`` exposes a method as a computed attribute — callers "
                        "write ``log.capacity`` with no parentheses while the class "
                        "controls the derivation; the core Result type uses the same "
                        "decorator to make impossible accesses raise. Inheritance is "
                        "``class Child(Parent):`` — the child reuses and overrides, and "
                        "``super()`` reaches the parent implementation from inside an "
                        "override (AppError's __init__ ends with ``super().__init__"
                        "(message)`` so the exception machinery keeps working — quoted "
                        "with the exceptions section). Multiple inheritance exists with a "
                        "defined method resolution order, but the composition-over-"
                        "inheritance rule this repo follows leaves you single inheritance "
                        "for framework contracts: SpanResponse(JSONResponse), "
                        "ContentDetail(Topic). Dunders — ``__repr__`` (the debug "
                        "representation), ``__str__`` (the human one; AppError builds it "
                        "with an f-string), ``__eq__`` (equality) — are the protocol "
                        "hooks. And the bridge: you will mostly NOT write them by hand "
                        "here, because @dataclass generates __init__, __repr__ and __eq__ "
                        "from a field list and pydantic models validate as they "
                        "construct — the dataclasses-vs-pydantic section ahead is exactly "
                        "that split. Classic classes remain right for behavior and "
                        "invariants rather than data shape: SpanLog guards a lock and a "
                        "bound; RequestSpan mints an id and clocks itself; neither is a "
                        "record."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="basics-classes-log",
                    language="py",
                    caption="Constructor discipline: a default arg, a defensive raise, per-instance mutable state, a property.",
                    source="server/guide/presentation/dependencies/request_span.py",
                    snippet=(
                        "    def __init__(self, capacity: int = SPAN_LOG_CAPACITY) -> None:\n"
                        "        \"\"\"Hold the last ``capacity`` events (at least one).\"\"\"\n"
                        "        if capacity < 1:\n"
                        "            raise ValueError(\"capacity must be at least 1\")\n"
                        "        self._capacity = capacity\n"
                        "        self._events: list[SpanEvent] = []\n"
                        "        self._lock = threading.Lock()\n"
                        "        self._next_sequence = 0\n"
                        "\n"
                        "    @property\n"
                        "    def capacity(self) -> int:\n"
                        "        \"\"\"The ring's bound (events held never exceed it).\"\"\"\n"
                        "        return self._capacity"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="basics-classes-span",
                    language="py",
                    caption="A whole classic class: initializer, self, two methods, no boilerplate.",
                    source="server/guide/presentation/dependencies/request_span.py",
                    snippet=(
                        "class RequestSpan:\n"
                        "    \"\"\"The per-request span a handler receives from the yield dependency.\"\"\"\n"
                        "\n"
                        "    def __init__(self, log: SpanLog) -> None:\n"
                        "        \"\"\"Open a span: mint the id, remember the clock origin and log.\"\"\"\n"
                        "        self.span_id: Final[str] = uuid4().hex[:12]\n"
                        "        self.opened_at: Final[str] = datetime.now(UTC).isoformat(timespec=\"milliseconds\")\n"
                        "        self._log = log\n"
                        "        self._opened_clock: Final[float] = time.perf_counter()\n"
                        "\n"
                        "    def record(self, event: SpanEventName) -> None:\n"
                        "        \"\"\"Append one beat of this span, timestamped and offset from setup.\"\"\"\n"
                        "        offset_ms = round((time.perf_counter() - self._opened_clock) * 1000)\n"
                        "        self._log.append(\n"
                        "            span_id=self.span_id,\n"
                        "            event=event,\n"
                        "            at=datetime.now(UTC).isoformat(timespec=\"milliseconds\"),\n"
                        "            offset_ms=offset_ms,\n"
                        "        )\n"
                        "\n"
                        "    def elapsed_ms(self) -> int:\n"
                        "        \"\"\"Milliseconds since this span opened (how the handler reports itself).\"\"\"\n"
                        "        return round((time.perf_counter() - self._opened_clock) * 1000)"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="basics-classes-inheritance",
                    language="py",
                    caption="Real inheritance: a Topic plus one field — pydantic models subclass too.",
                    source="server/guide/content/models.py",
                    snippet=(
                        "class ContentDetail(Topic):\n"
                        "    \"\"\"The detail route's response model: a full Topic plus the API version.\n"
                        "\n"
                        "    Family contract: BOTH content endpoints serve ``version`` so a client\n"
                        "    can detect a CONTENT_API_VERSION bump on any content response and\n"
                        "    migrate deliberately.\n"
                        "    \"\"\"\n"
                        "\n"
                        "    version: int"
                    ),
                ),
            ],
        ),
        # ── 3. Data structures and strings ──────────────────────────────────
        Section(
            id="python-data-and-strings",
            title="Built-in data structures and strings",
            lead="The four containers, indexing and slicing, and how strings get built.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="basics-data-structures",
                    text=(
                        "Four built-ins carry almost every data shape:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="basics-data-structures-list",
                    ordered=False,
                    items=[
                        "``list`` — ordered, mutable: literal ``[1, 2]``, grown with "
                        "``.append(x)``, and the defensive-copy idiom ``list(xs)`` (the "
                        "registry's ``groups()``) whenever a class must not leak its "
                        "internals.",
                        "``dict`` — key to value with constant-time lookup by hashable "
                        "key: literal ``{\"py\": style}``, read with ``d[k]`` (KeyError "
                        "on miss) or ``d.get(k)`` / ``d.get(k, fallback)`` for expected "
                        "absence — the control-flow quote's "
                        "``_KIND_BY_HTTP_STATUS.get(status)`` — while ``k in d`` tests "
                        "the keys.",
                        "``set`` — unordered, unique members, fast membership: literal "
                        "``{1, 2}``, but the EMPTY set is ``set()`` because ``{}`` is an "
                        "empty dict (the classic miss), grown with ``.add(x)``.",
                        "``tuple`` — ordered and immutable: a fixed record of positions, "
                        "unpackable — ``for number, line in enumerate(...)`` unpacks one "
                        "per iteration — and a single-element tuple needs its trailing "
                        "comma, ``(1,)``.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="basics-choosing-containers",
                    text=(
                        "Choosing among them is "
                        "the data-structure question: sequence → list; lookup by key → "
                        "dict; membership and deduplication → set; fixed-shape record "
                        "(and every dict key) → tuple. The registry's validation pass is "
                        "the honest composition — one set of seen topic ids and one dict "
                        "mapping each order to the topic that claimed it, maintained "
                        "across a loop with membership guards and dict assignment. The "
                        "annotations on the literals (``Final[dict[str, _CommentStyle]]``) "
                        "say what they hold; the type-hints section next makes those "
                        "annotations the whole story:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="basics-ds-registry",
                    language="py",
                    caption="The validator's bookkeeping: a set for seen ids, a dict for claimed orders.",
                    source="server/guide/content/registry.py",
                    snippet=(
                        "    seen_topic_ids: set[str] = set()\n"
                        "    seen_orders: dict[int, str] = {}\n"
                        "    for topic in topics:\n"
                        "        if topic.id in seen_topic_ids:\n"
                        "            raise RegistryError(f\"duplicate topic id: {topic.id!r}\")\n"
                        "        seen_topic_ids.add(topic.id)\n"
                        "\n"
                        "        if topic.group not in known_group_ids:\n"
                        "            raise RegistryError(\n"
                        "                f\"unknown group: topic {topic.id!r} references group {topic.group!r} \"\n"
                        "                \"that the registry does not define\"\n"
                        "            )\n"
                        "\n"
                        "        if topic.order in seen_orders:\n"
                        "            raise RegistryError(\n"
                        "                f\"duplicate topic order: {topic.order} used by \"\n"
                        "                f\"{seen_orders[topic.order]!r} and {topic.id!r}\"\n"
                        "            )\n"
                        "        seen_orders[topic.order] = topic.id"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="basics-ds-literals",
                    language="py",
                    caption="Real literals: a dict of per-language styles, a tuple of quote characters.",
                    source="server/guide/content/snippet_matcher.py",
                    snippet=(
                        "_STYLES: Final[dict[str, _CommentStyle]] = {\n"
                        "    \"py\": _CommentStyle(line_tokens=(\"#\",)),\n"
                        "    \"toml\": _CommentStyle(start_only_tokens=(\"#\",)),\n"
                        "    \"yaml\": _CommentStyle(start_only_tokens=(\"#\",)),\n"
                        "    \"yml\": _CommentStyle(start_only_tokens=(\"#\",)),\n"
                        "    \"ts\": _CommentStyle(line_tokens=(\"//\",)),\n"
                        "    \"tsx\": _CommentStyle(line_tokens=(\"//\",)),\n"
                        "    \"js\": _CommentStyle(line_tokens=(\"//\",)),\n"
                        "    \"sql\": _CommentStyle(start_only_tokens=(\"--\",)),\n"
                        "    \"css\": _CommentStyle(line_tokens=(\"//\",), block_start=\"/*\", block_end=\"*/\"),\n"
                        "    \"html\": _CommentStyle(block_start=\"<!--\", block_end=\"-->\", quote_aware=False),\n"
                        "}\n"
                        "\n"
                        "_QUOTE_CHARS: Final[tuple[str, ...]] = (\"'\", '\"', \"`\")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="basics-slicing",
                    text=(
                        "Every sequence — list, tuple, str — indexes from zero: ``xs[0]`` "
                        "is the first element, and negative indices count from the end — "
                        "the matcher asks ``code_so_far[-1] in _WHITESPACE`` to inspect "
                        "the character just written. Slicing takes a subsequence with "
                        "``xs[start:stop]``: half-open (stop excluded), either end "
                        "omittable (``xs[:n]`` is the first n, ``xs[n:]`` the rest), and "
                        "a third slot is the step — ``xs[::2]`` every second element, "
                        "``xs[::-1]`` the reversal idiom. A slice of a list is a new, "
                        "shallow-copied list; a slice of a string, a new string. This "
                        "repo's slices are all bounds-keeping: ``uuid4().hex[:12]`` cuts "
                        "a 32-character hex id to its 12-character display form (you "
                        "watched RequestSpan mint one), ``_short`` below caps a line at "
                        "80 characters, the span log evicts its own history with ``del "
                        "self._events[: len(self._events) - self._capacity]`` (quoted in "
                        "full with the context-manager section), and the comment stripper "
                        "advances past a block comment with ``text[end + len(style."
                        "block_end) :]`` — the start omitted after a computed boundary. "
                        "Strings being immutable sequences shapes their methods: nothing "
                        "mutates in place — ``.strip()``, ``.split()``, ``.splitlines()``, "
                        "``.replace()`` all return new strings, and ``\"\".join(parts)`` "
                        "is the idiomatic assembly (repeated ``+=`` in a loop is the "
                        "quadratic anti-pattern). ``in`` on a string is the substring "
                        "test; ``len()`` counts code points."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="basics-slicing-bounds",
                    language="py",
                    caption="A negative index and a capped slice — both real, one file apart.",
                    source="server/guide/content/snippet_matcher.py",
                    snippet=(
                        "def _at_token_boundary(code_so_far: str) -> bool:\n"
                        "    \"\"\"True when a start-only comment token is at line start/after whitespace.\"\"\"\n"
                        "    return not code_so_far or code_so_far[-1] in _WHITESPACE\n"
                        "\n"
                        "# …\n"
                        "\n"
                        "def _short(line: str) -> str:\n"
                        "    \"\"\"Cap a line for failure reasons so they stay readable.\"\"\"\n"
                        "    return line if len(line) <= _MAX_REASON_LINE else line[:_MAX_REASON_LINE] + _ELLIPSIS_CHAR"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="basics-formatting",
                    text=(
                        "String formatting has one modern default: the f-string. Prefix a "
                        "literal with f and ``{expression}`` interpolates anything — "
                        "attributes, calls, arithmetic — like the scan's ``f\"snippet "
                        "line {number} not found in source (in order): {_short(line)!r}\"``, "
                        "which calls _short at format time. The ``!r`` conversion formats "
                        "with repr, quotes visible — right for identifiers in error "
                        "messages. After the value, a colon starts a format spec: the "
                        "streaming loop's ``{tick * 1000:.0f}`` rounds a float to zero "
                        "decimals inside the interpolation, and ``{id(obj):x}`` renders "
                        "an integer as hex — the demo's identity tokens are built "
                        "exactly so. Since 3.8, ``{x=}`` prints the expression and its "
                        "value together, made for debugging. The honest history, because "
                        "you will read all three eras: ``%`` formatting (``\"name=%s\" % "
                        "value``) is the oldest and survives mainly in logging, where "
                        "the argument stays lazy — the structlog calls in this server "
                        "pass event names and key=value pairs to the logger rather than "
                        "pre-formatting, so a filtered-out line costs nothing. ``\"…\"."
                        "format(value)`` arrived in 3.0 and ruled until f-strings landed "
                        "in 3.6 and won on every axis: compile-time parsing, arbitrary "
                        "expressions, readability. This repo's rule falls out — f-strings "
                        "for every constructed message (each RegistryError raise above "
                        "names its subject with ``{x!r}``), keyword-argument logging at "
                        "the logger boundary. And one discipline worth adopting cold: "
                        "f-strings are for display, never for assembling commands, "
                        "queries, or paths from untrusted input — interpolation there is "
                        "the injection bug class, and parameterization is the fix."
                    ),
                ),
            ],
        ),
        # ── 4. Type hints + mypy ────────────────────────────────────────────
        Section(
            id="type-hints",
            title="Type hints and mypy",
            blocks=[
                TextBlock(
                    kind="text",
                    id="type-hints-syntax",
                    text=(
                        "Every function signature and class field in this repo carries "
                        "annotations, and the syntax is the product of a decade of PEPs:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="type-hints-core-forms-list",
                    ordered=False,
                    items=[
                        "Primitives — the classes themselves: text: str, times: int, "
                        "ok: bool.",
                        "Containers — subscript directly since 3.9 — list[Section], "
                        "dict[str, Topic], tuple[Topic, ...] — no typing.List imports "
                        "anywhere.",
                        "Absence — a union: X | None (PEP 604) replaced Optional[X]; a "
                        "type checker treats them identically, though at runtime they "
                        "build different objects — Optional[str] is a typing.Union "
                        "alias, str | None is a types.UnionType, and Section 10 "
                        "displays the latter.",
                        "``Literal`` — where unions generally mean \"either\", Literal "
                        "narrows to exact values: the demo scenario's inject_failure is "
                        "Literal[\"none\", \"error\", \"latency\"], so an illegal value is a "
                        "type error, not a runtime surprise.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="type-hints-modern",
                    text=(
                        "Generics got cheap in 3.12 (PEP 695): class Ok[T] parameterizes a "
                        "class with no TypeVar ceremony, and a type alias is an ordinary "
                        "expression — type Result[T] = Ok[T] | Err. Around them live the "
                        "finishing touches this repo uses daily:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="type-hints-touches-list",
                    ordered=False,
                    items=[
                        "``Final`` — for must-not-reassign names.",
                        "``Annotated`` — for attaching metadata (pydantic's "
                        "discriminated unions are built on it).",
                        "``Never`` — for values that cannot exist.",
                    ],
                ),
                CodeBlock(
                    kind="code",
                    id="type-hints-config",
                    language="py",
                    caption="Typed settings — every field declares what parses into it.",
                    source="server/guide/core/config.py",
                    snippet=(
                        "class AppConfig(BaseSettings):\n"
                        "    \"\"\"Process-wide settings; each field name doubles as its env var name.\"\"\"\n"
                        "\n"
                        "    model_config = SettingsConfigDict(env_prefix=\"FDG_\", frozen=True)\n"
                        "\n"
                        "    env: str = \"dev\"\n"
                        "    debug: bool = False\n"
                        "    database_url: str = \"postgresql+asyncpg://postgres:guide@localhost:5432/guide\"\n"
                        "    redis_url: str = \"redis://localhost:6379\"\n"
                        "    mongo_url: str = \"mongodb://localhost:27017\"\n"
                        "    log_level: str = \"info\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="type-hints-mypy",
                    text=(
                        "Annotations change nothing at runtime — enforcing them is mypy's job, "
                        "a separate static pass over the source that reads the annotations and "
                        "proves every call site agrees. This repo runs mypy strict: every "
                        "function annotated (constructors included), no implicit Any leaking "
                        "through generics, no returning Any where a type is declared. The "
                        "pydantic plugin pulls model classes into the proof: it synthesizes "
                        "each model's __init__ signature from its field declarations, so "
                        "Topic(id=123, ...) is rejected at the call site before the process "
                        "ever runs."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="type-hints-strict",
                    text=(
                        "Strict mode deserves spelling out, because it is the difference "
                        "between decoration and checking:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="type-hints-strict-rules-list",
                    ordered=False,
                    items=[
                        "``disallow_untyped_defs`` — means no unannotated function is "
                        "left to rot.",
                        "``disallow_any_generics`` and ``warn_return_any`` — mean Any "
                        "cannot sneak through a generic or a return statement.",
                        "``no_implicit_optional`` — means a parameter is Optional only "
                        "when you wrote it so.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="type-hints-strict-payoff",
                    text="Each rule exists because its absence is precisely where bugs hide.",
                ),
                TextBlock(
                    kind="text",
                    id="type-hints-generic-machinery",
                    text=(
                        "The generic machinery is not decorative. guide/core/result.py "
                        "implements Result[T] — the values-not-exceptions pattern this repo's "
                        "use cases return — with the PEP 695 syntax: one class generic over "
                        "its success payload, and a type alias naming the union:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="type-hints-result",
                    language="py",
                    caption="PEP 695 generics: parameterized class + type alias expression.",
                    source="server/guide/core/result.py",
                    snippet=(
                        "@final\n"
                        "@dataclass(frozen=True, slots=True)\n"
                        "class Ok[T]:\n"
                        "    \"\"\"The success variant; holds exactly one value.\"\"\"\n"
                        "\n"
                        "    value: T\n"
                        "\n"
                        "    # …\n"
                        "\n"
                        "type Result[T] = Ok[T] | Err"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="type-hints-mypy-config",
                    language="toml",
                    caption="The entire mypy configuration.",
                    source="server/pyproject.toml",
                    snippet=(
                        "[tool.mypy]\n"
                        "strict = true\n"
                        "plugins = [\"pydantic.mypy\"]\n"
                        "python_version = \"3.13\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="type-hints-contract",
                    text=(
                        "The verifier is `uv run mypy guide` against the locked environment — "
                        "the quoted block is the whole configuration. The contract that falls "
                        "out of it: annotations are intent, mypy proves the intent holds at "
                        "every call site, and the interpreter itself ignores every annotation. "
                        "That last clause is not a disclaimer — it is the subject of this "
                        "topic's live demo in Section 10."
                    ),
                ),
            ],
        ),
        # ── 5. dataclasses vs pydantic ──────────────────────────────────────
        Section(
            id="dataclasses-vs-pydantic",
            title="dataclasses vs pydantic models",
            blocks=[
                TextBlock(
                    kind="text",
                    id="dc-py-dataclass-idea",
                    text=(
                        "Most classes on a server are records: named fields, an initializer, "
                        "equality, a repr. Python has two standard answers, and they differ on "
                        "exactly one question — where did the data come from? If your own code "
                        "constructed it, a dataclass is enough: @dataclass generates "
                        "__init__, __repr__ and __eq__ from the field list, and this repo "
                        "always reaches for the two strictness flags. frozen=True makes "
                        "instances immutable and hashable — safe as set members and dict keys. "
                        "slots=True gives instances __slots__ instead of a per-instance "
                        "__dict__ — less memory, faster attribute access, and no accidentally "
                        "creating new attributes later. The snippet matcher's return value is "
                        "the canonical example:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dc-py-snippet-match",
                    language="py",
                    caption="A frozen, slotted dataclass — built and trusted in-process.",
                    source="server/guide/content/snippet_matcher.py",
                    snippet=(
                        "@dataclass(frozen=True, slots=True)\n"
                        "class SnippetMatch:\n"
                        "    \"\"\"Outcome of one snippet verification; truthy when ok.\"\"\"\n"
                        "\n"
                        "    ok: bool\n"
                        "    reason: str | None = None\n"
                        "\n"
                        "    def __bool__(self) -> bool:\n"
                        "        return self.ok"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dc-py-pydantic-idea",
                    text=(
                        "If the data crossed a trust boundary — an HTTP body, an environment "
                        "variable, another service's response — you want pydantic. A "
                        "BaseModel does what a dataclass does plus the parts that matter at an "
                        "edge:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="dc-py-edge-capabilities-list",
                    ordered=False,
                    items=[
                        "Validates on construction — wrong types are rejected with "
                        "structured errors instead of becoming corrupt state.",
                        "Coerces where coercion is sane — \"true\" from an env var "
                        "becomes True.",
                        "Serializes back out — with alias control.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="dc-py-camel-convention",
                    text=(
                        "Every wire model in this repo "
                        "derives from one CamelModel base: Python fields stay snake_case while "
                        "the wire is camelCase (sectionCount, not section_count), parsing "
                        "accepts both spellings, and instances are frozen — a wire model is an "
                        "immutable snapshot, never mutated in place:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dc-py-camel-model",
                    language="py",
                    caption="One base class defines the repo's whole wire convention.",
                    source="server/guide/core/serialization.py",
                    snippet=(
                        "class CamelModel(BaseModel):\n"
                        "    \"\"\"Base for every wire model: camelCase aliases, both-direction parsing, frozen.\"\"\"\n"
                        "\n"
                        "    model_config = ConfigDict(\n"
                        "        alias_generator=to_camel,\n"
                        "        populate_by_name=True,\n"
                        "        frozen=True,\n"
                        "    )"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="dc-py-topic-model",
                    language="py",
                    caption="The Topic model this very page is served through.",
                    source="server/guide/content/models.py",
                    snippet=(
                        "class Topic(CamelModel):\n"
                        "    \"\"\"A whole guide page: ordered sections, the unit the detail route serves.\"\"\"\n"
                        "\n"
                        "    id: str\n"
                        "    title: str\n"
                        "    subtitle: str | None = None\n"
                        "    group: str\n"
                        "    order: int\n"
                        "    sections: list[Section]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dc-py-choosing",
                    text=(
                        "The decision rule this repo follows: values you built yourself travel "
                        "as frozen dataclasses — SnippetMatch above is created by our code and "
                        "trusted by our code. Anything that arrived from outside is parsed "
                        "into a pydantic model at the boundary, then travels inward as a "
                        "validated, typed, immutable object. Performance is not the decider — "
                        "pydantic v2's validation core is written in Rust and is genuinely "
                        "fast — correctness placement is: pay for validation exactly once, "
                        "where trust changes. Note Topic's subtitle: str | None = None — "
                        "optional-with-default is the pydantic idiom for fields the wire may "
                        "simply omit."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="dc-py-dataclass-details",
                    text=(
                        "Two dataclass details worth knowing cold: mutable defaults are "
                        "forbidden in plain fields — default_factory=list is the escape "
                        "hatch, because a shared list as a default would be a bug factory — "
                        "and eq=True (the default) combined with frozen=True is what makes "
                        "instances legitimately hashable, fit for sets and dict keys. "
                        "SnippetMatch gets both behaviors for one decorator."
                    ),
                ),
            ],
        ),
        # ── 6. None and defensive returns ───────────────────────────────────
        Section(
            id="none-and-defensive",
            title="None and defensive returns",
            blocks=[
                TextBlock(
                    kind="text",
                    id="none-pitch",
                    text=(
                        "None is a value, not an error: it means \"no such thing\", and the "
                        "discipline is to say so in the signature. A lookup that can miss "
                        "returns Topic | None — the caller cannot pretend missingness away, "
                        "because mypy will not let them use the result as a Topic until they "
                        "narrow it. Two mechanical rules: test with `is None` / `is not None` "
                        "(identity — == can be fooled by an __eq__ override), and make the "
                        "decision at the edge, once. The registry below returns None for "
                        "unknown ids; the router alone decides what that means in HTTP terms:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="none-registry-lookup",
                    language="py",
                    caption="A typed lookup: absence is part of the contract.",
                    source="server/guide/content/registry.py",
                    snippet=(
                        "    def topic_by_id(self, topic_id: str) -> Topic | None:\n"
                        "        \"\"\"The full topic, or None when the id is unknown.\"\"\"\n"
                        "        return self._topics_by_id.get(topic_id)"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="none-router-404",
                    language="py",
                    caption="The edge decides policy: None becomes the 404 envelope.",
                    source="server/guide/presentation/routers/content.py",
                    snippet=(
                        "    topic = registry.topic_by_id(topic_id)\n"
                        "    if topic is None:\n"
                        "        raise AppError(FailureKind.NOT_FOUND, f\"Topic '{topic_id}' not found\")\n"
                        "    return ContentDetail.model_validate({**topic.model_dump(), \"version\": CONTENT_API_VERSION})"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="none-defensive-ladder",
                    text=(
                        "That None → 404 mapping is the bottom rung of a defensive ladder the "
                        "whole server climbs."
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="none-defensive-ladder-list",
                    ordered=False,
                    items=[
                        "Expected absence — Optional in the signature.",
                        "Expected failure — not absence, something went wrong: Result[T], "
                        "this repo's Ok/Err values, so failure is data the caller must "
                        "handle rather than an exception that might fly past unnoticed.",
                        "Impossible states — type them Never — accessing the payload a "
                        "Result variant does not hold is a loud programming error, not a "
                        "silent None:",
                    ],
                ),
                CodeBlock(
                    kind="code",
                    id="none-never",
                    language="py",
                    caption="Never: the type of a value that cannot exist.",
                    source="server/guide/core/result.py",
                    snippet=(
                        "    @property\n"
                        "    def failure(self) -> Never:\n"
                        "        \"\"\"Always raises: an Ok holds no failure.\"\"\"\n"
                        "        raise UnwrapError(\".failure accessed on Ok\")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="none-layering",
                    text=(
                        "The layering payoff: the domain knows nothing of HTTP. topic_by_id "
                        "returns None; use cases wrap failures in Result; only the "
                        "presentation edge maps an AppError's FailureKind onto a status code "
                        "inside the shared error envelope, with the request id attached. One "
                        "taxonomy, defined once, tested once — topic 30 takes it apart in "
                        "depth."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="none-get-fallback",
                    text=(
                        "One last None habit that pays specifically in HTTP code: "
                        "dict.get(key, fallback) is for when a fallback genuinely exists; "
                        "returning None is for when the caller must decide. Blurring them "
                        "produces APIs where \"not found\" and \"found, but empty\" are "
                        "indistinguishable. The registry deliberately returns None rather "
                        "than any stand-in Topic because the router needs that distinction "
                        "to answer 404 versus 200."
                    ),
                ),
            ],
        ),
        # ── 7. Modules, packages, imports ───────────────────────────────────
        Section(
            id="modules-and-imports",
            title="Modules, packages, and imports",
            blocks=[
                TextBlock(
                    kind="text",
                    id="modules-pitch",
                    text=(
                        "Python's unit of reuse is the module — one .py file, executed once, "
                        "cached as a module object in sys.modules. A directory containing an "
                        "__init__.py is a package; importing anything inside it runs the "
                        "__init__ first, which is why a heavy __init__ taxes every import. "
                        "This repo keeps one short root package, guide/, a deliberate family "
                        "decision so teaching imports stay short: guide.core.errors beats "
                        "com.family.guide.core.errors. Imports are absolute throughout — "
                        "never relative — so every file's dependencies are greppable from "
                        "anywhere. The composition root's import block is the style reference:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="modules-main-imports",
                    language="py",
                    caption="The app factory's imports: stdlib, third-party, first-party.",
                    source="server/guide/main.py",
                    snippet=(
                        "from typing import Final\n"
                        "\n"
                        "from fastapi import FastAPI\n"
                        "\n"
                        "from guide import __version__\n"
                        "from guide.content.registry import production_registry\n"
                        "from guide.core.config import get_config\n"
                        "from guide.core.errors import register_exception_handlers\n"
                        "from guide.core.logging import configure_logging\n"
                        "from guide.core.request_context import RequestIdMiddleware\n"
                        "from guide.core.scenario import ScenarioStore\n"
                        "from guide.presentation.routers import content, graphql, health, posts, realtime\n"
                        "from guide.presentation.routers.demo import py as demo_py\n"
                        "from guide.presentation.routers.demo import scenario as demo_scenario"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="modules-layout",
                    text=(
                        "The layout mirrors the layer rules the whole guide enforces — "
                        "presentation talks to domain, data implements domain's ports, core "
                        "is the shared kernel, and content is the guide's own teaching held "
                        "as data:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="modules-tree",
                    language="text",
                    caption="server/guide/ — one segment, six packages.",
                    source=None,
                    snippet=(
                        "server/guide/\n"
                        "├── __init__.py            # package root: docstring + __version__\n"
                        "├── main.py                # create_app() — the composition root\n"
                        "├── core/                  # config, errors, result, scenario, serialization, logging\n"
                        "├── content/               # the typed topic registry that IS this guide\n"
                        "│   └── topics/            # one module per topic — this page: python_language.py\n"
                        "├── domain/                # ports (Protocols), use cases, demo payload builders\n"
                        "│   └── teaching/          # compilable exhibits, only where no real counterpart exists\n"
                        "├── data/                  # repository implementations (arrive with the data phases)\n"
                        "└── presentation/          # routers + middleware, thin by invariant"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="modules-init-pitch",
                    text=(
                        "The __init__.py has three jobs: mark the package, define its public "
                        "surface, and document it — the domain package's __init__ states the "
                        "dependency rule outright, so the rule travels with the code. The root "
                        "package's is deliberately minimal, because everything imports it:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="modules-init",
                    language="py",
                    caption="The whole root package: a docstring and a version.",
                    source="server/guide/__init__.py",
                    snippet=(
                        "\"\"\"The FastAPI Developers Guide server package.\n"
                        "\n"
                        "Single-segment root package (family decision) so teaching imports stay short:\n"
                        "``guide.core``, ``guide.content``, ``guide.domain``, and so on. The uvicorn\n"
                        "entrypoint is ``guide.main:app``.\n"
                        "\"\"\"\n"
                        "\n"
                        "__version__ = \"0.1.0\""
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="modules-discipline",
                    text=(
                        "Import discipline is enforced, not aspirational: ruff's isort rules "
                        "demand stdlib first, third-party second, first-party last — visible "
                        "as the three groups in the composition-root quote above. Prefer "
                        "`from X import name` when you use the name, `import X` when you mean "
                        "the module; both appear above. And there is no "
                        "`if __name__ == \"__main__\"` anywhere in this repo — the entrypoint "
                        "is the ASGI server running guide.main:app, the factory pattern topic "
                        "04 dissects."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="modules-no-cycles",
                    text=(
                        "One property the layout enforces by construction: no circular "
                        "imports. The registry imports topic modules, topic modules import "
                        "only the content models, and nothing in content imports "
                        "presentation — dependencies point one way, so import order can "
                        "never matter. When two modules genuinely need each other (rare, and "
                        "usually a design smell), the escape hatches are moving the shared "
                        "name into a third module or importing inside a function; this repo "
                        "uses neither."
                    ),
                ),
            ],
        ),
        # ── 8. Exceptions and context managers ──────────────────────────────
        Section(
            id="exceptions-and-context-managers",
            title="Exceptions and context managers",
            blocks=[
                TextBlock(
                    kind="text",
                    id="exceptions-pitch",
                    text=(
                        "Exceptions are for abnormal flow — the language's non-local exit. A "
                        "raise carries the traceback and unwinds frames until a matching "
                        "except; if nothing matches, the process dies loudly, which is the "
                        "correct default. This repo's taxonomy has two shapes. Typed "
                        "application errors — AppError(kind, message, details) — carry one of "
                        "eight FailureKind buckets that the HTTP edge maps onto statuses; "
                        "nothing outside the errors module invents codes or numbers. And "
                        "module-local correctness errors: the content registry validates "
                        "everything at construction and refuses to exist otherwise, so broken "
                        "teaching content crashes the process at import time — on purpose, "
                        "because startup is the cheapest place to fail:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="exceptions-app-error",
                    language="py",
                    caption="The one error type layers raise; the edge translates it.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "class AppError(Exception):\n"
                        "    \"\"\"Typed application error: kind + message + optional details/headers.\n"
                        "    # …\n"
                        "    \"\"\"\n"
                        "\n"
                        "    def __init__(\n"
                        "        self,\n"
                        "        kind: FailureKind,\n"
                        "        message: str,\n"
                        "        details: dict[str, Any] | None = None,\n"
                        "        headers: dict[str, str] | None = None,\n"
                        "    ) -> None:\n"
                        "        self.kind = kind\n"
                        "        self.message = message\n"
                        "        self.details = details\n"
                        "        self.headers = headers\n"
                        "        super().__init__(message)\n"
                        "\n"
                        "    def __str__(self) -> str:\n"
                        "        return f\"[{self.kind.value}] {self.message}\""
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="exceptions-registry-error",
                    language="py",
                    caption="Fail-fast at construction: broken content never boots.",
                    source="server/guide/content/registry.py",
                    snippet=(
                        "class RegistryError(Exception):\n"
                        "    \"\"\"A registry violated a validation rule; the message names it.\"\"\""
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="exceptions-chaining",
                    language="py",
                    caption="`from exc` keeps the cause chained into the log.",
                    source="server/guide/core/scenario.py",
                    snippet=(
                        "        except ValueError as exc:\n"
                        "            raise AppError(\n"
                        "                FailureKind.VALIDATION_FAILED, f\"Invalid scenario patch: {exc}\"\n"
                        "            ) from exc"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="context-managers-pitch",
                    text=(
                        "Context managers are the other half of error discipline: resource "
                        "pairing that cannot be forgotten. `with x:` calls x.__enter__(), "
                        "runs the body, and guarantees x.__exit__(exc_type, exc, tb) "
                        "afterwards — on success and on exception alike — so release code "
                        "cannot be skipped by a raise. The protocol form implements the two "
                        "dunder methods; returning False from __exit__ means \"do not "
                        "suppress\". The generator form decorates a function with "
                        "@contextmanager: code before the yield is setup, the yield hands "
                        "its value to the as clause, and everything after it — best under "
                        "finally — is teardown. This repo's real counterpart is FastAPI's "
                        "yield dependencies: a request-scoped context manager the "
                        "framework enters before the handler runs and exits after the "
                        "response is sent. The request-span instrument is exactly that, "
                        "and it is production code — every dependency demo on this server "
                        "runs through it (topic 06 dissects the machinery):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cm-span-generator",
                    language="py",
                    caption="The generator form for real — as a FastAPI yield dependency.",
                    source="server/guide/presentation/dependencies/request_span.py",
                    snippet=(
                        "async def open_request_span(log: SpanLogDep) -> AsyncIterator[RequestSpan]:\n"
                        "    \"\"\"FastAPI yield dependency: setup, yield the span, teardown after send.\n"
                        "\n"
                        "    Everything before ``yield`` runs during dependency resolution (before\n"
                        "    the handler); the ``finally`` runs when FastAPI closes the request's\n"
                        "    ``AsyncExitStack`` — for a regular response, after the bytes have been\n"
                        "    sent. The dependency's own sub-dependency (``get_span_log``) is how the\n"
                        "    demo's override test swaps the log for a fake.\n"
                        "    \"\"\"\n"
                        "    span = RequestSpan(log)\n"
                        "    span.record(\"setup\")\n"
                        "    try:\n"
                        "        yield span\n"
                        "    finally:\n"
                        "        span.record(\"teardown\")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cm-protocol-note",
                    text=(
                        "Read it against the generator form taught above: setup before the "
                        "yield, teardown under finally, and the yielded value (the span) is "
                        "what the consumer — here the route handler — receives. The "
                        "async-generator shape is the same contract grown an async prefix; "
                        "FastAPI awaits it around the request. The protocol form "
                        "(__enter__/__exit__) you rarely write yourself in production, "
                        "because the objects worth pairing already implement it — a "
                        "threading.Lock is a context manager, and the span instrument's "
                        "ring buffer uses exactly that to keep its append path safe even "
                        "from threadpool threads:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="cm-lock",
                    language="py",
                    caption="The protocol form, worn daily: a real with-block on a lock.",
                    source="server/guide/presentation/dependencies/request_span.py",
                    snippet=(
                        "    def append(\n"
                        "        self, span_id: str, event: SpanEventName, at: str, offset_ms: int\n"
                        "    ) -> SpanEvent:\n"
                        "        \"\"\"Record one beat; returns the event with its allocated sequence.\"\"\"\n"
                        "        with self._lock:\n"
                        "            span_event = SpanEvent(\n"
                        "                sequence=self._next_sequence,\n"
                        "                span_id=span_id,\n"
                        "                event=event,\n"
                        "                at=at,\n"
                        "                offset_ms=offset_ms,\n"
                        "            )\n"
                        "            self._next_sequence += 1\n"
                        "            self._events.append(span_event)\n"
                        "            if len(self._events) > self._capacity:\n"
                        "                del self._events[: len(self._events) - self._capacity]\n"
                        "        return span_event"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="cm-coda",
                    text=(
                        "Both quotes are the same discipline at two scales: the lock's "
                        "with-block guarantees release even if the body raises; the yield "
                        "dependency's finally guarantees the span closes even if the "
                        "handler raises. And because the teardown records into the shared "
                        "log AFTER the response is sent, the demo's second endpoint can "
                        "prove the ordering — setup, handler, response, teardown — as "
                        "data. Setup, run, guaranteed teardown, exceptions pass through: "
                        "that contract is what FastAPI formalized as a dependency, and "
                        "topic 06 takes it from the language's point of view to the "
                        "framework's."
                    ),
                ),
            ],
        ),
        # ── 9. Comprehensions and generators ────────────────────────────────
        Section(
            id="comprehensions-and-generators",
            title="Comprehensions and generators",
            blocks=[
                TextBlock(
                    kind="text",
                    id="comp-pitch",
                    text=(
                        "A comprehension is a loop declared as a value — "
                        "[make(x) for x in xs if keeps(x)] reads left to right as the shape "
                        "of the result, then the source, then the filter. Compared to a "
                        "statement loop with .append():"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="comp-advantages-list",
                    ordered=False,
                    items=[
                        "Shorter — than a statement loop with .append().",
                        "Leaks no loop variable — comprehensions have their own scope.",
                        "States intent — this expression produces a collection.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="comp-dict-set-kinds",
                    text=(
                        "Dict and set comprehensions "
                        "swap the brackets and say what they build. The registry is made of "
                        "them — the validation pass collects known groups as a set, and the "
                        "lookup index is a dict comprehension keyed by topic id:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="comp-registry",
                    language="py",
                    caption="Set and dict comprehensions, one file apart.",
                    source="server/guide/content/registry.py",
                    snippet=(
                        "    known_group_ids = {group.id for group in groups}\n"
                        "# …\n"
                        "        self._topics_by_id: Final[dict[str, Topic]] = {topic.id: topic for topic in self._topics}"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="comp-summaries",
                    language="py",
                    caption="A list comprehension building one summary per topic.",
                    source="server/guide/content/registry.py",
                    snippet=(
                        "        return [\n"
                        "            ContentSummary(\n"
                        "                id=topic.id,\n"
                        "                title=topic.title,\n"
                        "                subtitle=topic.subtitle,\n"
                        "                group=topic.group,\n"
                        "                order=topic.order,\n"
                        "                section_count=len(topic.sections),\n"
                        "            )\n"
                        "            for topic in self._topics\n"
                        "        ]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="comp-normalize",
                    text=(
                        "The error module leans on comprehensions for exactly the jobs "
                        "statement loops make clumsy — inverting a mapping into its reverse "
                        "lookup, and normalizing a list of raw pydantic errors into the "
                        "{loc, msg, type} triples clients actually receive:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="comp-inversion",
                    language="py",
                    caption="Inverting a dict: value becomes key, key becomes value.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "_KIND_BY_HTTP_STATUS: dict[int, FailureKind] = {\n"
                        "    status: kind for kind, status in _HTTP_STATUS_BY_KIND.items()\n"
                        "}"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="comp-details",
                    language="py",
                    caption="Normalizing a list into the wire's shape.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "    details = [\n"
                        "        {\"loc\": list(err[\"loc\"]), \"msg\": err[\"msg\"], \"type\": err[\"type\"]} for err in exc.errors()\n"
                        "    ]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="genexp-pitch",
                    text=(
                        "Generators are comprehensions' lazy sibling. A generator expression — "
                        "(f(x) for x in xs), note the parentheses — builds nothing up front: "
                        "it produces elements one at a time, on demand, exactly once. Feed one "
                        "to any() or all() and it short-circuits — the registry's \"every "
                        "section must teach\" rule stops scanning at the first text block "
                        "found. A generator function uses yield for the same laziness across "
                        "multi-step walks: calling it creates an iterator, and each next() "
                        "runs to the following yield. The snippet ratchet harness uses one to "
                        "stream every must-source code block out of a registry without ever "
                        "materializing the intermediate list:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="comp-any-genexp",
                    language="py",
                    caption="any() + generator expression: scans until the first hit.",
                    source="server/guide/content/registry.py",
                    snippet=(
                        "            if len(section.blocks) < 2:\n"
                        "                raise RegistryError(\n"
                        "                    f\"section too short: {section.id!r} in topic {topic.id!r} \"\n"
                        "                    \"needs at least 2 blocks\"\n"
                        "                )\n"
                        "            if not any(isinstance(block, TextBlock) for block in section.blocks):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="genexp-function",
                    language="py",
                    caption="A generator function walking a registry lazily.",
                    source="server/tests/test_snippet_ratchet.py",
                    snippet=(
                        "def _must_source_blocks(registry: ContentRegistry) -> Iterator[CodeBlock]:\n"
                        "    for summary in registry.summaries():\n"
                        "        topic = registry.topic_by_id(summary.id)\n"
                        "        assert topic is not None\n"
                        "        for section in topic.sections:\n"
                        "            for block in section.blocks:\n"
                        "                if isinstance(block, CodeBlock) and block.language in MUST_SOURCE_LANGUAGES:\n"
                        "                    yield block"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="genexp-itertools",
                    text=(
                        "itertools — count, islice, chain, groupby — is the standard library's "
                        "generator toolkit for unbounded and grouped streams. Nothing in this "
                        "repo uses it yet, because nothing here streams an unbounded sequence; "
                        "it returns, honestly, with the streaming topics later in the "
                        "curriculum. When a comprehension and a generator would both do, take "
                        "the comprehension for fixed-size inputs (simpler, and the result is "
                        "reusable) and the generator when the input is large, lazy, or "
                        "single-pass."
                    ),
                ),
            ],
        ),
        # ── 10. Types at runtime (inline demo) ──────────────────────────────
        Section(
            id="runtime-types",
            title="Types at runtime",
            lead="The demo of this topic lives here — beside the teaching it proves.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="runtime-pitch",
                    text=(
                        "Now the fact everything above was building to: annotations are "
                        "metadata, and CPython never enforces them. A def statement stores its "
                        "annotations — function.__annotations__, and classes get "
                        "__annotations__ too — then moves on; no checks happen at calls, ever. "
                        "Even how they are stored is configurable: by default in 3.13 they are "
                        "evaluated eagerly into real objects at definition time; under "
                        "`from __future__ import annotations` (PEP 563) they stay strings until "
                        "someone resolves them; from 3.14 (PEP 649) evaluation becomes lazy by "
                        "default. The tooling that cares — FastAPI reading your signatures to "
                        "build validation and OpenAPI docs, pydantic reading model fields — "
                        "resolves them with typing.get_type_hints(), which evaluates those "
                        "strings against the module's globals and hands back real objects. The "
                        "demo module below is deliberately written under the future import so "
                        "the demo can show both storage modes on real repo code:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="runtime-repeat",
                    language="py",
                    caption="This module defers its annotations — on purpose.",
                    source="server/guide/domain/demos/runtime_types.py",
                    snippet=(
                        "from __future__ import annotations\n"
                        "# …\n"
                        "def repeat(text: str, times: int) -> str:\n"
                        "    \"\"\"The enforcement proof: annotated, but never checked at runtime.\n"
                        "\n"
                        "    Called as ``repeat(3.0, 2)`` this runs happily and returns ``6.0`` — a\n"
                        "    ``float`` where ``-> str`` was declared. CPython does not look at the\n"
                        "    annotations; mypy does, and rejects the call.\n"
                        "    \"\"\"\n"
                        "    return text * times"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="runtime-introspection",
                    text=(
                        "Introspection is how libraries do anything with types at runtime. "
                        "get_origin(list[int]) is list; get_args(list[int]) is (int,); and the "
                        "PEP 604 union Topic | None is a types.UnionType object with origin "
                        "UnionType and args (Topic, NoneType) — that is what \"X | None builds "
                        "a different object than Optional[X]\" meant back in Section 4. "
                        "Libraries walk this same metadata: dataclasses.fields() reads a "
                        "class's __annotations__ into Field objects, pydantic's model_fields "
                        "reads them into validated FieldInfo — same source of truth, two "
                        "interpretations, and the demo shows both."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="runtime-enforcement-proof",
                    text=(
                        "Then the enforcement proof, which the demo below runs live against "
                        "this repo's real objects: repeat(3.0, 2) — a float handed to a str "
                        "parameter — executes, multiplies, and returns 6.0. The declared "
                        "-> str is a documentation claim the interpreter never reads. Only two "
                        "forces check types: mypy, statically — it rejects this exact call, "
                        "and the demo payload quotes its verdict — and libraries that opt in "
                        "at boundaries: pydantic validates model construction and refuses an "
                        "int where Topic.id declares str, because pydantic v2 does not coerce "
                        "numbers to strings."
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="runtime-enforcement",
                    language="py",
                    caption="The proof, as code — note who is silenced.",
                    source="server/guide/domain/demos/runtime_types.py",
                    snippet=(
                        "def _enforcement() -> EnforcementRun:\n"
                        "    \"\"\"Call ``repeat`` with a wrong type; report that it ran anyway.\"\"\"\n"
                        "    # Silencing mypy IS the demo: a float where str is declared.\n"
                        "    value = repeat(3.0, 2)  # type: ignore[arg-type]\n"
                        "    return EnforcementRun(\n"
                        "        function=\"repeat\",\n"
                        "        signature=\"def repeat(text: str, times: int) -> str\",\n"
                        "        call=\"repeat(3.0, 2)\",\n"
                        "        # …\n"
                        "        actual_return=type(value).__name__,\n"
                        "        returned_value=repr(value),\n"
                        "        mypy_verdict=(\n"
                        "            'mypy (strict) rejects the call before it ever runs: '\n"
                        "            'Argument 1 to \"repeat\" has incompatible type \"float\"; expected \"str\"'\n"
                        "        ),\n"
                        "    )"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="runtime-demo-router",
                    language="py",
                    caption="The demo endpoint itself: a declared response model, a pure builder.",
                    source="server/guide/presentation/routers/demo/py.py",
                    snippet=(
                        "from fastapi import APIRouter\n"
                        "\n"
                        "from guide.domain.demos.runtime_types import RuntimeTypesPayload, build_runtime_types_payload\n"
                        "\n"
                        "router = APIRouter(prefix=\"/api/demo/py\", tags=[\"demo:py\"])\n"
                        "\n"
                        "\n"
                        "@router.get(\"/runtime-types\", response_model=RuntimeTypesPayload)\n"
                        "def read_runtime_types() -> RuntimeTypesPayload:\n"
                        "    \"\"\"Serve the runtime-typing proof payload (pure builder, no state).\"\"\"\n"
                        "    return build_runtime_types_payload()"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="py:runtime-types",
                    title="Types at runtime — the proof",
                    description=(
                        "Computed live from this repo's real objects: raw annotations vs "
                        "get_type_hints, get_origin/get_args, the dataclass/pydantic field "
                        "face-off, and a wrong-typed call that runs anyway."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="runtime-coda",
                    text="Read the demo in four beats:",
                ),
                ListBlock(
                    kind="list",
                    id="runtime-demo-beats-list",
                    ordered=False,
                    items=[
                        "The hints-vs-raw table — one symbol stores strings, the other "
                        "already-evaluated objects — get_type_hints resolves both.",
                        "The origin/args rows — taking generics apart.",
                        "The field face-off — dataclasses and pydantic reading the same "
                        "__annotations__.",
                        "The enforcement run — a returned 6.0 that mypy says cannot exist, "
                        "displayed beside the ValidationError pydantic raises where the "
                        "language stayed silent.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="runtime-division-of-labor",
                    text=(
                        "Static checking everywhere, runtime checking "
                        "at boundaries — that division of labor is the modern Python contract "
                        "this whole server is written under."
                    ),
                ),
            ],
        ),
        # ── 11. Terminal companion ──────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="The guide is its own API — read it from the shell.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-pitch",
                    text=(
                        "With the stack up (server on :8000), these commands walk the exact "
                        "surface this topic lives in. Piping to python3 -m json.tool gets you "
                        "pretty-printed JSON with zero extra tooling — the stdlib is the only "
                        "dependency this tour needs:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-list",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the curriculum index: groups + topic summaries with sectionCount\n"
                        "curl -s localhost:8000/api/content | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-detail",
                    language="bash",
                    source=None,
                    snippet=(
                        "# this topic, in full: sections → text/code/demo blocks\n"
                        "curl -s localhost:8000/api/content/python-language | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-demo",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the demo Section 10 renders — the runtime-types proof\n"
                        "curl -s localhost:8000/api/demo/py/runtime-types | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-oneliner",
                    language="bash",
                    source=None,
                    snippet=(
                        "# no jq required: a python one-liner over the index\n"
                        "python3 -c \"import json,urllib.request as u; print([t['id'] for t in json.load(u.urlopen('http://localhost:8000/api/content'))['topics']])\""
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-404",
                    language="bash",
                    source=None,
                    snippet=(
                        "# unknown topic → the shared error envelope + x-request-id\n"
                        "curl -s -i localhost:8000/api/content/nope"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Every failure you can provoke comes back in one envelope — "
                        "{error: {code, message, requestId}} — with an x-request-id header "
                        "matching the server logs; the taxonomy behind it gets its own deep "
                        "dive in topic 30. For the same surface rendered instead of raw, the "
                        "Vite dev server proxies /api on :5174 — but that is the client "
                        "shell's story, not the language's."
                    ),
                ),
            ],
        ),
    ],
)
