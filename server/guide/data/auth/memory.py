"""InMemoryAuthState: every auth store port on plain dictionaries.

One adapter satisfies all five Protocols (``UserDirectory``,
``SessionStore``, ``ApiKeyStore``, ``AuthorizationCodeStore``,
``RefreshStore``), exactly as ``RedisStreams`` satisfied three messaging
ports — the stores are small, per-app, and intentionally unpersisted
(the posts-substrate discipline: no new tables, honest in-memory state
that dies with the process). The seed is two demo users whose argon2
credential hashes were minted ONCE with the production hasher and
checked in as constants: same algorithm, same cost, zero hashing at
startup, and the raw passwords exist only in this docstring and the
topic's prose (they are demo facts, not secrets — production users'
passwords are never stored anywhere the server can read).

The demo password facts: ``ada`` / ``analytical-engine``, ``grace`` /
``nanosecond``. The hashes verify against them with the default
parameters (needs_rehash False); ``LEGACY_HASH`` in the password
service is the same password at 2015-era cost for the rehash lesson.
"""

from datetime import UTC, datetime

from guide.domain.auth.ports import (
    DemoUser,
    StoredApiKey,
    StoredAuthorizationCode,
    StoredRefreshFamily,
    StoredRefreshToken,
    StoredSession,
)

SEED_USERS: tuple[DemoUser, ...] = (
    DemoUser(
        username="ada",
        display_name="Ada Lovelace",
        password_hash=(
            "$argon2id$v=19$m=65536,t=3,p=4$kwLrdfcyKf0Y8QktrIxRbA$"
            "Pssupwpn9hPxowGvjwaEsQziYSncU6K7FAC2Ihmkzng"
        ),
        scopes=("posts:read", "posts:write"),
    ),
    DemoUser(
        username="grace",
        display_name="Grace Hopper",
        password_hash=(
            "$argon2id$v=19$m=65536,t=3,p=4$cf/5S6AAozJvS61sqdHfRA$"
            "JL4olu7EPjL7f9iPTutdUgd3yHDsJFa2nihngiJlVWY"
        ),
        scopes=("posts:read",),
    ),
)
"""Two deterministic users, pre-hashed — the credential substrate's seed."""


class InMemoryAuthState:
    """Users, sessions, keys, codes, families — one honest in-memory world.

    Implements the five store Protocols without inheriting from any
    (structural typing is the point); every mutation is a replace, every
    read a snapshot, and per-app construction gives every test its own
    world. Sessions honor their expiry on lookup (the janitor delete is
    the session service's clock story told once more, adapter-side).
    """

    def __init__(self, seed: bool = True) -> None:
        self._users: dict[str, DemoUser] = (
            {user.username: user for user in SEED_USERS} if seed else {}
        )
        self._sessions: dict[str, StoredSession] = {}
        self._api_keys: dict[str, StoredApiKey] = {}
        self._codes: dict[str, StoredAuthorizationCode] = {}
        self._families: dict[str, StoredRefreshFamily] = {}
        self._refresh_tokens: dict[str, StoredRefreshToken] = {}

    # ── UserDirectory ───────────────────────────────────────────────────

    async def find_user(self, username: str) -> DemoUser | None:
        """The seeded user, or None — the credential lookup half."""
        return self._users.get(username)

    async def list_users(self) -> list[DemoUser]:
        """The seeded roster — the hashing panel's credential facts."""
        return sorted(self._users.values(), key=lambda user: user.username)

    # ── SessionStore ────────────────────────────────────────────────────

    async def create_session(self, session: StoredSession) -> None:
        self._sessions[session.session_id] = session

    async def find_session(self, session_id: str) -> StoredSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if datetime.now(UTC) >= datetime.fromisoformat(session.expires_at):
            del self._sessions[session_id]
            return None
        return session

    async def revoke_session(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    async def list_sessions(self) -> list[StoredSession]:
        return sorted(self._sessions.values(), key=lambda row: row.issued_at)

    # ── ApiKeyStore ─────────────────────────────────────────────────────

    async def save_key(self, record: StoredApiKey) -> None:
        self._api_keys[record.prefix] = record

    async def find_key_by_prefix(self, prefix: str) -> StoredApiKey | None:
        return self._api_keys.get(prefix)

    async def revoke_key(self, prefix: str) -> bool:
        return self._api_keys.pop(prefix, None) is not None

    async def list_keys(self) -> list[StoredApiKey]:
        return sorted(self._api_keys.values(), key=lambda row: row.created_at)

    # ── AuthorizationCodeStore ──────────────────────────────────────────

    async def issue_code(self, code: StoredAuthorizationCode) -> None:
        self._codes[code.code_hash] = code

    async def take_code(self, code_hash: str) -> StoredAuthorizationCode | None:
        """Consume: the code leaves the shelf on first ask, result or not."""
        return self._codes.pop(code_hash, None)

    # ── RefreshStore ────────────────────────────────────────────────────

    async def start_family(
        self, family: StoredRefreshFamily, token: StoredRefreshToken
    ) -> None:
        self._families[family.family_id] = family
        self._refresh_tokens[token.token_hash] = token

    async def find_token(self, token_hash: str) -> StoredRefreshToken | None:
        return self._refresh_tokens.get(token_hash)

    async def find_family(self, family_id: str) -> StoredRefreshFamily | None:
        return self._families.get(family_id)

    async def add_token(self, token: StoredRefreshToken) -> None:
        self._refresh_tokens[token.token_hash] = token

    async def mark_used(self, token_hash: str, used_at: str) -> None:
        current = self._refresh_tokens.get(token_hash)
        if current is not None:
            self._refresh_tokens[token_hash] = current.model_copy(
                update={"status": "used", "used_at": used_at}
            )

    async def revoke_family(self, family_id: str) -> int:
        """The whole family dies as a unit — the reuse response, store-side."""
        current = self._families.get(family_id)
        if current is None:
            return 0
        self._families[family_id] = current.model_copy(update={"status": "revoked"})
        killed = 0
        for token_hash, token in self._refresh_tokens.items():
            if token.family_id == family_id and token.status != "revoked":
                self._refresh_tokens[token_hash] = token.model_copy(
                    update={"status": "revoked"}
                )
                killed += 1
        return killed

    async def list_families(self) -> list[tuple[StoredRefreshFamily, list[StoredRefreshToken]]]:
        roster: list[tuple[StoredRefreshFamily, list[StoredRefreshToken]]] = []
        for family in sorted(self._families.values(), key=lambda row: row.created_at):
            tokens = [
                token
                for token in sorted(
                    self._refresh_tokens.values(), key=lambda row: row.position
                )
                if token.family_id == family.family_id
            ]
            roster.append((family, tokens))
        return roster
