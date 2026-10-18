"""GraphQL playground demo payload: the live SDL + a curated query tour.

``GET /api/demo/api/graphql-playground`` serves this payload — topic 13's
demo. The endpoint hands the REAL schema's SDL (``schema.as_str()``, the
same object the mounted router executes) to this pure builder, which
packages it with the endpoint path and five curated queries — a paged
collection read, the nested author projection (the one the dataloader
batches), a real mutation, one introspection probe, and a deliberate
not-found error — so the client's interactive console can load each into
its editor and POST it to the live ``/api/graphql``.

The builder is pure: endpoint + SDL in, payload out — no I/O, no app
access. Every query string is exactly what the terminal companion curl
tour sends, so the demo and the tour cannot drift apart.
"""

from typing import Final

from guide.core.serialization import CamelModel

PAGE_QUERY: Final[str] = (
    "query {\n"
    "  posts(limit: 3, sort: OLDEST) {\n"
    "    total\n"
    "    pages\n"
    "    items {\n"
    "      id\n"
    "      title\n"
    "      status\n"
    "      authorName\n"
    "    }\n"
    "  }\n"
    "}"
)
"""The collection read: a typed page, oldest first — exactly REST's page 1."""

AUTHORS_QUERY: Final[str] = (
    "query {\n"
    "  posts(limit: 6) {\n"
    "    items {\n"
    "      title\n"
    "      author {\n"
    "        id\n"
    "        postCount\n"
    "      }\n"
    "    }\n"
    "  }\n"
    "}"
)
"""The nested projection: six posts, three authors, ONE batched loader round."""

MUTATION_QUERY: Final[str] = (
    "mutation {\n"
    "  createPost(input: {\n"
    '    title: "Hello from the playground"\n'
    '    author: "you"\n'
    '    tags: ["graphql"]\n'
    "    status: PUBLISHED\n"
    "  }) {\n"
    "    id\n"
    "    title\n"
    "    createdAt\n"
    "  }\n"
    "}"
)
"""A real write: the mutation mints a slug and stamps the clock."""

INTROSPECTION_QUERY: Final[str] = (
    "query {\n"
    "  __schema {\n"
    "    queryType {\n"
    "      name\n"
    "    }\n"
    "    mutationType {\n"
    "      name\n"
    "    }\n"
    "  }\n"
    "}"
)
"""The protocol reading its own contract: the entry points, from __schema."""

ERROR_QUERY: Final[str] = 'query {\n  post(slug: "no-such-post") {\n    id\n    title\n  }\n}'
"""The deliberate failure: a 200 whose errors array carries the family code."""


class ExampleQuery(CamelModel):
    """One curated query the playground can load into its editor."""

    id: str
    label: str
    description: str
    query: str


class GraphqlPlaygroundPayload(CamelModel):
    """Wire shape of ``GET /api/demo/api/graphql-playground``."""

    endpoint: str
    sdl: str
    examples: list[ExampleQuery]
    reasoning: str


def build_graphql_playground_payload(*, endpoint: str, sdl: str) -> GraphqlPlaygroundPayload:
    """Shape the playground package (pure): the endpoint, the SDL, the tour."""
    examples = [
        ExampleQuery(
            id="page",
            label="A page of posts",
            description=(
                "The collection read: page, limit, and sort arguments with a "
                "typed page back — the same facts GET /api/posts serves."
            ),
            query=PAGE_QUERY,
        ),
        ExampleQuery(
            id="authors",
            label="Nested authors (batched)",
            description=(
                "Six posts, each projecting its author object: the loader "
                "collects the bylines and answers all of them in ONE batch."
            ),
            query=AUTHORS_QUERY,
        ),
        ExampleQuery(
            id="mutation",
            label="A real mutation",
            description=(
                "createPost mints a slug, stamps the clock, and stores the "
                "post — the same use case POST /api/posts runs."
            ),
            query=MUTATION_QUERY,
        ),
        ExampleQuery(
            id="introspection",
            label="Introspection",
            description=(
                "The schema reading itself: __schema names the query and "
                "mutation entry points every client can discover at runtime."
            ),
            query=INTROSPECTION_QUERY,
        ),
        ExampleQuery(
            id="error",
            label="A not-found error",
            description=(
                "An unknown slug answers HTTP 200 with an errors array — "
                "message, locations, path, and the family code not_found."
            ),
            query=ERROR_QUERY,
        ),
    ]
    return GraphqlPlaygroundPayload(
        endpoint=endpoint,
        sdl=sdl,
        examples=examples,
        reasoning=(
            f"POST {endpoint} with a JSON body like "
            '\'{"query": "…"}\' is the entire transport. The SDL below is the '
            "running schema exactly as strawberry serves it (schema.as_str(), "
            "not hand-written), and each example loads into the editor and "
            "fires against the live endpoint — the mutation genuinely stores "
            "a post, and the error example earns its 200-with-errors honestly."
        ),
    )
