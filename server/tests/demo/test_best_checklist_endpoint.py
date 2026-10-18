"""The best-practices checklist endpoint (topic 41, area ``best``).

Pins the wire contract (GET /api/demo/best/checklist): the ten practice
areas, verdicts that are only ever pass/fail/manual, live rows carrying
REAL evidence from self-requests through the serving app, manual rows
claiming nothing and saying why, the repo-root visibility gate behaving
honestly in BOTH directions (real checks when the root is mounted, honest
manual rows when it is not), and the pure builder judging a broken tree
as fail rather than crashing.
"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

import guide.domain.demos.best_checklist as best_checklist_module
from guide.domain.demos.best_checklist import build_best_checklist_payload, resolve_roots

PANEL_PATH = "/api/demo/best/checklist"

EXPECTED_AREA_IDS = [
    "setup",
    "api-discipline",
    "security",
    "data",
    "reliability",
    "observability",
    "performance",
    "operations",
    "git-and-review",
    "human-practices",
]

REPO_ROOT_ITEM_IDS = [
    "compose-parity",
    "clean-build-contexts",
    "services-declare-health",
    "onboarding-one-command",
]


def rows_by_id(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every checklist row flat-mapped by id (ids are unique per panel)."""
    return {
        row["id"]: row for area in body["areas"] for row in area["items"]
    }


def test_panel_serves_the_ten_areas_with_consistent_verdicts(
    app: FastAPI, client: TestClient
) -> None:
    response = client.get(PANEL_PATH)
    assert response.status_code == 200
    body = response.json()

    assert [area["id"] for area in body["areas"]] == EXPECTED_AREA_IDS
    assert all(area["note"] for area in body["areas"])
    every = [row for area in body["areas"] for row in area["items"]]
    assert len(every) >= 20, "a practices synthesis earns its keep in rows"

    for row in every:
        assert row["verdict"] in ("pass", "fail", "manual")
        assert row["checkKind"] in ("live", "file", "manual")
        if row["verdict"] != "manual":
            assert row["evidence"], f"{row['id']} judges without evidence"
            assert row["whyManual"] is None
        else:
            # A manual row claims NOTHING and says why — never a faked pass.
            assert row["checkKind"] == "manual"
            assert row["whyManual"]
            assert row["evidence"] == []

    summary = body["summary"]
    assert summary["items"] == len(every)
    assert summary["passed"] + summary["failed"] + summary["manual"] == len(every)
    assert summary["manual"] >= 1, "honest manuals are a feature, not a gap"


def test_live_rows_derive_from_real_self_requests(
    app: FastAPI, client: TestClient
) -> None:
    rows = rows_by_id(client.get(PANEL_PATH).json())

    request_id = rows["request-id-roundtrip"]
    assert request_id["verdict"] == "pass"
    assert request_id["checkKind"] == "live"
    assert "echo verified: true" in request_id["evidence"]

    envelope = rows["one-error-envelope"]
    assert envelope["verdict"] == "pass"
    assert "GET /api/posts/best-checklist-nope → 404" in envelope["evidence"]
    assert "headerMatchesBody=true" in envelope["evidence"]

    validation = rows["boundary-validation"]
    assert validation["verdict"] == "pass"
    assert any("422" in line for line in validation["evidence"])

    contract = rows["openapi-contract"]
    assert contract["verdict"] == "pass"
    assert any("paths documented" in line for line in contract["evidence"])

    success_headers = rows["security-headers"]
    assert success_headers["verdict"] == "pass"
    joined = " ".join(success_headers["evidence"])
    for header in ("x-content-type-options", "x-frame-options", "referrer-policy"):
        assert header in joined

    error_headers = rows["headers-on-errors"]
    assert error_headers["verdict"] == "pass"
    assert "the 404 response carried:" in error_headers["evidence"][0]

    liveness = rows["liveness-endpoint"]
    assert liveness["verdict"] == "pass"
    assert "GET /api/health → 200" in liveness["evidence"]


def test_file_rows_quote_what_they_read(client: TestClient) -> None:
    rows = rows_by_id(client.get(PANEL_PATH).json())

    mypy = rows["mypy-strict"]
    assert mypy["verdict"] == "pass"
    assert mypy["checkKind"] == "file"
    assert "strict = true" in mypy["evidence"][0]

    chain = rows["migrations-own-the-schema"]
    assert chain["verdict"] == "pass"
    assert "0001 → 0002 → 0003 → 0004" in chain["evidence"][0]

    lock = rows["lockfile-is-the-contract"]
    assert lock["verdict"] == "pass"
    assert "TOML parse ok" in lock["evidence"][0]

    ratchet = rows["machine-checked-review"]
    assert ratchet["verdict"] == "pass"
    assert "RATCHET = 0" in ratchet["evidence"][0]


def test_manual_rows_are_the_honest_kind(client: TestClient) -> None:
    rows = rows_by_id(client.get(PANEL_PATH).json())

    diffs = rows["review-your-diffs"]
    assert diffs["verdict"] == "manual"
    assert "design intent" in diffs["whyManual"]

    secrets = rows["prod-secrets-real"]
    assert secrets["verdict"] == "manual"
    assert "operator fact" in secrets["whyManual"]


def test_repo_root_checks_follow_visibility_honestly(
    app: FastAPI, client: TestClient
) -> None:
    server_root, repo_root = resolve_roots(Path(best_checklist_module.__file__))
    assert server_root.is_dir()
    rows = rows_by_id(client.get(PANEL_PATH).json())

    if repo_root is not None:
        # The whole repo is mounted (dev container / host): real file checks.
        for item_id in REPO_ROOT_ITEM_IDS:
            assert rows[item_id]["checkKind"] == "file", item_id
            assert rows[item_id]["verdict"] == "pass", item_id
            assert rows[item_id]["evidence"], item_id
    else:
        # Server bind mount only: honest manual rows, never faked passes.
        for item_id in REPO_ROOT_ITEM_IDS:
            assert rows[item_id]["verdict"] == "manual", item_id
            assert "not visible from this process" in rows[item_id]["whyManual"]


def test_not_dones_present_the_deliberate_decisions(client: TestClient) -> None:
    body = client.get(PANEL_PATH).json()
    assert [row["id"] for row in body["notDones"]] == [
        "no-hosted-ci",
        "postgresql-only",
        "browser-e2e-deferred",
        "no-teaching-exhibits",
    ]
    for row in body["notDones"]:
        assert row["reason"]
        assert row["artifacts"]
    assert "computed at request time" in body["honestyNote"]


async def test_a_broken_tree_judges_fail_instead_of_crashing(
    app: FastAPI, tmp_path: Path
) -> None:
    payload = await build_best_checklist_payload(
        app=app, server_root=tmp_path, repo_root=None
    )
    rows = {row.id: row for area in payload.areas for row in area.items}

    # An empty tree is DATA for the audit, never an exception.
    assert rows["mypy-strict"].verdict == "fail"
    assert rows["linters-configured"].verdict == "fail"
    assert rows["lockfile-is-the-contract"].verdict == "fail"
    assert rows["migrations-own-the-schema"].verdict == "fail"
    assert "no revision files found" in rows["migrations-own-the-schema"].evidence[0]
    assert rows["compose-parity"].verdict == "manual"

    # The live probes judged the real app regardless of the broken tree.
    assert rows["request-id-roundtrip"].verdict == "pass"
    assert payload.summary.failed >= 4


def test_response_model_is_declared_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    ref = schema["paths"][PANEL_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert ref.endswith("BestChecklistPanel")
