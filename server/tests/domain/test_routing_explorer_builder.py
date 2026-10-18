"""Routing-explorer builder: the pure matcher against a fixture route table.

The builder is the demo's engine — template-to-regex compilation, the
first-match walk, path/query binding, and the 404/405/307 outcomes — so
these tests pin each outcome against a small hand-authored OpenAPI-style
paths mapping, independent of the live app.
"""

from guide.domain.demos.routing_explorer import build_routing_explorer_payload

PATHS = {
    "/api/health": {"get": {"tags": ["health"]}},
    "/api/content": {"get": {"tags": ["content"]}},
    "/api/content/{topic_id}": {"get": {"tags": ["content"]}},
    "/api/demo/http/headers": {
        "get": {"tags": ["demo:http"]},
        "post": {"tags": ["demo:http"]},
    },
}


def build(method: str, path: str):
    return build_routing_explorer_payload(method=method, path=path, paths=PATHS)


def test_match_binds_path_parameter_and_methods() -> None:
    payload = build("GET", "/api/content/routing")
    assert payload.outcome == "matched"
    assert payload.route_count == 4
    assert payload.matched_path == "/api/content/{topic_id}"
    assert payload.matched_methods == ["GET"]
    assert payload.matched_tags == ["content"]
    assert [(p.name, p.value, p.source) for p in payload.path_params] == [
        ("topic_id", "routing", "path")
    ]
    assert "topic_id='routing'" in payload.reasoning


def test_match_parses_query_parameters_with_blank_values_kept() -> None:
    payload = build("GET", "/api/content/routing?method=X&flag=")
    assert payload.outcome == "matched"
    assert [(p.name, p.value) for p in payload.query_params] == [("method", "X"), ("flag", "")]
    assert "method='X'" in payload.reasoning


def test_static_path_matches_without_parameters() -> None:
    payload = build("GET", "/api/health")
    assert payload.outcome == "matched"
    assert payload.matched_path == "/api/health"
    assert payload.path_params == []
    assert payload.query_params == []


def test_declared_method_on_multi_verb_route_matches() -> None:
    assert build("POST", "/api/demo/http/headers").outcome == "matched"
    assert build("GET", "/api/demo/http/headers").matched_methods == ["GET", "POST"]


def test_method_miss_is_405_with_allowed_methods() -> None:
    payload = build("DELETE", "/api/content/routing")
    assert payload.outcome == "method_not_allowed"
    assert payload.matched_path == "/api/content/{topic_id}"
    assert payload.allowed_methods == ["GET"]
    assert "405" in payload.reasoning
    assert "allow header" in payload.reasoning


def test_head_405_reasoning_names_the_no_implicit_head_rule() -> None:
    payload = build("HEAD", "/api/health")
    assert payload.outcome == "method_not_allowed"
    assert "no implicit HEAD" in payload.reasoning


def test_trailing_slash_is_a_redirect_with_the_query_preserved() -> None:
    payload = build("GET", "/api/content/?deep=1")
    assert payload.outcome == "redirect"
    assert payload.redirect_target == "/api/content?deep=1"
    assert "307" in payload.reasoning


def test_unknown_path_is_404_with_nearest_declared_paths() -> None:
    payload = build("GET", "/api/contentz")
    assert payload.outcome == "not_found"
    assert payload.near_misses is not None
    assert [miss.path for miss in payload.near_misses] == [
        "/api/content",
        "/api/content/{topic_id}",
        "/api/demo/http/headers",
    ]
    assert payload.near_misses[0].methods == ["GET"]
    assert "/api/content" in payload.reasoning


def test_far_404_reports_no_near_misses() -> None:
    payload = build("GET", "/nope")
    assert payload.outcome == "not_found"
    assert payload.near_misses == []
    assert "Closest" not in payload.reasoning


def test_root_path_is_404_not_a_self_redirect() -> None:
    assert build("GET", "/").outcome == "not_found"
