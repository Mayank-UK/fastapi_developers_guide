"""The posts domain vocabulary: entity, create draft, list query, page.

One module owns every shape the posts area speaks, because together they ARE
the resource contract: ``Post`` is the representation (and the entity — a
frozen snapshot, never mutated in place), ``PostCreate`` is the full
representation a client sends (POST creates it, PUT replaces with it),
``PostListQuery`` is the collection's query surface (pagination, filtering,
sorting — the same model binds FastAPI query parameters and the workbench
demo's body), and ``PostPage`` is the paginated answer.

Validation lives on the models (topic 10's discipline): an invalid draft or
query cannot be constructed, so use cases and the repository never re-check
bounds. Timestamps are ISO-8601 strings minted by the adapter that stores
the post — the domain does not own a clock.
"""

from typing import Annotated, Literal

from pydantic import Field

from guide.core.serialization import CamelModel

PostStatus = Literal["draft", "published"]
"""The two post states; a Literal so any other spelling dies at the edge."""

PostSort = Literal["newest", "oldest", "title"]
"""Collection sort orders — a closed vocabulary, not a free string."""

DEFAULT_LIST_LIMIT: int = 6
"""The collection's default page size; links omit it when unchanged."""


class PostCreate(CamelModel):
    """The POST/PUT body: the full representation a client sends."""

    title: Annotated[str, Field(min_length=1, max_length=120)]
    body: Annotated[str, Field(max_length=5000)] = ""
    author: Annotated[str, Field(min_length=1, max_length=40)]
    tags: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=40)]], Field(max_length=8)
    ] = []
    status: PostStatus = "draft"


class Post(CamelModel):
    """One stored post: the entity and the wire representation in one model.

    ``id`` is a slug minted by the repository (the adapter owns identifier
    strategy); ``created_at`` survives replacement while ``updated_at``
    does not — replace keeps identity metadata and refreshes the edit stamp.
    """

    id: str
    title: str
    body: str
    author: str
    tags: list[str]
    status: PostStatus
    created_at: str
    updated_at: str


class PostListQuery(CamelModel):
    """The collection query surface: pagination, filtering, sorting.

    Constraints are part of the contract: pages count from 1, the page size
    is capped at 100 so one request cannot demand the whole store, filters
    are exact matches, and ``sort`` is a closed vocabulary.
    """

    page: Annotated[int, Field(ge=1, le=10_000)] = 1
    limit: Annotated[int, Field(ge=1, le=100)] = DEFAULT_LIST_LIMIT
    author: str | None = Field(default=None, min_length=1, max_length=40)
    tag: str | None = Field(default=None, min_length=1, max_length=40)
    status: PostStatus | None = None
    sort: PostSort = "newest"


class PostPage(CamelModel):
    """One page of a filtered, sorted collection — totals included.

    ``total`` counts every matching post (before pagination) and ``pages``
    is the last page number, so clients can render honest page controls:
    ``page > pages`` yields an empty ``items`` list, not an error.
    """

    items: list[Post]
    total: int
    page: int
    limit: int
    pages: int
