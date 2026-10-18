"""Snippet-source verification: is a teaching snippet quoted from a real file?

The matcher answers one question: after language-aware normalization, is the
snippet an ORDERED SUBSEQUENCE of the source's lines? Normalization strips
blank lines and comments (full-line comments from both sides; trailing
teaching comments from code lines), so snippets may legitimately add prose
comments and ``# …`` / ``// ...`` elision lines — an elision normalizes to
empty and therefore marks a GAP: source lines may be skipped between
matches, but every remaining snippet line must equal a source line exactly
(after normalization + trim), in order.

Comment syntax is language-aware and quote-aware (a comment token inside a
string literal is not a comment — ``url = "http://x"`` survives ``//``
stripping in ts). ``--`` (sql) and ``#`` (yaml/toml) only start a comment at
line start or after whitespace, so ``i--`` and ``#field`` never get mangled.
JSON has no comments — blank-strip only. The scan is a single left-to-right
pass per line (two-pointer match over the normalized lists): linear time,
no regex backtracking.
"""

from dataclasses import dataclass
from typing import Final

_ELLIPSIS_CHAR: Final[str] = "…"
_MAX_REASON_LINE: Final[int] = 80


@dataclass(frozen=True, slots=True)
class SnippetMatch:
    """Outcome of one snippet verification; truthy when ok."""

    ok: bool
    reason: str | None = None

    def __bool__(self) -> bool:
        return self.ok


@dataclass(frozen=True, slots=True)
class _CommentStyle:
    """How comments are written in one language family."""

    line_tokens: tuple[str, ...] = ()
    """Trailing/full-line tokens that start a comment anywhere on the line."""

    start_only_tokens: tuple[str, ...] = ()
    """Tokens that start a comment only at line start or after whitespace."""

    block_start: str | None = None
    block_end: str | None = None
    quote_aware: bool = True


_PLAIN_STYLE: Final[_CommentStyle] = _CommentStyle()
"""Unknown languages + json: no comment syntax, blank-strip only."""

_STYLES: Final[dict[str, _CommentStyle]] = {
    "py": _CommentStyle(line_tokens=("#",)),
    "toml": _CommentStyle(start_only_tokens=("#",)),
    "yaml": _CommentStyle(start_only_tokens=("#",)),
    "yml": _CommentStyle(start_only_tokens=("#",)),
    "ts": _CommentStyle(line_tokens=("//",)),
    "tsx": _CommentStyle(line_tokens=("//",)),
    "js": _CommentStyle(line_tokens=("//",)),
    "proto": _CommentStyle(line_tokens=("//",), block_start="/*", block_end="*/"),
    "sql": _CommentStyle(start_only_tokens=("--",)),
    "css": _CommentStyle(line_tokens=("//",), block_start="/*", block_end="*/"),
    "html": _CommentStyle(block_start="<!--", block_end="-->", quote_aware=False),
}

_QUOTE_CHARS: Final[tuple[str, ...]] = ("'", '"', "`")
_WHITESPACE: Final[str] = " \t"


def _at_token_boundary(code_so_far: str) -> bool:
    """True when a start-only comment token is at line start/after whitespace."""
    return not code_so_far or code_so_far[-1] in _WHITESPACE


def _strip_line(line: str, style: _CommentStyle, in_block: bool) -> tuple[str, bool]:
    """Strip comments from one line; returns (code_fragment, still_in_block).

    Single left-to-right pass tracking string literals (with backslash
    escapes), full and inline block comments, and line-comment tokens —
    no regex, no backtracking.
    """
    text = line
    if in_block:
        if style.block_end is None:  # pragma: no cover - guarded by construction
            return text.strip(), False
        end = text.find(style.block_end)
        if end == -1:
            return "", True
        text = text[end + len(style.block_end) :]

    out = ""
    quote: str | None = None
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if quote is not None:
            out += ch
            if ch == "\\" and nxt:
                out += nxt
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if style.quote_aware and ch in _QUOTE_CHARS:
            quote = ch
            out += ch
            i += 1
            continue
        if style.block_start is not None and style.block_end is not None:
            if text.startswith(style.block_start, i):
                close = text.find(style.block_end, i + len(style.block_start))
                if close == -1:
                    return out.rstrip(), True
                i = close + len(style.block_end)
                continue
        for token in style.line_tokens:
            if text.startswith(token, i):
                return out.rstrip(), False
        for token in style.start_only_tokens:
            if text.startswith(token, i) and _at_token_boundary(out):
                return out.rstrip(), False
        out += ch
        i += 1
    return out.rstrip(), False


def _normalize(text: str, style: _CommentStyle) -> list[str]:
    """Reduce text to its meaningful lines: comments/blanks stripped, trimmed.

    Full-line comments — including elision lines (comment token + ``…`` or
    ``...``) — normalize to empty and drop out, which is what makes gaps
    legal during matching.
    """
    normalized: list[str] = []
    in_block = False
    for raw in text.splitlines():
        code, in_block = _strip_line(raw, style, in_block)
        code = code.strip()
        if code:
            normalized.append(code)
    return normalized


def _short(line: str) -> str:
    """Cap a line for failure reasons so they stay readable."""
    return line if len(line) <= _MAX_REASON_LINE else line[:_MAX_REASON_LINE] + _ELLIPSIS_CHAR


def match_snippet(source: str, snippet: str, language: str) -> SnippetMatch:
    """Verify the snippet is an ordered subsequence of the source, per language.

    Unknown languages (and json) get blank-strip-only normalization. Returns
    a truthy ``SnippetMatch`` on success, or ``ok=False`` with a short reason
    naming the first snippet line that could not be matched in order.
    """
    style = _STYLES.get(language, _PLAIN_STYLE)
    source_lines = _normalize(source, style)
    snippet_lines = _normalize(snippet, style)

    if not snippet_lines:
        return SnippetMatch(ok=False, reason="snippet is empty after normalization")

    position = 0
    for number, line in enumerate(snippet_lines, start=1):
        while position < len(source_lines) and source_lines[position] != line:
            position += 1
        if position == len(source_lines):
            return SnippetMatch(
                ok=False,
                reason=(
                    f"snippet line {number} not found in source (in order): "
                    f"{_short(line)!r}"
                ),
            )
        position += 1
    return SnippetMatch(ok=True, reason=None)
