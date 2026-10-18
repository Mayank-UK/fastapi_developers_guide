"""The audit-in-transaction demo payloads: proof, not claim.

``GET /api/demo/db/audit`` serves these payloads — topic 17's audit
demo, reusing topic 16's in-transaction audit writer verbatim. One
request runs BOTH halves: a committed change (post status flip) whose
audit row is read back from the table, and a rolled-back change (an
update that trips the title CHECK after the audit INSERT) that leaves
NO row — counted before and after, so the zero is a measurement. The
post's full audit history rides along: it grows by one row per run,
which is precisely what an audit log is for.
"""

from guide.core.serialization import CamelModel
from guide.domain.db.ports import AuditEventRow, AuditProof, CommittedChangeRow

ATTEMPTED_TITLE_DISPLAY_LIMIT = 60


class RolledBackCard(CamelModel):
    """The rolled-back half, display-truncated: nothing survived."""

    attempted_title: str
    failure: str
    change_visible: bool
    audit_rows_added: int


class AuditPayload(CamelModel):
    """Wire shape of ``GET /api/demo/db/audit``."""

    post_id: int
    post_title: str
    committed: CommittedChangeRow
    rolled_back: RolledBackCard
    history: list[AuditEventRow]
    history_count: int
    reasoning: str


def truncate_for_display(title: str, limit: int = ATTEMPTED_TITLE_DISPLAY_LIMIT) -> str:
    """Show the attempted title's shape without dumping 200 characters."""
    if len(title) <= limit:
        return title
    return f"{title[:limit]}… ({len(title)} characters)"


def build_audit_payload(proof: AuditProof) -> AuditPayload:
    """Shape the two-half proof with the growing history (pure)."""
    committed_ok = proof.committed.change_visible and proof.rolled_back.audit_rows_after == 0
    verdict = (
        "The audit row exists exactly when its change exists — atomicity measured, not asserted."
        if committed_ok
        else "Something in the proof did not hold — inspect both halves."
    )
    return AuditPayload(
        post_id=proof.post_id,
        post_title=proof.post_title,
        committed=proof.committed,
        rolled_back=RolledBackCard(
            attempted_title=truncate_for_display(proof.rolled_back.attempted_title),
            failure=proof.rolled_back.failure,
            change_visible=proof.rolled_back.change_visible,
            audit_rows_added=proof.rolled_back.audit_rows_after,
        ),
        history=proof.history,
        history_count=len(proof.history),
        reasoning=(
            f"The committed half flipped {proof.post_title!r} "
            f"{proof.committed.status_before} -> "
            f"{proof.committed.status_after} and its audit row is read "
            "back from audit_log (same transaction, same commit). The "
            "rolled-back half wrote an audit row FIRST, then tripped "
            "the title CHECK the same transaction — and the count after "
            "is the proof: "
            f"{proof.rolled_back.audit_rows_after} audit row(s) added, "
            f"change visible: {str(proof.rolled_back.change_visible).lower()}. "
            f"{verdict} The history below grows by one row per run — "
            "every run of this demo is itself audited."
        ),
    )
