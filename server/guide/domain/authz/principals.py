"""The principal resolver: authenticated identity → authorization principal.

Topic 23 established identity; this module is the one seam where that
identity gains its authorization HALVES. A verified Bearer token hands
over (username, scopes); the resolver adds the ROLES from the registry's
assignment map and the display name from the user directory when it has
one (alan and barbara own posts but have no login row — their display
name is simply the username, honestly). An API key hands over its
record; the resolver wraps it as a PROGRAM principal — no roles, the
scopes are the whole authority.

The resolver never verifies anything — credentials were checked by the
authentication engines before this runs. It only RESOLVES, and it fails
closed in the one way that matters here: a username with no assignment
gets an empty roles tuple, which the engine denies by default.
"""

from typing import Final

from guide.domain.auth.ports import ApiKeyCallRow, UserDirectory
from guide.domain.authz.model import Principal
from guide.domain.authz.roles import ROLE_ASSIGNMENTS

TOKEN_VIA: Final = (
    "Authorization: Bearer — verified statelessly against the signature; "
    "the claims carried the username and the scopes"
)
"""How a token-established principal arrived (teaching surface)."""

KEY_VIA: Final = "x-api-key — verified against the stored hash in constant time"
"""How a key-established principal arrived."""


class PrincipalResolver:
    """Builds ``Principal`` values from verified authentication outcomes."""

    def __init__(self, directory: UserDirectory) -> None:
        """Read display names from the directory topic 23 seeded."""
        self._directory = directory

    async def for_token(self, username: str, scopes: tuple[str, ...]) -> Principal:
        """A verified Bearer caller: roles from the registry, scopes from the claims."""
        user = await self._directory.find_user(username)
        role = ROLE_ASSIGNMENTS.get(username)
        return Principal(
            kind="user",
            name=username,
            display_name=user.display_name if user is not None else username,
            roles=(role,) if role is not None else (),
            scopes=scopes,
            via=TOKEN_VIA,
        )

    @staticmethod
    def for_key(record: ApiKeyCallRow) -> Principal:
        """A verified API-key caller: a program principal — scopes only, no roles."""
        return Principal(
            kind="program",
            name=record.prefix,
            display_name=f"api key {record.name!r}",
            roles=(),
            scopes=record.scopes,
            via=KEY_VIA,
        )
