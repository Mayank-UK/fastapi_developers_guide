"""SQL-safety demo payloads: one filter, two ways to build the query.

``GET /api/demo/db/sql-safety`` serves these payloads — topic 17's first
demo. The adapter (``guide.data.db.repository``) EXECUTES the
parameterized filter for real, whatever the caller's text contains; this
pure builder renders the string-interpolated statement the naive code
WOULD have produced — shown and explained, never executed. The contrast
is the whole lesson: with bind parameters the caller's quotes and
semicolons arrive as DATA (a filter that matches nothing), while the
interpolated text has already stopped being one query.

The builder is PURE — it shapes the adapter's ``FilterProbe`` and the
caller's filter value; it runs nothing.
"""

from guide.core.serialization import CamelModel
from guide.domain.db.ports import FilterProbe, PostBriefRow

UNSAFE_TEMPLATE = (
    "SELECT id, slug, title, status FROM posts WHERE title ILIKE '%{value}%' ORDER BY id"
)
"""The naive twin of the repository's filter: same query, but the value
is INTERPOLATED into the text instead of bound — the line that must
never ship."""


class SafeQueryCard(CamelModel):
    """The executed parameterized query: SQL, bind value, real rows."""

    sql: str
    parameter_name: str
    parameter_value: str
    row_count: int
    rows: list[PostBriefRow]
    note: str


class UnsafeQueryCard(CamelModel):
    """The interpolated query as text — rendered, explained, NOT executed."""

    template: str
    rendered_sql: str
    executed: bool
    why: str


class SqlSafetyPayload(CamelModel):
    """Wire shape of ``GET /api/demo/db/sql-safety``."""

    filter_value: str
    safe: SafeQueryCard
    unsafe: UnsafeQueryCard
    wildcard_note: str
    reasoning: str


def render_unsafe_sql(template: str, filter_value: str) -> str:
    """The statement string interpolation would produce — pure text.

    This is exactly what ``f"... ILIKE '%{value}%'"`` builds; nothing
    here ever reaches a database connection.
    """
    return template.format(value=filter_value)


def build_sql_safety_payload(probe: FilterProbe, filter_value: str) -> SqlSafetyPayload:
    """Shape the two-way contrast (pure): executed safety vs rendered danger."""
    rendered = render_unsafe_sql(UNSAFE_TEMPLATE, filter_value)
    looks_hostile = any(mark in filter_value for mark in ("'", ";", "--"))
    hostile_why = (
        "Rendered, never executed. Interpolation splices the value into "
        "the statement BEFORE parsing: a quote closes the string literal "
        "early, whatever follows becomes SQL — here a second statement, "
        "then a comment marker eating the rest of the line. That is the "
        "classic injection shape, on screen as text only."
    )
    tame_why = (
        "Rendered, never executed. This value looks harmless, but the "
        "METHOD is the vulnerability: whether the splice breaks the "
        "statement depends on the caller's input, never on your code — "
        "the next request may not be so polite."
    )
    return SqlSafetyPayload(
        filter_value=filter_value,
        safe=SafeQueryCard(
            sql=probe.sql,
            parameter_name=probe.parameter_name,
            parameter_value=probe.parameter_value,
            row_count=len(probe.rows),
            rows=probe.rows,
            note=(
                "The whole filter value — quotes, semicolons, comment "
                f"markers and all — traveled as the bind parameter "
                f"{probe.parameter_name!r}. PostgreSQL parsed the "
                "statement FIRST and matched the value against it as "
                "data, so hostile text can only ever make the pattern "
                "match fewer rows."
            ),
        ),
        unsafe=UnsafeQueryCard(
            template=UNSAFE_TEMPLATE,
            rendered_sql=rendered,
            executed=False,
            why=hostile_why if looks_hostile else tame_why,
        ),
        wildcard_note=(
            "One honest boundary: parameterization stops SQL injection, "
            "not LIKE-wildcard semantics — a caller who sends % or _ in "
            "the value still widens the pattern match. When that matters, "
            "escape the wildcards or use equality instead."
        ),
        reasoning=(
            f"The safe query really ran: {len(probe.rows)} row(s) matched "
            f"the pattern {probe.parameter_value!r} — an injection-shaped "
            "filter matches nothing because no title contains it as "
            "literal text. The unsafe card shows the same input spliced "
            "into the statement: one value, two completely different "
            "meanings. Bind parameters are not a style preference; they "
            "are the boundary between code and data."
        ),
    )
