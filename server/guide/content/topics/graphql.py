"""Topic 13 — graphql (third topic of the APIs group).

One endpoint, a typed schema, and the client choosing the shape of every
answer: the problem that motion solves (and what it costs), strawberry's
code-first schema over the EXISTING posts substrate, queries and
mutations whose resolvers call the same use cases the REST router
resolves, GraphQL's errors array beside the family's REST envelope, the
N+1 problem a dataloader batches away — with this topic's live demo
``api:graphql-playground`` INLINE in the introspection section — and the
terminal curl tour last, five real queries POSTed to /api/graphql.

Every code block quotes a real repo file (the snippet ratchet verifies
it): the GraphQL module written for exactly this teaching, its mount in
the composition root, and the demo endpoint that serves the live SDL.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="graphql",
    title="GraphQL",
    subtitle=(
        "One endpoint, a typed schema, and the client choosing the shape — "
        "strawberry over the same posts substrate REST serves."
    ),
    group="apis",
    order=13,
    sections=[
        # ── 1. The problem GraphQL solves ───────────────────────────────────
        Section(
            id="the-problem-graphql-solves",
            title="The problem GraphQL solves",
            blocks=[
                TextBlock(
                    kind="text",
                    id="why-shape-pitch",
                    text=(
                        "Topic 11 built /api/posts as a REST contract, and that "
                        "contract has a quiet rule inside it: the SERVER picks "
                        "the shape of every representation. The list answers "
                        "with whole Post objects — body included, even when the "
                        "caller only wanted titles for a table of contents. The "
                        "item answers with one post — but a screen that also "
                        "wanted the author's other posts must make a second "
                        "round trip, because that fact is not IN the "
                        "representation. Those are the two classic shape "
                        "failures: over-fetching (fields shipped and ignored) "
                        "and under-fetching (fields wanted but absent, so the "
                        "client composes them by hand). REST can fight both — "
                        "sparse fieldsets, compound expansions, bespoke "
                        "endpoints — but each fix is a new design decision the "
                        "server owns, per endpoint, forever."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-shape-move",
                    text=(
                        "GraphQL's move is to hand the shape decision to the "
                        "client, per request. The client sends a query — a "
                        "selection of fields off a typed schema — and the "
                        "server answers with exactly that object graph, "
                        "nothing more, nothing less. One endpoint receives "
                        "every request. The schema, not a document beside the "
                        "API, is the contract, and the client can ask the "
                        "schema itself what it offers (topic 12 promised that "
                        "introspection; this topic delivers it). For this "
                        "guide the substrate does not change at all — the "
                        "same twelve seeded posts, the same repository port, "
                        "the same use cases — because GraphQL is a second "
                        "PROTOCOL over one domain, not a second domain:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="why-shape-list",
                    ordered=False,
                    items=[
                        "One endpoint — every read and write is a POST to "
                        "/api/graphql with the operation in the body; there is "
                        "no URL vocabulary because the query names what it "
                        "wants.",
                        "Client-shaped responses — the selection set is the "
                        "shape: a list view asks for ids and titles, a detail "
                        "view asks for everything, and each gets exactly its "
                        "ask.",
                        "A typed schema — types, fields, arguments, and enums "
                        "form the contract; an unknown field is rejected "
                        "before any resolver runs, like a 422 that names the "
                        "line and column.",
                        "Introspection — the protocol queries its own schema "
                        "(__schema, __type), so tooling discovers the contract "
                        "at runtime instead of reading a file.",
                        "One error channel — failures ride a 200 response as "
                        "an errors array with locations and paths, a model "
                        "section 4 puts beside this repo's REST envelope.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="why-shape-trade",
                    text=(
                        "The trade is real, and this topic teaches it honestly "
                        "rather than selling it. Giving up URL-addressable "
                        "resources gives up the HTTP caching and CDN story "
                        "topic 03 sketched — every request is a POST to one "
                        "URL. Letting clients compose deep shapes moves work "
                        "onto the server: the N+1 problem (section 5) exists "
                        "because nested selections invite per-item resolution. "
                        "And a query language needs its own tooling — the "
                        "GraphiQL editor, schema-aware clients — where REST "
                        "needed only curl. Teams running both protocols side "
                        "by side is common enough that this guide keeps both "
                        "REAL: the REST resource from topic 11 and the GraphQL "
                        "mount from this topic serve the same store through "
                        "the same use cases, wired in the same composition "
                        "root:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="why-mount-code",
                    language="py",
                    caption="Two protocols, one substrate: the GraphQL mount beside the REST router.",
                    source="server/guide/main.py",
                    snippet=(
                        "    app.include_router(posts.router)\n"
                        "    # The GraphQL mount: resolvers over the SAME posts use cases the REST\n"
                        "    # router serves — one URL (POST /api/graphql), excluded from OpenAPI\n"
                        "    # because the query language has no OpenAPI shape; the SDL is the contract.\n"
                        "    app.include_router(graphql.router)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="why-shape-coda",
                    text=(
                        "Read the mount the way you read every mount in this "
                        "guide: a router, included once, over dependencies the "
                        "composition root already wired. Nothing about the "
                        "posts domain changed to make this section work — no "
                        "new port method, no new adapter — because the "
                        "resolvers (next section) are presentation, and "
                        "presentation is exactly the layer that already knows "
                        "how to call the use cases. The rest of the topic "
                        "walks the GraphQL stack top to bottom: the schema "
                        "and its resolvers, the operations clients send, the "
                        "error model, the N+1 exit, and the introspection "
                        "surface — then the terminal companion POSTs real "
                        "queries against the live stack."
                    ),
                ),
            ],
        ),
        # ── 2. Schema and resolvers (strawberry) ────────────────────────────
        Section(
            id="schema-and-resolvers",
            title="Schema and resolvers (strawberry)",
            blocks=[
                TextBlock(
                    kind="text",
                    id="schema-pitch",
                    text=(
                        "A GraphQL schema is a graph of types with two entry "
                        "points — a Query type for reads and a Mutation type "
                        "for writes — and the lingua franca for writing one is "
                        "SDL, the schema definition language. This app's "
                        "schema exists as strawberry classes first and SDL "
                        "second: strawberry is code-first, the FastAPI-idiomatic "
                        "GraphQL library, where ordinary Python types with "
                        "decorators ARE the schema and the SDL is generated "
                        "from them. Here is the slice of the generated schema "
                        "this section builds toward — real output of "
                        "schema.as_str(), not a sketch:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="schema-sdl-code",
                    language="graphql",
                    caption="Generated SDL: the Post type as the served schema describes it.",
                    source=None,
                    snippet=(
                        "type Post {\n"
                        "  id: String!\n"
                        "  title: String!\n"
                        "  createdAt: String!\n"
                        '  """The stored byline string — the loader\'s key."""\n'
                        "  authorName: String!\n"
                        '  """The byline as a projected author — batched per request by the loader."""\n'
                        "  author: Author\n"
                        "}"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="schema-type-map",
                    text=(
                        "Every fact in that SDL comes from the Python type. "
                        "Non-null markers (!) come from plain annotations — "
                        "str is String!, str | None is String. Field names "
                        "come from the attribute names, renamed to the "
                        "camelCase the GraphQL ecosystem expects through "
                        "strawberry.field(name=...). Descriptions come from "
                        "docstrings — the same declaration-powers-documentation "
                        "bet topic 12 watched OpenAPI make, made here by the "
                        "schema itself:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="schema-post-code",
                    language="py",
                    caption="The Post schema type: annotations become the SDL, docstrings become descriptions.",
                    source="server/guide/presentation/routers/graphql.py",
                    snippet=(
                        "@strawberry.type\n"
                        "class Post:\n"
                        '    """One posts-substrate post, as the schema serves it (camelCase wire)."""\n'
                        "\n"
                        "    id: str\n"
                        "    title: str\n"
                        "    body: str\n"
                        "    tags: list[str]\n"
                        "    status: PostStatus\n"
                        '    created_at: str = strawberry.field(name="createdAt")\n'
                        '    updated_at: str = strawberry.field(name="updatedAt")\n'
                        "    author_name: str = strawberry.field(\n"
                        '        name="authorName", description="The stored byline string — the loader\'s key."\n'
                        "    )\n"
                        "\n"
                        "    @strawberry.field\n"
                        "    async def author(self, info: strawberry.Info[GraphQLContext, None]) -> Author | None:\n"
                        '        """The byline as a projected author — batched per request by the loader."""\n'
                        "        return await info.context.authors.load(self.author_name)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="schema-resolvers",
                    text=(
                        "Most fields need no code: strawberry's default "
                        "resolvers read the attribute off the value, exactly "
                        "as the SDL implies. author is the exception that "
                        "teaches what a resolver IS: the substrate stores a "
                        "byline STRING (authorName), while the schema promises "
                        "an author OBJECT with live facts — so a field "
                        "resolver derives one from the other. Notice the "
                        "honesty of the mapping: the stored string stays "
                        "visible in the schema, and the derived object is "
                        "nullable (Author, no !) because derivation can fail "
                        "— section 5 shows why that resolver is async and "
                        "what authors.load batches. Resolvers reach the app "
                        "through info.context, which strawberry lets the "
                        "integration build per request:"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="schema-vocab",
                    text=(
                        "Two more schema vocabularies round out the type "
                        "system, and both project domain rules the guide "
                        "already owns. GraphQL has no Literal — its closed "
                        "vocabularies are enum types, and the sort and status "
                        "enums carry exactly the values the pydantic models "
                        "declare, so an illegal sort spelling dies at "
                        "validation the same way it does on the REST edge. "
                        "Arguments that belong together become input types "
                        "— this schema's PostFilter gathers the exact-match "
                        "filters, and section 3's CreatePostInput is the "
                        "mutation body. Both are the input-side twins of "
                        "types: plain classes with @strawberry.input, "
                        "nullable optional fields, and defaults that surface "
                        "in the SDL:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="schema-enum-code",
                    language="py",
                    caption="An enum: the domain's closed sort vocabulary, spelled as GraphQL values.",
                    source="server/guide/presentation/routers/graphql.py",
                    snippet=(
                        "@strawberry.enum\n"
                        "class PostSort(Enum):\n"
                        '    """The domain\'s closed sort vocabulary; NEWEST mirrors the REST default."""\n'
                        "\n"
                        '    NEWEST = "newest"\n'
                        '    OLDEST = "oldest"\n'
                        '    TITLE = "title"'
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="schema-context-code",
                    language="py",
                    caption="The context getter: the same dependency the REST router resolves.",
                    source="server/guide/presentation/routers/graphql.py",
                    snippet=(
                        "def build_graphql_context(request: Request) -> GraphQLContext:\n"
                        '    """FastAPI dependency: the SAME posts bundle the REST router resolves."""\n'
                        "    use_cases = get_post_use_cases(request)\n"
                        "    return GraphQLContext(posts=use_cases, authors=AuthorLoader(use_cases.list_posts))"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="schema-coda",
                    text=(
                        "The context getter is an ordinary FastAPI dependency "
                        "— it reads the same app.state bundle the posts "
                        "router's dependency reads, wraps it in a small "
                        "BaseContext subclass, and hands every resolver the "
                        "wired world. The dependency rule this guide has "
                        "enforced since topic 11 holds unchanged: "
                        "presentation → domain ← data. Strawberry's types "
                        "live in the presentation layer beside the REST "
                        "router, projecting the domain's pydantic Post onto "
                        "the schema's Post through a pure from_domain "
                        "factory — no schema type ever leaks past a resolver, "
                        "and no resolver ever learns which adapter answers."
                    ),
                ),
            ],
        ),
        # ── 3. Queries and mutations ────────────────────────────────────────
        Section(
            id="queries-and-mutations",
            title="Queries and mutations",
            blocks=[
                TextBlock(
                    kind="text",
                    id="ops-pitch",
                    text=(
                        "Clients speak two operation kinds. A query reads — "
                        "the posts field with its page, limit, sort, and "
                        "filter arguments is this schema's read surface, and "
                        "the arguments are typed: ints with defaults, an enum "
                        "for the sort vocabulary (NEWEST, OLDEST, TITLE — the "
                        "same closed set GET /api/posts accepts), and an input "
                        "object for the exact-match filters. A mutation "
                        "writes. The resolver bodies are deliberately the "
                        "least interesting code in this topic — they are the "
                        "thin-router invariant wearing strawberry's "
                        "decorators:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="ops-posts-code",
                    language="py",
                    caption="The collection query: arguments in, the same use case, a projected page.",
                    source="server/guide/presentation/routers/graphql.py",
                    snippet=(
                        "    @strawberry.field\n"
                        "    def posts(\n"
                        "        self,\n"
                        "        info: strawberry.Info[GraphQLContext, None],\n"
                        "        page: int = 1,\n"
                        "        limit: int = DEFAULT_LIST_LIMIT,\n"
                        "        sort: PostSort = PostSort.NEWEST,\n"
                        "        filter: PostFilter | None = None,\n"
                        "    ) -> PostPage:\n"
                        '        """One filtered, sorted, paginated page of posts (the page size caps at 100)."""\n'
                        "        chosen = filter if filter is not None else PostFilter()\n"
                        "        try:\n"
                        "            query = PostListQuery(\n"
                        "                page=page,\n"
                        "                limit=limit,\n"
                        "                sort=sort.value,\n"
                        "                author=chosen.author,\n"
                        "                tag=chosen.tag,\n"
                        "                status=chosen.status.value if chosen.status is not None else None,\n"
                        "            )\n"
                        "        except ValidationError as exc:\n"
                        '            raise _validation_error("posts", exc) from exc\n'
                        "        result = info.context.posts.list_posts.execute(query)\n"
                        "        if isinstance(result, Err):\n"
                        "            raise result.failure\n"
                        "        return PostPage.from_domain(result.value)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ops-posts-read",
                    text=(
                        "Read it as three moves. Parse: the GraphQL arguments "
                        "become a PostListQuery — the same pydantic model, "
                        "with the same bounds, that FastAPI built from query "
                        "parameters in topic 11; a limit of 500 dies against "
                        "the model's cap exactly as it would against the REST "
                        "query string. Execute: the SAME list use case runs, "
                        "Result and all. Answer: the domain page projects "
                        "onto the schema's PostPage — total and pages ride "
                        "along as fields the client may select or skip, where "
                        "the REST surface put them in x-total-count headers. "
                        "The mutation makes the same three moves for writes:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="ops-mutation-code",
                    language="py",
                    caption="The mutation: input in, the same create use case, the stored post back.",
                    source="server/guide/presentation/routers/graphql.py",
                    snippet=(
                        "    @strawberry.mutation\n"
                        "    def create_post(\n"
                        "        self, info: strawberry.Info[GraphQLContext, None], input: CreatePostInput\n"
                        "    ) -> Post:\n"
                        '        """Create from the input; the draft\'s bounds run as a GraphQL error."""\n'
                        "        try:\n"
                        "            draft = PostCreate(\n"
                        "                title=input.title,\n"
                        "                body=input.body,\n"
                        "                author=input.author,\n"
                        "                tags=input.tags,\n"
                        "                status=input.status.value,\n"
                        "            )\n"
                        "        except ValidationError as exc:\n"
                        '            raise _validation_error("createPost", exc) from exc\n'
                        "        result = info.context.posts.create_post.execute(draft)\n"
                        "        if isinstance(result, Err):\n"
                        "            raise result.failure\n"
                        "        return Post.from_domain(result.value)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ops-validation-note",
                    text=(
                        "One honest gap deserves naming: GraphQL arguments "
                        "are typed but not BOUNDED — the language has Int, "
                        "not Int between 1 and 100, and a two-character title "
                        "is a perfectly legal String. This resolver closes "
                        "the gap by constructing PostCreate and letting "
                        "pydantic run the same Field bounds topic 10 put on "
                        "the model; a violation is caught at the edge and "
                        "mapped onto a GraphQL error (the mapping is section "
                        "4's second quote). The REST and GraphQL surfaces "
                        "therefore share one validation vocabulary — the "
                        "bounds live on the model, not on either protocol's "
                        "edge."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ops-coda",
                    text=(
                        "Everything else clients send is sugar over these "
                        "operations. Variables parameterize a query without "
                        "string surgery — the demo console and the terminal "
                        "tour both send the plain form, a JSON body whose "
                        "query key holds the operation text. Aliases rename "
                        "fields so one operation can ask the same field "
                        "twice with different arguments — two pages in one "
                        "round trip, for instance. And the selection set "
                        "composes: because every field returns a typed "
                        "object, a query nests as deep as the schema allows, "
                        "which is precisely the freedom that creates the "
                        "next section's favorite problem."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="ops-defaults",
                    text=(
                        "One quiet win is worth noticing in the generated "
                        "SDL: arguments carry their defaults, and clients can "
                        "READ them. The posts field renders as posts(page: "
                        "Int! = 1, limit: Int! = 6, sort: PostSort! = NEWEST, "
                        "filter: PostFilter = null) — so an editor can offer "
                        "the real default page size, a code generator can "
                        "bake NEWEST into the typed SDK, and a reviewer "
                        "diffing the schema sees a default change as a "
                        "contract change. The REST surface carried the same "
                        "facts inside PostListQuery, but they were invisible "
                        "until a client sent something wrong; here they are "
                        "part of the discoverable contract."
                    ),
                ),
            ],
        ),
        # ── 4. Errors ───────────────────────────────────────────────────────
        Section(
            id="errors",
            title="Errors",
            blocks=[
                TextBlock(
                    kind="text",
                    id="errors-pitch",
                    text=(
                        "GraphQL inverts the REST error habit this guide "
                        "built in topics 11 and 30's preview: the transport "
                        "mostly answers 200, and failure lives in the BODY — "
                        "an errors array whose entries carry a message, the "
                        "locations (line and column) of the offending part of "
                        "the query, the path of the failing field, and "
                        "optionally extensions for machine facts. Both models "
                        "are now real in this repo at once: GET /api/posts/"
                        "nope answers 404 with the family envelope "
                        "{error: {code, message, requestId}}, while the "
                        "GraphQL post field for the same missing slug answers "
                        "200 with errors: [{message, locations, path, "
                        "extensions}]. Neither is wrong; they are two "
                        "protocols' answers to one domain fact. The mapping "
                        "lives where every mapping lives in this guide — the "
                        "presentation edge:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="errors-not-found-code",
                    language="py",
                    caption="A domain Err becomes a typed GraphQL error; the family code survives.",
                    source="server/guide/presentation/routers/graphql.py",
                    snippet=(
                        "        result = info.context.posts.get_post.execute(slug)\n"
                        "        if isinstance(result, Err):\n"
                        "            failure = result.failure\n"
                        "            raise GraphQLError(\n"
                        "                message=failure.message,\n"
                        "                extensions={\n"
                        '                    "code": failure.kind.value,\n'
                        '                    "entity": "Post",\n'
                        '                    "slug": slug,\n'
                        "                },\n"
                        "            ) from failure\n"
                        "        return Post.from_domain(result.value)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="errors-extensions",
                    text=(
                        "The use case still returns Err(not_found) with the "
                        "same message the REST 404 carries; the resolver "
                        "re-raises it as a GraphQLError whose extensions "
                        "carry the family's failure-kind string (not_found) "
                        "plus the entity and slug. A client branches on "
                        "errors[0].extensions.code exactly the way a REST "
                        "client branches on the envelope's code — the "
                        "vocabulary did not change, only the transport. "
                        "Validation failures get the same treatment, and "
                        "this is where extensions earn their keep: the "
                        "per-field detail pydantic produces is data, so it "
                        "rides along as data:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="errors-validation-code",
                    language="py",
                    caption="Pydantic's edge validation, mapped onto the errors array with details.",
                    source="server/guide/presentation/routers/graphql.py",
                    snippet=(
                        "def _validation_error(operation: str, exc: ValidationError) -> GraphQLError:\n"
                        '    """Map pydantic\'s edge validation onto the family\'s error vocabulary."""\n'
                        "    details = [\n"
                        '        f"{\'.\'.join(str(part) for part in error[\'loc\'])}: {error[\'msg\']}"\n'
                        "        for error in exc.errors()\n"
                        "    ]\n"
                        "    return GraphQLError(\n"
                        '        message=f"{operation} arguments failed validation.",\n'
                        '        extensions={"code": FailureKind.VALIDATION_FAILED.value, "details": details},\n'
                        "    )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="errors-shapes",
                    text=(
                        "Three more shapes are worth knowing before you meet "
                        "them live in the demo and the curl tour. A field "
                        "error nulls its field and keeps executing the rest "
                        "— data can come back PARTIALLY populated, with "
                        "errors listing what fell; a top-level failure like "
                        "the missing post answers data: null plus the errors "
                        "array. A syntactically broken query — an empty "
                        "string, a stray brace — fails validation before any "
                        "resolver runs and answers with a syntax error and "
                        "its line and column, never a traceback. And the "
                        "outer machinery this guide already built keeps "
                        "working: the request runs through the request-id "
                        "middleware, so the 200-with-errors response still "
                        "carries x-request-id, and an error strawberry "
                        "cannot map is logged with that id — nothing is "
                        "swallowed, only transported differently."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="errors-coda",
                    text=(
                        "The discipline to carry into your own APIs: decide "
                        "the error contract per protocol, but derive both "
                        "contracts from one taxonomy. Here the domain says "
                        "not_found once; the REST handler renders a 404 "
                        "envelope, the resolver renders an errors entry with "
                        "extensions.code — one fact, two transports, zero "
                        "drift in meaning. What GraphQL does NOT give you is "
                        "the status code as a cheap triage — every client "
                        "must read the body — which is the honest price of "
                        "the 200-always habit, and the reason gateways and "
                        "load balancers treat GraphQL endpoints as a single "
                        "always-up URL rather than a surface with per-route "
                        "health."
                    ),
                ),
            ],
        ),
        # ── 5. N+1 and dataloaders ──────────────────────────────────────────
        Section(
            id="n-plus-one-and-dataloaders",
            title="N+1 and dataloaders",
            blocks=[
                TextBlock(
                    kind="text",
                    id="nplus-pitch",
                    text=(
                        "Here is the bill for client-shaped nesting. A "
                        "resolver that answers posts can afford one "
                        "repository round — but the author field on EACH "
                        "post needs the author's facts, and a naive resolver "
                        "would fetch them per post: one list query plus six "
                        "author queries for a six-post page, N+1 in the "
                        "classic spelling. REST never hit this because the "
                        "page embeds only the byline string; the moment a "
                        "schema promises a derived OBJECT per row, the "
                        "per-item fetch is one decorator away. Against SQL "
                        "the same shape becomes six SELECTs where one WHERE "
                        "author IN (...) would do — the fix is batching, and "
                        "the batching tool GraphQL ecosystems standardized "
                        "on is the dataloader:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="nplus-loader-code",
                    language="py",
                    caption="The author loader: collect the batch's keys, ONE repository round, answer in order.",
                    source="server/guide/presentation/routers/graphql.py",
                    snippet=(
                        "class AuthorLoader(DataLoader[str, Author | None]):\n"
                        '    """Batched author lookups: ONE repository round answers the whole batch."""\n'
                        "\n"
                        "    def __init__(self, list_posts: ListPostsUseCase) -> None:\n"
                        "        super().__init__(load_fn=self._load_authors)\n"
                        "        self._list_posts = list_posts\n"
                        "\n"
                        "    async def _load_authors(self, names: list[str]) -> list[Author | None]:\n"
                        '        """Tally one page-sized snapshot of the store; answer keys in order."""\n'
                        "        result = self._list_posts.execute(PostListQuery(limit=100, sort=\"oldest\"))\n"
                        "        if isinstance(result, Err):\n"
                        "            raise result.failure\n"
                        "        tally: Counter[str] = Counter(post.author for post in result.value.items)\n"
                        "        return [\n"
                        "            Author(id=name, post_count=tally[name]) if name in tally else None\n"
                        "            for name in names\n"
                        "        ]"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="nplus-mechanics",
                    text=(
                        "The mechanics are the interesting part, and they are "
                        "why the author resolver in section 2 is async. A "
                        "loader's load(key) does not fetch — it registers the "
                        "key with the current batch and returns a future. "
                        "While one level of the query resolves, every author "
                        "field calls load with its byline; only then does the "
                        "loader dispatch ONE call to its load function with "
                        "the collected, deduplicated keys. Six posts whose "
                        "bylines are grace, alan, barbara become six load "
                        "calls and ONE _load_authors(['barbara', 'alan', "
                        "'grace']) — the repo's test suite pins that with a "
                        "spy: a six-post nested query must produce exactly "
                        "one batched call or the test fails. The context "
                        "getter builds one loader per request, so the batch "
                        "and its cache live exactly as long as the query that "
                        "needed them; a second page of posts in the same "
                        "operation reuses cached authors instead of "
                        "re-asking."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="nplus-honesty",
                    text=(
                        "Be honest about what THIS loader batches against: "
                        "the substrate's in-memory port, so the \"round\" is "
                        "one list call that tallies authors off a page-sized "
                        "snapshot. Against a SQL adapter the same shape is "
                        "one WHERE id IN (...) — the load function changes, "
                        "the pattern does not. Note also what the loader "
                        "does NOT claim: freshness beyond the request (the "
                        "tally is a snapshot) and existence (a byline with no "
                        "posts answers None, and the schema's nullable Author "
                        "says so). The dataloader is a batching cache, not a "
                        "source of truth — the domain remains the only one "
                        "of those."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="nplus-coda",
                    text=(
                        "When to reach for one: any resolver that resolves a "
                        "LIST of things each needing a derived lookup — "
                        "authors off posts, permissions off users, covers off "
                        "books. When NOT to: a top-level field fetching one "
                        "value (there is no batch to collect), or a "
                        "derivation the parent already carries (the byline "
                        "string needs no loader). And the deeper fix is "
                        "sometimes modeling: if clients ALWAYS want authors "
                        "with posts, a joined read at the repository level "
                        "beats a loader papering over N calls — the loader "
                        "solves per-request batching, not a shape the domain "
                        "should own. Topic 18's ORM relationships meet this "
                        "same problem again, from the SQL side."
                    ),
                ),
            ],
        ),
        # ── 6. Introspection and tooling ────────────────────────────────────
        Section(
            id="introspection-and-tooling",
            title="Introspection and tooling",
            lead="This section carries the topic's demo — the GraphQL playground.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="intro-pitch",
                    text=(
                        "Topic 12's contract was a document the app "
                        "generates and serves BESIDE itself. GraphQL's "
                        "contract is queryable FROM itself: the schema "
                        "reserves __schema and __type, so any client can ask "
                        "what types exist, what fields they carry, what "
                        "arguments they take — at runtime, over the same "
                        "endpoint as the data. That single fact powers the "
                        "tooling: editors autocomplete queries against the "
                        "live schema, codegen clients build typed SDKs from "
                        "it, and a newcomer can discover the API without a "
                        "wiki. The SDL itself is one as_str() call away — "
                        "and this guide serves it, because a schema you can "
                        "print is a schema you can drift-test:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="intro-demo-code",
                    language="py",
                    caption="The demo endpoint: the running schema's SDL, packaged with a query tour.",
                    source="server/guide/presentation/routers/demo/api.py",
                    snippet=(
                        "@router.get(\"/graphql-playground\", response_model=GraphqlPlaygroundPayload)\n"
                        "def read_graphql_playground() -> GraphqlPlaygroundPayload:\n"
                        '    """Serve the GraphQL playground package: the live SDL + curated queries."""\n'
                        "    return build_graphql_playground_payload(\n"
                        "        endpoint=GRAPHQL_PATH,\n"
                        "        sdl=graphql_schema.as_str(),\n"
                        "    )"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="api:graphql-playground",
                    title="The GraphQL playground",
                    description=(
                        "GET /api/demo/api/graphql-playground packages the "
                        "running schema's real SDL (schema.as_str(), never "
                        "hand-written) with five curated queries — a paged "
                        "collection read, the nested author projection the "
                        "dataloader batches, a real createPost mutation, one "
                        "introspection probe, and a deliberate not-found "
                        "error. The console loads any example into its "
                        "editor and POSTs it to the LIVE /api/graphql: watch "
                        "the page query answer totals you never asked REST "
                        "for, six posts resolve three authors, the mutation "
                        "mint a real slug, and the error query return 200 "
                        "with the family's not_found code in extensions."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="intro-tooling",
                    text=(
                        "Try the playground's mutation example, then refresh "
                        "GET /api/posts in another tab: the post is there — "
                        "one store, two protocols, zero seams. The same "
                        "openness that powers the console powers strawberry's "
                        "own IDE: GET /api/graphql with an HTML Accept header "
                        "serves GraphiQL, the in-browser editor with schema "
                        "autocomplete and a run button — the GraphQL answer "
                        "to Swagger UI's Try it out, and it needs no "
                        "integration code because it reads the same "
                        "introspection every client reads."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="intro-openapi-contrast",
                    text=(
                        "And here is the topic 12 contrast worth pinning: "
                        "GraphQL routes do NOT appear in /openapi.json — the "
                        "mount is deliberately excluded, and the exclusion "
                        "is a constructor argument, not a patch:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="intro-router-code",
                    language="py",
                    caption="The mount: GraphiQL on GET, queries on POST, invisible to OpenAPI by choice.",
                    source="server/guide/presentation/routers/graphql.py",
                    snippet=(
                        "router = GraphQLRouter(\n"
                        "    schema,\n"
                        "    path=GRAPHQL_PATH,\n"
                        "    context_getter=build_graphql_context,\n"
                        "    include_in_schema=False,\n"
                        '    tags=["graphql"],\n'
                        ")"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="intro-sdl-artifact",
                    text=(
                        "Because the SDL is one print away, it makes a "
                        "first-class REVIEW artifact: paste schema.as_str() "
                        "into the pull request that changes a resolver and "
                        "the diff shows the contract change — a field added, "
                        "a default moved, a nullability loosened — as text a "
                        "reviewer can read without knowing strawberry. Teams "
                        "that pin the SDL in a test get topic 12's drift "
                        "discipline in GraphQL form: rename a field without "
                        "deciding to, and the suite fails on the printed "
                        "schema the same way it failed on a $ref. The demo "
                        "carries exactly that guarantee — its payload IS the "
                        "print, served fresh."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="intro-coda",
                    text=(
                        "The OpenAPI exclusion is honest, not lazy: an "
                        "OpenAPI document describes URL-shaped APIs, and a "
                        "query language has no URL shape — including it would "
                        "advertise two empty operations and teach readers "
                        "nothing. The contract lives where clients can "
                        "actually use it: introspection for tools, the served "
                        "SDL for humans and reviews, and drift tests for the "
                        "build — the endpoint test asserts the demo's SDL "
                        "equals the live schema's, so the playground cannot "
                        "teach a stale contract any more than topic 12's hub "
                        "could teach stale counts. One caution for "
                        "production: introspection is a surface, and some "
                        "teams disable it or gate it behind auth in hostile "
                        "environments — an honest trade between "
                        "discoverability and not handing attackers a map."
                    ),
                ),
            ],
        ),
        # ── 7. Terminal companion ───────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="Five real operations against the live endpoint — the query language, by hand.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-pitch",
                    text=(
                        "With the stack up (server on :8000), every stop on "
                        "this tour is one POST to the SAME URL — the whole "
                        "API surface exercised through one address. Watch "
                        "three things as you go: the shape of each answer is "
                        "the shape of its query; errors ride 200s; and the "
                        "mutation's post is really in the store (a GET "
                        "/api/posts after stop 3 shows it). python3 -m "
                        "json.tool keeps it dependency-free:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-page",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 1 — the collection read: a page, exactly the fields you asked for\n"
                        "curl -s -X POST localhost:8000/api/graphql -H 'content-type: application/json' \\\n"
                        '  -d \'{"query":"{ posts(limit: 3, sort: OLDEST) { total pages items { id title authorName } } }"}\' \\\n'
                        "  | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-authors",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 2 — the nested projection: six posts, three authors, ONE batched round\n"
                        "curl -s -X POST localhost:8000/api/graphql -H 'content-type: application/json' \\\n"
                        '  -d \'{"query":"{ posts(limit: 6) { items { title author { id postCount } } } }"}\' \\\n'
                        "  | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-mutation",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 3 — a real write: the mutation mints a slug and stamps the clock\n"
                        "curl -s -X POST localhost:8000/api/graphql -H 'content-type: application/json' \\\n"
                        "  -d '{\"query\":\"mutation { createPost(input: {title: \\\"Tour post\\\", author: \\\"you\\\", tags: [\\\"graphql\\\"], status: PUBLISHED}) { id createdAt } }\"}' \\\n"
                        "  | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-error",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 4 — the deliberate failure: 200, an errors array, the family code inside\n"
                        "curl -s -X POST localhost:8000/api/graphql -H 'content-type: application/json' \\\n"
                        '  -d \'{"query":"{ post(slug: \\"no-such-post\\") { id } }"}\' \\\n'
                        "  | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-introspection",
                    language="bash",
                    source=None,
                    snippet=(
                        "# stop 5 — the protocol reading its own contract: entry points, then one type\n"
                        "curl -s -X POST localhost:8000/api/graphql -H 'content-type: application/json' \\\n"
                        '  -d \'{"query":"{ __schema { queryType { name } mutationType { name } } }"}\' \\\n'
                        "  | python3 -m json.tool\n"
                        "curl -s -X POST localhost:8000/api/graphql -H 'content-type: application/json' \\\n"
                        '  -d \'{"query":"{ __type(name: \\"Post\\") { fields { name } } }"}\' \\\n'
                        "  | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-demo",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the demo's package: the live SDL plus the curated tour this console runs\n"
                        "curl -s localhost:8000/api/demo/api/graphql-playground | python3 -c \\\n"
                        '  \'import json,sys; p=json.load(sys.stdin); print(p["endpoint"]); print(p["sdl"][:400])\''
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Stop 5 is the whole topic in one reply: the answer "
                        "to __schema names Query and Mutation — discovered, "
                        "not documented — and __type lists Post's fields "
                        "back, including authorName and author, the stored "
                        "fact and the derived one from section 2. You have "
                        "now driven this group's two contracts from the "
                        "terminal: topic 12's generated document, and this "
                        "topic's queryable schema. The APIs group continues "
                        "with topic 14, where the calls reverse direction — "
                        "the server calls the client, and the contract "
                        "becomes an event catalog with signed payloads."
                    ),
                ),
            ],
        ),
    ],
)
