"""GET/POST /api/demo/pyd/lab: the validation lab's wire contract.

The endpoints run the real builder through the real app, so these tests
drive the documented journeys: the generated schema, the coercion-rich POST
(with the camelCase report and the omitted-when-absent optional fields),
the constraint rejection with normalized specimen errors, and — through the
REAL 422 handler — bodies the request model itself refuses.
"""

from fastapi.testclient import TestClient

SCHEMA_PATH = "/api/demo/pyd/lab/schema"
VALIDATE_PATH = "/api/demo/pyd/lab/validate"

COERCION_BODY = {
    "count": "42",
    "flag": "true",
    "tags": ["boundary", "types"],
    "score": "100",
    "handle": "  Grace Hopper ",
}


def test_schema_serves_the_specimens_generated_json_schema(client: TestClient) -> None:
    response = client.get(SCHEMA_PATH)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"model", "jsonSchema"}
    assert body["model"] == "LabSpecimen"
    schema = body["jsonSchema"]
    assert schema["title"] == "LabSpecimen"
    assert schema["properties"]["score"] == {
        "maximum": 100,
        "minimum": 1,
        "title": "Score",
        "type": "integer",
    }
    assert sorted(schema["required"]) == ["count", "flag", "handle", "score", "tags"]


def test_coercion_rich_post_reports_per_field_and_the_specimen(client: TestClient) -> None:
    response = client.post(VALIDATE_PATH, json=COERCION_BODY)
    assert response.status_code == 200
    body = response.json()
    # exclude_none: the happy path carries no specimenErrors key at all.
    assert set(body) == {"rows", "specimenValid", "specimen"}

    rows = {row["field"]: row for row in body["rows"]}
    assert list(rows) == ["count", "flag", "tags", "score", "handle"]
    assert rows["count"]["received"] == {"type": "str", "repr": "'42'"}
    assert rows["count"]["outcome"] == {
        "status": "coerced",
        "value": 42,
        "valueType": "int",
        "fromType": "str",
    }
    assert rows["flag"]["outcome"]["value"] is True
    assert rows["tags"]["outcome"]["status"] == "clean"
    assert rows["handle"]["outcome"]["value"] == "grace-hopper"

    assert body["specimenValid"] is True
    assert body["specimen"] == {
        "count": 42,
        "flag": True,
        "tags": ["boundary", "types"],
        "score": 100,
        "handle": "grace-hopper",
    }


def test_constraint_violation_reports_the_error_type_and_specimen_errors(
    client: TestClient,
) -> None:
    response = client.post(
        VALIDATE_PATH, json={**COERCION_BODY, "count": 7, "flag": True, "score": 0, "handle": "ok"}
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"rows", "specimenValid", "specimenErrors"}

    score = {row["field"]: row for row in body["rows"]}["score"]
    assert score["outcome"]["status"] == "rejected"
    assert score["outcome"]["errorType"] == "greater_than_equal"
    assert "greater than or equal to 1" in score["outcome"]["message"]

    assert body["specimenValid"] is False
    (error,) = body["specimenErrors"]
    assert error["loc"] == ["score"]
    assert error["type"] == "greater_than_equal"


def test_cross_field_rule_fails_with_model_level_error(client: TestClient) -> None:
    response = client.post(
        VALIDATE_PATH, json={**COERCION_BODY, "count": 7, "flag": True, "tags": [], "score": 5,
                             "handle": "ok"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["specimenValid"] is False
    (error,) = body["specimenErrors"]
    assert error["loc"] == []
    assert "flag requires at least one tag" in error["msg"]
    assert error["type"] == "value_error"


def test_non_list_tags_gets_fastapis_own_422_envelope(client: TestClient) -> None:
    response = client.post(
        VALIDATE_PATH,
        content='{"count":7,"flag":true,"tags":"oops","score":5,"handle":"ok"}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert response.headers["x-request-id"]
    (detail,) = error["details"]
    assert detail["loc"] == ["body", "tags"]
    assert detail["type"] == "list_type"
    assert detail["msg"]


def test_missing_field_and_non_string_handle_refuse_at_the_boundary(
    client: TestClient,
) -> None:
    missing = client.post(VALIDATE_PATH, json={"flag": True, "tags": [], "score": 5, "handle": "x"})
    assert missing.status_code == 422
    (detail,) = missing.json()["error"]["details"]
    assert detail["loc"] == ["body", "count"]
    assert detail["type"] == "missing"

    # v2 refuses int-for-str: no silent 42 -> "42" coercion at the boundary.
    wrong_type = client.post(VALIDATE_PATH, json={**COERCION_BODY, "handle": 42})
    assert wrong_type.status_code == 422
    (detail,) = wrong_type.json()["error"]["details"]
    assert detail["loc"] == ["body", "handle"]
    assert detail["type"] == "string_type"


def test_response_models_are_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    schema_ref = paths[SCHEMA_PATH]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert schema_ref.endswith("PydLabSchemaPayload")
    validate_op = paths[VALIDATE_PATH]["post"]
    report_ref = validate_op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert report_ref.endswith("PydLabReportPayload")
    body_ref = validate_op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    assert body_ref.endswith("LabRequest")
