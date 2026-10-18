"""Snippet-source ratchet: every must-source block quotes a real repo file.

THE CODE IS THE SOURCE OF TRUTH. For every block in a registry whose
language is must-source: the ``source`` path must resolve under the repo
root and the snippet must match the real file (RATCHET = 0 violations).
The production registry carries real topics from Phase 3 on — python-
language's blocks all source real files — and the canary below proves the
harness actually bites: an intentionally-bad fixture block sourcing a
REAL file with a snippet line that exists nowhere in it must be flagged,
and only it.
"""

from collections.abc import Iterator
from pathlib import Path

from content_builders import a_code_block, a_group, a_section, a_text_block, a_topic

from guide.content.models import MUST_SOURCE_LANGUAGES, CodeBlock
from guide.content.registry import ContentRegistry, production_registry
from guide.content.snippet_matcher import match_snippet

RATCHET = 0
"""Maximum allowed violations. Never raise it; drive it to 0 and keep it there."""

REPO_ROOT = Path(__file__).resolve().parents[2]
"""tests/ → server/ → repo root. Sources are repo-root-relative by contract."""


def _must_source_blocks(registry: ContentRegistry) -> Iterator[CodeBlock]:
    for summary in registry.summaries():
        topic = registry.topic_by_id(summary.id)
        assert topic is not None
        for section in topic.sections:
            for block in section.blocks:
                if isinstance(block, CodeBlock) and block.language in MUST_SOURCE_LANGUAGES:
                    yield block


def violations(registry: ContentRegistry) -> list[str]:
    """Every sourcing violation in the registry, as "block id: reason"."""
    found: list[str] = []
    for block in _must_source_blocks(registry):
        if not block.source or not block.source.strip():
            found.append(f"{block.id}: missing source path")
            continue
        path = (REPO_ROOT / block.source).resolve()
        if not path.is_relative_to(REPO_ROOT):
            found.append(f"{block.id}: source escapes the repo root: {block.source}")
            continue
        if not path.is_file():
            found.append(f"{block.id}: source file not found: {block.source}")
            continue
        match = match_snippet(path.read_text(encoding="utf-8"), block.snippet, block.language)
        if not match:
            found.append(f"{block.id}: {match.reason}")
    return found


def test_production_registry_ratchet_is_zero() -> None:
    """Every must-source block in the production registry matches its file."""
    assert len(violations(production_registry)) <= RATCHET


def test_canary_harness_flags_exactly_the_bad_block() -> None:
    """A real-file-sourced block with an invented line — flagged, and only it."""
    canary = ContentRegistry(
        groups=[a_group()],
        topics=[
            a_topic(
                id="ratchet-canary",
                sections=[
                    a_section(
                        id="good",
                        blocks=[
                            a_text_block(text="sourced:"),
                            a_code_block(
                                id="good-py",
                                source="server/pyproject.toml",
                                snippet='name = "guide"\n\nrequires-python = ">=3.13"',
                            ),
                        ],
                    ),
                    a_section(
                        id="bad",
                        blocks=[
                            a_text_block(id="t2", text="invented:"),
                            a_code_block(
                                id="bad-py",
                                source="server/guide/main.py",
                                snippet="THIS_LINE_EXISTS_IN_NO_REPO_FILE = True",
                            ),
                        ],
                    ),
                    a_section(
                        id="terminal",
                        blocks=[
                            a_text_block(id="t3", text="tour:"),
                            a_code_block(
                                id="bash-tour",
                                language="bash",
                                source=None,
                                snippet="curl localhost:8000/api/content",
                            ),
                        ],
                    ),
                ],
            )
        ],
    )
    found = violations(canary)
    assert len(found) == 1
    assert found[0].startswith("bad-py:")
    assert "not found in source" in found[0]


def test_source_paths_must_stay_under_the_repo_root() -> None:
    outside = ContentRegistry(
        groups=[a_group()],
        topics=[
            a_topic(
                id="outside",
                sections=[
                    a_section(
                        blocks=[
                            a_text_block(),
                            a_code_block(
                                id="escaping",
                                source="../../../../etc/hosts",
                                snippet="localhost",
                            ),
                        ]
                    )
                ],
            )
        ],
    )
    assert violations(outside) == [
        "escaping: source escapes the repo root: ../../../../etc/hosts"
    ]
