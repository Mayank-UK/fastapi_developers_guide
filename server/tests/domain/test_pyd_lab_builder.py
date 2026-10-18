"""The pyd-lab builder: coercion report, specimen verdict, generated schema.

These tests pin pydantic's ACTUAL v2 behavior (lax coercion rules verified
against pydantic 2.14 before authoring): smart-union raw fidelity, the
per-field TypeAdapter outcomes (clean / coerced / rejected with real error
types), the cross-field @model_validator, and the JSON Schema the schema
endpoint serves.
"""

import pytest
from pydantic import ValidationError

from guide.domain.demos.pyd_lab import (
    CoercedOutcome,
    LabRequest,
    LabSpecimen,
    RejectedOutcome,
    build_schema_payload,
    build_validation_report,
    canonical_handle,
)


def _request(**overrides: object) -> LabRequest:
    """A valid baseline request; per-test overrides prove each rule."""
    baseline: dict[str, object] = {
        "count": 7,
        "flag": True,
        "tags": ["x"],
        "score": 50,
        "handle": "ok",
    }
    return LabRequest.model_validate({**baseline, **overrides})


def test_canonical_handle_lowercases_and_hyphenates() -> None:
    assert canonical_handle("  Grace Hopper ") == "grace-hopper"
    assert canonical_handle("already-canonical") == "already-canonical"
    assert canonical_handle("\tMixed   WHITESPACE\nhere") == "mixed-whitespace-here"


def test_permissive_request_keeps_raw_spellings_verbatim() -> None:
    # Smart unions prefer the exact type: no coercion happens on the way in.
    request = LabRequest.model_validate(
        {"count": "42", "flag": "true", "tags": ["a"], "score": 4.5, "handle": "ok"}
    )
    assert (type(request.count).__name__, request.count) == ("str", "42")
    assert (type(request.flag).__name__, request.flag) == ("str", "true")
    assert (type(request.score).__name__, request.score) == ("float", 4.5)


def test_report_marks_clean_fields_clean() -> None:
    rows = {row.field: row for row in build_validation_report(_request()).rows}
    assert rows["count"].outcome.status == "clean"
    assert rows["tags"].outcome.status == "clean"
    assert rows["handle"].outcome.status == "clean"


def test_report_shows_lax_coercion_deciding() -> None:
    report = build_validation_report(
        _request(count="42", flag="true", score="100", handle="  Grace Hopper ")
    )
    rows = {row.field: row for row in report.rows}

    count = rows["count"].outcome
    assert isinstance(count, CoercedOutcome)
    assert count.value == 42
    assert count.value_type == "int"
    assert count.from_type == "str"

    flag = rows["flag"].outcome
    assert isinstance(flag, CoercedOutcome)
    assert flag.value is True
    assert flag.from_type == "str"

    score = rows["score"].outcome
    assert isinstance(score, CoercedOutcome)
    assert score.value == 100

    handle = rows["handle"].outcome
    assert isinstance(handle, CoercedOutcome)
    assert handle.value == "grace-hopper"

    assert rows["count"].received.type == "str"
    assert rows["count"].received.repr == "'42'"


def test_report_coerces_int_one_to_bool() -> None:
    outcome = {r.field: r for r in build_validation_report(_request(flag=1)).rows}["flag"].outcome
    assert isinstance(outcome, CoercedOutcome)
    assert outcome.value is True
    assert outcome.from_type == "int"


def test_report_rejects_with_pydantics_own_error_types() -> None:
    report = build_validation_report(
        _request(count="abc", flag="maybe", score=0, handle="  Grace Hopper ")
    )
    rows = {row.field: row for row in report.rows}
    for name, expected_type in (
        ("count", "int_parsing"),
        ("flag", "bool_parsing"),
        ("score", "greater_than_equal"),
    ):
        outcome = rows[name].outcome
        assert isinstance(outcome, RejectedOutcome)
        assert outcome.error_type == expected_type
        assert outcome.message
    assert "bounds" in rows["score"].rule


def test_report_rejects_out_of_bounds_high_score() -> None:
    report = build_validation_report(_request(score=101))
    outcome = {r.field: r for r in report.rows}["score"].outcome
    assert isinstance(outcome, RejectedOutcome)
    assert outcome.error_type == "less_than_equal"


def test_report_rejects_fractional_score_with_int_from_float() -> None:
    report = build_validation_report(_request(score=4.5))
    outcome = {r.field: r for r in report.rows}["score"].outcome
    assert isinstance(outcome, RejectedOutcome)
    assert outcome.error_type == "int_from_float"


def test_valid_submission_carries_the_typed_specimen() -> None:
    report = build_validation_report(
        _request(count="42", flag="on", tags=("a", "b"), score="100", handle=" Grace HOPPER ")
    )
    assert report.specimen_valid is True
    assert report.specimen_errors is None
    assert report.specimen == {
        "count": 42,
        "flag": True,
        "tags": ["a", "b"],  # a python tuple coerced into the declared list
        "score": 100,
        "handle": "grace-hopper",
    }


def test_cross_field_rule_fails_a_submission_whose_fields_all_pass() -> None:
    report = build_validation_report(_request(flag=True, tags=[]))
    rows = {row.field: row for row in report.rows}
    assert all(row.outcome.status != "rejected" for row in rows.values())
    assert report.specimen_valid is False
    assert report.specimen is None
    assert report.specimen_errors is not None
    (error,) = report.specimen_errors
    assert error.loc == []  # the model is wrong, no single field is
    assert "flag requires at least one tag" in error.msg
    assert error.type == "value_error"


def test_received_repr_is_capped_for_hostile_inputs() -> None:
    report = build_validation_report(_request(tags=[f"tag-{i}" for i in range(40)]))
    tags = {r.field: r for r in report.rows}["tags"]
    assert len(tags.received.repr) <= 81  # 80 chars + the ellipsis marker
    assert tags.received.repr.endswith("…")


def test_schema_payload_is_generated_introspection() -> None:
    payload = build_schema_payload()
    assert payload.model == "LabSpecimen"
    schema = payload.json_schema
    assert schema["title"] == "LabSpecimen"
    assert schema["properties"]["score"] == {
        "maximum": 100,
        "minimum": 1,
        "title": "Score",
        "type": "integer",
    }
    assert sorted(schema["required"]) == ["count", "flag", "handle", "score", "tags"]


def test_lab_specimen_is_frozen_and_normalizes_on_construction() -> None:
    specimen = LabSpecimen.model_validate(
        {"count": 1, "flag": False, "tags": [], "score": 1, "handle": "  Ada Lovelace "}
    )
    assert specimen.handle == "ada-lovelace"
    with pytest.raises(ValidationError):
        specimen.handle = "mutate"  # type: ignore[misc]
