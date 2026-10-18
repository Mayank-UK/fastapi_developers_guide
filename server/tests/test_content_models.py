"""Content model: discriminated blocks, camelCase wire, must-source contract."""

import pytest
from content_builders import (
    a_code_block,
    a_demo_block,
    a_list_block,
    a_section,
    a_text_block,
    a_topic,
)
from pydantic import ValidationError

from guide.content.models import (
    MUST_SOURCE_LANGUAGES,
    ContentSummary,
    DemoBlock,
    ListBlock,
    Section,
    TextBlock,
    Topic,
)


def test_round_trip_preserves_all_block_kinds() -> None:
    topic = a_topic()
    topic.sections.append(
        a_section(
            id="s2",
            blocks=[TextBlock(kind="text", id="t2", text="More."), a_demo_block()],
        )
    )
    dumped = topic.model_dump(by_alias=True)
    reparsed = Topic.model_validate(dumped)
    assert reparsed == topic


def test_list_block_round_trips_through_the_discriminated_union() -> None:
    topic = a_topic(
        sections=[a_section(blocks=[a_text_block(), a_list_block(ordered=True)])]
    )
    dumped = topic.model_dump(by_alias=True)
    wire_block = dumped["sections"][0]["blocks"][1]
    assert wire_block == {
        "kind": "list",
        "id": "l1",
        "ordered": True,
        "items": ["First — one", "Second — two", "Third — three"],
    }

    reparsed = Topic.model_validate(dumped)
    assert reparsed == topic
    assert isinstance(reparsed.sections[0].blocks[1], ListBlock)


def test_wire_keys_are_camel_case_both_directions() -> None:
    summary = ContentSummary(
        id="t",
        title="T",
        group="g",
        order=1,
        section_count=3,
    )
    assert summary.model_dump(by_alias=True)["sectionCount"] == 3

    from_wire = ContentSummary.model_validate(
        {"id": "t", "title": "T", "group": "g", "order": 1, "sectionCount": 3}
    )
    assert from_wire.section_count == 3


def test_unknown_block_kind_is_rejected_at_parse_time() -> None:
    with pytest.raises(ValidationError):
        Section.model_validate(
            {
                "id": "s",
                "title": "S",
                "blocks": [
                    {"kind": "text", "id": "t", "text": "ok"},
                    {"kind": "video", "id": "v", "src": "x.mp4"},
                ],
            }
        )


def test_optional_fields_are_omitted_when_unset() -> None:
    block = a_code_block(caption=None, source=None, language="bash")
    wire = block.model_dump(by_alias=True, exclude_none=True)
    assert "caption" not in wire
    assert "source" not in wire
    assert wire["snippet"] == "x = 1"


def test_must_source_language_contract_is_the_recorded_family_set() -> None:
    assert MUST_SOURCE_LANGUAGES == frozenset(
        {"py", "ts", "tsx", "js", "toml", "yaml", "yml", "sql", "json", "proto", "html", "css"}
    )
    for exempt in ("bash", "sh", "shell", "dockerfile", "text"):
        assert exempt not in MUST_SOURCE_LANGUAGES


def test_demo_block_carries_title_and_description() -> None:
    block = DemoBlock(kind="demo", id="runtime:async", title="Async lab")
    assert block.model_dump(by_alias=True, exclude_none=True) == {
        "kind": "demo",
        "id": "runtime:async",
        "title": "Async lab",
    }
