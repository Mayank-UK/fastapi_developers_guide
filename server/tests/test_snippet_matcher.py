"""SnippetMatcher: normalization + ordered-subsequence, per language."""

from guide.content.snippet_matcher import match_snippet

PY_SOURCE = """\
import os


def configure(name: str) -> str:
    # full-line comment in the source
    value = os.environ.get(name, "default")
    return value.lower()  # normalize case
"""


def test_exact_lines_match() -> None:
    snippet = 'value = os.environ.get(name, "default")\nreturn value.lower()'
    assert match_snippet(PY_SOURCE, snippet, "py")


def test_blanks_and_reindentation_are_tolerated() -> None:
    snippet = "def configure(name: str) -> str:\n\n        return value.lower()"
    assert match_snippet(PY_SOURCE, snippet, "py")


def test_full_line_comments_are_stripped() -> None:
    snippet = "# teaching prose the source does not have\nreturn value.lower()"
    assert match_snippet(PY_SOURCE, snippet, "py")


def test_trailing_teaching_comments_are_stripped() -> None:
    snippet = 'value = os.environ.get(name, "default")  # read once per call'
    assert match_snippet(PY_SOURCE, snippet, "py")


def test_elisions_at_start_middle_and_end() -> None:
    snippet = (
        "# …\n"
        "import os\n"
        "# ... rest of the imports\n"
        "def configure(name: str) -> str:\n"
        "# …\n"
        "return value.lower()\n"
        "# …\n"
    )
    assert match_snippet(PY_SOURCE, snippet, "py")


def test_ts_line_comments_and_url_strings() -> None:
    source = (
        "const base = 'https://api.example.com/v1';\n"
        "const timeout = 5_000; // milliseconds\n"
        "fetch(base, { signal });\n"
    )
    snippet = (
        "const base = 'https://api.example.com/v1';\n"
        "const timeout = 5_000;\n"
        "fetch(base, { signal });"
    )
    assert match_snippet(source, snippet, "ts")


def test_sql_dash_comments_need_a_boundary() -> None:
    source = (
        "UPDATE counters SET total = total--  -- decrement\n"
        "-- full-line comment\n"
        "WHERE id = $1;\n"
    )
    snippet = "UPDATE counters SET total = total--\nWHERE id = $1;"
    assert match_snippet(source, snippet, "sql")


def test_css_block_and_line_comments() -> None:
    source = (
        "/* theme tokens */\n"
        ".card {\n"
        "  color: red;\n"
        "  /* brand */ padding: 0;\n"
        "  margin: 0; // reset\n"
        "}\n"
    )
    snippet = ".card {\ncolor: red;\npadding: 0;\nmargin: 0;\n}"
    assert match_snippet(source, snippet, "css")


def test_html_comments_and_multiline_blocks() -> None:
    source = (
        "<!-- header -->\n"
        "<main>\n"
        "  <p>guide</p>\n"
        "</main>\n"
        "<!-- a long comment\n"
        "     spanning lines -->\n"
        "<footer>fin</footer>\n"
    )
    snippet = "<main>\n<p>guide</p>\n</main>\n<footer>fin</footer>"
    assert match_snippet(source, snippet, "html")


def test_json_is_blank_strip_only() -> None:
    source = '{\n  "name": "guide",\n  "python": "3.13"\n}'
    assert match_snippet(source, '{\n\n  "name": "guide",\n}', "json")
    # A // "comment" is content in json — it must NOT match a source lacking it.
    bad = match_snippet(source, '"name": "guide",\n// teaching note', "json")
    assert not bad
    assert bad.reason is not None


def test_yaml_and_toml_hash_after_whitespace() -> None:
    source = "services:\n  server: # the api\n    port: 8000\n    key: '#literal'\n"
    snippet = "services:\n  server:\n    port: 8000\n    key: '#literal'"
    assert match_snippet(source, snippet, "yaml")
    assert match_snippet('python = "3.13"  # pinned\n', 'python = "3.13"', "toml")


def test_proto_line_and_block_comments() -> None:
    source = (
        "// the contract\n"
        "syntax = \"proto3\";\n"
        "\n"
        "message Post {\n"
        "  string slug = 1;  // the id\n"
        "  /* repeated tags */ repeated string tags = 5;\n"
        "}\n"
    )
    # Comment lines (full and trailing) strip; block comments strip inline.
    snippet = (
        "syntax = \"proto3\";\nmessage Post {\n"
        "  string slug = 1;\n  repeated string tags = 5;\n}"
    )
    assert match_snippet(source, snippet, "proto")
    # Elision lines mark gaps like everywhere else.
    elided = "syntax = \"proto3\";\n// …\nmessage Post {"
    assert match_snippet(source, elided, "proto")



def test_reordered_lines_fail() -> None:
    snippet = "return value.lower()\nimport os"
    result = match_snippet(PY_SOURCE, snippet, "py")
    assert not result
    assert result.reason is not None


def test_missing_line_fails_with_reason() -> None:
    result = match_snippet(PY_SOURCE, "value = os.environ.get(name, 'other')", "py")
    assert not result
    assert "not found in source" in (result.reason or "")


def test_wrong_language_token_is_content_not_comment() -> None:
    snippet = "import os\n// a js-style comment inside a py snippet"
    result = match_snippet(PY_SOURCE, snippet, "py")
    assert not result


def test_all_comment_snippet_fails() -> None:
    result = match_snippet(PY_SOURCE, "# …\n# only elisions", "py")
    assert not result
    assert result.reason is not None
