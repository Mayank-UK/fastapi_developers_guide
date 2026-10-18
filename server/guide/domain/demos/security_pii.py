"""The PII lab demo payload: classify, mask by role, export, erase — purely shaped.

``build_pii_panel`` shapes the roster panel topic 25's ``security:pii``
serves INLINE in the PII/GDPR section: the seeded subjects (id + country
only — the roster itself practices minimization), the FULL classification
catalog (every field's category/tier/partial rules with their rationales),
and the role→mask-level table that ties topic 24's roles to what they may
see. ``build_masked_subject`` shapes one viewer's view of one subject —
the fields AS THAT ROLE SEES THEM, never the raw record. Export and erase
rows shape their proofs: export carries the raw record (the admin earned
it, and data portability is a right to the REAL data), erase carries the
before/after counts that make "gone" checkable.
"""

from typing import Final

from guide.core.serialization import CamelModel
from guide.domain.authz.roles import ROLE_ORDER
from guide.domain.security.pii import (
    FieldClassification,
    FieldView,
    MaskLevel,
    classification_catalog,
    mask_level_for_roles,
    mask_record,
)
from guide.domain.security.records import CustomerRecord, CustomerRecordStore

SUBJECT_PATH_TEMPLATE: Final = "/api/demo/security/pii/subjects/{subject_id}"
EXPORT_SUFFIX: Final = "/export"
ERASE_SUFFIX: Final = "/erase"
RESET_PATH: Final = "/api/demo/security/pii/reset"

ANONYMOUS: Final = "(anonymous)"
"""The display name for the no-credential caller — masked as a viewer."""


class SubjectRow(CamelModel):
    """One seeded subject as the PUBLIC roster shows them: id + country.

    The roster runs at anonymous masking by design — a subject LIST that
    leaked names while the detail view masked them would be the leak the
    lesson is about.
    """

    customer_id: str
    country: str


class RoleMaskRow(CamelModel):
    """One role (or the anonymous caller) and the mask level it earns."""

    role: str
    mask_level: MaskLevel
    note: str


class PiiPanel(CamelModel):
    """Wire shape of ``GET /api/demo/security/pii`` — the lab's contract."""

    subjects: list[SubjectRow]
    classification: list[FieldClassification]
    role_masks: list[RoleMaskRow]
    store_count: int
    subject_endpoint: str
    export_endpoint: str
    erase_endpoint: str
    reset_endpoint: str
    minimization_note: str
    reasoning: str


class MaskedSubjectRow(CamelModel):
    """Wire shape of one subject AS ONE VIEWER SEES THEM.

    ``principal``/``principal_role`` name whose eyes the fields went
    through; ``mask_level`` is the level their roles granted. The row
    contains NO unmasked sensitive value at any level below none.
    """

    customer_id: str
    principal: str
    principal_role: str | None
    mask_level: MaskLevel
    fields: list[FieldView]
    detail: str


class ExportedSubjectRow(CamelModel):
    """Wire shape of the admin-gated export: the RAW record plus its map."""

    customer_id: str
    principal: str
    record: CustomerRecord
    classification: list[FieldClassification]
    detail: str


class EraseProofRow(CamelModel):
    """Wire shape of the erasure proof: gone, and countable."""

    customer_id: str
    principal: str
    records_before: int
    records_after: int
    detail: str


class ResetRow(CamelModel):
    """Wire shape of the lab reset: the demo records, reseeded."""

    seeded: int
    detail: str


_ROLE_MASK_NOTES: Final[dict[str, str]] = {
    "admin": "sees the raw values — admin is the grant that earns them",
    "editor": "sees the honest residue (last-4s, initials) — enough for support",
    "viewer": "sees full masks — reading the record is not this role's job",
    "author": "sees full masks — writing posts says nothing about customer data",
}
"""The per-role teaching notes, keyed by the authz registry's own roles."""


def build_pii_panel(store: CustomerRecordStore) -> PiiPanel:
    """Shape the panel (pure) over the store's current contents."""
    subjects = store.list()
    role_masks = [
        RoleMaskRow(
            role=role,
            mask_level=mask_level_for_roles((role,)),
            note=_ROLE_MASK_NOTES.get(role, ""),
        )
        for role in ROLE_ORDER
    ]
    role_masks.append(
        RoleMaskRow(
            role=ANONYMOUS,
            mask_level=mask_level_for_roles(()),
            note="no credential presented — full mask, the same fail-closed default",
        )
    )
    return PiiPanel(
        subjects=[
            SubjectRow(customer_id=record.customer_id, country=record.country)
            for record in subjects
        ],
        classification=classification_catalog(),
        role_masks=role_masks,
        store_count=store.count(),
        subject_endpoint=SUBJECT_PATH_TEMPLATE,
        export_endpoint=SUBJECT_PATH_TEMPLATE + EXPORT_SUFFIX,
        erase_endpoint=SUBJECT_PATH_TEMPLATE + ERASE_SUFFIX,
        reset_endpoint=RESET_PATH,
        minimization_note=(
            "the cheapest protection is absence: the record you never stored "
            "cannot leak, be subpoenaed, or be forgotten too late — the card "
            "number is here only to make the masking visible, and the honest "
            "fix for it is last-4 at capture time"
        ),
        reasoning=(
            "Classification decides what a field IS; roles decide what THIS "
            "caller may see; erasure makes the record unfindable with counts "
            "as proof — the three habits that turn 'we take privacy "
            "seriously' into mechanisms."
        ),
    )


def build_masked_subject(
    record: CustomerRecord, principal: str, roles: tuple[str, ...]
) -> MaskedSubjectRow:
    """One subject through one caller's eyes — the engine decides everything."""
    level = mask_level_for_roles(roles)
    fields = mask_record(record, level)
    masked_count = sum(1 for field in fields if field.masked)
    return MaskedSubjectRow(
        customer_id=record.customer_id,
        principal=principal,
        principal_role=roles[0] if roles else None,
        mask_level=level,
        fields=fields,
        detail=(
            f"{principal} ({roles[0] if roles else 'no role'}) views "
            f"{record.customer_id!r} at mask level {level!r} — "
            f"{masked_count} of {len(fields)} fields masked"
        ),
    )


def build_exported_subject(
    record: CustomerRecord, principal: str
) -> ExportedSubjectRow:
    """The export a data-portability request earns: raw data, fully labeled."""
    return ExportedSubjectRow(
        customer_id=record.customer_id,
        principal=principal,
        record=record,
        classification=classification_catalog(),
        detail=(
            f"{principal} exported {record.customer_id!r} — data portability "
            "returns the REAL record to the subject, which is why it is "
            "admin-gated in this lab and identity-gated in production"
        ),
    )


def build_erase_proof(
    customer_id: str, principal: str, records_before: int, records_after: int
) -> EraseProofRow:
    """The erasure proof: the subject is gone and the counts say so."""
    return EraseProofRow(
        customer_id=customer_id,
        principal=principal,
        records_before=records_before,
        records_after=records_after,
        detail=(
            f"{principal} erased {customer_id!r}: {records_before} → "
            f"{records_after} records — the next read is the 404 envelope, "
            "not a tombstone holding the data it promised to forget"
        ),
    )


def build_reset_row(seeded: int) -> ResetRow:
    """The lab-reset row: the demo records are back."""
    return ResetRow(
        seeded=seeded,
        detail=f"reseeded {seeded} demo records — the erasure round can run again",
    )
