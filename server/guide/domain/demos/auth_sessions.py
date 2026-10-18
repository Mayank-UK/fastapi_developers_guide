"""The sessions demo payload: the cookie lab's roster, derived purely.

``GET /api/demo/auth/sessions`` serves this payload — topic 23's first
demo (``auth:sessions``), inline in the login-flow section. The panel
carries the cookie's whole contract (name, path, Max-Age, flags set vs
the Secure note) and the live session roster from the store, so every
sentence the payload makes can be checked against the store's state.
"""

from guide.core.serialization import CamelModel
from guide.domain.auth.ports import StoredSession


class SessionRosterEntry(CamelModel):
    """One live session as the roster shows it — preview, user, expiry."""

    session_id_preview: str
    username: str
    display_name: str
    issued_at: str
    expires_at: str


class SessionsPanelPayload(CamelModel):
    """Wire shape of ``GET /api/demo/auth/sessions`` — the cookie lab's state."""

    cookie_name: str
    cookie_path: str
    max_age_seconds: int
    flags_set: list[str]
    secure_note: str
    seal_note: str
    active_sessions: list[SessionRosterEntry]
    login_endpoint: str
    me_endpoint: str
    logout_endpoint: str
    reasoning: str


def build_sessions_panel_payload(
    sessions: list[StoredSession],
    *,
    cookie_name: str,
    cookie_path: str,
    max_age_seconds: int,
    flags_set: list[str],
    seal_note: str,
    login_endpoint: str,
    me_endpoint: str,
    logout_endpoint: str,
) -> SessionsPanelPayload:
    """Shape the roster (pure) — the reasoning derives from the live state."""
    roster = [
        SessionRosterEntry(
            session_id_preview=session.session_id[:8] + "…",
            username=session.username,
            display_name=session.display_name,
            issued_at=session.issued_at,
            expires_at=session.expires_at,
        )
        for session in sessions
    ]
    if roster:
        state_note = (
            f"{len(roster)} live session(s) server-side: login created the row, the "
            "cookie carries only its signed id, and logout DELETES the row — the "
            "next call with any copy of that cookie is a 401"
        )
    else:
        state_note = (
            "no live sessions — log in and watch the row appear: password verified "
            "against argon2, session id minted (256-bit), cookie sealed and returned"
        )
    reasoning = (
        f"The cookie contract, set for real on every login: name {cookie_name}, "
        f"path {cookie_path}, Max-Age {max_age_seconds}s, {', '.join(flags_set)} — "
        "Secure stays OFF only because this stack is plain http (production turns "
        "it on unconditionally). " + state_note + "."
    )
    return SessionsPanelPayload(
        cookie_name=cookie_name,
        cookie_path=cookie_path,
        max_age_seconds=max_age_seconds,
        flags_set=flags_set,
        secure_note=(
            "Secure is a production flag: it forbids the cookie on plain http, and "
            "the dev stack IS plain http — so the demo sets HttpOnly and SameSite=Lax "
            "for real and teaches Secure as the one flag that waits for TLS"
        ),
        seal_note=seal_note,
        active_sessions=roster,
        login_endpoint=login_endpoint,
        me_endpoint=me_endpoint,
        logout_endpoint=logout_endpoint,
        reasoning=reasoning,
    )
