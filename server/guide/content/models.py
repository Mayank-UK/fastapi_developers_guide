"""The typed content model the React client renders: topic → sections → blocks.

The server owns 100% of the teaching as data; this module defines its shape.
Python fields are snake_case, the wire is camelCase (via ``CamelModel``).
Blocks form a pydantic discriminated union on ``kind`` so an unknown kind is
rejected at parse time, never rendered as a mystery block.

Sourcing contract (see agentic_development.md invariants): code blocks in
``MUST_SOURCE_LANGUAGES`` MUST carry a repo-root-relative ``source`` and a
non-empty ``snippet`` that the snippet matcher verifies against the real
file (RATCHET = 0). Terminal tours are bash blocks — bash/sh/shell/
dockerfile/text are deliberately EXEMPT: commands and transcripts have no
source file to quote. Never relabel a language to dodge the check.
"""

from typing import Annotated, Final, Literal

from pydantic import Field

from guide.core.serialization import CamelModel

CONTENT_API_VERSION: Final[int] = 1
"""Bumped when these response shapes change, so the client migrates deliberately."""

MUST_SOURCE_LANGUAGES: Final[frozenset[str]] = frozenset(
    {"py", "ts", "tsx", "js", "toml", "yaml", "yml", "sql", "json", "proto", "html", "css"}
)
"""Languages whose snippets are real code/config a repo file can own.

Exempt (no source file exists): bash, sh, shell, dockerfile, text — terminal
tours and output transcripts. Family invariant: terminal tours are bash
blocks, exempt from sourcing.
"""


class TextBlock(CamelModel):
    """Prose. May contain ``\\n\\n`` paragraph breaks; never empty."""

    kind: Literal["text"]
    id: str
    text: str


class CodeBlock(CamelModel):
    """A code snippet, ideally quoted from a real repo file.

    ``language`` is a free string (the matcher + registry know which are
    must-source); ``source`` is repo-root-relative or None for exempt
    languages; ``snippet`` is the displayed code itself.
    """

    kind: Literal["code"]
    id: str
    language: str
    caption: str | None = None
    source: str | None = None
    snippet: str


class DemoBlock(CamelModel):
    """Names a client-side live demo bound to real server endpoints.

    The block id doubles as the demo id (``<area>:<name>``, e.g.
    ``runtime:async``) — the client's lookup key, validated by the registry.
    """

    kind: Literal["demo"]
    id: str
    title: str
    description: str | None = None


class ListBlock(CamelModel):
    """A flat enumeration of parallel items (block-selection standard).

    Authoring grammar, enforced by the registry: 3–8 items, each written as
    ``Lead term — explanation.``; ``ordered`` is true only when sequence
    matters (steps, rankings) — parallel features stay unordered; no nesting
    (a sub-list means the content wants sections or reworded items instead).
    Prose stays the default: a list never substitutes for an explanation, and
    every section keeps connecting prose around its structures.
    """

    kind: Literal["list"]
    id: str
    ordered: bool
    items: list[str]


ContentBlock = Annotated[TextBlock | CodeBlock | DemoBlock | ListBlock, Field(discriminator="kind")]


class Section(CamelModel):
    """One teaching unit inside a topic: prose + code + its inline demo."""

    id: str
    title: str
    lead: str | None = None
    blocks: list[ContentBlock]


class Topic(CamelModel):
    """A whole guide page: ordered sections, the unit the detail route serves."""

    id: str
    title: str
    subtitle: str | None = None
    group: str
    order: int
    sections: list[Section]


class TopicGroup(CamelModel):
    """A nav group topics belong to; ``order`` drives nav display order."""

    id: str
    title: str
    order: int


class ContentSummary(CamelModel):
    """A topic without its sections payload — what the list route serves."""

    id: str
    title: str
    subtitle: str | None = None
    group: str
    order: int
    section_count: int


class ContentDetail(Topic):
    """The detail route's response model: a full Topic plus the API version.

    Family contract: BOTH content endpoints serve ``version`` so a client
    can detect a CONTENT_API_VERSION bump on any content response and
    migrate deliberately.
    """

    version: int


class ContentListResponse(CamelModel):
    """Wire shape of GET /api/content."""

    version: int
    groups: list[TopicGroup]
    topics: list[ContentSummary]
