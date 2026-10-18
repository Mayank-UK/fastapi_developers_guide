"""Full-text search demo payloads: tsvector ranking with both plans.

``GET /api/demo/db/search?q=`` serves these payloads — topic 17's FTS
demo. The adapter runs the ranked query over the 0002 generated
tsvector column for real (plainto_tsquery keeps the caller's input
SAFE — it is a bind parameter AND a parsed query type), captures the
GIN-indexed plan and the no-index plan via EXPLAIN ANALYZE, and this
pure builder shapes the verdict: stems, ranks, and the honest note
about how each plan was obtained.
"""

from guide.core.serialization import CamelModel
from guide.domain.db.ports import SearchMatchRow, SearchProbe


class SearchPayload(CamelModel):
    """Wire shape of ``GET /api/demo/db/search``."""

    query: str
    parsed_query: str
    sql: str
    match_count: int
    matches: list[SearchMatchRow]
    indexed_plan: list[str]
    naive_plan: list[str]
    plan_note: str
    reasoning: str


def build_search_payload(probe: SearchProbe, query: str) -> SearchPayload:
    """Shape the ranked answer with the two-plan story (pure)."""
    top = probe.matches[0] if probe.matches else None
    top_line = (
        f"the strongest hit is {top.title!r} at rank {top.rank:.4f}"
        if top is not None
        else "no post matches — the tsvector column simply has no such terms"
    )
    return SearchPayload(
        query=query,
        parsed_query=probe.parsed_query,
        sql=probe.sql,
        match_count=len(probe.matches),
        matches=probe.matches,
        indexed_plan=probe.indexed_plan,
        naive_plan=probe.naive_plan,
        plan_note=(
            "Honesty about the plans: at 12 rows the planner prefers a "
            "seq scan for BOTH shapes, so the indexed plan was captured "
            "with SET LOCAL enable_seqscan = off inside one throwaway "
            "transaction — it shows the Bitmap Index Scan the GIN index "
            "offers, which the planner picks on its own once the table "
            "is real-sized. The naive plan is the untouched default: a "
            "seq scan that recomputes to_tsvector for EVERY row."
        ),
        reasoning=(
            f"plainto_tsquery('english', …) parsed the input into "
            f"{probe.parsed_query!r} — AND-ed, stemmed lexemes ('errors' "
            "and 'envelope' both fold to their stems), never raw "
            f"substrings. {len(probe.matches)} post(s) matched and "
            f"ts_rank ordered them: {top_line}. The @@ match is what "
            "the GIN index answers; ts_rank and ts_headline then run "
            "only on the matching rows."
        ),
    )
