"""Builder unit tests: the runtime-types payload's pure helpers."""

from typing import Annotated, Any, get_type_hints

from guide.content.models import Topic
from guide.content.registry import ContentRegistry
from guide.domain.demos.runtime_types import (
    RuntimeTypesPayload,
    _display,
    _origin_row,
    build_runtime_types_payload,
    repeat,
)


def test_display_names_plain_and_parameterized_types() -> None:
    assert _display(bool) == "bool"
    assert _display(str) == "str"
    assert _display(list[int]) == "list[int]"
    assert _display(dict[str, Topic]) == "dict[str, Topic]"
    assert _display(tuple[str, ...]) == "tuple[str, ...]"
    assert _display(type(None)) == "None"
    assert _display(Any) == "Any"


def test_display_recurses_into_unions_and_strips_annotated() -> None:
    assert _display(str | None) == "str | None"
    assert _display(dict[str, Any] | None) == "dict[str, Any] | None"
    assert _display(Annotated[str, "metadata"]) == "str"
    assert _display(list[Annotated[str, "m"]]) == "list[str]"


def test_repeat_runs_with_a_wrong_type_and_returns_a_float() -> None:
    value = repeat(3.0, 2)  # type: ignore[arg-type]
    assert value == 6.0
    assert type(value) is float


def test_this_module_pair_deferred_raw_strings_against_resolved_hints() -> None:
    # The demo module is written under `from __future__ import annotations`.
    assert repeat.__annotations__ == {"text": "str", "times": "int", "return": "str"}
    assert get_type_hints(repeat) == {"text": str, "times": int, "return": str}


def test_origin_row_splits_alias_origin_and_args() -> None:
    row = _origin_row("list[int]", list[int])
    assert row.alias == "list[int]"
    assert row.origin == "list"
    assert row.args == ["int"]

    union = _origin_row("topic_by_id (return)", Topic | None)
    assert union.origin == "UnionType"
    assert union.args == ["Topic", "None"]


def test_builder_is_pure_two_calls_build_equal_payloads() -> None:
    first: RuntimeTypesPayload = build_runtime_types_payload()
    second: RuntimeTypesPayload = build_runtime_types_payload()
    assert first == second


def test_payload_quotes_real_repo_symbols_only() -> None:
    payload = build_runtime_types_payload()
    symbols = [s.symbol for s in payload.hints_vs_raw]
    assert symbols == [
        "guide.domain.demos.runtime_types.repeat",
        "guide.content.registry.ContentRegistry.topic_by_id",
    ]
    assert payload.face_off.dataclass_symbol == "guide.content.snippet_matcher.SnippetMatch"
    assert payload.face_off.pydantic_symbol == "guide.content.models.Topic"


def test_boundary_check_never_leaks_a_valid_model() -> None:
    boundary = build_runtime_types_payload().boundary
    assert boundary.outcome == "rejected"
    assert boundary.error_type == "string_type"
    assert "Input should be a valid string" in boundary.message


def test_registry_return_hint_is_the_union_the_demo_displays() -> None:
    hint = get_type_hints(ContentRegistry.topic_by_id)["return"]
    assert _display(hint) == "Topic | None"
