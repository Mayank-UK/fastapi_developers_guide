"""The refresh demo payload: the family timelines, derived purely.

``GET /api/demo/auth/refresh`` serves this payload — topic 23's seventh
demo (``auth:refresh``), inline in the refresh-rotation section. The
panel carries every family's token timeline (position, status, stamps)
plus the service's telemetry counters, so the reuse proof — a family
flipping to revoked with its killed count — reads straight off rows the
store really holds.
"""

from guide.core.serialization import CamelModel
from guide.domain.auth.ports import StoredRefreshFamily, StoredRefreshToken


class RefreshTokenRow(CamelModel):
    """One link in a family's timeline — position, status, stamps."""

    position: int
    status: str
    issued_at: str
    used_at: str | None


class RefreshFamilyRow(CamelModel):
    """One family: its owner, its life status, its whole token chain."""

    family_id: str
    username: str
    status: str
    created_at: str
    tokens: list[RefreshTokenRow]


class RefreshTelemetryRow(CamelModel):
    """The engine's in-process counters, snapshot at panel time."""

    logins: int
    rotations: int
    reuse_events: int


class RefreshPanelPayload(CamelModel):
    """Wire shape of ``GET /api/demo/auth/refresh`` — the family board."""

    families: list[RefreshFamilyRow]
    telemetry: RefreshTelemetryRow
    pattern_note: str
    login_endpoint: str
    exchange_endpoint: str
    reasoning: str


def build_refresh_panel_payload(
    families: list[tuple[StoredRefreshFamily, list[StoredRefreshToken]]],
    *,
    logins: int,
    rotations: int,
    reuse_events: int,
    pattern_note: str,
    login_endpoint: str,
    exchange_endpoint: str,
) -> RefreshPanelPayload:
    """Shape the board (pure) — the timelines and the counters agree."""
    rows = [
        RefreshFamilyRow(
            family_id=family.family_id,
            username=family.username,
            status=family.status,
            created_at=family.created_at,
            tokens=[
                RefreshTokenRow(
                    position=token.position,
                    status=token.status,
                    issued_at=token.issued_at,
                    used_at=token.used_at,
                )
                for token in tokens
            ],
        )
        for family, tokens in families
    ]
    if rows:
        reuse_hint = (
            f" ({reuse_events} reuse event(s) already tripped — find the revoked "
            "family and its killed timeline below)" if reuse_events else ""
        )
        state_note = (
            f"{len(rows)} family(ies) on the board: log in to start one, exchange "
            "to rotate (the presented token flips to used, a new active link "
            "appears), then replay ANY used token and watch the whole chain flip "
            f"to revoked{reuse_hint}"
        )
    else:
        state_note = (
            "no families yet — log in: the response carries the FIRST refresh "
            "token raw (once), the store keeps only its SHA-256, and every "
            "exchange rotates to a fresh one-time successor"
        )
    reasoning = f"{pattern_note} {state_note}."
    return RefreshPanelPayload(
        families=rows,
        telemetry=RefreshTelemetryRow(
            logins=logins, rotations=rotations, reuse_events=reuse_events
        ),
        pattern_note=pattern_note,
        login_endpoint=login_endpoint,
        exchange_endpoint=exchange_endpoint,
        reasoning=reasoning,
    )
