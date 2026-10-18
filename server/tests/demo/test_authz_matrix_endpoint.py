"""The authz matrix endpoints — panel, what-if check, and the two real guards.

The guarded endpoints are the heart: PUT /posts/{id} walks the object
guard's full ladder (401 unauthenticated, 404 missing post, 403 with the
engine's reason in details, 200 with the reason it allowed) and POST
/comments/{id}/moderate walks the collection guard's (401, 403, 404,
200 — verdict before existence). Credentials come from topic 23's real
substrate: tokens minted per principal with chosen scopes, and API keys
generated with chosen scopes — no fabricated headers.
"""

from fastapi.testclient import TestClient

PANEL_PATH = "/api/demo/authz"
CHECK_PATH = "/api/demo/authz/check"
EDIT_PATH = "/api/demo/authz/posts/{post_id}"
MODERATE_PATH = "/api/demo/authz/comments/{comment_id}/moderate"
MINT_PATH = "/api/demo/auth/jwt/mint"
KEYS_PATH = "/api/demo/auth/keys"

GRACE_POST = "designing-urls-people-can-read"
ALAN_POST = "idempotency-retold"
COMMENT = "urls-are-for-machines"


def _token(client: TestClient, username: str, scopes: list[str]) -> str:
    """Mint a real token as any principal with any scopes (topic 23's form)."""
    minted = client.post(MINT_PATH, json={"username": username, "scopes": scopes})
    assert minted.status_code == 200
    return minted.json()["token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _edit(client: TestClient, post_id: str, headers: dict[str, str]) -> dict[str, object]:
    response = client.put(EDIT_PATH.format(post_id=post_id), headers=headers)
    assert response.status_code == 200
    return response.json()


def _edit_error(client: TestClient, post_id: str, headers: dict[str, str]) -> dict[str, object]:
    response = client.put(EDIT_PATH.format(post_id=post_id), headers=headers)
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "forbidden"
    return body["error"]["details"]


# ── The panel ─────────────────────────────────────────────────────────────────


def test_panel_serves_roster_matrix_and_targets(client: TestClient) -> None:
    body = client.get(PANEL_PATH).json()
    assert [(p["name"], p["role"]) for p in body["principals"]] == [
        ("ada", "admin"),
        ("alan", "viewer"),
        ("barbara", "editor"),
        ("grace", "author"),
    ]
    roles = {row["role"]: row["grants"] for row in body["roles"]}
    assert list(roles) == ["viewer", "author", "editor", "admin"]
    viewer = {cell["action"]: cell["level"] for cell in roles["viewer"]}
    assert viewer == {
        "posts:read": "any",
        "posts:write": None,
        "comments:read": "any",
        "comments:moderate": None,
    }
    author = {cell["action"]: cell["level"] for cell in roles["author"]}
    assert author["posts:write"] == "own"
    assert {cell["action"]: cell["level"] for cell in roles["admin"]}[
        "comments:moderate"
    ] == "any"
    assert len(body["seededPosts"]) == 12
    assert {c["id"] for c in body["seededComments"]} == {
        "urls-are-for-machines",
        "envelope-skeptic",
        "retry-this",
    }
    assert body["wildcardScope"] == "*"
    assert body["denyNote"] and body["scopeNote"] and body["ownershipNote"]
    assert body["checkEndpoint"] == CHECK_PATH


# ── The what-if check ─────────────────────────────────────────────────────────


def test_check_answers_allow_and_deny_with_reasons(client: TestClient) -> None:
    allowed = client.post(
        CHECK_PATH,
        json={
            "principalName": "barbara",
            "action": "posts:write",
            "resourceKind": "post",
            "resourceId": GRACE_POST,
        },
    )
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["role"] == "editor"
    assert body["decision"]["allowed"] is True
    assert body["resource"]["owner"] == "grace"

    denied = client.post(
        CHECK_PATH,
        json={
            "principalName": "grace",
            "scopes": ["posts:read"],
            "action": "posts:write",
            "resourceKind": "post",
            "resourceId": GRACE_POST,
        },
    ).json()
    assert denied["decision"]["allowed"] is False
    assert "scopes narrow, never widen" in denied["decision"]["reason"]


def test_check_denies_the_unknown_space(client: TestClient) -> None:
    ghost = client.post(
        CHECK_PATH, json={"principalName": "ghost", "action": "posts:read"}
    ).json()
    assert ghost["role"] is None
    assert "has no role in the registry" in ghost["decision"]["reason"]

    unknown_action = client.post(
        CHECK_PATH, json={"principalName": "ada", "action": "posts:nuke"}
    ).json()
    assert "unknown action 'posts:nuke'" in unknown_action["decision"]["reason"]

    missing = client.post(
        CHECK_PATH,
        json={
            "principalName": "ada",
            "action": "posts:write",
            "resourceKind": "post",
            "resourceId": "no-such-post",
        },
    ).json()
    assert "no such post 'no-such-post'" in missing["decision"]["reason"]


# ── The object guard: PUT /posts/{post_id} ────────────────────────────────────


def test_edit_without_credentials_is_the_401_envelope(client: TestClient) -> None:
    response = client.put(EDIT_PATH.format(post_id=GRACE_POST))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert "x-request-id" in response.headers


def test_edit_with_a_garbage_token_is_the_401_envelope(client: TestClient) -> None:
    response = client.put(
        EDIT_PATH.format(post_id=GRACE_POST), headers=_bearer("not.a.token")
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_missing_post_is_the_404_before_any_verdict(client: TestClient) -> None:
    response = client.put(
        EDIT_PATH.format(post_id="no-such-post"), headers=_bearer(_token(client, "ada", ["*"]))
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_owner_edits_their_own_post_with_the_reason_attached(client: TestClient) -> None:
    body = _edit(client, GRACE_POST, _bearer(_token(client, "grace", ["*"])))
    assert body["principal"] == "grace"
    assert body["action"] == "posts:write"
    assert "ownership is the authority here" in body["reason"]
    assert body["post"]["id"] == GRACE_POST


def test_roleless_write_on_own_post_and_cross_user_escalation_both_deny(
    client: TestClient,
) -> None:
    details = _edit_error(client, ALAN_POST, _bearer(_token(client, "alan", ["*"])))
    assert details["principal"] == "alan"
    assert "no role of ('viewer') grants posts:write" in details["reason"]

    details = _edit_error(client, ALAN_POST, _bearer(_token(client, "grace", ["*"])))
    assert "belongs to 'alan', not 'grace'" in details["reason"]


def test_editor_and_admin_bypass_ownership(client: TestClient) -> None:
    for username in ("barbara", "ada"):
        body = _edit(client, GRACE_POST, _bearer(_token(client, username, ["*"])))
        assert body["principal"] == username
        assert "on any post" in body["reason"]


def test_narrowed_credential_denies_the_write_the_role_would_allow(
    client: TestClient,
) -> None:
    details = _edit_error(
        client, GRACE_POST, _bearer(_token(client, "grace", ["posts:read"]))
    )
    assert "scopes narrow, never widen" in details["reason"]


def test_edit_request_may_carry_a_real_title_change(client: TestClient) -> None:
    response = client.put(
        EDIT_PATH.format(post_id=GRACE_POST),
        headers=_bearer(_token(client, "grace", ["*"])),
        json={"title": "Designing URLs people can read (edited)"},
    )
    assert response.status_code == 200
    assert response.json()["post"]["title"] == "Designing URLs people can read (edited)"
    assert response.json()["post"]["author"] == "grace"


def test_program_key_is_allowed_exactly_its_scopes(client: TestClient) -> None:
    write_key = client.post(KEYS_PATH, json={"name": "tour", "scopes": ["posts:write"]}).json()
    body = _edit(client, GRACE_POST, {"x-api-key": write_key["key"]})
    assert body["principalKind"] == "program"
    assert "exactly its scopes" in body["reason"]

    read_key = client.post(KEYS_PATH, json={"name": "ro", "scopes": ["posts:read"]}).json()
    details = _edit_error(client, GRACE_POST, {"x-api-key": read_key["key"]})
    assert "do not carry posts:write" in details["reason"]


# ── The collection guard: POST /comments/{comment_id}/moderate ────────────────


def test_moderation_ladder_401_403_404_200(client: TestClient) -> None:
    assert (
        client.post(MODERATE_PATH.format(comment_id=COMMENT), json={"status": "hidden"}).status_code
        == 401
    )

    denied = client.post(
        MODERATE_PATH.format(comment_id=COMMENT),
        json={"status": "hidden"},
        headers=_bearer(_token(client, "barbara", ["*"])),
    )
    assert denied.status_code == 403
    assert "no role of ('editor') grants comments:moderate" in (
        denied.json()["error"]["details"]["reason"]
    )

    missing = client.post(
        MODERATE_PATH.format(comment_id="no-such-comment"),
        json={"status": "hidden"},
        headers=_bearer(_token(client, "ada", ["*"])),
    )
    assert missing.status_code == 404

    allowed = client.post(
        MODERATE_PATH.format(comment_id=COMMENT),
        json={"status": "hidden"},
        headers=_bearer(_token(client, "ada", ["*"])),
    )
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["principal"] == "ada"
    assert body["comment"]["status"] == "hidden"
    assert body["comment"]["moderatedBy"] == "ada"


def test_moderation_flips_back_and_records_the_moderator(client: TestClient) -> None:
    headers = _bearer(_token(client, "ada", ["*"]))
    hidden = client.post(
        MODERATE_PATH.format(comment_id=COMMENT), json={"status": "hidden"}, headers=headers
    ).json()
    assert hidden["comment"]["status"] == "hidden"
    visible = client.post(
        MODERATE_PATH.format(comment_id=COMMENT), json={"status": "visible"}, headers=headers
    ).json()
    assert visible["comment"]["status"] == "visible"
    assert visible["comment"]["moderatedBy"] == "ada"


def test_author_cannot_moderate_comments(client: TestClient) -> None:
    response = client.post(
        MODERATE_PATH.format(comment_id=COMMENT),
        json={"status": "hidden"},
        headers=_bearer(_token(client, "grace", ["*"])),
    )
    assert response.status_code == 403
    assert "no role of ('author') grants comments:moderate" in (
        response.json()["error"]["details"]["reason"]
    )
