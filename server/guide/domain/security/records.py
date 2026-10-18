"""The PII demo's customer records: seeded, fake, erasable — the GDPR substrate.

Topic 25's PII/GDPR section needs a REAL store to protect, so it gets one
in the family's in-domain shape (the comment ledger's sibling): a small
``CustomerRecord`` model and a per-app in-memory store seeded with three
obviously fake people. Every record carries the classic leak-surface —
contact details, a birth date, a national id, a card number — precisely so
the masking engine has every tier to work on; none of it describes a real
person, which is itself the first lesson of demo data (seed with
synthetic PII, never with production copies).

The store's whole surface is list/find/erase/reset/count — read, read,
and the two powers GDPR actually grants pressure about: erasure must make
the record UNFINDABLE (not a soft-delete flag a forgetful query skips),
and the count answers "how many records hold this person's data" with a
number, not a promise.
"""

from typing import Final

from guide.core.serialization import CamelModel


class CustomerRecord(CamelModel):
    """One fake customer, every field the classification engine knows."""

    customer_id: str
    full_name: str
    email: str
    phone: str
    date_of_birth: str
    national_id: str
    card_number: str
    country: str
    signup_at: str


SEED_CUSTOMERS: Final[tuple[CustomerRecord, ...]] = (
    CustomerRecord(
        customer_id="cust-2f9a41",
        full_name="Marta Ilves",
        email="marta.ilves@example.org",
        phone="+372 55 667 8899",
        date_of_birth="1987-03-14",
        national_id="EE-39203178741",
        card_number="4024 0071 4638 2213",
        country="EE",
        signup_at="2026-02-11T09:24:00Z",
    ),
    CustomerRecord(
        customer_id="cust-7c1d02",
        full_name="Kenji Aoyama",
        email="kenji.aoyama@example.com",
        phone="+81 90 1234 5678",
        date_of_birth="1992-11-02",
        national_id="JP-8921011234567",
        card_number="5412 7534 0091 8762",
        country="JP",
        signup_at="2026-04-03T17:52:00Z",
    ),
    CustomerRecord(
        customer_id="cust-9e4b8c",
        full_name="Amina Sadiq",
        email="amina.sadiq@example.net",
        phone="+44 7700 900123",
        date_of_birth="1979-07-30",
        national_id="GB-7790730",
        card_number="4917 6600 3344 5566",
        country="GB",
        signup_at="2026-06-19T11:08:00Z",
    ),
)
"""Three synthetic people — no real person's data was copied to teach with."""


class CustomerRecordStore:
    """Per-app, in-memory: list, find, erase, reset — count always proven."""

    def __init__(self, seed: bool = True) -> None:
        """Start with the fixed three-record seed, or empty for tests."""
        self._records: dict[str, CustomerRecord] = (
            {record.customer_id: record for record in SEED_CUSTOMERS} if seed else {}
        )

    def list(self) -> list[CustomerRecord]:
        """Every record, seed order — the panel's subject roster."""
        return list(self._records.values())

    def find(self, customer_id: str) -> CustomerRecord | None:
        """One record, or None — the router maps that to the 404 envelope."""
        return self._records.get(customer_id)

    def erase(self, customer_id: str) -> bool:
        """Right-to-erasure: the record is GONE, or False if already absent.

        A hard delete by design — a tombstone row holding the PII it
        promised to forget is the classic erasure bug, so the store does
        not keep one.
        """
        return self._records.pop(customer_id, None) is not None

    def reset(self) -> int:
        """Reseed the demo records (the lab's affordance); returns the count."""
        self._records = {record.customer_id: record for record in SEED_CUSTOMERS}
        return len(self._records)

    def count(self) -> int:
        """How many records the store holds — erasure's before/after proof."""
        return len(self._records)
