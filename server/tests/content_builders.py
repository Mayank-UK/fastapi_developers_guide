"""Builders for content fixtures: one minimal VALID topic, mutable per test.

Registry-validation and route tests mutate these to break exactly one rule
at a time; the defaults always construct a registry that validates.
"""

from guide.content.models import (
    CodeBlock,
    DemoBlock,
    ListBlock,
    Section,
    TextBlock,
    Topic,
    TopicGroup,
)


def a_text_block(id: str = "t1", text: str = "Teaching prose.") -> TextBlock:
    return TextBlock(kind="text", id=id, text=text)


def a_list_block(id: str = "l1", **overrides: object) -> ListBlock:
    defaults: dict[str, object] = {
        "kind": "list",
        "id": id,
        "ordered": False,
        "items": ["First — one", "Second — two", "Third — three"],
    }
    return ListBlock.model_validate({**defaults, **overrides})  # type: ignore[arg-type]


def a_code_block(id: str = "c1", **overrides: object) -> CodeBlock:
    defaults: dict[str, object] = {
        "kind": "code",
        "id": id,
        "language": "py",
        "snippet": "x = 1",
        "source": "server/pyproject.toml",
    }
    return CodeBlock.model_validate({**defaults, **overrides})  # type: ignore[arg-type]


def a_demo_block(id: str = "demo:sample", **overrides: object) -> DemoBlock:
    defaults: dict[str, object] = {"kind": "demo", "id": id, "title": "Sample demo"}
    return DemoBlock.model_validate({**defaults, **overrides})  # type: ignore[arg-type]


def a_section(id: str = "s1", blocks: list[object] | None = None) -> Section:
    return Section.model_validate(
        {
            "id": id,
            "title": "A section",
            "blocks": blocks if blocks is not None else [a_text_block(), a_code_block()],
        }
    )


def a_topic(
    id: str = "topic-one",
    order: int = 1,
    group: str = "foundations",
    sections: list[Section] | None = None,
) -> Topic:
    return Topic.model_validate(
        {
            "id": id,
            "title": "Topic One",
            "group": group,
            "order": order,
            "sections": sections if sections is not None else [a_section()],
        }
    )


def a_group(id: str = "foundations", order: int = 1) -> TopicGroup:
    return TopicGroup(id=id, title="Foundations", order=order)
