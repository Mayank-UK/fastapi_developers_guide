"""The validation arena's pure builders: real pydantic runs, honest reports.

Pinned per roster model: the roster summaries derive required-ness and wire
names from the real models' FieldInfo; accept / coerce / reject outcomes
all come from the model's own model_validate run; rejection rows carry the
exact body-prefixed {loc, msg, type} triples the 422 envelope would serve;
absent optional fields report the real default; extra keys are surfaced as
ignored; the python-name spelling validates the same as the wire alias.
"""

import pytest

from guide.domain.demos.validation_arena import (
    ArenaRequest,
    build_arena_roster,
    build_arena_verdict,
)


def test_roster_lists_the_three_real_models_with_field_specs() -> None:
    roster = build_arena_roster()
    assert [model.key for model in roster.models] == [
        "note-create",
        "lab-specimen",
        "scenario-patch",
    ]
    note = roster.models[0]
    assert note.model == "NoteCreate"
    assert note.source == "guide.domain.demos.request_methods"
    assert [(spec.name, spec.required) for spec in note.fields] == [
        ("title", True),
        ("body", False),
        ("tags", False),
    ]
    scenario = roster.models[2]
    assert scenario.model == "ScenarioPatch"
    # Wire names are aliases: dataMode/injectFailure, camelCase on the wire.
    assert [spec.name for spec in scenario.fields] == ["dataMode", "injectFailure"]
    assert "422" in roster.reasoning


def test_accepted_round_reports_values_and_defaults() -> None:
    payload = build_arena_verdict(
        ArenaRequest(model="note-create", candidates={"title": "ok", "tags": ["a"]})
    )
    assert payload.verdict == "accepted"
    by_field = {row.field: row.outcome for row in payload.rows}
    assert by_field["title"].status == "accepted"
    assert by_field["tags"].status == "accepted"
    assert by_field["body"].status == "absent"
    assert payload.validated == {"title": "ok", "body": "", "tags": ["a"]}
    assert payload.errors is None
    assert payload.extra_keys_ignored == []


def test_coercion_shows_original_and_coerced_per_field() -> None:
    payload = build_arena_verdict(
        ArenaRequest(
            model="lab-specimen",
            candidates={
                "count": "3",
                "flag": "true",
                "tags": ["t"],
                "score": "100",
                "handle": "  Validation Arena ",
            },
        )
    )
    assert payload.verdict == "accepted"
    by_field = {row.field: row.outcome for row in payload.rows}
    assert by_field["count"].status == "coerced"
    assert by_field["count"].original == "3"  # type: ignore[attr-defined]
    assert by_field["count"].value == 3  # type: ignore[attr-defined]
    assert by_field["flag"].value is True  # type: ignore[attr-defined]
    # The @field_validator's canonicalization is visible end to end.
    assert by_field["handle"].value == "validation-arena"  # type: ignore[attr-defined]
    assert payload.validated is not None and payload.validated["handle"] == "validation-arena"


def test_rejected_row_carries_the_envelope_triple() -> None:
    payload = build_arena_verdict(
        ArenaRequest(
            model="lab-specimen",
            candidates={"count": 1, "flag": True, "tags": ["t"], "score": 101, "handle": "x"},
        )
    )
    assert payload.verdict == "rejected"
    score = next(row for row in payload.rows if row.field == "score")
    assert score.outcome.status == "rejected"
    assert score.outcome.loc == ["body", "score"]  # type: ignore[attr-defined]
    assert score.outcome.type == "less_than_equal"  # type: ignore[attr-defined]
    assert payload.validated is None
    assert payload.errors is not None and payload.errors[0].loc == ["body", "score"]


def test_missing_required_field_is_a_rejected_row_with_missing_triple() -> None:
    payload = build_arena_verdict(ArenaRequest(model="note-create", candidates={}))
    assert payload.verdict == "rejected"
    title = next(row for row in payload.rows if row.field == "title")
    assert title.outcome.status == "rejected"
    assert title.outcome.type == "missing"  # type: ignore[attr-defined]
    body = next(row for row in payload.rows if row.field == "body")
    assert body.outcome.status == "absent"


def test_cross_field_rule_refuses_with_body_loc_only() -> None:
    payload = build_arena_verdict(
        ArenaRequest(
            model="lab-specimen",
            candidates={"count": 1, "flag": True, "tags": [], "score": 5, "handle": "x"},
        )
    )
    assert payload.verdict == "rejected"
    # No single field is wrong: every row passed its own validation.
    assert all(row.outcome.status != "rejected" for row in payload.rows)
    assert payload.errors is not None
    assert payload.errors[0].loc == ["body"]
    assert payload.errors[0].type == "value_error"


def test_literal_vocabulary_rejects_with_alias_loc() -> None:
    payload = build_arena_verdict(
        ArenaRequest(model="scenario-patch", candidates={"dataMode": "loud"})
    )
    assert payload.verdict == "rejected"
    row = next(row for row in payload.rows if row.field == "dataMode")
    assert row.outcome.status == "rejected"
    assert row.outcome.loc == ["body", "dataMode"]  # type: ignore[attr-defined]
    assert row.outcome.type == "literal_error"  # type: ignore[attr-defined]


def test_python_name_spelling_validates_like_the_alias() -> None:
    payload = build_arena_verdict(
        ArenaRequest(model="scenario-patch", candidates={"data_mode": "live"})
    )
    assert payload.verdict == "accepted"
    row = next(row for row in payload.rows if row.field == "dataMode")
    assert row.outcome.status == "accepted"
    # The validated dump speaks the wire's spelling.
    assert payload.validated == {"dataMode": "live", "injectFailure": None}


def test_passing_field_next_to_a_rejected_one_stays_accepted() -> None:
    payload = build_arena_verdict(
        ArenaRequest(
            model="scenario-patch",
            candidates={"dataMode": "fake", "injectFailure": "sometimes"},
        )
    )
    assert payload.verdict == "rejected"
    by_field = {row.field: row.outcome for row in payload.rows}
    assert by_field["dataMode"].status == "accepted"
    assert by_field["injectFailure"].status == "rejected"


def test_explicit_null_for_optional_union_field_is_accepted() -> None:
    payload = build_arena_verdict(
        ArenaRequest(model="scenario-patch", candidates={"dataMode": None})
    )
    assert payload.verdict == "accepted"
    row = next(row for row in payload.rows if row.field == "dataMode")
    assert row.outcome.status == "accepted"


def test_unknown_candidate_keys_are_reported_as_ignored_extras() -> None:
    payload = build_arena_verdict(
        ArenaRequest(model="note-create", candidates={"title": "x", "nope": 1, "zzz": 2})
    )
    assert payload.verdict == "accepted"
    assert payload.extra_keys_ignored == ["nope", "zzz"]
    assert payload.validated is not None and "nope" not in payload.validated


@pytest.mark.parametrize("model", ["note-create", "lab-specimen", "scenario-patch"])
def test_every_roster_key_judges_a_round(model: str) -> None:
    payload = build_arena_verdict(ArenaRequest(model=model, candidates={}))
    assert payload.model.key == model
    assert [m.key for m in payload.roster] == ["note-create", "lab-specimen", "scenario-patch"]
    assert payload.reasoning
