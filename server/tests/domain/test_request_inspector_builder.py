"""Builder unit tests: the request-inspector payload's pure reflection.

The builder is a pure function over plain data, so these tests pin exactly:
how repeated query keys collect every occurrence (and single keys do not),
how the header selection orders and normalizes, how content-length parses
defensively, how the client address and optional facts stay honest (None
means omitted), and what the reasoning sentence promises.
"""

from guide.domain.demos.request_inspector import build_request_inspector_payload


def _build(
    *,
    method: str = "GET",
    path: str = "/api/demo/reqres/inspector",
    raw_query: str | None = None,
    query_pairs: list[tuple[str, str]] | None = None,
    headers: dict[str, str] | None = None,
    client_host: str | None = "127.0.0.1",
    client_port: int | None = 51000,
    request_id: str = "probe-1",
    body_message: str | None = None,
):
    return build_request_inspector_payload(
        method=method,
        path=path,
        raw_query=raw_query,
        query_pairs=query_pairs or [],
        headers=headers or {},
        client_host=client_host,
        client_port=client_port,
        request_id=request_id,
        body_message=body_message,
    )


def test_repeated_query_keys_collect_every_occurrence_in_arrival_order() -> None:
    payload = _build(
        raw_query="tag=a&zoom=2&tag=b&tag=c",
        query_pairs=[("tag", "a"), ("zoom", "2"), ("tag", "b"), ("tag", "c")],
    )
    by_name = {param.name: param for param in payload.query_params}
    assert by_name["tag"].values == ["a", "b", "c"]
    assert by_name["tag"].is_repeated is True
    assert by_name["zoom"].values == ["2"]
    assert by_name["zoom"].is_repeated is False
    # First-seen order is preserved.
    assert [param.name for param in payload.query_params] == ["tag", "zoom"]
    assert "tag" in payload.reasoning and "list[str]" in payload.reasoning


def test_empty_query_yields_an_empty_view_without_repeated_note() -> None:
    payload = _build()
    assert payload.query_params == []
    assert payload.raw_query is None
    assert "collect every occurrence" not in payload.reasoning


def test_header_selection_is_fixed_order_then_x_extras_sorted() -> None:
    payload = _build(
        headers={
            "X-Zebra": "last",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Alpha": "first",
            "Host": "localhost:8000",  # never selected
        }
    )
    assert [header.name for header in payload.headers] == [
        "accept",
        "content-type",
        "x-alpha",
        "x-zebra",
    ]
    assert payload.headers[0].value == "application/json"
    assert payload.headers[2].value == "first"


def test_content_length_parses_and_garbage_reads_as_absent() -> None:
    ok = _build(headers={"content-length": " 42 "})
    garbage = _build(headers={"content-length": "not-a-number"})
    absent = _build(headers={"user-agent": "probe"})
    assert ok.content_length == 42
    assert garbage.content_length is None
    assert absent.content_length is None


def test_client_address_reflects_only_when_both_facts_exist() -> None:
    present = _build()
    no_port = _build(client_port=None)
    no_host = _build(client_host=None)
    assert present.client is not None
    assert present.client.host == "127.0.0.1"
    assert present.client.port == 51000
    assert no_port.client is None
    assert no_host.client is None


def test_optional_facts_stay_none_and_blank_query_becomes_none() -> None:
    payload = _build(raw_query="", body_message=None)
    assert payload.raw_query is None
    assert payload.content_type is None
    assert payload.body_message is None


def test_post_facts_report_method_body_and_content_type() -> None:
    payload = _build(
        method="POST",
        headers={"content-type": "application/json"},
        body_message="hello",
    )
    assert payload.method == "POST"
    assert payload.content_type == "application/json"
    assert payload.body_message == "hello"


def test_request_id_facts_ride_the_payload() -> None:
    payload = _build(request_id="req-77")
    assert payload.request_id == "req-77"
    assert payload.request_id_header == "x-request-id"
    assert "req-77" in payload.reasoning
