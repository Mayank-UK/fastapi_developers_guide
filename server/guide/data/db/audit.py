"""The in-transaction audit writer — the pattern's data half.

Two lines of load-bearing code: ``record_audit`` INSERTs the event's
row values INTO ``audit_log`` using the CALLER'S connection, so the
audit row and the change it describes are one transaction — commit
together, roll back together, never a change without its trail. The
event and its column values come from the domain (``audit_row_values``);
this adapter only knows the connection type and the table.
"""

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from guide.data.db.schema import audit_log
from guide.domain.db.audit import AuditEvent, audit_row_values


async def record_audit(connection: AsyncConnection, event: AuditEvent) -> None:
    """Write one audit row on the caller's connection (same transaction)."""
    await connection.execute(sa.insert(audit_log).values(**audit_row_values(event)))
