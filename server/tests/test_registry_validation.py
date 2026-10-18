"""ContentRegistry construction rules: one bad fixture per rule, by name."""

import pytest
from content_builders import (
    a_code_block,
    a_demo_block,
    a_group,
    a_list_block,
    a_section,
    a_text_block,
    a_topic,
)

from guide.content.registry import ContentRegistry, RegistryError


def build(*, topics=None, groups=None) -> ContentRegistry:
    return ContentRegistry(
        topics=topics if topics is not None else [a_topic()],
        groups=groups if groups is not None else [a_group()],
    )


def test_minimal_valid_registry_constructs() -> None:
    registry = build(topics=[a_topic()], groups=[a_group()])
    assert registry.topic_by_id("topic-one") is not None
    assert registry.summaries()[0].section_count == 1
    assert registry.groups()[0].id == "foundations"


def test_duplicate_topic_id_is_rejected() -> None:
    with pytest.raises(RegistryError, match="duplicate topic id"):
        build(topics=[a_topic(), a_topic()])


def test_duplicate_section_id_within_topic_is_rejected() -> None:
    topic = a_topic(sections=[a_section(id="same"), a_section(id="same")])
    with pytest.raises(RegistryError, match="duplicate section id"):
        build(topics=[topic])


def test_duplicate_block_id_within_topic_is_rejected() -> None:
    section = a_section(blocks=[a_text_block(id="dupe"), a_code_block(id="dupe")])
    with pytest.raises(RegistryError, match="duplicate block id"):
        build(topics=[a_topic(sections=[section])])


def test_unknown_group_reference_is_rejected() -> None:
    with pytest.raises(RegistryError, match="unknown group"):
        build(topics=[a_topic(group="nope")])


def test_duplicate_topic_order_is_rejected() -> None:
    with pytest.raises(RegistryError, match="duplicate topic order"):
        build(
            topics=[a_topic(id="a", order=1), a_topic(id="b", order=1)],
        )


def test_demo_id_must_be_colon_separated_kebab() -> None:
    section = a_section(blocks=[a_text_block(), a_demo_block(id="Not A Demo Id")])
    with pytest.raises(RegistryError, match="invalid demo id"):
        build(topics=[a_topic(sections=[section])])


def test_section_with_fewer_than_two_blocks_is_rejected() -> None:
    section = a_section(blocks=[a_text_block()])
    with pytest.raises(RegistryError, match="section too short"):
        build(topics=[a_topic(sections=[section])])


def test_section_without_text_block_is_rejected() -> None:
    section = a_section(blocks=[a_code_block(id="c1"), a_code_block(id="c2")])
    with pytest.raises(RegistryError, match="section without text block"):
        build(topics=[a_topic(sections=[section])])


def test_must_source_block_without_source_is_rejected() -> None:
    section = a_section(blocks=[a_text_block(), a_code_block(source=None)])
    with pytest.raises(RegistryError, match="unsourced code block"):
        build(topics=[a_topic(sections=[section])])


def test_must_source_block_with_empty_snippet_is_rejected() -> None:
    section = a_section(blocks=[a_text_block(), a_code_block(snippet="   ")])
    with pytest.raises(RegistryError, match="empty snippet"):
        build(topics=[a_topic(sections=[section])])


def test_empty_text_block_is_rejected() -> None:
    section = a_section(blocks=[a_text_block(text="   "), a_code_block()])
    with pytest.raises(RegistryError, match="empty text block"):
        build(topics=[a_topic(sections=[section])])


def test_list_block_with_too_few_items_is_rejected() -> None:
    section = a_section(blocks=[a_text_block(), a_list_block(items=["One — 1", "Two — 2"])])
    with pytest.raises(RegistryError, match="list block size"):
        build(topics=[a_topic(sections=[section])])


def test_list_block_with_too_many_items_is_rejected() -> None:
    items = [f"Item {n} — the {n}th" for n in range(1, 10)]
    section = a_section(blocks=[a_text_block(), a_list_block(items=items)])
    with pytest.raises(RegistryError, match="list block size"):
        build(topics=[a_topic(sections=[section])])


def test_list_block_with_empty_item_is_rejected() -> None:
    section = a_section(blocks=[a_text_block(), a_list_block(items=["One — 1", "  ", "Three — 3"])])
    with pytest.raises(RegistryError, match="empty list item"):
        build(topics=[a_topic(sections=[section])])


def test_list_block_at_both_size_bounds_is_accepted() -> None:
    for items in (
        ["One — 1", "Two — 2", "Three — 3"],
        [f"Item {n} — the {n}th" for n in range(1, 9)],
    ):
        section = a_section(blocks=[a_text_block(), a_list_block(items=items)])
        registry = build(topics=[a_topic(sections=[section])])
        assert registry.topic_by_id("topic-one") is not None


def test_exempt_language_block_needs_no_source() -> None:
    section = a_section(blocks=[a_text_block(), a_code_block(language="bash", source=None)])
    registry = build(topics=[a_topic(sections=[section])])
    assert registry.topic_by_id("topic-one") is not None
