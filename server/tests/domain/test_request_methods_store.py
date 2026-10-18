"""Substrate unit tests: the NoteStore + the pure listing builder.

These pin the playground's honest rules: seeding and id minting, the
None-when-unknown lookups (the router decides 404), full-replace
semantics (content replaced, identity metadata kept, revision bumped, the
caller's record never mutated), delete-once-then-404, insertion-order
listing as a copy, and the public views carrying no bookkeeping fields.
"""

from guide.domain.demos.request_methods import (
    NoteCreate,
    NoteRecord,
    NoteStore,
    build_notes_listing,
)


def test_seeded_store_lists_three_notes_with_ids_from_one() -> None:
    store = NoteStore()
    records = store.all()
    assert [record.id for record in records] == [1, 2, 3]
    assert all(record.revision == 1 for record in records)
    assert all(record.created_at for record in records)


def test_unseeded_store_starts_empty_and_create_mints_upward_ids() -> None:
    store = NoteStore(seed=False)
    assert store.all() == []
    first = store.create(NoteCreate(title="one"))
    second = store.create(NoteCreate(title="two"))
    assert first.id == 1
    assert second.id == 2


def test_get_returns_none_for_unknown_ids() -> None:
    store = NoteStore(seed=False)
    assert store.get(99) is None
    created = store.create(NoteCreate(title="present"))
    assert store.get(created.id) is not None


def test_replace_swaps_content_keeps_identity_and_bumps_revision() -> None:
    store = NoteStore(seed=False)
    original = store.create(NoteCreate(title="before", body="old", tags=["a"]))
    replaced = store.replace(original.id, NoteCreate(title="after", body="new", tags=["b"]))
    assert replaced is not None
    assert replaced.title == "after"
    assert replaced.body == "new"
    assert replaced.tags == ["b"]
    assert replaced.id == original.id
    assert replaced.created_at == original.created_at
    assert replaced.revision == original.revision + 1
    # The caller's original snapshot was never mutated (frozen snapshots).
    assert original.title == "before"
    assert store.get(original.id) is replaced
    assert store.replace(42, NoteCreate(title="nope")) is None


def test_tags_are_copied_not_shared_with_the_draft() -> None:
    draft = NoteCreate(title="t", tags=["x"])
    record = NoteStore(seed=False).create(draft)
    draft.tags.append("mutated-later")
    assert record.tags == ["x"]


def test_delete_once_then_reports_unknown() -> None:
    store = NoteStore(seed=False)
    note = store.create(NoteCreate(title="doomed"))
    assert store.delete(note.id) is True
    assert store.get(note.id) is None
    assert store.delete(note.id) is False


def test_all_returns_insertion_order_copy_not_the_live_values() -> None:
    store = NoteStore(seed=False)
    store.create(NoteCreate(title="first"))
    store.create(NoteCreate(title="second"))
    snapshot = store.all()
    snapshot.clear()
    assert len(store.all()) == 2


def test_listing_builder_serves_public_views_without_bookkeeping() -> None:
    store = NoteStore()
    records: list[NoteRecord] = store.all()
    listing = build_notes_listing(records)
    assert listing.count == 3
    assert len(listing.notes) == 3
    assert "revision" not in listing.notes[0].model_dump()
    assert listing.reasoning.startswith("GET answered 200 with")
