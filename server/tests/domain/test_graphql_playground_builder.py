"""The graphql-playground payload builder: pure packaging of a live schema.

Builder discipline (mirror of the docs-link builder tests): pure function,
every fact derived from the inputs, the curated tour stable — five
examples with distinct ids, each query exactly the operation text the
endpoint and terminal companion send, and the reasoning derived from the
endpoint it was handed.
"""

from guide.domain.demos.graphql_playground import build_graphql_playground_payload

SDL = "type Query {\n  posts: PostPage\n}\n"


def test_pure_builder_packages_endpoint_sdl_and_tour() -> None:
    payload = build_graphql_playground_payload(endpoint="/api/graphql", sdl=SDL)
    assert payload.endpoint == "/api/graphql"
    assert payload.sdl == SDL
    assert [example.id for example in payload.examples] == [
        "page",
        "authors",
        "mutation",
        "introspection",
        "error",
    ]
    assert "/api/graphql" in payload.reasoning
    assert "schema.as_str()" in payload.reasoning


def test_every_example_carries_label_description_and_operation() -> None:
    payload = build_graphql_playground_payload(endpoint="/api/graphql", sdl=SDL)
    for example in payload.examples:
        assert example.label
        assert example.description
        assert example.query.strip()
        assert example.query.lstrip().startswith(("query", "mutation"))


def test_the_tour_spans_read_write_introspection_and_error() -> None:
    payload = build_graphql_playground_payload(endpoint="/api/graphql", sdl=SDL)
    by_id = {example.id: example for example in payload.examples}
    # The nested example asks for the author projection the loader batches.
    assert "author {" in by_id["authors"].query
    # The mutation is a real createPost with typed input.
    assert "createPost" in by_id["mutation"].query
    # Introspection reads the protocol's own meta fields.
    assert "__schema" in by_id["introspection"].query
    # The error example targets a slug the seed never mints.
    assert 'post(slug: "no-such-post")' in by_id["error"].query


def test_builder_is_deterministic_and_input_isolated() -> None:
    first = build_graphql_playground_payload(endpoint="/api/graphql", sdl=SDL)
    second = build_graphql_playground_payload(endpoint="/api/graphql", sdl=SDL)
    assert first == second
    other = build_graphql_playground_payload(endpoint="/other", sdl="type X")
    assert other.endpoint == "/other"
    assert other.sdl == "type X"
    # The inputs never leak into the curated tour.
    assert [e.query for e in other.examples] == [e.query for e in first.examples]
