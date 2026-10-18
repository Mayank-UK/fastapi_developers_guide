"""The audit-logging pattern, domain half: the event and its row values.

An ``AuditEvent`` is a frozen fact about one change — WHO touched WHAT
row HOW, with the before/after as a plain map. ``audit_row_values`` is
the pure translation into exactly the columns the ``audit_log`` table
owns, so the data adapter's writer stays two lines and the payload
shape is testable without a database. The load-bearing rule lives in
the adapter: the writer takes the CALLER'S connection, so the audit row
commits or rolls back WITH the change it describes — never after it.
"""

from typing import Literal

from guide.core.serialization import CamelModel

AuditAction = Literal["insert", "update", "delete"]
"""The three changes worth auditing; a closed vocabulary, not free text."""


class AuditEvent(CamelModel):
    """One change as the audit log records it."""

    actor: str
    action: AuditAction
    table_name: str
    row_pk: str
    changes: dict[str, str] = {}
    """Field → what changed (``"draft -> published"``); empty for inserts."""


def audit_row_values(event: AuditEvent) -> dict[str, object]:
    """The exact column values the in-transaction audit INSERT writes."""
    return {
        "actor": event.actor,
        "action": event.action,
        "table_name": event.table_name,
        "row_pk": event.row_pk,
        "changes": event.changes,
    }
