"""The security demos: topic 25's lab + PII lab (area ``security``).

Thin routers (family invariant). The lab panel QUOTES the app's real
security surfaces — the middleware's header table, the CORS constants the
composition root wires, the limiter's live policy — so the demo can never
drift from the app it explains. The burner is the one endpoint with a
REAL throttle: ``RateLimitDep`` runs before the handler, so the 429
envelope (with ``Retry-After``) is raised by the dependency and this file
contains no rate-limit logic at all.

The PII half consumes topic 24's identity as-is: the masked view resolves
an OPTIONAL principal (no credential headers → the anonymous principal at
full mask; a presented-but-invalid credential still gets the honest 401),
and export/erase are role-gated dependencies — the 403 carries the reason
the same way every guarded endpoint in this guide does.
"""

from typing import Annotated, Final

from fastapi import APIRouter, Depends, Header, Request, Response

from guide.core.errors import AppError, FailureKind
from guide.domain.authz.model import Principal
from guide.domain.demos.security_lab import (
    BurnRow,
    SecurityLabPanel,
    build_burn_row,
    build_security_lab_panel,
)
from guide.domain.demos.security_pii import (
    ANONYMOUS,
    EraseProofRow,
    ExportedSubjectRow,
    MaskedSubjectRow,
    PiiPanel,
    ResetRow,
    build_erase_proof,
    build_exported_subject,
    build_masked_subject,
    build_pii_panel,
    build_reset_row,
)
from guide.domain.security.rate_limit import SlidingWindowLimiter
from guide.domain.security.records import CustomerRecordStore
from guide.presentation.dependencies.authz import resolve_principal
from guide.presentation.dependencies.rate_limit import (
    RATE_LIMIT_REMAINING_HEADER,
    RateLimitDep,
    get_rate_limiter,
)

router = APIRouter(prefix="/api/demo/security", tags=["demo:security"])

LAB_PATH: Final = ""
BURN_ROUTE: Final = "/rate-limit/burn"
PANEL_ROUTE: Final = "/pii"
SUBJECT_ROUTE: Final = "/pii/subjects/{subject_id}"
EXPORT_ROUTE: Final = "/pii/subjects/{subject_id}/export"
ERASE_ROUTE: Final = "/pii/subjects/{subject_id}/erase"
RESET_ROUTE: Final = "/pii/reset"
"""The routers' paths (prefix-relative) — the terminal companion names them."""

ADMIN_ROLE: Final = "admin"
"""The one role the PII lab trusts with raw data and erasure — the authz
registry's own admin, nothing invented here."""

ANONYMOUS_PRINCIPAL: Final[Principal] = Principal(
    kind="user",
    name=ANONYMOUS,
    display_name="anonymous caller",
    roles=(),
    scopes=(),
    via="no credential presented — masked at the fail-closed default",
)
"""The no-credential caller: a principal with no roles, so every mask
level resolves to full. Presented-but-invalid credentials do NOT get this
courtesy — ``resolve_principal`` raises the standard 401 for them."""


def get_pii_store(request: Request) -> CustomerRecordStore:
    """FastAPI dependency: the seeded record store (wired in create_app)."""
    store = request.app.state.pii_records
    if not isinstance(store, CustomerRecordStore):
        raise AppError(FailureKind.INTERNAL, "PII record store not wired on app.state")
    return store


StoreDep = Annotated[CustomerRecordStore, Depends(get_pii_store)]
LimiterDep = Annotated[SlidingWindowLimiter, Depends(get_rate_limiter)]


async def resolve_optional_principal(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
) -> Principal:
    """The masked view's caller: anonymous when header-less, real otherwise.

    No credential headers at all → the anonymous principal (full mask).
    ANY credential header present → topic 24's strict resolution, so a
    forged or expired token gets the same 401 as everywhere else.
    """
    if authorization is None and x_api_key is None:
        return ANONYMOUS_PRINCIPAL
    return await resolve_principal(request, authorization, x_api_key)


OptionalPrincipalDep = Annotated[Principal, Depends(resolve_optional_principal)]


async def require_admin(
    principal: Annotated[Principal, Depends(resolve_principal)],
) -> Principal:
    """The export/erase gate: the admin role, or the standard 403.

    Runs over the SAME credential resolution as every guarded endpoint
    (Bearer first, x-api-key second, 401 without) — only the verdict is
    this lab's own: a role check against the authz registry's vocabulary.
    """
    if ADMIN_ROLE not in principal.roles:
        raise AppError(
            FailureKind.FORBIDDEN,
            (
                "forbidden — customer data export/erase is admin-only, and "
                f"{principal.name!r} carries roles {list(principal.roles)}"
            ),
            details={
                "requiredRole": ADMIN_ROLE,
                "principal": principal.name,
                "roles": list(principal.roles),
            },
        )
    return principal


AdminDep = Annotated[Principal, Depends(require_admin)]


# ── The security lab (demo security:lab, INLINE in the headers section) ───────


@router.get(LAB_PATH, response_model=SecurityLabPanel)
async def read_security_lab_panel(limiter: LimiterDep) -> SecurityLabPanel:
    """The lab panel: the header table, the real CORS policy, the throttle."""
    return build_security_lab_panel(limiter.policy)


@router.post(BURN_ROUTE, response_model=BurnRow)
async def burn_budget(verdict: RateLimitDep, response: Response) -> BurnRow:
    """Burn one unit of the REAL budget; the dependency raises the 429s.

    The handler only runs while budget REMAINS — an exhausted caller never
    reaches this body, which is the whole lesson of a throttle that lives
    in the dependency layer.
    """
    response.headers[RATE_LIMIT_REMAINING_HEADER] = str(verdict.remaining)
    return build_burn_row(verdict)


# ── The PII lab (demo security:pii, INLINE in the PII/GDPR section) ───────────


@router.get(PANEL_ROUTE, response_model=PiiPanel)
async def read_pii_panel(store: StoreDep) -> PiiPanel:
    """The PII panel: subjects, classification, role→mask levels, endpoints."""
    return build_pii_panel(store)


@router.get(SUBJECT_ROUTE, response_model=MaskedSubjectRow)
async def read_subject_as_caller(
    subject_id: str, store: StoreDep, principal: OptionalPrincipalDep
) -> MaskedSubjectRow:
    """One subject through the caller's eyes — the engine picks the mask."""
    record = store.find(subject_id)
    if record is None:
        raise AppError(FailureKind.NOT_FOUND, f"Customer {subject_id!r} not found")
    return build_masked_subject(record, principal.name, principal.roles)


@router.post(EXPORT_ROUTE, response_model=ExportedSubjectRow)
async def export_subject(
    subject_id: str, store: StoreDep, principal: AdminDep
) -> ExportedSubjectRow:
    """Data portability: the RAW record plus its classification map."""
    record = store.find(subject_id)
    if record is None:
        raise AppError(FailureKind.NOT_FOUND, f"Customer {subject_id!r} not found")
    return build_exported_subject(record, principal.name)


@router.post(ERASE_ROUTE, response_model=EraseProofRow)
async def erase_subject(
    subject_id: str, store: StoreDep, principal: AdminDep
) -> EraseProofRow:
    """Right-to-erasure: gone is gone, and the counts prove it."""
    if store.find(subject_id) is None:
        raise AppError(FailureKind.NOT_FOUND, f"Customer {subject_id!r} not found")
    records_before = store.count()
    store.erase(subject_id)
    return build_erase_proof(subject_id, principal.name, records_before, store.count())


@router.post(RESET_ROUTE, response_model=ResetRow)
async def reset_pii_lab(store: StoreDep) -> ResetRow:
    """Reseed the demo records — the erasure round can run again."""
    return build_reset_row(store.reset())
