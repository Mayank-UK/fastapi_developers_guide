"""The /api/demo/validation/arena endpoints: roster + judged rounds.

These tests pin the arena's wire contract against the per-test app: the
roster serves the three real models with their field rules; a POST round
reports the chosen model's real pydantic verdict (accepted with the
validated dump, rejected with the exact body-prefixed triples); unknown
model keys and non-object candidates are refused by the edge's own 422
envelope — loc naming the offending request field — and the declared
response models appear in OpenAPI.
"""

from fastapi.testclient import TestClient

ARENA_PATH = "/api/demo/validation/arena"


def test_roster_serves_the_three_real_models(client: TestClient) -> None:
    body = client.get(f"{ARENA_PATH}/roster").json()
    assert [model["key"] for model in body["models"]] == [
        "note-create",
        "lab-specimen",
        "scenario-patch",
    ]
    note = body["models"][0]
    assert note["model"] == "NoteCreate"
    assert note["source"] == "guide.domain.demos.request_methods"
    assert [field["name"] for field in note["fields"]] == ["title", "body", "tags"]


def test_accepted_round_serves_the_validated_dump(client: TestClient) -> None:
    response = client.post(
        ARENA_PATH,
        json={"model": "note-create", "candidates": {"title": "from a test"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "accepted"
    assert body["model"]["key"] == "note-create"
    assert body["validated"] == {"title": "from a test", "body": "", "tags": []}
    # exclude_none drops the rejected-only fields from an accepted payload.
    assert "errors" not in body
    assert body["extraKeysIgnored"] == []


def test_rejected_round_serves_the_envelope_triples(client: TestClient) -> None:
    response = client.post(
        ARENA_PATH,
        json={
            "model": "lab-specimen",
            "candidates": {
                "count": 1,
                "flag": True,
                "tags": ["t"],
                "score": 101,
                "handle": "x",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "rejected"
    assert "validated" not in body
    assert body["errors"][0] == {
        "loc": ["body", "score"],
        "msg": "Input should be less than or equal to 100",
        "type": "less_than_equal",
    }
    score_row = next(row for row in body["rows"] if row["field"] == "score")
    assert score_row["outcome"]["status"] == "rejected"
    assert score_row["outcome"]["loc"] == ["body", "score"]


def test_coerced_round_shows_original_and_coerced(client: TestClient) -> None:
    body = client.post(
        ARENA_PATH,
        json={
            "model": "lab-specimen",
            "candidates": {
                "count": "3",
                "flag": "true",
                "tags": ["t"],
                "score": "5",
                "handle": " X Y ",
            },
        },
    ).json()
    assert body["verdict"] == "accepted"
    count_row = next(row for row in body["rows"] if row["field"] == "count")
    assert count_row["outcome"] == {
        "status": "coerced",
        "original": "3",
        "originalType": "str",
        "value": 3,
        "valueType": "int",
    }
    assert body["validated"]["handle"] == "x-y"


def test_unknown_model_key_is_the_edges_own_422(client: TestClient) -> None:
    response = client.post(ARENA_PATH, json={"model": "nope", "candidates": {}})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["details"][0]["loc"] == ["body", "model"]
    assert error["details"][0]["type"] == "literal_error"
    assert response.headers["x-request-id"] == error["requestId"]


def test_non_object_candidates_is_the_edges_own_422(client: TestClient) -> None:
    response = client.post(ARENA_PATH, json={"model": "note-create", "candidates": [1, 2]})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["details"][0]["loc"] == ["body", "candidates"]
    assert error["details"][0]["type"] == "dict_type"


def test_response_models_are_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    roster_ref = schema["paths"][f"{ARENA_PATH}/roster"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]["$ref"]
    assert roster_ref.endswith("ArenaRosterPayload")
    arena_post = schema["paths"][ARENA_PATH]["post"]
    assert arena_post["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("ArenaVerdictPayload")
    # The request model is documented too — the contract is two-sided.
    assert arena_post["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "ArenaRequest"
    )
