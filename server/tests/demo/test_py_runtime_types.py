"""GET /api/demo/py/runtime-types: the endpoint's payload contract."""

from fastapi.testclient import TestClient

DEMO_PATH = "/api/demo/py/runtime-types"


def test_returns_200_typed_payload(client: TestClient) -> None:
    response = client.get(DEMO_PATH)
    assert response.status_code == 200
    body = response.json()

    # Wire is camelCase (CamelModel) with exactly the five proof sections.
    assert set(body) == {
        "hintsVsRaw",
        "originArgs",
        "faceOff",
        "enforcement",
        "boundary",
    }


def test_hints_vs_raw_contrasts_deferred_and_eager_symbols(client: TestClient) -> None:
    symbols = client.get(DEMO_PATH).json()["hintsVsRaw"]
    assert [s["mode"] for s in symbols] == ["deferred", "eager"]

    deferred_rows = {row["name"]: row for row in symbols[0]["rows"]}
    # PEP 563: raw annotations are strings until get_type_hints resolves them.
    assert deferred_rows["text"] == {"name": "text", "raw": "'str'", "resolved": "str"}
    assert deferred_rows["return"] == {"name": "return", "raw": "'str'", "resolved": "str"}

    eager_rows = {row["name"]: row for row in symbols[1]["rows"]}
    # Eagerly evaluated annotations are already objects; raw == resolved.
    assert eager_rows["topic_id"]["raw"] == "str"
    assert eager_rows["return"] == {"name": "return", "raw": "Topic | None",
                                    "resolved": "Topic | None"}
    assert symbols[1]["symbol"].endswith("ContentRegistry.topic_by_id")


def test_origin_args_take_generics_apart(client: TestClient) -> None:
    rows = {row["symbol"]: row for row in client.get(DEMO_PATH).json()["originArgs"]}
    assert rows["list[int]"] == {
        "symbol": "list[int]",
        "alias": "list[int]",
        "origin": "list",
        "args": ["int"],
    }
    # Section.blocks is the discriminated union: Annotated metadata stripped,
    # the underlying union displayed.
    assert rows["Section.blocks"]["origin"] == "list"
    assert rows["Section.blocks"]["alias"] == "list[TextBlock | CodeBlock | DemoBlock | ListBlock]"
    assert rows["ErrorBody.details"]["origin"] == "UnionType"
    assert rows["ErrorBody.details"]["args"] == [
        "dict[str, Any]",
        "list[dict[str, Any]]",
        "None",
    ]
    assert rows["ContentRegistry.topic_by_id (return)"]["args"] == ["Topic", "None"]


def test_field_face_off_contrasts_the_two_libraries(client: TestClient) -> None:
    face_off = client.get(DEMO_PATH).json()["faceOff"]
    assert face_off["dataclassSymbol"].endswith("SnippetMatch")
    assert face_off["pydanticSymbol"].endswith("Topic")

    dataclass_rows = {row["name"]: row for row in face_off["dataclassFields"]}
    assert dataclass_rows["ok"] == {
        "name": "ok",
        "annotation": "bool",
        "required": True,
    }
    assert dataclass_rows["reason"]["annotation"] == "str | None"
    assert dataclass_rows["reason"]["required"] is False

    pydantic_rows = {row["name"]: row for row in face_off["pydanticFields"]}
    assert pydantic_rows["id"]["required"] is True
    assert pydantic_rows["subtitle"]["annotation"] == "str | None"
    assert pydantic_rows["subtitle"]["required"] is False
    assert pydantic_rows["sections"]["annotation"] == "list[Section]"


def test_enforcement_run_proves_annotations_are_not_checked(client: TestClient) -> None:
    enforcement = client.get(DEMO_PATH).json()["enforcement"]
    assert enforcement["function"] == "repeat"
    assert enforcement["call"] == "repeat(3.0, 2)"
    assert enforcement["declaredReturn"] == "str"
    assert enforcement["actualReturn"] == "float"
    assert enforcement["returnedValue"] == "6.0"
    assert "incompatible type" in enforcement["mypyVerdict"]


def test_boundary_check_shows_opt_in_runtime_enforcement(client: TestClient) -> None:
    boundary = client.get(DEMO_PATH).json()["boundary"]
    assert boundary["model"] == "Topic"
    assert boundary["outcome"] == "rejected"
    assert boundary["errorType"]
    assert boundary["message"]


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][DEMO_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("RuntimeTypesPayload")
