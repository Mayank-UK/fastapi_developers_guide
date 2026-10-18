"""The API-keys demo payload: the key roster, derived purely.

``GET /api/demo/auth/keys`` serves this payload — topic 23's second
demo (``auth:api-keys``), inline in the API-keys section. The roster
shows every stored key record BY PREFIX ONLY (the hash column is a
preview of the SHA-256 — display, not secret), and the reasoning states
the storage rule the service enforces: raw shown once, at creation.
"""

from guide.core.serialization import CamelModel
from guide.domain.auth.ports import StoredApiKey


class KeyRecordRow(CamelModel):
    """One stored key record as the roster shows it — prefix, name, hash preview."""

    prefix: str
    name: str
    scopes: tuple[str, ...]
    key_hash_preview: str
    created_at: str


class ApiKeysPanelPayload(CamelModel):
    """Wire shape of ``GET /api/demo/auth/keys`` — the key lab's state."""

    records: list[KeyRecordRow]
    storage_note: str
    lookup_note: str
    create_endpoint: str
    call_endpoint: str
    revoke_endpoint: str
    reasoning: str


def build_api_keys_panel_payload(
    records: list[StoredApiKey],
    *,
    storage_note: str,
    lookup_note: str,
    create_endpoint: str,
    call_endpoint: str,
    revoke_endpoint: str,
) -> ApiKeysPanelPayload:
    """Shape the roster (pure) — prefixes only, never secrets."""
    rows = [
        KeyRecordRow(
            prefix=record.prefix,
            name=record.name,
            scopes=record.scopes,
            key_hash_preview=record.key_hash[:12] + "…",
            created_at=record.created_at,
        )
        for record in records
    ]
    if rows:
        state_note = (
            f"{len(rows)} key record(s) at rest, every one stored as SHA-256 only: "
            "generate a key, copy it ONCE (this roster will never show it again), "
            "call the protected endpoint with it, then revoke by prefix and watch "
            "the same key answer 401 instantly"
        )
    else:
        state_note = (
            "no keys at rest — generate one: the response is the ONLY place the raw "
            "key ever appears; the roster you are reading gets the prefix and a hash "
            "preview and that is all it will ever have"
        )
    reasoning = f"{storage_note} {lookup_note} {state_note}."
    return ApiKeysPanelPayload(
        records=rows,
        storage_note=storage_note,
        lookup_note=lookup_note,
        create_endpoint=create_endpoint,
        call_endpoint=call_endpoint,
        revoke_endpoint=revoke_endpoint,
        reasoning=reasoning,
    )
