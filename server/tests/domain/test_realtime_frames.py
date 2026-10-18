"""The SSE frame serializer: the wire format's rules, pinned byte by byte.

Multi-line data must dispatch as ONE event (one ``data:`` line per newline,
exactly one terminating blank line); ids, event names, and the retry hint
frame in their grammar order; keepalive comments are invisible grammar; a
CRLF smuggled into payload data cannot forge a frame boundary.
"""

from guide.domain.realtime.frames import encode_keepalive, encode_sse_event


def test_single_event_framing_terminates_with_exactly_one_blank_line() -> None:
    frame = encode_sse_event('{"seq":1}')
    assert frame == 'data: {"seq":1}\n\n'


def test_event_id_and_retry_frame_before_the_data() -> None:
    frame = encode_sse_event("1.25", event="tick", id="7", retry_ms=3000)
    assert frame == "event: tick\nid: 7\nretry: 3000\ndata: 1.25\n\n"


def test_multiline_data_is_one_event_with_repeated_data_lines() -> None:
    frame = encode_sse_event("first\nsecond\nthird")
    assert frame == "data: first\ndata: second\ndata: third\n\n"


def test_empty_data_line_survives_as_a_bare_prefix() -> None:
    frame = encode_sse_event("a\n\nb")
    assert frame == "data: a\ndata: \ndata: b\n\n"


def test_crlf_in_data_is_normalized_not_forged() -> None:
    frame = encode_sse_event("line\r\ninjected: fake")
    assert frame == "data: line\ndata: injected: fake\n\n"
    assert "\r" not in frame


def test_a_single_leading_space_after_the_colon_is_dropped() -> None:
    assert encode_sse_event(" value") == "data: value\n\n"
    assert encode_sse_event("  two spaces") == "data: " + " two spaces" + "\n\n"


def test_keepalive_is_a_comment_frame() -> None:
    assert encode_keepalive() == ": keepalive\n\n"
    assert encode_keepalive("hb 42") == ": hb 42\n\n"


def test_framed_events_concatenate_into_a_parseable_stream() -> None:
    stream = encode_sse_event("one", id="1") + encode_keepalive() + encode_sse_event("two", id="2")
    # Three blocks, each terminated by a blank line: one, comment, two.
    assert stream.count("\n\n") == 3
    blocks = [block for block in stream.split("\n\n") if block]
    assert blocks[0] == "id: 1\ndata: one"
    assert blocks[1] == ": keepalive"
    assert blocks[2] == "id: 2\ndata: two"
