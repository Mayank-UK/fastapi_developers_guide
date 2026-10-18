"""API workbench: one picked /api/posts request, answered layer by layer.

``GET /api/demo/api/workbench`` and ``POST /api/demo/api/workbench`` serve
these payloads. The workbench is topic 11's demo: the caller picks a
method + path template (plus the collection query, or an item id, or a
create/replace body), and the demo endpoint runs that request through the
REAL posts substrate — the same ``PostUseCases`` bundle ``/api/posts``
resolves, the same in-memory repository — then reports what happened:
the request it would send, the status line, the page/post/envelope payload
it earns, the pagination headers a list would carry, and the layer stack
(routing → validation → use case → repository → response) that served it.

Nothing here is simulated except the clock the real request would have
taken: POST/PUT rounds genuinely mutate the repository (a workbench create
is visible at ``/api/posts``), failures carry the exact envelope the real
route would serve — including the 405 a method+template combination no
route answers, mirroring what Starlette itself does for ``DELETE
/api/posts`` — and the 404/405 envelope's requestId is the CURRENT
request's id, so it matches the ``x-request-id`` header on the workbench's
own response.

The builders are pure: request + results in, payload out, no I/O. The
router runs the use cases and hands each result to the matching builder;
every number in the reasoning strings comes from that real run.
"""

from typing import Final, Literal

from pydantic import Field, JsonValue, model_validator

from guide.core.errors import AppError, FailureKind, http_status_for
from guide.core.result import Err, Result
from guide.core.serialization import CamelModel
from guide.domain.posts.entities import (
    Post,
    PostCreate,
    PostListQuery,
    PostPage,
    PostSort,
    PostStatus,
)
from guide.domain.posts.pagination import COLLECTION_PATH, build_page_links, request_path

WorkbenchMethod = Literal["GET", "POST", "PUT", "DELETE"]
"""The methods the workbench offers — DELETE is there to earn its 405."""

COLLECTION_TEMPLATE: Final[str] = "/api/posts"
ITEM_TEMPLATE: Final[str] = "/api/posts/{postId}"
"""Runtime spellings of the two path shapes (tests pin them to the Literal)."""

WorkbenchTemplate = Literal["/api/posts", "/api/posts/{postId}"]
"""The two path shapes of the posts resource, template-spelled."""

WorkbenchOperation = Literal["list", "get", "create", "replace", "method-not-allowed"]
"""What a method+template combination resolves to on the real route table."""


class WorkbenchRequest(CamelModel):
    """One workbench round: the request you would send, spelled as data.

    ``post_id`` belongs to the item template alone, ``query`` to GET on the
    collection, ``body`` to POST/PUT — the cross-field rules below are the
    request model refusing combinations no route answers, so a bogus round
    dies as the edge's own 422 before any use case runs (part of the
    lesson, same discipline as the arena's roster Literal).
    """

    method: WorkbenchMethod
    template: WorkbenchTemplate
    post_id: str | None = Field(default=None, min_length=1, max_length=80)
    query: PostListQuery | None = None
    body: PostCreate | None = None

    @model_validator(mode="after")
    def _combination_must_match_a_route(self) -> "WorkbenchRequest":
        item = self.template == ITEM_TEMPLATE
        if item and self.post_id is None:
            raise ValueError("post_id is required with the item template")
        if not item and self.post_id is not None:
            raise ValueError("post_id only applies to the item template")
        if self.query is not None and not (self.method == "GET" and not item):
            raise ValueError("query applies only to GET /api/posts")
        if self.method in ("POST", "PUT"):
            if self.body is None:
                raise ValueError(f"a body is required for {self.method}")
        elif self.body is not None:
            raise ValueError(f"a body does not apply to {self.method}")
        return self


class WorkbenchRequestFact(CamelModel):
    """The request the picked round would put on the wire."""

    method: WorkbenchMethod
    template: WorkbenchTemplate
    path: str
    """The concrete URL: template instantiated, canonical query string."""

    body: dict[str, JsonValue] | None = None


class WorkbenchEnvelope(CamelModel):
    """The error envelope a failure earns — shape-identical to the real one."""

    code: str
    message: str
    request_id: str


class WorkbenchPagination(CamelModel):
    """The pagination facts a list response carries in its headers."""

    total: int
    page: int
    limit: int
    pages: int
    next: str | None = None
    prev: str | None = None


class WorkbenchLayer(CamelModel):
    """One pipeline layer that served the round, in call order."""

    name: str
    detail: str


class WorkbenchPayload(CamelModel):
    """Wire shape of POST /api/demo/api/workbench."""

    operation: WorkbenchOperation
    request: WorkbenchRequestFact
    status: int
    status_reason: str
    kind: Literal["page", "post", "envelope"]
    page: PostPage | None = None
    post: Post | None = None
    envelope: WorkbenchEnvelope | None = None
    pagination: WorkbenchPagination | None = None
    layers: list[WorkbenchLayer]
    reasoning: str


class WorkbenchRosterPayload(CamelModel):
    """Wire shape of GET /api/demo/api/workbench: the substrate's facets."""

    authors: list[str]
    tags: list[str]
    statuses: list[PostStatus]
    sorts: list[PostSort]
    total_posts: int
    reasoning: str


_STATUS_REASONS: Final[dict[int, str]] = {
    200: "200 OK",
    201: "201 Created",
    404: "404 Not Found",
    405: "405 Method Not Allowed",
}
"""Status lines the workbench reports; every value is a real outcome here."""

_METHOD_NOT_ALLOWED_MESSAGE: Final[str] = "Method Not Allowed"
"""Starlette's own 405 detail — the workbench mirrors the real response."""

_ROUTES_FACT: Final[str] = (
    "the posts router defines GET+POST on /api/posts and GET+PUT on /api/posts/{post_id}"
)


def workbench_operation(request: WorkbenchRequest) -> WorkbenchOperation:
    """Resolve a method+template pair against the real route table's shape."""
    item = request.template == ITEM_TEMPLATE
    if request.method == "GET":
        return "get" if item else "list"
    if request.method == "POST" and not item:
        return "create"
    if request.method == "PUT" and item:
        return "replace"
    return "method-not-allowed"


def _request_fact(request: WorkbenchRequest) -> WorkbenchRequestFact:
    """The concrete request the round describes (canonical URL, body dump)."""
    if request.template == ITEM_TEMPLATE:
        path = f"{COLLECTION_PATH}/{request.post_id}"
    else:
        query = request.query if request.query is not None else PostListQuery()
        path = request_path(query)
    return WorkbenchRequestFact(
        method=request.method,
        template=request.template,
        path=path,
        body=(
            request.body.model_dump(mode="json", by_alias=True)
            if request.body is not None
            else None
        ),
    )


def _layers(*entries: tuple[str, str]) -> list[WorkbenchLayer]:
    return [WorkbenchLayer(name=name, detail=detail) for name, detail in entries]


def _failure_payload(
    operation: WorkbenchOperation,
    fact: WorkbenchRequestFact,
    failure: AppError,
    request_id: str,
    use_case_detail: str,
) -> WorkbenchPayload:
    """The shared shape of every Err outcome: honest status, real envelope."""
    status = http_status_for(failure.kind)
    return WorkbenchPayload(
        operation=operation,
        request=fact,
        status=status,
        status_reason=_STATUS_REASONS.get(status, f"{status} {failure.kind.value}"),
        kind="envelope",
        envelope=WorkbenchEnvelope(
            code=failure.kind.value, message=failure.message, request_id=request_id
        ),
        layers=_layers(
            _routing_layer_of_fact(fact),
            _validation_layer_of_fact(fact),
            ("use case", use_case_detail),
            (
                "response",
                "the router raised the AppError; the shared handler rendered "
                "the family envelope — code, message, requestId — and logged "
                "it with the request id",
            ),
        ),
        reasoning=(
            f"The real {fact.method} {fact.path} would answer {status} with "
            "this exact envelope: the failure kind maps through the same "
            "taxonomy table every endpoint shares, and the requestId below "
            "is this workbench round's own id."
        ),
    )


def _routing_layer_of_fact(fact: WorkbenchRequestFact) -> tuple[str, str]:
    if fact.template == ITEM_TEMPLATE:
        return (
            "routing",
            f"{fact.method} /api/posts/{{postId}} matched the item route; "
            "post_id extracted from the path",
        )
    return (
        "routing",
        f"{fact.method} /api/posts matched the collection route (no path parameters to extract)",
    )


def _validation_layer_of_fact(fact: WorkbenchRequestFact) -> tuple[str, str]:
    if fact.body is not None:
        return (
            "validation",
            "the JSON body validated through PostCreate — title/author length "
            "bounds, at most 8 tags, status a Literal; a bad body is the "
            "edge's own 422 before any use case runs",
        )
    if fact.template == COLLECTION_TEMPLATE and fact.method == "GET":
        return (
            "validation",
            "FastAPI bound the query string through PostListQuery (Depends) — "
            "page >= 1, limit 1..100, closed sort/status vocabularies",
        )
    return (
        "validation",
        "the path parameter is a str; no query or body to validate",
    )


def build_method_not_allowed(request: WorkbenchRequest, request_id: str) -> WorkbenchPayload:
    """The 405 a combination no route answers — mirroring Starlette's own."""
    fact = _request_fact(request)
    return WorkbenchPayload(
        operation="method-not-allowed",
        request=fact,
        status=405,
        status_reason=_STATUS_REASONS[405],
        kind="envelope",
        envelope=WorkbenchEnvelope(
            code=FailureKind.NOT_FOUND.value,
            message=_METHOD_NOT_ALLOWED_MESSAGE,
            request_id=request_id,
        ),
        layers=_layers(
            (
                "routing",
                f"{request.method} + {request.template} matches no route: {_ROUTES_FACT}",
            ),
            (
                "response",
                "Starlette answers 405 Method Not Allowed; the shared handler "
                "wraps it in the family envelope — kind not_found, the "
                "taxonomy's bucket for unnamed 4xx statuses",
            ),
        ),
        reasoning=(
            f"No route answers {fact.method} {fact.path}, so the framework "
            "itself replies 405 — before any handler, use case, or "
            "repository runs. Try the same round as GET, POST, or PUT to "
            "watch a matched route traverse the whole stack."
        ),
    )


def build_list_outcome(
    request: WorkbenchRequest, result: Result[PostPage], request_id: str
) -> WorkbenchPayload:
    """A GET /api/posts round: the page, the headers, the stack that built it."""
    fact = _request_fact(request)
    if isinstance(result, Err):
        return _failure_payload(
            "list", fact, result.failure, request_id, "ListPostsUseCase returned Err"
        )
    page = result.value
    query = request.query if request.query is not None else PostListQuery()
    links = build_page_links(query, page.total)
    filters = []
    if query.author is not None:
        filters.append(f"author={query.author}")
    if query.tag is not None:
        filters.append(f"tag={query.tag}")
    if query.status is not None:
        filters.append(f"status={query.status}")
    filter_text = ", ".join(filters) if filters else "no filters"
    link_header = ", ".join(
        part
        for part in (
            f'<{links.next}>; rel="next"' if links.next is not None else None,
            f'<{links.prev}>; rel="prev"' if links.prev is not None else None,
        )
        if part is not None
    )
    header_text = link_header if link_header else "no Link header on a single page"
    return WorkbenchPayload(
        operation="list",
        request=fact,
        status=200,
        status_reason=_STATUS_REASONS[200],
        kind="page",
        page=page,
        pagination=WorkbenchPagination(
            total=page.total,
            page=page.page,
            limit=page.limit,
            pages=page.pages,
            next=links.next,
            prev=links.prev,
        ),
        layers=_layers(
            _routing_layer_of_fact(fact),
            _validation_layer_of_fact(fact),
            (
                "use case",
                "ListPostsUseCase.execute ran with the validated query and "
                "called the PostRepository port",
            ),
            (
                "repository",
                f"InMemoryPostRepository.list applied {filter_text}, sorted "
                f"{query.sort}, and sliced page {page.page} of {page.pages} — "
                f"{page.total} post(s) match in total",
            ),
            (
                "response",
                f"PostPage serialized camelCase; x-total-count: {page.total}, "
                f"x-page-count: {page.pages}, {header_text}",
            ),
        ),
        reasoning=(
            f"The real GET {fact.path} answers 200 with these {len(page.items)} "
            f"post(s) of {page.total} matching, page {page.page} of "
            f"{page.pages}. The pagination block is exactly what the response "
            "headers carry — fire page 2 (or a filter) and watch the links "
            "and totals move together."
        ),
    )


def build_get_outcome(
    request: WorkbenchRequest, result: Result[Post], request_id: str
) -> WorkbenchPayload:
    """A GET /api/posts/{postId} round: one post, or the honest 404."""
    fact = _request_fact(request)
    if isinstance(result, Err):
        return _failure_payload(
            "get",
            fact,
            result.failure,
            request_id,
            "GetPostUseCase returned Err(AppError(not_found)) — existence is "
            "a domain answer, not a validation one",
        )
    post = result.value
    return WorkbenchPayload(
        operation="get",
        request=fact,
        status=200,
        status_reason=_STATUS_REASONS[200],
        kind="post",
        post=post,
        layers=_layers(
            _routing_layer_of_fact(fact),
            _validation_layer_of_fact(fact),
            ("use case", "GetPostUseCase.execute asked the port for one post"),
            (
                "repository",
                f"InMemoryPostRepository.get returned the stored snapshot for {post.id!r}",
            ),
            (
                "response",
                "200; Post serialized camelCase — response_model declares the contract in OpenAPI",
            ),
        ),
        reasoning=(
            f"The real GET {fact.path} answers 200 with this exact "
            "representation. Change the id to something unknown and re-fire: "
            "the same layers run, the use case returns Err(not_found), and "
            "the shared handler answers the family envelope."
        ),
    )


def build_create_outcome(
    request: WorkbenchRequest, result: Result[Post], request_id: str
) -> WorkbenchPayload:
    """A POST /api/posts round: 201 + Location — and the store really grew."""
    fact = _request_fact(request)
    if isinstance(result, Err):
        return _failure_payload(
            "create", fact, result.failure, request_id, "CreatePostUseCase returned Err"
        )
    post = result.value
    return WorkbenchPayload(
        operation="create",
        request=fact,
        status=201,
        status_reason=_STATUS_REASONS[201],
        kind="post",
        post=post,
        layers=_layers(
            _routing_layer_of_fact(fact),
            _validation_layer_of_fact(fact),
            ("use case", "CreatePostUseCase.execute handed the draft to the port"),
            (
                "repository",
                f"InMemoryPostRepository.create minted the slug {post.id!r} "
                "(uniquified when a title collides), stamped the clock, and "
                "stored the snapshot",
            ),
            (
                "response",
                f"201 Created; Location: /api/posts/{post.id} names the new "
                "resource — resolved with url_path_for, never string-pasted",
            ),
        ),
        reasoning=(
            f"The real POST /api/posts accepted this body and answered 201 "
            f"with Location naming {post.id!r}. The repository genuinely "
            "holds it now — GET /api/posts lists it, and firing the same "
            "title again mints a uniquified slug."
        ),
    )


def build_replace_outcome(
    request: WorkbenchRequest, result: Result[Post], request_id: str
) -> WorkbenchPayload:
    """A PUT /api/posts/{postId} round: 200 full-replace, identity kept."""
    fact = _request_fact(request)
    if isinstance(result, Err):
        return _failure_payload(
            "replace",
            fact,
            result.failure,
            request_id,
            "ReplacePostUseCase returned Err(AppError(not_found)) — replace never creates",
        )
    post = result.value
    return WorkbenchPayload(
        operation="replace",
        request=fact,
        status=200,
        status_reason=_STATUS_REASONS[200],
        kind="post",
        post=post,
        layers=_layers(
            _routing_layer_of_fact(fact),
            _validation_layer_of_fact(fact),
            (
                "use case",
                "ReplacePostUseCase.execute asked the port to full-replace the post",
            ),
            (
                "repository",
                "InMemoryPostRepository.replace stored a NEW snapshot — new "
                "content, same id and created_at, a fresh updated_at stamp",
            ),
            (
                "response",
                "200 with the new representation; the entity and the wire "
                "model are one, so the contract is declared once",
            ),
        ),
        reasoning=(
            f"The real PUT {fact.path} answered 200 with the replaced "
            "representation: identity metadata (id, created_at) survived, "
            "updated_at moved. PUT is idempotent — fire it twice and the "
            "second answer matches the first."
        ),
    )


def build_workbench_roster(page: PostPage) -> WorkbenchRosterPayload:
    """The substrate's live facets: authors, tags, statuses, sorts, counts."""
    authors = sorted({post.author for post in page.items})
    tags = sorted({tag for post in page.items for tag in post.tags})
    published = sum(post.status == "published" for post in page.items)
    return WorkbenchRosterPayload(
        authors=authors,
        tags=tags,
        statuses=["draft", "published"],
        sorts=["newest", "oldest", "title"],
        total_posts=page.total,
        reasoning=(
            f"The workbench runs over the REAL /api/posts substrate: "
            f"{page.total} posts live in the in-memory repository right now "
            f"({published} published, {page.total - published} drafts) by "
            f"{len(authors)} author(s). Pick a method and template, tune the "
            "query or body, and fire — the round executes through the same "
            "use cases the real router resolves, so POST and PUT really "
            "change what GET sees."
        ),
    )
