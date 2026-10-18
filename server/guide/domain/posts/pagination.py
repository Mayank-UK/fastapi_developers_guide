"""Pagination math + canonical list URLs, shared by router and workbench.

The real ``GET /api/posts`` stamps its pagination facts into headers
(``x-total-count``, ``x-page-count``, RFC 8288 ``Link`` for prev/next), and
the api-design workbench demo reports the SAME links in its payload — this
module is the single source of both, so the demo cannot drift from the
route. Links are relative paths with only the non-default query parts
(``page=1``, the default limit, ``sort=newest`` are omitted), URL-encoded
through ``urlencode`` so filter values never forge the URL.
"""

from math import ceil
from typing import Final
from urllib.parse import urlencode

from guide.domain.posts.entities import DEFAULT_LIST_LIMIT, PostListQuery

COLLECTION_PATH: Final[str] = "/api/posts"
"""The collection the link builder addresses (kept beside it on purpose)."""


def page_count(total: int, limit: int) -> int:
    """Last page number for ``total`` items at ``limit`` per page (min 1).

    An empty collection is one empty page, not zero pages — clients can
    always point at page 1 without special-casing the void.
    """
    if limit < 1:
        raise ValueError(f"limit must be >= 1, got {limit}")
    return max(1, ceil(total / limit))


def _params(query: PostListQuery) -> list[tuple[str, str]]:
    """Only the non-default query parts, in a stable order."""
    params: list[tuple[str, str]] = []
    if query.page != 1:
        params.append(("page", str(query.page)))
    if query.limit != DEFAULT_LIST_LIMIT:
        params.append(("limit", str(query.limit)))
    if query.author is not None:
        params.append(("author", query.author))
    if query.tag is not None:
        params.append(("tag", query.tag))
    if query.status is not None:
        params.append(("status", query.status))
    if query.sort != "newest":
        params.append(("sort", query.sort))
    return params


def request_path(query: PostListQuery, base_path: str = COLLECTION_PATH) -> str:
    """The canonical URL for one list request: defaults omitted."""
    params = _params(query)
    return f"{base_path}?{urlencode(params)}" if params else base_path


def page_url(query: PostListQuery, page: int, base_path: str = COLLECTION_PATH) -> str:
    """The canonical URL for the same query on another page."""
    return request_path(query.model_copy(update={"page": page}), base_path)


class PageLinks:
    """prev/next URLs for one list result; None where the page has no such."""

    def __init__(self, prev: str | None, next_: str | None) -> None:
        self.prev = prev
        self.next = next_


def build_page_links(
    query: PostListQuery, total: int, base_path: str = COLLECTION_PATH
) -> PageLinks:
    """Where the neighboring pages live, or None at the edges.

    Computed from ``page_count`` — a query past the last page gets a next
    link only while ``page < pages``, so links never promise an empty page.
    """
    pages = page_count(total, query.limit)
    prev = page_url(query, query.page - 1, base_path) if query.page > 1 else None
    next_ = page_url(query, query.page + 1, base_path) if query.page < pages else None
    return PageLinks(prev, next_)


def format_link_header(links: PageLinks) -> str | None:
    """The RFC 8288 header value, or None when there is nothing to say."""
    parts: list[str] = []
    if links.next is not None:
        parts.append(f'<{links.next}>; rel="next"')
    if links.prev is not None:
        parts.append(f'<{links.prev}>; rel="prev"')
    return ", ".join(parts) if parts else None
