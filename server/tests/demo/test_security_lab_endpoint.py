"""The security demo endpoints — the lab panel, the burner, the PII round.

The burner is the heart: five POSTs walk the budget down 4→0 with
x-ratelimit-remaining telemetry, the sixth never reaches the handler —
the dependency raises the standard 429 envelope with Retry-After and the
numbers in details. The PII half walks the masking ladder with REAL
minted credentials (anonymous → viewer → editor → admin), proves export
and erase are admin-gated for real (401, then 403 with the reason, then
200), and closes the erasure round with counts and a 404.
"""

from fastapi.testclient import TestClient

LAB_PATH = "/api/demo/security"
BURN_PATH = "/api/demo/security/rate-limit/burn"
PII_PATH = "/api/demo/security/pii"
SUBJECT_PATH = "/api/demo/security/pii/subjects/{subject_id}"
MINT_PATH = "/api/demo/auth/jwt/mint"

SUBJECT = "cust-2f9a41"


def _token(client: TestClient, username: str) -> str:
    minted = client.post(MINT_PATH, json={"username": username, "scopes": ["*"]})
    assert minted.status_code == 200
    return minted.json()["token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _field(body: dict[str, object], name: str) -> dict[str, object]:
    fields = body["fields"]
    assert isinstance(fields, list)
    return next(field for field in fields if field["field"] == name)


# ── The lab panel ─────────────────────────────────────────────────────────────


def test_panel_serves_the_header_table_cors_policy_and_throttle(
    client: TestClient,
) -> None:
    body = client.get(LAB_PATH).json()
    assert [row["header"] for row in body["headers"]] == [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Content-Security-Policy",
        "Strict-Transport-Security",
    ]
    assert all(row["why"] for row in body["headers"])
    assert body["cors"]["allowedOrigins"] == ["http://localhost:5174"]
    assert body["cors"]["allowCredentials"] is True
    assert "wildcard" in body["cors"]["misconfigNote"]
    assert body["rateLimit"]["budget"] == 5
    assert body["rateLimit"]["windowSeconds"] == 10
    assert body["rateLimit"]["burnEndpoint"] == BURN_PATH


# ── The burner: a real budget on a real endpoint ─────────────────────────────


def test_burn_walks_the_budget_down_to_the_429(client: TestClient) -> None:
    for attempt, remaining in enumerate((4, 3, 2, 1, 0), start=1):
        response = client.post(BURN_PATH)
        assert response.status_code == 200
        body = response.json()
        assert body["attempt"] == attempt
        assert body["remaining"] == remaining
        assert response.headers["x-ratelimit-remaining"] == str(remaining)

    throttled = client.post(BURN_PATH)
    assert throttled.status_code == 429
    envelope = throttled.json()["error"]
    assert envelope["code"] == "rate_limited"
    details = envelope["details"]
    assert details["limit"] == 5
    assert details["windowSeconds"] == 10
    assert details["retryAfterSeconds"] == int(throttled.headers["retry-after"])
    assert throttled.headers["retry-after"].isdigit()
    assert "retry in" in envelope["message"]


def test_the_throttle_burns_one_route_not_the_app(client: TestClient) -> None:
    for _ in range(5):
        assert client.post(BURN_PATH).status_code == 200
    assert client.post(BURN_PATH).status_code == 429
    # A different route still answers — the budget is keyed by ip + route.
    assert client.get(LAB_PATH).status_code == 200


# ── The PII panel ─────────────────────────────────────────────────────────────


def test_pii_panel_serves_subjects_classification_and_role_masks(
    client: TestClient,
) -> None:
    body = client.get(PII_PATH).json()
    assert [subject["customerId"] for subject in body["subjects"]] == [
        "cust-2f9a41",
        "cust-7c1d02",
        "cust-9e4b8c",
    ]
    assert {subject["country"] for subject in body["subjects"]} == {"EE", "JP", "GB"}
    classified = {row["field"]: row for row in body["classification"]}
    assert classified["national_id"]["tier"] == "regulated"
    assert classified["national_id"]["allowsPartial"] is False
    assert classified["card_number"]["allowsPartial"] is True
    assert classified["country"]["tier"] == "internal"
    levels = {row["role"]: row["maskLevel"] for row in body["roleMasks"]}
    assert levels == {
        "viewer": "full",
        "author": "full",
        "editor": "partial",
        "admin": "none",
        "(anonymous)": "full",
    }
    assert body["storeCount"] == 3
    assert body["minimizationNote"]


# ── The masking ladder ────────────────────────────────────────────────────────


def test_anonymous_and_viewer_see_full_masks(client: TestClient) -> None:
    anonymous = client.get(SUBJECT_PATH.format(subject_id=SUBJECT)).json()
    assert anonymous["maskLevel"] == "full"
    assert anonymous["principalRole"] is None
    assert _field(anonymous, "email")["value"] == "***"
    assert _field(anonymous, "card_number")["value"] == "***"
    assert _field(anonymous, "country")["value"] == "EE"  # internal: pass-through

    viewer = client.get(
        SUBJECT_PATH.format(subject_id=SUBJECT), headers=_bearer(_token(client, "alan"))
    ).json()
    assert viewer["principalRole"] == "viewer"
    assert viewer["maskLevel"] == "full"
    assert _field(viewer, "email")["value"] == "***"


def test_editor_sees_the_partial_residue_and_admin_sees_raw(
    client: TestClient,
) -> None:
    editor = client.get(
        SUBJECT_PATH.format(subject_id=SUBJECT),
        headers=_bearer(_token(client, "barbara")),
    ).json()
    assert editor["maskLevel"] == "partial"
    assert _field(editor, "email")["value"] == "m***@example.org"
    assert _field(editor, "card_number")["value"] == "2213"
    assert _field(editor, "full_name")["value"] == "Marta I."
    assert _field(editor, "date_of_birth")["value"] == "***"  # no honest partial form
    assert _field(editor, "national_id")["value"] == "***"

    admin = client.get(
        SUBJECT_PATH.format(subject_id=SUBJECT), headers=_bearer(_token(client, "ada"))
    ).json()
    assert admin["maskLevel"] == "none"
    assert _field(admin, "email")["value"] == "marta.ilves@example.org"
    assert _field(admin, "national_id")["value"] == "EE-39203178741"


def test_a_presented_but_invalid_credential_is_still_the_401(client: TestClient) -> None:
    response = client.get(
        SUBJECT_PATH.format(subject_id=SUBJECT), headers=_bearer("not.a.token")
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_unknown_subject_is_the_404_envelope(client: TestClient) -> None:
    response = client.get(SUBJECT_PATH.format(subject_id="cust-nope"))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# ── Export and erase: admin-gated for real ────────────────────────────────────


def test_export_ladder_401_403_200(client: TestClient) -> None:
    export_path = SUBJECT_PATH.format(subject_id=SUBJECT) + "/export"
    assert client.post(export_path).status_code == 401

    denied = client.post(export_path, headers=_bearer(_token(client, "alan")))
    assert denied.status_code == 403
    details = denied.json()["error"]["details"]
    assert details["requiredRole"] == "admin"
    assert details["roles"] == ["viewer"]

    exported = client.post(export_path, headers=_bearer(_token(client, "ada"))).json()
    assert exported["record"]["email"] == "marta.ilves@example.org"
    assert {row["field"] for row in exported["classification"]} == {
        "customer_id",
        "full_name",
        "email",
        "phone",
        "date_of_birth",
        "national_id",
        "card_number",
        "country",
        "signup_at",
    }


def test_erase_round_proves_the_record_gone_and_reset_reseeds(
    client: TestClient,
) -> None:
    erase_path = SUBJECT_PATH.format(subject_id=SUBJECT) + "/erase"
    admin_headers = _bearer(_token(client, "ada"))

    denied = client.post(erase_path, headers=_bearer(_token(client, "barbara")))
    assert denied.status_code == 403

    proof = client.post(erase_path, headers=admin_headers).json()
    assert proof["recordsBefore"] == 3
    assert proof["recordsAfter"] == 2

    after = client.get(SUBJECT_PATH.format(subject_id=SUBJECT))
    assert after.status_code == 404
    assert client.post(erase_path, headers=admin_headers).status_code == 404

    reset = client.post(f"{PII_PATH}/reset").json()
    assert reset["seeded"] == 3
    assert client.get(SUBJECT_PATH.format(subject_id=SUBJECT)).status_code == 200
