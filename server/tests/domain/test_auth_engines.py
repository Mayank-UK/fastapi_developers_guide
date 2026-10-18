"""The six auth engines' security guarantees, deterministically.

Domain-level tests over the real in-memory adapter: password hashing
(salt freshness, the rehash signal, timing-uniform unknown users), the
session seal (tamper dies at the signature, logout kills the store row),
API keys (hash-at-rest, constant-time verify, instant revocation), JWTs
(mint with an explicit clock for the expired / not-yet-valid paths, the
wrong-secret forgery, malformed), OAuth (S256, one-time codes burned on
first presentation, wrong verifier), and refresh families (rotation
chain, reuse detection revoking the family, the dead-family 401). The
engines run on ordered awaits with no sleeps — time is injected where
claims are minted.
"""

from datetime import UTC, datetime, timedelta

import pytest

from guide.core.errors import AppError, FailureKind
from guide.data.auth import InMemoryAuthState
from guide.domain.auth.api_key_service import ApiKeyService, hash_key
from guide.domain.auth.jwt_service import TokenService
from guide.domain.auth.oauth_service import OAuthProviderService, s256_challenge
from guide.domain.auth.password_service import (
    LEGACY_HASH,
    PasswordService,
    production_hasher,
)
from guide.domain.auth.ports import (
    AuthorizeRequest,
    CreateKeyRequest,
    HashPasswordRequest,
    LoginRequest,
    MintTokenRequest,
    RefreshExchangeRequest,
    RefreshLoginRequest,
    TokenExchangeRequest,
    VerifyPasswordRequest,
)
from guide.domain.auth.refresh_service import RefreshRotationService
from guide.domain.auth.session_service import SessionService

SECRET = "test-secret-that-is-long-enough-32-bytes-ok"
def _past(seconds: int) -> datetime:
    """A wall-clock-derived past instant — deterministic claims, no sleeps."""
    return datetime.now(UTC) - timedelta(seconds=seconds)


def _world() -> tuple[InMemoryAuthState, PasswordService]:
    return InMemoryAuthState(), PasswordService(production_hasher())


# ── Passwords ────────────────────────────────────────────────────────────────


def test_hash_is_salted_and_parameter_stamped() -> None:
    passwords = PasswordService(production_hasher())
    first = passwords.hash_password(HashPasswordRequest(password="same input"))
    second = passwords.hash_password(HashPasswordRequest(password="same input"))
    assert first.hash != second.hash  # fresh salt every time
    assert first.hash.startswith("$argon2id$")
    assert first.elapsed_ms > 0  # the honest cost, really measured
    assert "m=65536" in first.parameters  # the active cost is stated


def test_verify_matches_rejects_and_flags_legacy_cost() -> None:
    passwords = PasswordService(production_hasher())
    minted = passwords.hash_password(HashPasswordRequest(password="correct"))
    ok = passwords.verify_password(
        VerifyPasswordRequest(password="correct", hash=minted.hash)
    )
    assert ok.ok is True and ok.needs_rehash is False
    wrong = passwords.verify_password(
        VerifyPasswordRequest(password="incorrect", hash=minted.hash)
    )
    assert wrong.ok is False and wrong.error is None
    legacy = passwords.verify_password(
        VerifyPasswordRequest(password="analytical-engine", hash=LEGACY_HASH)
    )
    assert legacy.ok is True and legacy.needs_rehash is True


def test_malformed_hash_is_an_error_not_a_failed_match() -> None:
    passwords = PasswordService(production_hasher())
    verdict = passwords.verify_password(
        VerifyPasswordRequest(password="x", hash="not-an-argon2-hash")
    )
    assert verdict.ok is False and verdict.error is not None


def test_unknown_users_burn_the_same_decoy_work() -> None:
    passwords = PasswordService(production_hasher())
    assert passwords.verify_uniform(None, "whatever") is False
    assert passwords.verify_uniform(LEGACY_HASH, "wrong password") is False
    assert passwords.verify_uniform(LEGACY_HASH, "analytical-engine") is True


# ── Sessions ─────────────────────────────────────────────────────────────────


async def test_login_sets_the_flags_and_logout_kills_the_row() -> None:
    state, passwords = _world()
    sessions = SessionService(state, state, passwords, SECRET)
    row = await sessions.login(LoginRequest(username="ada", password="analytical-engine"))
    cookie = row.cookie
    assert cookie.httponly is True and cookie.samesite == "lax" and cookie.secure is False
    assert cookie.max_age_seconds == 900

    inspected = await sessions.inspect(cookie.value)
    assert inspected.username == "ada"
    assert "posts:write" in inspected.scopes

    logout = await sessions.logout(cookie.value)
    assert logout.revoked is True
    with pytest.raises(AppError) as rejection:
        await sessions.inspect(cookie.value)
    assert rejection.value.kind is FailureKind.UNAUTHORIZED


async def test_tampered_and_missing_cookies_fail_indistinguishably() -> None:
    state, passwords = _world()
    sessions = SessionService(state, state, passwords, SECRET)
    row = await sessions.login(LoginRequest(username="ada", password="analytical-engine"))
    for bad_value in (
        row.cookie.value[:-2] + "xx",  # edit the signature
        row.cookie.value.split(".")[0],  # drop the signature entirely
        "",
        None,  # no cookie at all
    ):
        with pytest.raises(AppError) as rejection:
            await sessions.inspect(bad_value)
        assert rejection.value.kind is FailureKind.UNAUTHORIZED
        assert "which" not in rejection.value.message  # no oracle in the message


async def test_wrong_credentials_reject_unknown_and_wrong_identically() -> None:
    state, passwords = _world()
    sessions = SessionService(state, state, passwords, SECRET)
    for username, password in (("ada", "wrong"), ("ghost", "analytical-engine")):
        with pytest.raises(AppError) as rejection:
            await sessions.login(LoginRequest(username=username, password=password))
        assert rejection.value.kind is FailureKind.UNAUTHORIZED
        assert rejection.value.message == (
            "invalid credentials — username and password are checked as one"
        )


# ── API keys ─────────────────────────────────────────────────────────────────


async def test_keys_store_only_hashes_and_show_the_secret_once() -> None:
    state, _ = _world()
    keys = ApiKeyService(state)
    created = await keys.generate(CreateKeyRequest(name="ci", scopes=["posts:read"]))
    assert created.key.startswith(created.prefix + ".")
    record = await state.find_key_by_prefix(created.prefix)
    assert record is not None
    assert record.key_hash == hash_key(created.key)  # hash at rest, never raw
    roster = await keys.roster()
    assert created.key not in {row.key_hash for row in roster}
    call = await keys.call(created.key)
    assert call.scopes == ("posts:read",)


async def test_key_verify_rejects_wrong_secret_and_revoked_keys() -> None:
    state, _ = _world()
    keys = ApiKeyService(state)
    created = await keys.generate(CreateKeyRequest(name="ci"))
    for bad in (
        created.key[:-4] + "zzzz",  # wrong secret
        created.prefix + ".shortsecretvalue-that-is-not-the-one",  # same prefix
        "no-separator-at-all",
        None,  # header missing
    ):
        with pytest.raises(AppError) as rejection:
            await keys.call(bad)
        assert rejection.value.kind is FailureKind.UNAUTHORIZED
    revoked = await keys.revoke(created.prefix)
    assert revoked.revoked is True
    with pytest.raises(AppError) as rejection:  # the perfect key, dead instantly
        await keys.call(created.key)
    assert rejection.value.kind is FailureKind.UNAUTHORIZED
    with pytest.raises(AppError) as missing:
        await keys.revoke(created.prefix)
    assert missing.value.kind is FailureKind.NOT_FOUND


# ── Tokens ───────────────────────────────────────────────────────────────────


def _tokens(state: InMemoryAuthState, passwords: PasswordService) -> TokenService:
    return TokenService(SECRET, state, passwords)


def test_minted_token_verifies_with_its_claims() -> None:
    state, passwords = _world()
    tokens = _tokens(state, passwords)
    minted = tokens.mint(
        MintTokenRequest(username="ada", scopes=["posts:read"]), now=_past(0)
    )
    assert minted.signed_with == "real"
    assert minted.payload["sub"] == "ada"
    verdict = tokens.verify(minted.token)
    assert verdict.outcome == "valid" and verdict.username == "ada"
    assert verdict.scopes == ("posts:read",)


def test_expired_and_not_yet_valid_are_minted_not_slept() -> None:
    state, passwords = _world()
    tokens = _tokens(state, passwords)
    expired = tokens.mint(
        MintTokenRequest(username="ada", ttl_seconds=60),
        now=_past(120),
    )
    assert tokens.verify(expired.token).outcome == "expired"
    premature = tokens.mint(
        MintTokenRequest(username="ada", not_before_seconds=3600), now=_past(0),
    )
    assert tokens.verify(premature.token).outcome == "not-yet-valid"


def test_forged_signature_malformed_and_missing_claims_classify() -> None:
    state, passwords = _world()
    tokens = _tokens(state, passwords)
    forged = tokens.mint(
        MintTokenRequest(username="ada", sign_with="wrong"), now=_past(0)
    )
    assert tokens.verify(forged.token).outcome == "bad-signature"
    assert tokens.verify("garbage.not-a.jwt").outcome == "malformed"

    import jwt as pyjwt

    unsigned = pyjwt.encode(
        {"sub": "ada", "iat": 1, "exp": 9999999999, "nbf": 1, "iss": "guide.demo"},
        SECRET,
        algorithm="HS256",
    )
    assert tokens.verify(unsigned).outcome == "valid"  # same secret, minimal claims
    no_claims = pyjwt.encode({"sub": "ada"}, SECRET, algorithm="HS256")
    assert tokens.verify(no_claims).outcome == "malformed"  # required claims absent

    username, scopes = tokens.require(unsigned)
    assert username == "ada" and scopes == ()
    with pytest.raises(AppError) as missing:
        tokens.require(None)
    assert missing.value.kind is FailureKind.UNAUTHORIZED


async def test_token_login_form_rejects_bad_credentials() -> None:
    state, passwords = _world()
    tokens = _tokens(state, passwords)
    row = await tokens.login("grace", "nanosecond")
    assert row.token_type == "bearer" and row.scope == "posts:read"
    assert tokens.verify(row.access_token).username == "grace"
    for username, password in (("grace", "wrong"), ("ghost", "nanosecond")):
        with pytest.raises(AppError) as rejection:
            await tokens.login(username, password)
        assert rejection.value.kind is FailureKind.UNAUTHORIZED


# ── OAuth ────────────────────────────────────────────────────────────────────


async def _authorize_row(provider: OAuthProviderService, challenge: str) -> str:
    """Authorize with the registered client; answer the one-time code."""
    row = await provider.authorize(
        AuthorizeRequest(
            client_id="guide-cli",
            redirect_uri="https://client.example/callback",
            state="s",
            code_challenge=challenge,
        )
    )
    return row.redirect_to.split("code=")[1].split("&")[0]


def test_s256_is_the_rfc_transform() -> None:
    import base64
    import hashlib

    verifier = "x" * 43
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    assert s256_challenge(verifier) == base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


async def test_exchange_proves_pkce_and_burns_codes_on_first_presentation() -> None:
    state, passwords = _world()
    provider = OAuthProviderService(state, _tokens(state, passwords))
    pair = provider.pkce_pair()
    assert len(pair.verifier) >= 43 and pair.code_challenge == s256_challenge(pair.verifier)

    code = await _authorize_row(provider, pair.code_challenge)
    wrong = TokenExchangeRequest(
        code=code,
        verifier="y" * 43,
        redirect_uri="https://client.example/callback",
    )
    with pytest.raises(AppError) as rejection:
        await provider.exchange(wrong)
    assert rejection.value.kind is FailureKind.UNAUTHORIZED
    # The failed attempt spent the code: even the RIGHT verifier fails now.
    right = TokenExchangeRequest(
        code=code,
        verifier=pair.verifier,
        redirect_uri="https://client.example/callback",
    )
    with pytest.raises(AppError):
        await provider.exchange(right)

    fresh = await _authorize_row(provider, pair.code_challenge)
    granted = await provider.exchange(
        TokenExchangeRequest(
            code=fresh,
            verifier=pair.verifier,
            redirect_uri="https://client.example/callback",
        )
    )
    assert granted.scope == "posts:read posts:write"


async def test_authorize_refuses_unknown_clients_redirects_and_plain() -> None:
    state, passwords = _world()
    provider = OAuthProviderService(state, _tokens(state, passwords))
    pair = provider.pkce_pair()
    for request in (
        AuthorizeRequest(
            client_id="evil-app",
            redirect_uri="https://client.example/callback",
            code_challenge=pair.code_challenge,
        ),
        AuthorizeRequest(
            client_id="guide-cli",
            redirect_uri="https://attacker.example/callback",
            code_challenge=pair.code_challenge,
        ),
    ):
        with pytest.raises(AppError) as rejection:
            await provider.authorize(request)
        assert rejection.value.kind is FailureKind.VALIDATION_FAILED


# ── Refresh families ─────────────────────────────────────────────────────────


async def test_rotation_chains_and_reuse_revokes_the_whole_family() -> None:
    state, passwords = _world()
    refresh = RefreshRotationService(state, state, passwords, _tokens(state, passwords))
    login = await refresh.login(RefreshLoginRequest(username="ada", password="analytical-engine"))
    assert login.family_id.startswith("fam_")

    first = await refresh.exchange(RefreshExchangeRequest(refresh_token=login.refresh_token))
    assert first.outcome == "rotated" and first.rotated_from_position == 1
    second = await refresh.exchange(RefreshExchangeRequest(refresh_token=first.refresh_token or ""))
    assert second.outcome == "rotated" and second.rotated_from_position == 2

    replay = await refresh.exchange(RefreshExchangeRequest(refresh_token=login.refresh_token))
    assert replay.outcome == "reuse-detected"
    assert replay.family_id == login.family_id
    assert replay.family_tokens_revoked == 3  # positions 1, 2, 3 — the whole chain

    with pytest.raises(AppError) as dead:  # the current token died with the family
        await refresh.exchange(RefreshExchangeRequest(refresh_token=second.refresh_token or ""))
    assert dead.value.kind is FailureKind.UNAUTHORIZED

    families = await refresh.families()
    assert families[0][0].status == "revoked"
    assert [token.status for _, tokens in families for token in tokens] == ["revoked"] * 3


async def test_unknown_refresh_tokens_are_invalid_not_reuse() -> None:
    state, passwords = _world()
    refresh = RefreshRotationService(state, state, passwords, _tokens(state, passwords))
    with pytest.raises(AppError) as rejection:
        await refresh.exchange(RefreshExchangeRequest(refresh_token="rt_never_issued"))
    assert rejection.value.kind is FailureKind.UNAUTHORIZED
    with pytest.raises(AppError):
        await refresh.login(RefreshLoginRequest(username="ada", password="wrong"))
    assert await refresh.families() == []


async def test_expired_refresh_lease_is_invalid_without_killing_families() -> None:
    """A token past its 24h lease fails as expired — but a FAMILY that never
    tripped reuse is not collateral damage (only its own token is dead)."""
    from guide.domain.auth.ports import (
        REFRESH_TTL_SECONDS,
        StoredRefreshFamily,
        StoredRefreshToken,
    )
    from guide.domain.auth.refresh_service import hash_refresh_token

    state, passwords = _world()
    refresh = RefreshRotationService(state, state, passwords, _tokens(state, passwords))
    stale_issued = (datetime.now(UTC) - timedelta(seconds=REFRESH_TTL_SECONDS + 60)).isoformat(
        timespec="milliseconds"
    )
    await state.start_family(
        StoredRefreshFamily(
            family_id="fam_old",
            username="ada",
            status="active",
            created_at=stale_issued,
        ),
        StoredRefreshToken(
            token_hash=hash_refresh_token("rt_aged"),
            family_id="fam_old",
            position=1,
            status="active",
            issued_at=stale_issued,
            used_at=None,
        ),
    )
    with pytest.raises(AppError) as rejection:
        await refresh.exchange(RefreshExchangeRequest(refresh_token="rt_aged"))
    assert rejection.value.kind is FailureKind.UNAUTHORIZED
    assert "lease" in rejection.value.message
    family, tokens = (await refresh.families())[0]
    assert family.status == "active"  # expiry is not theft; the family lives
