"""The session engine: login → signed cookie → server-side session → logout.

``SessionService`` is the server-side session pattern whole: the login
verifies credentials through the ``PasswordService`` (timing-uniform for
unknown users), mints a random session id, records the session row in
the ``SessionStore``, and answers the cookie the browser will carry —
the VALUE is the session id signed with itsdangerous (the same signing
family Starlette's ``SessionMiddleware`` uses), so a forged or edited
cookie fails the signature check before it ever reaches the store. The
flags the cookie carries are the section's teaching: ``HttpOnly`` keeps
the value away from page JavaScript, ``SameSite=Lax`` stops the cookie
riding cross-site posts, and ``Secure`` is deliberately OFF in dev (the
local stack is plain http) — production turns it on, unconditionally.

Logout is invalidation made visible: the server row is DELETED (not
flagged — gone), so even a stolen pre-logout cookie value is dead the
moment logout lands; the clear instruction then expires the browser's
copy. ``inspect`` is the /me path: bad signature, unknown id, expired
row — every failure is just "not authenticated", with no detail about
which half failed.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Final

import structlog
from itsdangerous import BadSignature, URLSafeSerializer

from guide.core.errors import AppError, FailureKind
from guide.domain.auth.password_service import PasswordService
from guide.domain.auth.ports import (
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_PATH,
    SESSION_MAX_AGE_SECONDS,
    CookieInstruction,
    LoginRequest,
    SessionInspectionRow,
    SessionLoginRow,
    SessionLogoutRow,
    SessionStore,
    StoredSession,
    UserDirectory,
)

logger = structlog.get_logger()

SESSION_ID_BYTES: Final = 32
"""The session id's entropy: 32 bytes → 256 bits of unguessable handle."""

INVALID_CREDENTIALS_MESSAGE: Final = (
    "invalid credentials — username and password are checked as one"
)
"""One 401 for every credential failure; no half is ever named."""

SIGNED_COOKIE_NOTE: Final = (
    "the cookie carries the session id SEALED with itsdangerous — the same "
    "signing family Starlette's SessionMiddleware uses — so the browser "
    "holds an opaque, tamper-evident handle and the session facts stay "
    "server-side"
)
"""The signed-cookie semantics, stated where the suite can pin it."""


def _utcnow() -> datetime:
    """One clock seam — tests inject determinism by monkeypatching time."""
    return datetime.now(UTC)


def _clear_instruction() -> CookieInstruction:
    """The logout cookie: same name and flags, empty value, Max-Age 0."""
    return CookieInstruction(
        name=SESSION_COOKIE_NAME,
        value="",
        max_age_seconds=0,
        path=SESSION_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=False,
    )


class SessionService:
    """Login, inspect, logout — the cookie lifecycle over the store."""

    def __init__(
        self,
        directory: UserDirectory,
        store: SessionStore,
        passwords: PasswordService,
        session_secret: str,
    ) -> None:
        self._directory = directory
        self._store = store
        self._passwords = passwords
        self._seal = URLSafeSerializer(session_secret, salt="fdg.sessions")

    def _seal_session_id(self, session_id: str) -> str:
        """Sign the id: the cookie value becomes ``id.signature``."""
        return str(self._seal.dumps(session_id))

    def _open_session_id(self, cookie_value: str) -> str | None:
        """Verify the signature and answer the id — None on ANY tamper."""
        try:
            opened = self._seal.loads(cookie_value)
        except BadSignature:
            return None
        return opened if isinstance(opened, str) else None

    async def login(self, request: LoginRequest, *, now: datetime | None = None) -> SessionLoginRow:
        """Verify credentials, create the server session, answer the cookie.

        An unknown username burns a decoy argon2 run first (``verify_uniform``)
        so its rejection costs the same as a wrong password — the 401 is
        indistinguishable, by timing or by message.
        """
        moment = now or _utcnow()
        user = await self._directory.find_user(request.username)
        if user is None:
            self._passwords.verify_uniform(None, request.password)
            logger.info("session_login_rejected", username=request.username)
            raise AppError(FailureKind.UNAUTHORIZED, INVALID_CREDENTIALS_MESSAGE)
        if not self._passwords.verify_uniform(user.password_hash, request.password):
            logger.info("session_login_rejected", username=request.username)
            raise AppError(FailureKind.UNAUTHORIZED, INVALID_CREDENTIALS_MESSAGE)

        session_id = secrets.token_urlsafe(SESSION_ID_BYTES)
        issued_at = moment.isoformat(timespec="milliseconds")
        expires_at = (moment + timedelta(seconds=SESSION_MAX_AGE_SECONDS)).isoformat(
            timespec="milliseconds"
        )
        await self._store.create_session(
            StoredSession(
                session_id=session_id,
                username=user.username,
                display_name=user.display_name,
                scopes=user.scopes,
                issued_at=issued_at,
                expires_at=expires_at,
            )
        )
        sealed = self._seal_session_id(session_id)
        cookie = CookieInstruction(
            name=SESSION_COOKIE_NAME,
            value=sealed,
            max_age_seconds=SESSION_MAX_AGE_SECONDS,
            path=SESSION_COOKIE_PATH,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        logger.info("session_login_ok", username=user.username)
        preview = session_id[:8] + "…"
        return SessionLoginRow(
            username=user.username,
            display_name=user.display_name,
            scopes=user.scopes,
            cookie=cookie,
            cookie_value_anatomy=(
                f"{sealed.split('.')[0]}… . <{len(sealed) - len(sealed.split('.')[0]) - 1} "
                "signature chars> — the session id (opaque) sealed with a "
                "signature; edit one character and the seal is broken"
            ),
            detail=(
                f"logged in as {user.display_name}: password verified against the "
                f"stored argon2 hash, session {preview} recorded server-side, and "
                "the cookie carries only the SIGNED id — HttpOnly and SameSite=Lax "
                "set for real, Secure waits for https in production"
            ),
        )

    async def inspect(self, cookie_value: str | None) -> SessionInspectionRow:
        """The /me answer for a presented cookie — or the 401 envelope.

        Every failure mode (missing cookie, bad signature, unknown id,
        expired row) is one indistinguishable unauthorized: the response
        teaches the caller nothing about which half failed.
        """
        session = await self._resolve(cookie_value)
        if session is None:
            raise AppError(FailureKind.UNAUTHORIZED, "not authenticated — no valid session")
        return SessionInspectionRow(
            session_id_preview=session.session_id[:8] + "…",
            username=session.username,
            display_name=session.display_name,
            scopes=session.scopes,
            issued_at=session.issued_at,
            expires_at=session.expires_at,
            detail=(
                f"the cookie's signature verified, session {session.session_id[:8]}… "
                f"resolved server-side for {session.display_name} — the browser "
                "holds only the sealed handle, everything above lives in the "
                "store and dies with the session"
            ),
        )

    async def logout(self, cookie_value: str | None) -> SessionLogoutRow:
        """Revoke the server session, then clear the browser's cookie.

        Revocation is deletion: the row leaves the store, so the cookie
        value — original or stolen copy — resolves to nothing afterwards.
        Idempotent by design: logging out twice is not an error.
        """
        revoked = False
        session = await self._resolve(cookie_value)
        if session is not None:
            revoked = await self._store.revoke_session(session.session_id)
        logger.info("session_logout", revoked=revoked)
        return SessionLogoutRow(
            revoked=revoked,
            cookie=_clear_instruction(),
            detail=(
                "session deleted server-side and the cookie expired with Max-Age 0 — "
                "the value (or any copy of it) is dead: invalidation is a store "
                "delete, not a browser promise"
                if revoked
                else "no live session behind this cookie — logout is idempotent, "
                "and the cookie is cleared anyway"
            ),
        )

    async def _resolve(self, cookie_value: str | None) -> StoredSession | None:
        """Cookie value → live session row, or None on any failure."""
        if not cookie_value:
            return None
        session_id = self._open_session_id(cookie_value)
        if session_id is None:
            return None
        session = await self._store.find_session(session_id)
        if session is None:
            return None
        if _utcnow() >= datetime.fromisoformat(session.expires_at):
            await self._store.revoke_session(session.session_id)
            return None
        return session
