"""Topic 11 — api-design (first topic of the APIs group).

What REST actually is, taught against the guide's first REAL resource —
the posts substrate this topic builds: ``guide/domain/posts/`` (entity +
port + use cases), ``guide/data/posts/`` (the in-memory adapter with its
twelve-post seed), and ``guide/presentation/routers/posts.py`` (the real
``/api/posts`` router). Designing resources · methods and status codes ·
URLs, pagination, and filtering · error responses (RFC 9457 and how this
guide's family envelope relates to it) · versioning · and the whole
pipeline traced one request at a time, with this topic's live demo
``api:posts-workbench`` INLINE in that section — then the terminal curl
tour last.

Every code block quotes a real repo file (the snippet ratchet verifies
it): the posts entity and create draft, the port Protocol, the query
model and pagination link builder, the four route handlers, the error
taxonomy's envelope and status mapping, the content API's version
constant — and the workbench builder + router, written for exactly this
teaching.
"""

from guide.content.models import CodeBlock, DemoBlock, ListBlock, Section, TextBlock, Topic

TOPIC = Topic(
    id="api-design",
    title="API design",
    subtitle=(
        "Designing HTTP APIs as contracts — resources, methods, status "
        "codes, pagination, errors, and versioning, every rule grounded in "
        "this guide's first real resource: /api/posts."
    ),
    group="apis",
    order=11,
    sections=[
        # ── 1. What REST is ─────────────────────────────────────────────────
        Section(
            id="what-rest-is",
            title="What REST is",
            blocks=[
                TextBlock(
                    kind="text",
                    id="rest-pitch",
                    text=(
                        "REST is the architectural style HTTP was designed "
                        "around, and the nine topics before this one have "
                        "been assembling it piece by piece without naming "
                        "it. Roy Fielding's 2000 dissertation defined it as "
                        "a set of constraints — resources identified by "
                        "URLs, manipulated through representations; a "
                        "uniform interface of standard methods; stateless "
                        "interactions; cacheable responses — and an API "
                        "that follows those constraints inherits HTTP's "
                        "properties: proxies can cache it, clients can "
                        "predict it, and the protocol's own machinery "
                        "(status codes, headers, content negotiation) does "
                        "work a custom protocol would have to reinvent. "
                        "The name gets misused constantly — REST is not "
                        "\"any JSON over HTTP\", and it is not CRUD. It is "
                        "a contract style: the URL names a THING, the "
                        "method names a VERB, the status code names the "
                        "OUTCOME, and nothing else in the exchange is "
                        "improvised."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rest-uniform-interface",
                    text=(
                        "The constraints worth memorizing, because each one "
                        "buys something concrete when you follow it:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="rest-constraints-list",
                    ordered=False,
                    items=[
                        "Addressability — every interesting thing has its "
                        "own URL (/api/posts/status-codes-are-a-contract), "
                        "so links can be shared, bookmarked, and fetched "
                        "again without ceremony.",
                        "Representations — clients exchange a "
                        "representation of the resource (JSON today), not "
                        "the resource itself; the server decides how to "
                        "store it and may change that decision freely.",
                        "Uniform methods — GET, POST, PUT, PATCH, DELETE "
                        "carry agreed meanings (topic 03's safety and "
                        "idempotency table), so no client has to learn "
                        "your verbs.",
                        "Stateless interactions — each request carries "
                        "everything needed to understand it; no server-side "
                        "session lurks between requests (cookies are "
                        "request data, not hidden state).",
                        "Cacheability — responses say whether they may be "
                        "reused, which is what lets CDNs and browsers "
                        "do your scaling for you.",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="rest-first-real-resource",
                    text=(
                        "This topic stops being theoretical in a new way: "
                        "everything it teaches is grounded in the guide's "
                        "first REAL resource, built for exactly this "
                        "moment and reused by the topics after it — a "
                        "posts substrate shaped like production code "
                        "(domain entity, port, use cases, in-memory "
                        "adapter, thin router) living at /api/posts. The "
                        "router is four handlers, and even the smallest "
                        "one already speaks the whole style: a URL naming "
                        "one thing, a standard method, a declared response "
                        "model, and a failure path that ends in the shared "
                        "envelope rather than an improvised error body:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="rest-read-post-code",
                    language="py",
                    caption="One resource, one verb, one outcome per line — the style in miniature.",
                    source="server/guide/presentation/routers/posts.py",
                    snippet=(
                        '@router.get("/api/posts/{post_id}", response_model=Post)\n'
                        'def read_post(post_id: str, use_cases: PostUseCasesDep) -> Post:\n'
                        '    """Serve one post; unknown ids are the shared 404 envelope."""\n'
                        "    result = use_cases.get_post.execute(post_id)\n"
                        "    if isinstance(result, Err):\n"
                        "        raise result.failure\n"
                        "    return result.value"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="rest-coda",
                    text=(
                        "The rest of this topic designs that resource the "
                        "way you would design any API: decide what the "
                        "things are, pick methods and status codes that "
                        "tell the truth, keep collections pageable and "
                        "filterable, make errors a first-class part of the "
                        "contract, version what must not break, and "
                        "understand the whole request path end to end. "
                        "None of it is FastAPI-specific — the discipline "
                        "transfers to any HTTP framework — but FastAPI's "
                        "typed models and dependency injection make the "
                        "honest version of each decision the EASY version "
                        "too."
                    ),
                ),
            ],
        ),
        # ── 2. Designing resources ──────────────────────────────────────────
        Section(
            id="designing-resources",
            title="Designing resources",
            blocks=[
                TextBlock(
                    kind="text",
                    id="resources-nouns-pitch",
                    text=(
                        "The first design act is deciding what the THINGS "
                        "are — not endpoints, not functions: nouns a "
                        "client can hold a URL for. A blog-like guide has "
                        "an obvious candidate: posts. The test for a "
                        "resource is whether you can finish the sentence "
                        "\"GET …/thing returns a representation of ___\" "
                        "without using a verb — /api/posts passes, "
                        "/api/getPosts and /api/posts/list fail, and "
                        "/api/posts/{id} with /api/posts as its collection "
                        "gives you the two-shape pattern almost every "
                        "resource follows: a collection (pageable, "
                        "filterable, POSTable) and items (readable, "
                        "replaceable). Verbs still exist — they are the "
                        "HTTP methods, the next section's business, not "
                        "the URL's."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="resources-representation",
                    text=(
                        "The second act is deciding what a representation "
                        "carries. In this substrate the entity and the "
                        "wire model are deliberately ONE pydantic class: "
                        "every field a client sees is exactly what the "
                        "domain stores, camelCase on the wire through the "
                        "shared CamelModel base (topic 05), frozen so no "
                        "layer mutates a snapshot in place. Identity is "
                        "part of the representation — the id is the slug "
                        "the adapter minted — and so is the edit history "
                        "the domain actually tracks:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="resources-post-code",
                    language="py",
                    caption="The Post entity: one model is both the stored snapshot and the wire shape.",
                    source="server/guide/domain/posts/entities.py",
                    snippet=(
                        "class Post(CamelModel):\n"
                        '    """One stored post: the entity and the wire representation in one model.\n'
                        "\n"
                        "    ``id`` is a slug minted by the repository (the adapter owns identifier\n"
                        "    strategy); ``created_at`` survives replacement while ``updated_at``\n"
                        "    does not — replace keeps identity metadata and refreshes the edit stamp.\n"
                        '    """\n'
                        "\n"
                        "    id: str\n"
                        "    title: str\n"
                        "    body: str\n"
                        "    author: str\n"
                        "    tags: list[str]\n"
                        "    status: PostStatus\n"
                        "    created_at: str\n"
                        "    updated_at: str"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="resources-create-code-read",
                    text=(
                        "What clients SEND is a separate model, and that "
                        "separation is a design decision, not ceremony: "
                        "the server owns identity and timestamps, so the "
                        "create/replace draft carries only the fields a "
                        "client may choose — every one guarded by the "
                        "constraint vocabulary topic 10 taught (declared "
                        "bounds, Literal vocabulary, a default that makes "
                        "absence meaningful):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="resources-post-create-code",
                    language="py",
                    caption="PostCreate: the client's half of the contract, constraints declared on the field.",
                    source="server/guide/domain/posts/entities.py",
                    snippet=(
                        "class PostCreate(CamelModel):\n"
                        '    """The POST/PUT body: the full representation a client sends."""\n'
                        "\n"
                        "    title: Annotated[str, Field(min_length=1, max_length=120)]\n"
                        '    body: Annotated[str, Field(max_length=5000)] = ""\n'
                        "    author: Annotated[str, Field(min_length=1, max_length=40)]\n"
                        "    # …\n"
                        '    status: PostStatus = "draft"'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="resources-boundary",
                    text=(
                        "The third act is deciding who may know HOW the "
                        "things are stored. This is where the guide's "
                        "dependency rule earns its keep: the domain "
                        "declares a port — a Protocol naming the four "
                        "operations a posts store must answer — and "
                        "nothing above it ever learns which adapter is "
                        "wired underneath. Today that adapter is an "
                        "in-memory dictionary seeded with twelve posts; "
                        "Phase 6 swaps in PostgreSQL and the router, the "
                        "use cases, and every test that talks to them do "
                        "not change a line:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="resources-port-code",
                    language="py",
                    caption="The port: the domain says WHAT a posts store does, never HOW.",
                    source="server/guide/domain/posts/ports.py",
                    snippet=(
                        "@runtime_checkable\n"
                        "class PostRepository(Protocol):\n"
                        '    """What every posts adapter must do; returns snapshots, never live state."""\n'
                        "\n"
                        "    def list(self, query: PostListQuery) -> PostPage:\n"
                        '        """One filtered, sorted, paginated page of posts."""\n'
                        "        ..."
                    ),
                ),
            ],
        ),
        # ── 3. Methods and status codes ─────────────────────────────────────
        Section(
            id="methods-and-status-codes",
            title="Methods and status codes",
            blocks=[
                TextBlock(
                    kind="text",
                    id="methods-pitch",
                    text=(
                        "Once the nouns exist, the methods are nearly "
                        "chosen for you — that is the point of the uniform "
                        "interface. GET is safe and cacheable; PUT is "
                        "idempotent and replaces the whole representation; "
                        "POST is neither safe nor idempotent and creates; "
                        "DELETE is idempotent and removes. Topic 03 taught "
                        "the semantics; API design is the discipline of "
                        "not bending them. The posts resource uses four of "
                        "them and, just as deliberately, does NOT offer "
                        "DELETE at all — a resource with no removal story "
                        "yet should say so by absence, and the framework "
                        "answers an attempt with its honest 405 through "
                        "the shared envelope. Designing WITH methods means "
                        "the surface you don't build is still correct."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="methods-create-read",
                    text=(
                        "Status codes are the other half of the verb "
                        "vocabulary, and the rule is simple: the code is "
                        "part of the contract, so spend it honestly. The "
                        "clearest example on the posts surface is create "
                        "— 201, not a lazy 200, because the request "
                        "created a resource and the Location header names "
                        "it (resolved with url_path_for, exactly like "
                        "topic 09's notes, never string-pasted):"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="methods-create-code",
                    language="py",
                    caption="Create: 201 Created + Location — the status code and the header tell one story.",
                    source="server/guide/presentation/routers/posts.py",
                    snippet=(
                        '@router.post("/api/posts", response_model=Post, status_code=201)\n'
                        "def create_post(draft: PostCreate, response: Response, use_cases: PostUseCasesDep) -> Post:\n"
                        '    """Create from the validated body: 201 + Location names the resource."""\n'
                        "    result = use_cases.create_post.execute(draft)\n"
                        "    if isinstance(result, Err):\n"
                        "        raise result.failure\n"
                        "    post = result.value\n"
                        '    response.headers["location"] = router.url_path_for("read_post", post_id=post.id)\n'
                        "    return post"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="methods-vocabulary",
                    text=(
                        "The full status vocabulary this one resource "
                        "answers, each code earned by a specific layer of "
                        "the stack rather than chosen by mood:"
                    ),
                ),
                ListBlock(
                    kind="list",
                    id="methods-status-list",
                    ordered=False,
                    items=[
                        "200 OK — GET and PUT answers: here is the "
                        "representation (list page, one post, or the "
                        "replacement you just wrote).",
                        "201 Created — POST answers, with Location naming "
                        "the new resource so the client never constructs "
                        "its URL.",
                        "404 Not Found — the item URL names something no "
                        "route value holds: a domain answer from the use "
                        "case, rendered by the shared envelope.",
                        "405 Method Not Allowed — the method is not on "
                        "this resource (DELETE today): answered by the "
                        "routing layer before any handler runs.",
                        "422 Unprocessable Content — the body or query "
                        "failed validation: the edge's answer, with one "
                        "{loc, msg, type} triple per problem (topic 10).",
                    ],
                ),
                TextBlock(
                    kind="text",
                    id="methods-coda",
                    text=(
                        "Two habits keep this honest at scale. First, let "
                        "the layer that OWNS the answer produce it — "
                        "validation 422s come from FastAPI's edge, "
                        "existence 404s from the use case, missing-route "
                        "405s from the router table — so no handler "
                        "hand-crafts a status it doesn't own. Second, "
                        "when a code is ambiguous in the wild, prefer the "
                        "one a generic client handles correctly without "
                        "reading your docs: 404 over 400 for unknown ids "
                        "(caches and retry logic behave differently), 409 "
                        "for conflicts you want the client to resolve, "
                        "422 for \"well-formed but semantically refused\" "
                        "— the line this guide's taxonomy draws once for "
                        "every endpoint."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="methods-put-vs-patch",
                    text=(
                        "A word on PUT versus PATCH, because the posts "
                        "surface chooses deliberately: PUT here is a FULL "
                        "replace — the body is the complete new "
                        "representation (the same PostCreate model POST "
                        "accepts), and fields you omit fall back to their "
                        "defaults rather than surviving. That is the "
                        "contract PUT promises everywhere: send me the "
                        "whole thing, idempotently. PATCH would mean "
                        "partial update — missing keys mean \"unchanged\", "
                        "exactly the semantics the scenario toggle's PATCH "
                        "body implements with model_dump(exclude_unset="
                        "True) — and a resource that needs both usually "
                        "ships both. What you must never do is name a "
                        "route PUT and then give it partial semantics: "
                        "clients retry PUTs after timeouts precisely "
                        "because they trust the full-replace promise, and "
                        "a PUT that merges quietly destroys data on the "
                        "second send."
                    ),
                ),
            ],
        ),
        # ── 4. URLs, pagination, and filtering ──────────────────────────────
        Section(
            id="urls-pagination-and-filtering",
            title="URLs, pagination, and filtering",
            blocks=[
                TextBlock(
                    kind="text",
                    id="urls-pitch",
                    text=(
                        "URL design has one load-bearing rule: the PATH "
                        "identifies the resource; the QUERY describes the "
                        "view you want of it. /api/posts IS the collection "
                        "— /api/posts?page=2&author=grace is not a "
                        "different resource, it is the same resource seen "
                        "through a lens, which is why pagination and "
                        "filtering belong in query parameters and never "
                        "in path segments (/api/posts/page/2/author/grace "
                        "multiplies URLs without adding things). The "
                        "lens is typed by the same model discipline as "
                        "everything else — one pydantic model carries the "
                        "whole query surface, and FastAPI binds it with "
                        "Depends so every constraint is enforced at the "
                        "edge and documented in OpenAPI for free:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="urls-query-code",
                    language="py",
                    caption="PostListQuery: the collection's lens — pagination, filters, sort, all bounded.",
                    source="server/guide/domain/posts/entities.py",
                    snippet=(
                        "class PostListQuery(CamelModel):\n"
                        '    """The collection query surface: pagination, filtering, sorting.\n'
                        "\n"
                        "    Constraints are part of the contract: pages count from 1, the page size\n"
                        "    is capped at 100 so one request cannot demand the whole store, filters\n"
                        "    are exact matches, and ``sort`` is a closed vocabulary.\n"
                        '    """\n'
                        "\n"
                        "    page: Annotated[int, Field(ge=1, le=10_000)] = 1\n"
                        "    limit: Annotated[int, Field(ge=1, le=100)] = DEFAULT_LIST_LIMIT\n"
                        "    author: str | None = Field(default=None, min_length=1, max_length=40)\n"
                        "    tag: str | None = Field(default=None, min_length=1, max_length=40)\n"
                        "    status: PostStatus | None = None\n"
                        '    sort: PostSort = "newest"'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="urls-unbounded-collections",
                    text=(
                        "Why pagination is not optional: an unbounded "
                        "collection endpoint is a resource with no shape — "
                        "it answers differently as the store grows, breaks "
                        "clients at some unknown future size, and cannot "
                        "be cached sensibly. The posts contract makes the "
                        "shape explicit in both the body and the headers: "
                        "the body's PostPage carries items, total, page, "
                        "limit, and pages (totals counted AFTER filters, "
                        "so a client's page controls never lie), while the "
                        "headers carry the same facts where generic tooling "
                        "can read them — x-total-count, x-page-count, and "
                        "an RFC 8288 Link header pointing at the neighbor "
                        "pages:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="urls-list-route-code",
                    language="py",
                    caption="The list route: page in the body, pagination facts in the headers.",
                    source="server/guide/presentation/routers/posts.py",
                    snippet=(
                        '@router.get("/api/posts", response_model=PostPage)\n'
                        "def list_posts(\n"
                        "    query: Annotated[PostListQuery, Depends()],\n"
                        "    use_cases: PostUseCasesDep,\n"
                        "    response: Response,\n"
                        ") -> PostPage:\n"
                        '    """Serve one filtered, sorted, paginated page; pagination in headers."""\n'
                        "    result = use_cases.list_posts.execute(query)\n"
                        "    if isinstance(result, Err):\n"
                        "        raise result.failure\n"
                        "    page = result.value\n"
                        '    response.headers["x-total-count"] = str(page.total)\n'
                        '    response.headers["x-page-count"] = str(page.pages)'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="urls-canonical-read",
                    text=(
                        "The links themselves follow a canonical-URL rule "
                        "worth stealing: only the NON-default parts of the "
                        "query appear, so page 1 with the default limit "
                        "and sort is just /api/posts, and every filter a "
                        "client set survives into the next link (dropping "
                        "a filter between pages is the classic silent-data-"
                        "change bug). One builder produces these URLs for "
                        "both the real route's headers and this topic's "
                        "workbench demo, so the two cannot drift:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="urls-canonical-code",
                    language="py",
                    caption="Canonical list URLs: defaults omitted, filters preserved, URL-encoded.",
                    source="server/guide/domain/posts/pagination.py",
                    snippet=(
                        "def request_path(query: PostListQuery, base_path: str = COLLECTION_PATH) -> str:\n"
                        '    """The canonical URL for one list request: defaults omitted."""\n'
                        "    params = _params(query)\n"
                        '    return f"{base_path}?{urlencode(params)}" if params else base_path'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="urls-coda",
                    text=(
                        "The boundaries are honest too: pages count from "
                        "1 (page=0 is a 422 from the model's ge=1, not a "
                        "silent alias for 1), the limit caps at 100 so one "
                        "request cannot demand the whole store, a page "
                        "past the end is an empty 200 page rather than an "
                        "error, and filters are exact matches over a "
                        "closed vocabulary — predictable beats clever. "
                        "Page-based pagination like this is the right "
                        "default; when a collection mutates constantly "
                        "and clients need stable slices, cursor-based "
                        "pagination (an opaque \"after\" token) trades "
                        "page numbers for consistency — a trade topic 18 "
                        "revisits with real database offsets behind it."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="urls-filter-design",
                    text=(
                        "Why exact match over a closed vocabulary instead "
                        "of a search box? Because a filter is part of the "
                        "CONTRACT and search is a FEATURE. The workbench "
                        "roster endpoint serves the distinction live: it "
                        "lists the authors, tags, statuses, and sorts the "
                        "collection actually knows — the legal values of "
                        "every filter — so a client builds pickers, not "
                        "free-text inputs, and typo'd values fail visibly "
                        "(an author nobody wrote under yields an honest "
                        "empty page, and a status the Literal doesn't "
                        "name is a 422 before the store is touched). Tag "
                        "filtering is membership, not equality — the "
                        "query asks \"posts carrying this tag\" — and "
                        "combining filters is always AND, never a "
                        "surprise OR. When full-text search eventually "
                        "belongs on this surface, it will arrive as its "
                        "own named concern (a q parameter with documented "
                        "semantics, topic 17), not by quietly loosening "
                        "the filters clients already depend on."
                    ),
                ),
            ],
        ),
        # ── 5. Error responses ──────────────────────────────────────────────
        Section(
            id="error-responses",
            title="Error responses (RFC 9457)",
            blocks=[
                TextBlock(
                    kind="text",
                    id="errors-pitch",
                    text=(
                        "Errors are half of every API's traffic on a bad "
                        "day, so they are contract, not afterthought. RFC "
                        "9457 (\"Problem Details for HTTP APIs\", "
                        "formerly 7807) is the internet's answer: serve "
                        "application/problem+json with a small standard "
                        "vocabulary — type (a URI identifying the problem "
                        "class), title (human summary), status (the "
                        "suggested HTTP code), detail (what happened in "
                        "THIS case), instance (a URI for this occurrence) "
                        "— plus any extension members you need. Its "
                        "insight is that an error's IDENTITY should be "
                        "machine-stable (the type URI) while its "
                        "explanation stays human, and that every endpoint "
                        "answers in one media type so clients write error "
                        "handling exactly once."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="errors-envelope-intro",
                    text=(
                        "This guide's family envelope borrows exactly that "
                        "insight and diverges on the spelling, "
                        "deliberately and on record. One nested error "
                        "object rides every failure this server produces "
                        "— 404s from missing posts, 405s from DELETE, "
                        "422s from bad bodies, 500s from bugs — with a "
                        "machine code drawn from a fixed taxonomy "
                        "(problem+json's type), a human message (title/"
                        "detail), and a requestId standing in for "
                        "instance:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="errors-envelope-code",
                    language="py",
                    caption="The family envelope's error object: the guide's problem-details shape.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "class ErrorBody(CamelModel):\n"
                        '    """The ``error`` object of the envelope; wire keys are camelCase."""\n'
                        "\n"
                        "    code: str\n"
                        '    """Machine-readable failure kind (e.g. ``not_found``)."""\n'
                        "\n"
                        "    message: str\n"
                        '    """Human-readable, client-safe message."""\n'
                        "\n"
                        "    request_id: str\n"
                        '    """The request id from the request-context middleware."""'
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="errors-mapping",
                    text=(
                        "The mapping side is where ad-hoc APIs usually rot: "
                        "an exotic status arrives and every endpoint "
                        "invents its own body. Here ONE table decides — "
                        "the taxonomy names eight kinds with exact "
                        "statuses, and anything the table doesn't name "
                        "(like 405) keeps its truthful status and falls "
                        "into the closest bucket. That decision is why "
                        "DELETE /api/posts answers 405 with code "
                        "not_found — the bucket is coarse, the status "
                        "never lies, and a client's generic handler still "
                        "works:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="errors-mapping-code",
                    language="py",
                    caption="One status-to-kind mapping; unnamed statuses keep the truthful status.",
                    source="server/guide/core/errors.py",
                    snippet=(
                        "def kind_for_http_status(status: int) -> FailureKind:\n"
                        '    """Map an HTTP status to the closest failure kind.\n'
                        "\n"
                        "    Statuses the taxonomy names map exactly; unnamed 4xx statuses take the\n"
                        "    ``not_found`` bucket (closest client-error kind — e.g. 405 method not\n"
                        "    allowed) and unnamed 5xx statuses take ``internal``. The response keeps\n"
                        "    the truthful status either way.\n"
                        '    """\n'
                        "    exact = _KIND_BY_HTTP_STATUS.get(status)\n"
                        "    if exact is not None:\n"
                        "        return exact\n"
                        "    return FailureKind.NOT_FOUND if status < 500 else FailureKind.INTERNAL"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="errors-divergence",
                    text=(
                        "Where the envelope deliberately diverges from "
                        "problem+json, and why: codes come from a closed "
                        "StrEnum instead of type URIs (shorter on the "
                        "wire, checkable by the client's DTO, and this "
                        "client treats null-or-unknown as invalid — "
                        "topic 10's discipline flowing into error "
                        "handling); requestId replaces instance because "
                        "an opaque correlation id is what logs actually "
                        "index on (and it rides the x-request-id header "
                        "too, stamped by the middleware); the body nests "
                        "under error for camelCase consistency with "
                        "every success shape rather than switching media "
                        "types mid-API. If you serve true application/"
                        "problem+json — a fine choice with real "
                        "ecosystem support — the design lesson "
                        "transfers intact: one shape everywhere, "
                        "machine-stable identity, human-safe text, and "
                        "a per-occurrence handle. What no client should "
                        "ever forgive is endpoint-local error bodies "
                        "that drift apart."
                    ),
                ),
            ],
        ),
        # ── 6. Versioning ───────────────────────────────────────────────────
        Section(
            id="versioning",
            title="Versioning",
            blocks=[
                TextBlock(
                    kind="text",
                    id="versioning-pitch",
                    text=(
                        "An API's contract outlives any one deployment of "
                        "it, and versioning is how you change the contract "
                        "without breaking clients you cannot coordinate "
                        "with. The industry has three places to put a "
                        "version, each with real trade-offs. URL-path "
                        "versioning (/v1/posts) is the bluntest and most "
                        "visible: trivially cacheable and proxyable, "
                        "painful because it forks the whole surface and "
                        "invites \"v2 is a rewrite\" drift. Header "
                        "versioning (a custom request header) keeps URLs "
                        "clean and is invisible to casual users — and "
                        "invisible to caching layers, debugging, and "
                        "people sharing links. Media-type versioning "
                        "(Accept: application/vnd.guide.v1+json) is the "
                        "most correct-by-theory — the version belongs to "
                        "the REPRESENTATION, and content negotiation "
                        "(topic 03) already exists to pick "
                        "representations — but it costs the most tooling "
                        "literacy from every client. Choose by audience: "
                        "public, long-lived APIs justify URL paths; "
                        "internal APIs rarely justify the ceremony at "
                        "all."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="versioning-content-api",
                    text=(
                        "This guide's content API makes a fourth, lighter "
                        "choice that fits its audience: the version lives "
                        "IN the representation, as a field, with one "
                        "constant owning the number. Additive changes "
                        "(a new topic, a new block kind the old client "
                        "ignores) ship without a bump; the number moves "
                        "only when a response SHAPE changes in a way a "
                        "client must migrate for — and because both "
                        "content endpoints serve it, a client can detect "
                        "the bump on any content response, not just one "
                        "route:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="versioning-constant-code",
                    language="py",
                    caption="One constant owns the contract version; the docstring is the migration rule.",
                    source="server/guide/content/models.py",
                    snippet=(
                        "CONTENT_API_VERSION: Final[int] = 1\n"
                        '"""Bumped when these response shapes change, so the client migrates deliberately."""'
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="versioning-detail-code",
                    language="py",
                    caption="The detail response carries the version beside the payload it versions.",
                    source="server/guide/content/models.py",
                    snippet=(
                        "class ContentDetail(Topic):\n"
                        '    """The detail route\'s response model: a full Topic plus the API version.\n'
                        "\n"
                        "    Family contract: BOTH content endpoints serve ``version`` so a client\n"
                        "    can detect a CONTENT_API_VERSION bump on any content response and\n"
                        "    migrate deliberately.\n"
                        '    """\n'
                        "\n"
                        "    version: int"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="versioning-coda",
                    text=(
                        "The version field is not decoration — it was "
                        "load-bearing within this guide's own lifetime: "
                        "an early wire drift (a detail payload missing "
                        "its version) broke every topic page in the "
                        "browser while fixture-driven tests stayed green, "
                        "and the fix plus the server-side shape pin that "
                        "followed are exactly the migration contract the "
                        "field promises. The honest summary for your own "
                        "APIs: design so most changes are additive and "
                        "need no version at all (this whole topic is "
                        "that discipline), pick ONE version placement "
                        "and document it as loudly as any endpoint, and "
                        "treat a version bump as a release event with a "
                        "written migration path — not a finding your "
                        "clients discover in production logs."
                    ),
                ),
            ],
        ),
        # ── 7. The whole pipeline ───────────────────────────────────────────
        Section(
            id="the-whole-pipeline",
            title="The whole pipeline",
            lead="The demo of this topic lives here — beside the layers it traces.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="pipeline-pitch",
                    text=(
                        "API design is easiest to trust when you can watch "
                        "one request traverse the whole stack, so this "
                        "section traces GET /api/posts?author=grace&page=2 "
                        "from socket to JSON — through the layers topics "
                        "04 through 10 built one at a time, now carrying "
                        "a real resource. The uvicorn worker hands the "
                        "ASGI scope to the app; the middleware stack runs "
                        "outside-in (topic 08) and the FIRST thing that "
                        "touches the request is the request-id middleware, "
                        "which assigns the correlation id every log line "
                        "and error envelope will carry:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pipeline-middleware-code",
                    language="py",
                    caption="Layer 1 — middleware: one id for the request's whole life.",
                    source="server/guide/core/request_context.py",
                    snippet=(
                        "        request_id = _assign_request_id(_inbound_id(scope))\n"
                        "        token = _request_id.set(request_id)\n"
                        "        # Mirror into the shared ASGI scope so handlers outside this\n"
                        "        # middleware (ServerErrorMiddleware's 500 path) still see the id.\n"
                        "        _mirror_into_scope(scope, request_id)\n"
                        "        if scope[\"type\"] == \"websocket\":\n"
                        "            # A websocket has no response headers to stamp — the id binds so\n"
                        "            # every log line the handler writes correlates to the connection.\n"
                        "            try:\n"
                        "                await self.app(scope, receive, send)\n"
                        "            finally:\n"
                        "                _request_id.reset(token)\n"
                        "            return"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pipeline-routing-validation",
                    text=(
                        "Layer 2 is routing: the path matches the list "
                        "route's template (topic 07) and FastAPI's "
                        "dependency solver assembles the handler's "
                        "arguments — layer 3. The query string binds "
                        "through PostListQuery via Depends (a bad value "
                        "dies HERE as the 422 envelope, topic 10), and "
                        "the handler's use-case bundle resolves from "
                        "app.state, wired once by the composition root — "
                        "the router never learns which adapter sits "
                        "behind the port:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pipeline-wiring-code",
                    language="py",
                    caption="The composition root: one wiring decision per app, invisible above.",
                    source="server/guide/main.py",
                    snippet=(
                        "    posts_repository: PostRepository = InMemoryPostRepository()\n"
                        "    app.state.posts_repository = posts_repository\n"
                        "    posts_use_cases = PostUseCases(\n"
                        "        list_posts=ListPostsUseCase(posts_repository),\n"
                        "        get_post=GetPostUseCase(posts_repository),\n"
                        "        create_post=CreatePostUseCase(posts_repository),\n"
                        "        replace_post=ReplacePostUseCase(posts_repository),\n"
                        "    )\n"
                        "    app.state.posts_use_cases = posts_use_cases"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pipeline-use-case-repo",
                    text=(
                        "Layer 4: the thin handler calls the use case — "
                        "parse, execute, map the Result to HTTP, nothing "
                        "else. The use case is deliberately small here "
                        "(the models already guarantee validity), owning "
                        "exactly the judgment models can't make: does "
                        "this thing EXIST? Failures travel as values — "
                        "Err carries the typed AppError the shared "
                        "handler will render, the domain never throws "
                        "across layers:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pipeline-use-case-code",
                    language="py",
                    caption="Layer 4 — the use case: existence is a domain answer, failures are values.",
                    source="server/guide/domain/posts/use_cases.py",
                    snippet=(
                        "    def execute(self, post_id: str) -> Result[Post]:\n"
                        '        """Ok(post), or Err(not_found) carrying the client-safe message."""\n'
                        "        post = self._posts.get(post_id)\n"
                        "        if post is None:\n"
                        '            return Err(AppError(FailureKind.NOT_FOUND, f"Post {post_id!r} not found"))\n'
                        "        return Ok(post)"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pipeline-repository-read",
                    text=(
                        "Layer 5: the adapter behind the port does the "
                        "actual work — filter, sort, count, slice — and "
                        "returns a frozen snapshot. For the traced "
                        "request: every post by grace (four of the "
                        "twelve seeds), newest first, sliced to page 2 "
                        "at the default limit. The response then flows "
                        "back out: the handler's declared response_model "
                        "documents and filters the wire shape, the "
                        "pagination headers are stamped, and the "
                        "middleware stack unwinds in reverse, the "
                        "request id riding the final header:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="pipeline-repository-code",
                    language="py",
                    caption="Layer 5 — the adapter: the port's contract, fulfilled in memory (a database later).",
                    source="server/guide/data/posts/in_memory.py",
                    snippet=(
                        "    def list(self, query: PostListQuery) -> PostPage:\n"
                        '        """Filter, sort, count, slice — totals reflect the filters."""\n'
                        "        selected = [post for post in self._posts.values() if _matches(post, query)]\n"
                        "        ordered = _ordered(selected, query.sort)\n"
                        "        total = len(ordered)\n"
                        "        start = (query.page - 1) * query.limit\n"
                        "        return PostPage(\n"
                        "            items=ordered[start : start + query.limit],\n"
                        "            # …\n"
                        "        )"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pipeline-demo-pitch",
                    text=(
                        "The demo makes the trace hands-on. It is a "
                        "workbench over the REAL posts substrate: pick a "
                        "method and a path template, tune the query "
                        "(pagination, author/tag/status filters, sort) "
                        "or a create/replace body, and fire — the round "
                        "executes through the same use cases the real "
                        "router resolves, and the answer shows the "
                        "request it would send, the status line, the "
                        "page/post/envelope payload it earns, the "
                        "pagination headers a list would carry, and the "
                        "layer stack that served it. POST and PUT "
                        "genuinely mutate the store (a workbench create "
                        "is visible at /api/posts), missing ids earn the "
                        "real 404 envelope with THIS round's request id, "
                        "and DELETE earns its 405 exactly as the live "
                        "route would answer it:"
                    ),
                ),
                DemoBlock(
                    kind="demo",
                    id="api:posts-workbench",
                    title="The posts workbench",
                    description=(
                        "Assemble a request against the real /api/posts "
                        "resource and watch every layer answer: choose "
                        "GET with a query (page, limit, author, tag, "
                        "status, sort) and read the page payload plus "
                        "the pagination headers; choose GET on the item "
                        "template and a slug like idempotency-retold to "
                        "fetch one post — or a missing slug to earn the "
                        "404 envelope; choose POST and PUT with a body "
                        "(title, author, tags, status) to run the real "
                        "create/replace use cases and see 201 + Location "
                        "or 200 with identity preserved; choose DELETE "
                        "on either template to watch the routing layer "
                        "answer 405 through the shared envelope. Every "
                        "round reports the use-case and repository "
                        "layers that served it, with the numbers from "
                        "that real run."
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="pipeline-coda",
                    text=(
                        "That full trace — middleware, routing, "
                        "validation, dependency wiring, use case, "
                        "adapter, response — is the mental model every "
                        "remaining topic plugs into: documentation "
                        "generates from the models you just saw "
                        "(topic 12), GraphQL reuses the same use cases "
                        "under a different uniform interface (topic 13), "
                        "and webhooks reverse the arrow with the same "
                        "envelope discipline (topic 14). When a request "
                        "misbehaves in any of them, you now know which "
                        "layer to read first."
                    ),
                ),
            ],
        ),
        # ── 8. Terminal companion ───────────────────────────────────────────
        Section(
            id="terminal-companion",
            title="Terminal companion: the curl tour",
            lead="One real resource, every design decision, read straight off the wire.",
            blocks=[
                TextBlock(
                    kind="text",
                    id="terminal-pitch",
                    text=(
                        "With the stack up (server on :8000), this tour "
                        "walks the posts resource exactly as designed: "
                        "the collection with its pagination headers, a "
                        "filtered page whose Link header preserves the "
                        "lens, one item, the honest 404, a create that "
                        "answers 201 + Location, a replace, and the 405 "
                        "the absent DELETE earns. -i shows status lines "
                        "and headers; python3 -m json.tool keeps it "
                        "dependency-free:"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-list",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the collection: default page, totals in headers\n"
                        "curl -s -i localhost:8000/api/posts | head -20"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-filtered",
                    language="bash",
                    source=None,
                    snippet=(
                        "# a filtered, sorted page — Link preserves the lens, defaults omitted\n"
                        "curl -s -i 'localhost:8000/api/posts?author=grace&tag=design&sort=oldest&page=1' \\\n"
                        "  | grep -iE '^(HTTP|x-total-count|x-page-count|link:)'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-item",
                    language="bash",
                    source=None,
                    snippet=(
                        "# one item by slug\n"
                        "curl -s localhost:8000/api/posts/idempotency-retold | python3 -m json.tool"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-404",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the honest 404: shared envelope, request id, x-request-id header\n"
                        "curl -s -i localhost:8000/api/posts/does-not-exist"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-create",
                    language="bash",
                    source=None,
                    snippet=(
                        "# create: 201 + Location (the adapter minted the slug from the title)\n"
                        "curl -s -i -X POST localhost:8000/api/posts -H 'content-type: application/json' \\\n"
                        "  -d '{\"title\":\"A post from the tour\",\"author\":\"you\",\"tags\":[\"api\"],\"status\":\"published\"}'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-replace",
                    language="bash",
                    source=None,
                    snippet=(
                        "# full replace: same id and created_at, fresh updated_at, status moved\n"
                        "curl -s -X PUT localhost:8000/api/posts/a-post-from-the-tour -H 'content-type: application/json' \\\n"
                        "  -d '{\"title\":\"A post from the tour, revised\",\"author\":\"you\",\"tags\":[\"api\"],\"status\":\"draft\"}' \\\n"
                        "  | python3 -m json.tool | grep -E '\"(id|created_at|updated_at|status)\"'"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-405",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the method the resource does not define: 405 through the shared envelope\n"
                        "curl -s -i -X DELETE localhost:8000/api/posts/a-post-from-the-tour"
                    ),
                ),
                CodeBlock(
                    kind="code",
                    id="terminal-workbench",
                    language="bash",
                    source=None,
                    snippet=(
                        "# the topic's demo from the terminal: one traced round, layer by layer\n"
                        "curl -s -X POST localhost:8000/api/demo/api/workbench -H 'content-type: application/json' \\\n"
                        "  -d '{\"method\":\"GET\",\"template\":\"/api/posts\",\"query\":{\"page\":2,\"limit\":4}}' \\\n"
                        "  | python3 -m json.tool | grep -A3 '\"statusReason\"'"
                    ),
                ),
                TextBlock(
                    kind="text",
                    id="terminal-coda",
                    text=(
                        "Read the create answer closely and the whole "
                        "topic is there: 201 because a resource came into "
                        "being, Location naming it because the server "
                        "owns identity, the slug derived from your title "
                        "because that is the adapter's documented "
                        "strategy, and the x-request-id header because "
                        "the middleware stamped it before routing began. "
                        "Then delete nothing, on purpose — the 405 is "
                        "the API telling the truth about its own "
                        "surface. That is API design: not a style "
                        "checker's score, but a surface where every "
                        "URL, verb, status, header, and error is a "
                        "deliberate, documented answer. The APIs group "
                        "continues with topic 12, where this same "
                        "resource gets machine-readable documentation "
                        "for free."
                    ),
                ),
            ],
        ),
    ],
)
