"""The /api/demo/reqres/notes methods playground: the per-method contract.

These tests pin the request→response contract of every verb against the
seeded per-test store: GET list/one filtered through the public model
(revision never crosses the wire), POST 201 + Location, PUT full-replace
200, DELETE 204 with an empty body, the 404 envelopes for unknown ids and
second deletes, the 422 envelope for invalid bodies and non-integer path
ids, and the declared response models in OpenAPI.
"""

from fastapi.testclient import TestClient

NOTES_PATH = "/api/demo/reqres/notes"


def test_get_list_serves_seeded_notes_without_revision(client: TestClient) -> None:
    response = client.get(NOTES_PATH)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert len(body["notes"]) == 3
    for note in body["notes"]:
        assert "revision" not in note
        assert set(note) == {"id", "title", "body", "tags", "createdAt"}
    assert body["reasoning"].startswith("GET answered 200")


def test_get_one_serves_the_filtered_view(client: TestClient) -> None:
    body = client.get(f"{NOTES_PATH}/1").json()
    assert body["id"] == 1
    assert "revision" not in body


def test_get_one_unknown_id_is_the_404_envelope(client: TestClient) -> None:
    response = client.get(f"{NOTES_PATH}/99")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert "99" in error["message"]
    assert response.headers["x-request-id"] == error["requestId"]


def test_get_one_non_integer_id_is_the_422_envelope(client: TestClient) -> None:
    response = client.get(f"{NOTES_PATH}/not-a-number")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


def test_post_creates_with_201_location_and_filtered_body(client: TestClient) -> None:
    response = client.post(
        NOTES_PATH, json={"title": "created by test", "body": "b", "tags": ["t"]}
    )
    assert response.status_code == 201
    assert response.headers["location"] == f"{NOTES_PATH}/4"
    body = response.json()
    assert body["id"] == 4
    assert body["title"] == "created by test"
    assert "revision" not in body
    # The new note is immediately readable through the same contract.
    assert client.get(f"{NOTES_PATH}/4").json()["title"] == "created by test"


def test_post_invalid_body_is_the_422_envelope_with_detail_triples(client: TestClient) -> None:
    response = client.post(NOTES_PATH, json={"title": ""})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["details"][0]["loc"] == ["body", "title"]
    assert response.headers["x-request-id"] == error["requestId"]


def test_post_title_over_the_cap_is_rejected(client: TestClient) -> None:
    response = client.post(NOTES_PATH, json={"title": "x" * 81})
    assert response.status_code == 422


def test_put_full_replaces_content_and_keeps_identity(client: TestClient) -> None:
    before = client.get(f"{NOTES_PATH}/2").json()
    response = client.put(f"{NOTES_PATH}/2", json={"title": "replaced", "tags": ["new"]})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "replaced"
    assert body["body"] == ""  # full replace: omitted content resets
    assert body["tags"] == ["new"]
    assert body["createdAt"] == before["createdAt"]
    assert "revision" not in body


def test_put_unknown_id_is_the_404_envelope(client: TestClient) -> None:
    response = client.put(f"{NOTES_PATH}/99", json={"title": "nope"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_delete_answers_204_with_empty_body_then_404(client: TestClient) -> None:
    response = client.delete(f"{NOTES_PATH}/3")
    assert response.status_code == 204
    assert response.content == b""
    assert response.text == ""
    assert client.get(f"{NOTES_PATH}/3").status_code == 404
    assert client.delete(f"{NOTES_PATH}/3").status_code == 404


def test_response_models_are_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    notes = schema["paths"][NOTES_PATH]
    listing_ref = notes["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert listing_ref.endswith("NotesListing")
    create = notes["post"]
    assert create["responses"]["201"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "NotePublic"
    )
    detail = schema["paths"][f"{NOTES_PATH}/{{note_id}}"]
    for method, expected_status in (("get", "200"), ("put", "200"), ("delete", "204")):
        assert expected_status in detail[method]["responses"]
    assert detail["delete"]["responses"]["204"].get("content") is None
