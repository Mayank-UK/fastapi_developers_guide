"""The PII engine: classify fields, mask by role — minimization as code.

Topic 25's PII/GDPR section runs on two pure functions. ``classify`` reads
a field NAME against a rule table and answers the data-classification
question — what CATEGORY is this, how SENSITIVE, and does an honest
partial form exist — because masking policy should never be invented per
endpoint. ``mask`` then applies a MASK LEVEL per field: ``full`` (redact
everything), ``partial`` (keep the industry-honest residue — a card's
last four, an email's domain), or ``none`` (the raw value, for principals
whose role earned it). Public/internal tiers pass through untouched:
masking ``country`` would be theater, not privacy.

The level itself comes from the CALLER'S ROLES via ``mask_level_for_roles``
— the same least-privilege posture as topic 24's engine, pointed at data
instead of actions: the default is FULL mask, and only an explicitly
granted role unlocks ``partial`` (editor) or ``none`` (admin). Unknown
roles, empty roles, anonymous callers: all fully masked, fail closed.

The masking is deterministic string work — no hashing, no randomness — so
the demo panel and the tests pin exact outputs. A masked value that
varied would be unusable as a display AND untestable as a guarantee.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final, Literal

from guide.core.serialization import CamelModel
from guide.domain.security.records import CustomerRecord

SensitivityTier = Literal["public", "internal", "sensitive", "regulated"]
"""How much damage a leak of the field does — the axis masking keys on."""

FieldCategory = Literal[
    "identifier", "identity", "contact", "financial", "demographic", "operational"
]
"""What KIND of data the field is — the axis classification reports."""

MaskLevel = Literal["none", "partial", "full"]
"""How much of a sensitive value survives: everything, the honest residue,
or nothing. Applied per the caller's roles; fields below the sensitive
tiers ignore it (they were never masked)."""

FULL_MASK: Final = "***"
"""The full-mask token — short, obvious, and value-free by construction."""

_MASKABLE_TIERS: Final[frozenset[SensitivityTier]] = frozenset(
    {"sensitive", "regulated"}
)
"""Tiers masking applies to; public/internal pass through at every level."""


@dataclass(frozen=True, slots=True)
class FieldRule:
    """One field's classification: category, tier, and partial behavior.

    ``partial`` is the field's honest residue function (None when no
    partial form exists — a national id or a birth date has none), and
    ``rationale`` is the WHY, verbatim to the panel: classification
    without reasons cannot be reviewed, and unreviewable classification
    rots into copy-paste tiers.
    """

    field: str
    category: FieldCategory
    tier: SensitivityTier
    rationale: str
    partial: Callable[[str], str] | None = None

    @property
    def allows_partial(self) -> bool:
        """Whether a partial mask is honest for this field."""
        return self.partial is not None


def _last4(value: str) -> str:
    return value[-4:]


def _name_partial(value: str) -> str:
    parts = value.split()
    if len(parts) <= 1:
        return FULL_MASK
    return f"{parts[0]} {parts[-1][0]}."


def _email_partial(value: str) -> str:
    local, separator, domain = value.partition("@")
    if not separator or not local:
        return FULL_MASK
    return f"{local[0]}***@{domain}"


FIELD_RULES: Final[tuple[FieldRule, ...]] = (
    FieldRule(
        field="customer_id",
        category="identifier",
        tier="public",
        rationale=(
            "the URL-facing handle — safe to display precisely because it is "
            "random, not derived from anything about the person"
        ),
    ),
    FieldRule(
        field="full_name",
        category="identity",
        tier="sensitive",
        rationale=(
            "directly identifying on its own; the partial form keeps the given "
            "name and an initial — enough for a support greeting, not for a lookup"
        ),
        partial=_name_partial,
    ),
    FieldRule(
        field="email",
        category="contact",
        tier="sensitive",
        rationale=(
            "identifies the person and reaches them; the partial form keeps the "
            "domain — often enough to recognize YOUR OWN account at a glance"
        ),
        partial=_email_partial,
    ),
    FieldRule(
        field="phone",
        category="contact",
        tier="sensitive",
        rationale=(
            "identifies the person in most countries' directories; the partial "
            "form keeps the last four, the caller-ID convention"
        ),
        partial=_last4,
    ),
    FieldRule(
        field="date_of_birth",
        category="demographic",
        tier="regulated",
        rationale=(
            "with a name it is an identity-theft kit and a correlation key; no "
            "honest partial form exists, so partial degrades to full"
        ),
    ),
    FieldRule(
        field="national_id",
        category="identifier",
        tier="regulated",
        rationale=(
            "government identity — the strongest identifier a record can carry "
            "and the one that must never render in a support UI; no partial form"
        ),
    ),
    FieldRule(
        field="card_number",
        category="financial",
        tier="regulated",
        rationale=(
            "payment credentials — the honest fix is NOT STORING it (last-4 is "
            "the minimized form real systems keep); the demo stores a fake one "
            "to make the masking visible"
        ),
        partial=_last4,
    ),
    FieldRule(
        field="country",
        category="demographic",
        tier="internal",
        rationale=(
            "coarse and not identifying alone — internal analytics read it, "
            "and masking it would be theater, not privacy"
        ),
    ),
    FieldRule(
        field="signup_at",
        category="operational",
        tier="internal",
        rationale=(
            "operational metadata — useful for support timelines, harmless "
            "alone, and kept honest by not being about the person at all"
        ),
    ),
)
"""The rule table: one row per record field, stated once, reviewed as data."""


class FieldClassification(CamelModel):
    """One classified field, as the panel serves it.

    ``allows_partial`` False means the partial level degrades to full for
    this field — the rule table said no honest residue exists.
    """

    field: str
    category: FieldCategory
    tier: SensitivityTier
    allows_partial: bool
    rationale: str


class FieldView(CamelModel):
    """One field as a given viewer sees it: the value (masked or raw) + why.

    ``masked`` says whether the value differs from what is stored;
    ``applied`` names the level that produced it (``none`` for unmasked
    pass-through fields too, so the wire never lies about what ran).
    """

    field: str
    category: FieldCategory
    tier: SensitivityTier
    value: str
    masked: bool
    applied: MaskLevel


MASK_LEVEL_BY_ROLE: Final[dict[str, MaskLevel]] = {
    "admin": "none",
    "editor": "partial",
}
"""Roles granted a lighter mask — everything else (viewer, author, unknown,
anonymous) fails closed to full. The registry is deliberately tiny: earning
raw PII is a grant, not a default."""


def mask_level_for_roles(roles: Sequence[str]) -> MaskLevel:
    """The least mask a caller's roles grant — full unless a role says less.

    Scans every role and keeps the LIGHTEST mask any of them grants, so a
    caller holding both editor and admin gets admin's view — the same
    union posture topic 24's grants take. An empty list, an unknown role,
    a typo'd role: all full mask.
    """
    order: Final[tuple[MaskLevel, ...]] = ("full", "partial", "none")
    granted: MaskLevel = "full"
    for role in roles:
        level = MASK_LEVEL_BY_ROLE.get(role, "full")
        if order.index(level) > order.index(granted):
            granted = level
    return granted


def mask_field(rule: FieldRule, raw: str, level: MaskLevel) -> FieldView:
    """Apply one rule at one level — pure, deterministic, tier-gated."""
    if rule.tier not in _MASKABLE_TIERS or level == "none":
        return _view(rule, value=raw, masked=False, applied="none")
    if level == "full" or rule.partial is None:
        return _view(rule, value=FULL_MASK, masked=True, applied="full")
    return _view(
        rule, value=rule.partial(raw), masked=True, applied="partial"
    )


def mask_record(record: CustomerRecord, level: MaskLevel) -> list[FieldView]:
    """Mask every field of a CustomerRecord at one level, rule order."""
    return [
        mask_field(rule, str(getattr(record, rule.field)), level)
        for rule in FIELD_RULES
    ]


def classification_catalog() -> list[FieldClassification]:
    """The whole rule table as wire rows — the panel's classification view."""
    return [
        FieldClassification(
            field=rule.field,
            category=rule.category,
            tier=rule.tier,
            allows_partial=rule.allows_partial,
            rationale=rule.rationale,
        )
        for rule in FIELD_RULES
    ]


def _view(
    rule: FieldRule, *, value: str, masked: bool, applied: MaskLevel
) -> FieldView:
    return FieldView(
        field=rule.field,
        category=rule.category,
        tier=rule.tier,
        value=value,
        masked=masked,
        applied=applied,
    )
