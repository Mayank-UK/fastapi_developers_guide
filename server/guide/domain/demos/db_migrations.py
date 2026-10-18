"""Migration-rehearsal demo payloads: atomicity, proven not claimed.

``GET /api/demo/db/migrations`` serves these payloads — topic 17's
transactions demo. The adapter runs a scratch migration sequence inside
ONE transaction where a middle step FAILS: PostgreSQL — alone among the
common databases in taking DDL transactionally — rolls the whole thing
back, CREATE TABLE and INSERT included, and the verification read proves
the table never happened. The second run applies the FIXED sequence and
commits. This pure builder shapes the two runs into the side-by-side
story and writes the honesty notes (what the demo cleans up so it can
repeat).
"""

from guide.core.serialization import CamelModel
from guide.domain.db.ports import MigrationRunRow


class MigrationsPayload(CamelModel):
    """Wire shape of ``GET /api/demo/db/migrations``."""

    scratch_table: str
    failing: MigrationRunRow
    succeeding: MigrationRunRow
    cleanup_note: str
    reasoning: str


def build_migrations_payload(
    scratch_table: str, failing: MigrationRunRow, succeeding: MigrationRunRow
) -> MigrationsPayload:
    """Shape the rollback-vs-commit story (pure)."""
    applied_before_failure = sum(1 for step in failing.steps if step.outcome == "applied")
    return MigrationsPayload(
        scratch_table=scratch_table,
        failing=failing,
        succeeding=succeeding,
        cleanup_note=(
            f"After the proof, the demo drops {scratch_table} again "
            "(committed) so the next request can rehearse from zero — "
            "the payload above already recorded both verifications."
        ),
        reasoning=(
            f"The failing run applied {applied_before_failure} step(s), "
            f"then PostgreSQL refused step {applied_before_failure + 1} "
            "— and the ROLLBACK took the earlier steps with it: the "
            "verification read finds no table, no row, nothing. The "
            "succeeding run adds the column WITH a default, backfills "
            f"it, and commits — {succeeding.row_count_after} row(s) "
            "survive in the table the verification can finally see. "
            "That is transactional DDL: a migration either fully applies "
            "or leaves no trace, which is exactly what makes 'migrations "
            "run at app startup' a safe strategy."
        ),
    )
