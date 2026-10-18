"""The ORM-probe demo payloads: measured, not asserted.

``GET /api/demo/db/orm-probe`` serves these payloads — topic 18's
single demo, inline in the section that teaches relationship loading.
One request runs the canonical access pattern (load N posts, touch each
post's author and comments) under all three load strategies with the
engine-level recorder attached, then proves the session's two quiet
superpowers: the identity map (two ``get`` calls, ONE SELECT, one
object) and dirty checking (one mutated field → flush emits exactly one
UPDATE, then rolled back). The builder below is PURE — it shapes the
adapter's proofs and derives every verdict sentence from the measured
counts, so the payload can never drift from what actually ran.
"""

from guide.core.serialization import CamelModel
from guide.domain.db.ports import (
    DirtyCheckProof,
    IdentityMapProof,
    LoadingProbe,
    StrategyRow,
)


class StrategyCard(CamelModel):
    """One strategy's measured run, display-shaped."""

    strategy: str
    sql_count: int
    statements: list[str]
    elapsed_ms: float
    author_count: int
    comment_total: int


class OrmProbePayload(CamelModel):
    """Wire shape of ``GET /api/demo/db/orm-probe``."""

    post_count: int
    first_post_title: str
    strategies: list[StrategyCard]
    results_match: bool
    identity_map: IdentityMapProof
    dirty_check: DirtyCheckProof
    reasoning: str


def _card(row: StrategyRow) -> StrategyCard:
    """Compress one strategy row for display (full statements kept)."""
    return StrategyCard(
        strategy=row.strategy,
        sql_count=row.sql_count,
        statements=row.statements,
        elapsed_ms=row.elapsed_ms,
        author_count=len(row.authors),
        comment_total=row.comment_total,
    )


def build_orm_probe_payload(
    loading: LoadingProbe,
    identity_map: IdentityMapProof,
    dirty_check: DirtyCheckProof,
) -> OrmProbePayload:
    """Shape the strategy comparison + both session proofs (pure)."""
    counts = {row.strategy: row.sql_count for row in loading.strategies}
    lazy, joined, selectin = counts["lazy"], counts["joinedload"], counts["selectinload"]
    n_plus_one = lazy - 1
    reasoning = (
        f"The same access pattern — {loading.post_count} posts, touch each "
        f"post's author and comments — cost {lazy} statements under lazy "
        f"loading (1 for the posts, {n_plus_one} emitted while touching: "
        f"per-relationship SELECTs, the N+1 shape), {selectin} under "
        f"selectinload (one SELECT per table with IN batches), and "
        f"{joined} under joinedload (one SELECT, everything joined). All "
        f"three returned the same authors and comments: {str(loading.results_match).lower()}. "
        "The identity-map proof ran two gets for one id and the engine "
        f"emitted {identity_map.select_count} SELECT — the second get is "
        "answered from the session. The dirty-check proof changed one "
        f"field ({dirty_check.field}: {dirty_check.before} -> "
        f"{dirty_check.after}) and flush emitted exactly "
        f"{dirty_check.update_count} UPDATE — then rolled back, so this "
        "demo repeats identically."
    )
    return OrmProbePayload(
        post_count=loading.post_count,
        first_post_title=loading.first_post_title,
        strategies=[_card(row) for row in loading.strategies],
        results_match=loading.results_match,
        identity_map=identity_map,
        dirty_check=dirty_check,
        reasoning=reasoning,
    )
