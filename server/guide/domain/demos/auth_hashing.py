"""The hashing demo payload: argon2's contract, derived purely.

``GET /api/demo/auth/hashing`` serves this payload — topic 23's sixth
demo (``auth:hashing``), inline in the password-hashing section. The
panel carries the active hasher's cost parameters, the legacy cost the
rehash lesson uses, and the seeded credential hashes (previews — the
hashes belong to DEMO passwords and are teaching facts, but the display
stays a preview on principle).
"""

from guide.core.serialization import CamelModel
from guide.domain.auth.ports import DemoUser


class SeedCredentialRow(CamelModel):
    """One seeded user's credential facts — hash preview and scopes."""

    username: str
    display_name: str
    hash_preview: str
    scopes: tuple[str, ...]


class HashingPanelPayload(CamelModel):
    """Wire shape of ``GET /api/demo/auth/hashing`` — argon2's contract."""

    algorithm: str
    parameters: str
    legacy_parameters: str
    seed_credentials: list[SeedCredentialRow]
    distinction_note: str
    logging_note: str
    hash_endpoint: str
    verify_endpoint: str
    reasoning: str


def build_hashing_panel_payload(
    seed_users: list[DemoUser],
    *,
    algorithm: str,
    parameters: str,
    legacy_parameters: str,
    distinction_note: str,
    logging_note: str,
    hash_endpoint: str,
    verify_endpoint: str,
) -> HashingPanelPayload:
    """Shape the contract (pure) — cost, legacy cost, and the seed."""
    seeds = [
        SeedCredentialRow(
            username=user.username,
            display_name=user.display_name,
            hash_preview=user.password_hash[:32] + "…",
            scopes=user.scopes,
        )
        for user in seed_users
    ]
    reasoning = (
        f"The active cost is {parameters} — roughly a tenth of a second per "
        "verification on this machine, which a user logs in through once and an "
        "attacker must pay PER GUESS. The same password verified against "
        f"{legacy_parameters} passes today and fires needs_rehash — parameters are "
        "stamped INSIDE every argon2 hash, so upgrading cost never breaks old "
        "credentials: verify with what is stamped, rehash when it is behind. Hash "
        "any password and watch the string differ every time (fresh salt); verify "
        "right and wrong and watch both burn the same milliseconds."
    )
    return HashingPanelPayload(
        algorithm=algorithm,
        parameters=parameters,
        legacy_parameters=legacy_parameters,
        seed_credentials=seeds,
        distinction_note=distinction_note,
        logging_note=logging_note,
        hash_endpoint=hash_endpoint,
        verify_endpoint=verify_endpoint,
        reasoning=reasoning,
    )
