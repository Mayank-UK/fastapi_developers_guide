"""SQL-lab demo payloads: CTEs and windows, run for real over the seed.

``GET /api/demo/db/sql-lab?exhibit=`` serves these payloads — topic 17's
hand-written SQL demo. The adapter executes the chosen exhibit against
the seeded posts/comments; this pure builder adds the catalog (what each
exhibit teaches) and the reading guide for its rows. Three exhibits:

- ``ranked`` — a CTE computing per-post comment counts, then TWO windows
  over it: ROW_NUMBER per author (their posts numbered oldest-first) and
  a global RANK by comment count.
- ``window`` — a running total and running average of comments across
  the whole timeline, one pass, no self-join.
- ``thread`` — a recursive CTE walking one post's comment thread link by
  link (anchor = first comment; each step joins LATERAL to the NEXT
  comment by id), depth counting as it goes.
"""

from guide.core.serialization import CamelModel
from guide.domain.db.ports import LabQueryResult


class ExhibitCard(CamelModel):
    """One lab exhibit as the picker lists it."""

    id: str
    name: str
    teaches: str


EXHIBITS: tuple[ExhibitCard, ...] = (
    ExhibitCard(
        id="ranked",
        name="CTE + ranking windows",
        teaches="ROW_NUMBER OVER (PARTITION BY author …) numbers each "
        "author's posts oldest-first; RANK orders everyone by comment "
        "count with ties sharing a rank.",
    ),
    ExhibitCard(
        id="window",
        name="Running totals",
        teaches="SUM(COUNT(…)) OVER (ORDER BY … ROWS BETWEEN UNBOUNDED "
        "PRECEDING AND CURRENT ROW) accumulates as it scans — a running "
        "total and average in one pass.",
    ),
    ExhibitCard(
        id="thread",
        name="Recursive CTE",
        teaches="WITH RECURSIVE walks the thread one comment at a time: "
        "an anchor row, then a UNION ALL step that always finds the NEXT "
        "comment, depth incrementing per hop.",
    ),
)

_READINGS: dict[str, str] = {
    "ranked": (
        "Read nth_post within one author: 1 is their oldest post. "
        "by_comments is global — rank 1 is the most-commented post in "
        "the table, and ties share a rank (RANK, not ROW_NUMBER)."
    ),
    "window": (
        "Each row carries the timeline so far: running_comments is the "
        "total of every comment on posts up to and including this one; "
        "avg_comments_so_far is that same window's mean. The last row's "
        "running_comments equals the whole table's comment count."
    ),
    "thread": (
        "depth is the recursion's step counter: 1 is the anchor (the "
        "thread's first comment by id), and each following row was found "
        "by the recursive term joining LATERAL to the next id. The walk "
        "ends when there is no next comment — the anchor plus N-1 hops "
        "equals N rows."
    ),
}


class SqlLabPayload(CamelModel):
    """Wire shape of ``GET /api/demo/db/sql-lab``."""

    exhibit: str
    exhibits: list[ExhibitCard]
    sql: str
    columns: list[str]
    rows: list[dict[str, str]]
    row_count: int
    reading: str
    reasoning: str


def build_sql_lab_payload(result: LabQueryResult) -> SqlLabPayload:
    """Shape one exhibit's answer with its catalog and reading (pure)."""
    return SqlLabPayload(
        exhibit=result.exhibit,
        exhibits=list(EXHIBITS),
        sql=result.sql,
        columns=result.columns,
        rows=result.rows,
        row_count=len(result.rows),
        reading=_READINGS.get(result.exhibit, "Run the exhibit to read its rows."),
        reasoning=(
            f"This really ran against the live PostgreSQL: "
            f"{len(result.rows)} row(s) from one statement — no ORM, no "
            "Python-side loops. The SQL above is the exhibit's verbatim "
            "text (bind parameters included); switch exhibits to watch "
            "the same seeded data answer different shapes of question."
        ),
    )
