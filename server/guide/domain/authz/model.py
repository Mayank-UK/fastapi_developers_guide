"""The authorization vocabulary: principals, owned resources, verdicts.

Topic 24's whole subject in three small frozen models. ``Principal`` is
what authentication HANDS authorization — identity (``name``), the roles
assigned to it, and the scopes the credential carries (topic 23 minted
both halves; this domain only reads them). ``OwnedResource`` is the
object a verdict may depend on: a kind, an id, and the owner — the
smallest shape that can express "can edit THIS post". ``Decision`` is
the verdict: one boolean and one REASON, because the reason strings are
teaching surface — the demo panel shows them and the 403 envelope
carries them, so a denial always says what it would have taken.
"""

from typing import Literal

from guide.core.serialization import CamelModel

PrincipalKind = Literal["user", "program"]
"""Who the principal is: a logged-in user, or a program credential (API key)."""

ResourceKind = Literal["post", "comment"]
"""The two resource kinds the demo substrate guards — both owned objects."""

GrantLevel = Literal["any", "own"]
"""A grant's reach: any object of the kind, or only the principal's own."""


class Principal(CamelModel):
    """The caller as authorization sees them — identity plus authority halves.

    ``kind`` "user" principals carry ROLES (the registry's half) narrowed
    by the credential's ``scopes`` (the token's half); ``kind`` "program"
    principals (API keys) carry no roles at all — their scopes ARE their
    authority. ``via`` records which credential established the
    principal, purely so responses can teach how the identity arrived.
    """

    kind: PrincipalKind
    name: str
    display_name: str
    roles: tuple[str, ...]
    scopes: tuple[str, ...]
    via: str


class OwnedResource(CamelModel):
    """The object a verdict may depend on: kind, id, owner.

    ``owner`` is the posts-substrate author (or comment author) — the
    string the ownership rules compare against the principal's name.
    """

    kind: ResourceKind
    id: str
    owner: str


class Decision(CamelModel):
    """One verdict: allowed or not, and the human reason why.

    The reason is client-safe by construction — it names roles, scopes,
    and owners, never secrets or internals — because it rides the 403
    envelope's details and the demo panel alike.
    """

    allowed: bool
    reason: str
