"""Builder unit tests: the headers-echo payload's pure selection + classification.

The builder is a pure function over plain data, so these tests pin exactly:
which headers get selected (base set order, then x-*/hop-by-hop sorted),
how names normalize, how scopes classify against the RFC 9110 list, which
teaching notes attach, and how absent facts (query, content type, body)
stay absent rather than becoming empty strings or nulls.
"""

from guide.domain.demos.http_headers import (
    BASE_HEADER_SELECTION,
    HOP_BY_HOP_HEADERS,
    build_http_headers_echo,
)

CANONICAL_HOP_BY_HOP: frozenset[str] = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)


def test_hop_by_hop_list_is_the_canonical_set() -> None:
    assert HOP_BY_HOP_HEADERS == CANONICAL_HOP_BY_HOP


def test_payload_carries_the_sorted_hop_by_hop_reference_list() -> None:
    payload = build_http_headers_echo(
        method="GET", path="/", query=None, headers={}
    )
    assert payload.hop_by_hop == sorted(CANONICAL_HOP_BY_HOP)


def test_selects_base_headers_in_fixed_order_then_x_headers_sorted() -> None:
    payload = build_http_headers_echo(
        method="GET",
        path="/api/demo/http/headers",
        query=None,
        headers={
            "X-Zebra": "last",
            "Accept": "application/json",
            "X-Alpha": "first",
            "User-Agent": "probe/1.0",
        },
    )
    assert [header.name for header in payload.headers] == [
        "user-agent",
        "accept",
        "x-alpha",
        "x-zebra",
    ]
    assert payload.headers[0].value == "probe/1.0"
    assert payload.headers[2].value == "first"


def test_names_normalize_to_lowercase_and_scopes_classify() -> None:
    payload = build_http_headers_echo(
        method="GET",
        path="/",
        query=None,
        headers={"User-Agent": "u", "Connection": "keep-alive", "X-Custom": "c"},
    )
    scopes = {header.name: header.scope for header in payload.headers}
    assert scopes["user-agent"] == "end-to-end"
    assert scopes["x-custom"] == "end-to-end"
    assert scopes["connection"] == "hop-by-hop"


def test_known_headers_carry_teaching_notes_and_x_headers_get_the_generic_one() -> None:
    payload = build_http_headers_echo(
        method="GET",
        path="/",
        query=None,
        headers={"User-Agent": "u", "X-Custom": "c", "X-Request-Id": "r"},
    )
    notes = {header.name: header.note for header in payload.headers}
    assert notes["user-agent"] is not None
    assert notes["x-request-id"] is not None
    assert notes["x-custom"] == "extension header: the x- prefix is convention, not standard"


def test_unselected_headers_are_never_echoed() -> None:
    payload = build_http_headers_echo(
        method="GET",
        path="/",
        query=None,
        headers={"Host": "localhost:8000", "Referer": "https://example.com", "X-Kept": "yes"},
    )
    assert [header.name for header in payload.headers] == ["x-kept"]


def test_request_facts_report_method_path_query_content_type_and_body() -> None:
    payload = build_http_headers_echo(
        method="POST",
        path="/api/demo/http/headers",
        query="from=client-demo",
        headers={"content-type": "application/json"},
        body_message="hello",
    )
    assert payload.method == "POST"
    assert payload.path == "/api/demo/http/headers"
    assert payload.query == "from=client-demo"
    assert payload.content_type == "application/json"
    assert payload.body_message == "hello"


def test_absent_facts_stay_none_and_empty_query_becomes_none() -> None:
    payload = build_http_headers_echo(
        method="GET", path="/api/demo/http/headers", query="", headers={}
    )
    assert payload.query is None
    assert payload.content_type is None
    assert payload.body_message is None
    assert payload.headers == []


def test_base_selection_covers_the_negotiation_set() -> None:
    assert BASE_HEADER_SELECTION == ("user-agent", "accept", "accept-encoding", "content-type")
