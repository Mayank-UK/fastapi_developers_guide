"""The pure conditional helpers: ETag computation + If-None-Match matching.

Unit-level (no redis, no app): the ETag is a deterministic quoted digest
that tracks the payload's bytes, and the matcher speaks every spelling
RFC 9110 allows a cache to send — exact, weak-prefixed, comma-joined
candidates, the match-anything star — while refusing absent, empty, and
stale headers.
"""

from guide.domain.caching.conditionals import compute_etag, etag_matches


def test_etag_is_a_quoted_deterministic_digest() -> None:
    first = compute_etag('{"items":[]}')
    assert first.startswith('"') and first.endswith('"')
    assert len(first) == 18  # quotes + 16 hex chars
    assert compute_etag('{"items":[]}') == first  # same bytes, same etag
    assert compute_etag('{"items":[1]}') != first  # any byte change moves it
    assert compute_etag("") != compute_etag(" ")  # even emptiness is content


def test_absent_or_empty_header_is_not_conditional() -> None:
    assert etag_matches(None, '"abc"') is False
    assert etag_matches("", '"abc"') is False
    assert etag_matches("   ", '"abc"') is False


def test_exact_and_weak_candidates_match() -> None:
    assert etag_matches('"abc"', '"abc"') is True
    assert etag_matches('W/"abc"', '"abc"') is True  # weak comparison on GET
    assert etag_matches(' "abc" ', '"abc"') is True


def test_comma_joined_candidates_match_any_current() -> None:
    assert etag_matches('"old", "abc"', '"abc"') is True
    assert etag_matches('"old", W/"abc"', '"abc"') is True
    assert etag_matches('"old", "new"', '"abc"') is False


def test_the_star_matches_any_current_representation() -> None:
    assert etag_matches("*", '"abc"') is True
    assert etag_matches(" * ", '"abc"') is True
