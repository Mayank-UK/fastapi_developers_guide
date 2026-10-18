"""The security engines: sliding-window limiter, PII masking, CORS verdicts.

The limiter cases are the deterministic core the topic promises: the
allow…allow → 429 → window-slide → allow sequence with an INJECTED clock
(integer seconds, zero sleeps), the retry-after arithmetic anchored on
the oldest in-window hit, denials recording nothing (hammering must not
extend the lockout), per-key isolation, and peek's read-only guarantee.
The masking cases pin the tier gating (public/internal pass through),
the partial forms that exist, the fields that have none, and the role
map's fail-closed default — plus the store's erasure round.
"""

from guide.domain.security.cors import cors_outcome
from guide.domain.security.pii import (
    FIELD_RULES,
    FULL_MASK,
    mask_field,
    mask_level_for_roles,
    mask_record,
)
from guide.domain.security.rate_limit import RateLimitPolicy, SlidingWindowLimiter
from guide.domain.security.records import (
    SEED_CUSTOMERS,
    CustomerRecordStore,
)

SUBJECT = SEED_CUSTOMERS[0]
POLICY = RateLimitPolicy(window_s=10.0, budget=3, keying="test")


def _rule(field: str):
    return next(rule for rule in FIELD_RULES if rule.field == field)


# ── The sliding window ────────────────────────────────────────────────────────


def test_allows_under_budget_then_denies_with_retry_after() -> None:
    limiter = SlidingWindowLimiter(POLICY)
    assert limiter.hit("a", now=0.0).remaining == 2
    assert limiter.hit("a", now=1.0).remaining == 1
    assert limiter.hit("a", now=2.0).remaining == 0
    denied = limiter.hit("a", now=3.0)
    assert not denied.allowed
    assert denied.remaining == 0
    # The oldest in-window hit was at t=0: the slot reopens exactly at t=10.
    assert denied.retry_after_s == 7.0


def test_denied_hits_are_not_recorded_so_hammering_extends_nothing() -> None:
    limiter = SlidingWindowLimiter(POLICY)
    for moment in (0.0, 1.0, 2.0):
        limiter.hit("a", now=moment)
    for moment in (3.0, 4.0, 5.0):
        assert not limiter.hit("a", now=moment).allowed
    # Still anchored on the t=0 hit — the five denials pushed nothing out.
    assert limiter.hit("a", now=5.5).retry_after_s == 4.5


def test_window_slides_at_the_exact_boundary() -> None:
    limiter = SlidingWindowLimiter(POLICY)
    for moment in (0.0, 1.0, 2.0):
        limiter.hit("a", now=moment)
    assert not limiter.hit("a", now=9.99).allowed
    # At t=10 the t=0 hit is exactly outside (t - window): one slot reopened.
    slid = limiter.hit("a", now=10.0)
    assert slid.allowed
    assert slid.remaining == 0


def test_keys_hold_independent_budgets() -> None:
    limiter = SlidingWindowLimiter(POLICY)
    for moment in (0.0, 1.0, 2.0):
        limiter.hit("ip:route-a", now=moment)
    assert not limiter.hit("ip:route-a", now=3.0).allowed
    # Same caller, different route: a fresh budget — keying is real.
    assert limiter.hit("ip:route-b", now=3.0).remaining == 2
    # Same route, different caller: also fresh.
    assert limiter.hit("other:route-a", now=3.0).remaining == 2


def test_peek_answers_without_consuming() -> None:
    limiter = SlidingWindowLimiter(POLICY)
    for moment in (0.0, 1.0, 2.0):
        limiter.hit("a", now=moment)
    for _ in range(3):
        peeked = limiter.peek("a", now=3.0)
        assert not peeked.allowed
        assert peeked.retry_after_s == 7.0
    assert limiter.hit("a", now=3.0).retry_after_s == 7.0


def test_injected_clock_is_used_when_now_is_omitted() -> None:
    ticks = iter((100.0, 101.0, 102.0, 103.0))
    limiter = SlidingWindowLimiter(POLICY, clock=lambda: next(ticks))
    assert all(limiter.hit("a").allowed for _ in range(3))
    denied = limiter.hit("a")
    assert not denied.allowed
    assert denied.retry_after_s == 7.0  # anchored on the t=100 hit, asked at 103


# ── Mask levels by role ───────────────────────────────────────────────────────


def test_mask_level_fails_closed_and_takes_the_lightest_grant() -> None:
    assert mask_level_for_roles(("admin",)) == "none"
    assert mask_level_for_roles(("editor",)) == "partial"
    assert mask_level_for_roles(("viewer",)) == "full"
    assert mask_level_for_roles(("author",)) == "full"
    assert mask_level_for_roles(()) == "full"  # anonymous
    assert mask_level_for_roles(("no-such-role",)) == "full"
    assert mask_level_for_roles(("editor", "admin")) == "none"
    assert mask_level_for_roles(("viewer", "editor")) == "partial"


# ── Field masking ─────────────────────────────────────────────────────────────


def test_partial_level_keeps_the_honest_residue_per_field() -> None:
    assert mask_field(_rule("full_name"), "Marta Ilves", "partial").value == "Marta I."
    partial_email = mask_field(_rule("email"), "marta.ilves@example.org", "partial")
    assert partial_email.value == "m***@example.org"
    assert mask_field(_rule("phone"), "+372 55 667 8899", "partial").value == "8899"
    assert mask_field(_rule("card_number"), "4024 0071 4638 2213", "partial").value == "2213"


def test_fields_without_an_honest_partial_form_go_full_at_partial() -> None:
    for field in ("date_of_birth", "national_id"):
        view = mask_field(_rule(field), "whatever", "partial")
        assert view.value == FULL_MASK
        assert view.applied == "full"


def test_public_and_internal_tiers_pass_through_at_every_level() -> None:
    for level in ("none", "partial", "full"):
        assert mask_field(_rule("country"), "EE", level).value == "EE"
        assert not mask_field(_rule("country"), "EE", level).masked
        assert mask_field(_rule("customer_id"), "cust-2f9a41", level).value == "cust-2f9a41"


def test_full_level_redacts_every_maskable_field_and_none_shows_raw() -> None:
    full = mask_record(SUBJECT, "full")
    masked = {view.field: view for view in full}
    assert masked["email"].value == FULL_MASK
    assert masked["card_number"].value == FULL_MASK
    assert sum(1 for view in full if view.masked) == 6  # the sensitive+regulated six
    raw = {view.field: view.value for view in mask_record(SUBJECT, "none")}
    assert raw["email"] == SUBJECT.email
    assert raw["national_id"] == SUBJECT.national_id


# ── CORS verdicts ─────────────────────────────────────────────────────────────


def test_cors_outcome_allows_exactly_the_listed_origins() -> None:
    allowed = cors_outcome("http://localhost:5174")
    assert allowed.allowed
    assert "allow-list" in allowed.basis
    for origin in ("http://localhost:5174/", "http://evil.example", "localhost:5174", ""):
        assert not cors_outcome(origin).allowed


# ── The record store's erasure round ──────────────────────────────────────────


def test_erase_is_a_hard_delete_with_counts_and_reset_reseeds() -> None:
    store = CustomerRecordStore()
    assert store.count() == 3
    assert store.find(SUBJECT.customer_id) is not None
    assert store.erase(SUBJECT.customer_id) is True
    assert store.find(SUBJECT.customer_id) is None
    assert store.count() == 2
    assert store.erase(SUBJECT.customer_id) is False  # already gone
    assert store.reset() == 3
    assert store.find(SUBJECT.customer_id) is not None
