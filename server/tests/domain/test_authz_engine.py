"""The policy engine's whole matrix, as arithmetic — no HTTP, no fakes needed.

Every verdict path the topic teaches, pinned on a pure engine: role
grants at both reaches, ownership allow/deny, scope narrowing (including
empty and wildcard), program credentials (scopes as grants, wildcard
denied), and the deny-by-default space — unknown actions, roleless
principals, inert unknown roles, orphan resources. Reason strings are
asserted by substring because they are teaching surface: the demo shows
them and the 403 envelope carries them.
"""

from guide.domain.authz.engine import PolicyEngine
from guide.domain.authz.model import OwnedResource, Principal

ENGINE = PolicyEngine()

GRACE_POST = OwnedResource(kind="post", id="designing-urls-people-can-read", owner="grace")
ALAN_POST = OwnedResource(kind="post", id="idempotency-retold", owner="alan")
COMMENT = OwnedResource(kind="comment", id="urls-are-for-machines", owner="alan")


def user(
    name: str,
    roles: tuple[str, ...],
    scopes: tuple[str, ...],
) -> Principal:
    """The test's principal builder — identity plus the two authority halves."""
    return Principal(
        kind="user", name=name, display_name=name, roles=roles, scopes=scopes, via="test"
    )


def key(scopes: tuple[str, ...]) -> Principal:
    """A program principal: an API key's shape — no roles, scopes only."""
    return Principal(
        kind="program",
        name="fdg_test",
        display_name="api key 'test'",
        roles=(),
        scopes=scopes,
        via="test",
    )


# ── Role grants, both reaches ─────────────────────────────────────────────────


def test_viewer_reads_but_cannot_write() -> None:
    alan = user("alan", ("viewer",), ("*",))
    assert ENGINE.decide(alan, "posts:read").allowed
    decision = ENGINE.decide(alan, "posts:write", ALAN_POST)
    assert not decision.allowed
    assert "no role of ('viewer') grants posts:write" in decision.reason


def test_admin_is_the_only_moderator() -> None:
    ada = user("ada", ("admin",), ("*",))
    assert ENGINE.decide(ada, "comments:moderate", COMMENT).allowed
    barbara = user("barbara", ("editor",), ("*",))
    editor_verdict = ENGINE.decide(barbara, "comments:moderate", COMMENT)
    assert not editor_verdict.allowed
    assert "editor" in editor_verdict.reason


def test_editor_and_admin_bypass_ownership() -> None:
    for name, role in (("barbara", "editor"), ("ada", "admin")):
        principal = user(name, (role,), ("*",))
        decision = ENGINE.decide(principal, "posts:write", GRACE_POST)
        assert decision.allowed
        assert "grants posts:write on any post" in decision.reason


# ── Ownership ─────────────────────────────────────────────────────────────────


def test_author_may_edit_their_own_post() -> None:
    grace = user("grace", ("author",), ("*",))
    decision = ENGINE.decide(grace, "posts:write", GRACE_POST)
    assert decision.allowed
    assert "ownership is the authority here" in decision.reason


def test_author_may_not_edit_someone_elses_post() -> None:
    grace = user("grace", ("author",), ("*",))
    decision = ENGINE.decide(grace, "posts:write", ALAN_POST)
    assert not decision.allowed
    assert "belongs to 'alan', not 'grace'" in decision.reason


def test_own_reach_without_an_object_denies() -> None:
    grace = user("grace", ("author",), ("*",))
    decision = ENGINE.decide(grace, "posts:write")
    assert not decision.allowed
    assert "needs a specific object" in decision.reason


def test_owner_without_the_grant_still_denies() -> None:
    alan = user("alan", ("viewer",), ("*",))
    decision = ENGINE.decide(alan, "posts:write", ALAN_POST)
    assert not decision.allowed
    assert "no role of ('viewer') grants posts:write" in decision.reason


def test_orphan_resource_allows_any_reach_but_not_own_reach() -> None:
    orphan = OwnedResource(kind="post", id="ghost-post", owner="deleted-user")
    assert ENGINE.decide(user("ada", ("admin",), ("*",)), "posts:write", orphan).allowed
    grace = user("grace", ("author",), ("*",))
    decision = ENGINE.decide(grace, "posts:write", orphan)
    assert not decision.allowed
    assert "belongs to 'deleted-user'" in decision.reason


# ── Scope narrowing ───────────────────────────────────────────────────────────


def test_narrowed_credential_denies_what_the_role_grants() -> None:
    grace = user("grace", ("author",), ("posts:read",))
    decision = ENGINE.decide(grace, "posts:write", GRACE_POST)
    assert not decision.allowed
    assert "role 'author' grants posts:write but the credential's scopes" in decision.reason
    assert "scopes narrow, never widen" in decision.reason
    assert ENGINE.decide(grace, "posts:read").allowed


def test_empty_scopes_intersect_to_nothing() -> None:
    grace = user("grace", ("author",), ())
    for action in ("posts:read", "posts:write"):
        decision = ENGINE.decide(grace, action, GRACE_POST if action == "posts:write" else None)
        assert not decision.allowed


def test_wildcard_scope_restores_full_role_authority() -> None:
    grace = user("grace", ("author",), ("*",))
    assert ENGINE.decide(grace, "posts:write", GRACE_POST).allowed


# ── Program principals ────────────────────────────────────────────────────────


def test_a_key_is_allowed_exactly_its_scopes() -> None:
    read_key = key(("posts:read",))
    assert ENGINE.decide(read_key, "posts:read").allowed
    assert "a program principal's authority is exactly its scopes" in (
        ENGINE.decide(read_key, "posts:read").reason
    )
    write_verdict = ENGINE.decide(read_key, "posts:write", GRACE_POST)
    assert not write_verdict.allowed
    assert "do not carry posts:write" in write_verdict.reason


def test_wildcard_scope_unlocks_nothing_for_a_key() -> None:
    decision = ENGINE.decide(key(("*",)), "posts:read")
    assert not decision.allowed
    assert "a program credential has none" in decision.reason


def test_unknown_scopes_are_inert_not_granting() -> None:
    decision = ENGINE.decide(key(("banana",)), "posts:read")
    assert not decision.allowed


# ── Deny by default ───────────────────────────────────────────────────────────


def test_unknown_action_denies_before_any_grant_is_read() -> None:
    ada = user("ada", ("admin",), ("*",))
    decision = ENGINE.decide(ada, "posts:nuke", GRACE_POST)
    assert not decision.allowed
    assert "unknown action 'posts:nuke'" in decision.reason
    assert "denies what it does not know" in decision.reason


def test_principal_without_a_role_denies_everything() -> None:
    ghost = user("ghost", (), ("*",))
    decision = ENGINE.decide(ghost, "posts:read")
    assert not decision.allowed
    assert "'ghost' has no role in the registry" in decision.reason


def test_unknown_roles_contribute_nothing() -> None:
    wizard = user("merlin", ("space-wizard",), ("*",))
    decision = ENGINE.decide(wizard, "posts:read")
    assert not decision.allowed
    assert "has no role in the registry" in decision.reason
