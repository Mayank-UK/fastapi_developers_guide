"""InMemoryPostRepository: the posts port's adapter, tested through the port.

Structural typing means mypy verified the Protocol match statically; these
tests pin the BEHAVIOR: the twelve-post seed's shape, filter/sort/slice
math (including empty results and page bounds), identifier minting
(slugify, collision suffixing, the punctuation fallback), and replace's
identity-preserving snapshot semantics. The runtime-checkable Protocol
instance check doubles as a wiring sanity guard.
"""

from guide.data.posts.in_memory import SEED_POSTS, InMemoryPostRepository
from guide.domain.posts.entities import PostCreate, PostListQuery
from guide.domain.posts.ports import PostRepository

FIELDS = ("title", "body", "author", "tags", "status")


def test_adapter_satisfies_the_port() -> None:
    repo: PostRepository = InMemoryPostRepository()
    assert isinstance(repo, PostRepository)


def test_seed_is_twelve_deterministic_posts() -> None:
    assert len(SEED_POSTS) == 12
    assert len({seed.post_id for seed in SEED_POSTS}) == 12
    repo = InMemoryPostRepository()
    page = repo.list(PostListQuery(limit=100, sort="oldest"))
    assert page.total == 12
    assert page.items[0].id == "designing-urls-people-can-read"
    assert page.items[-1].id == "drafting-the-grpc-chapter"
    # Timestamps one day apart keep every ordering deterministic.
    stamps = [post.created_at for post in page.items]
    assert stamps == sorted(stamps)


def test_empty_repository_lists_an_empty_single_page() -> None:
    repo = InMemoryPostRepository(seed=False)
    page = repo.list(PostListQuery())
    assert page.items == []
    assert page.total == 0
    assert page.pages == 1


def test_pagination_slices_after_filtering() -> None:
    repo = InMemoryPostRepository()
    page = repo.list(PostListQuery(page=2, limit=4))
    assert page.total == 12  # totals reflect the pre-slice count
    assert page.pages == 3
    assert len(page.items) == 4

    tail = repo.list(PostListQuery(page=3, limit=4))
    assert len(tail.items) == 4
    assert repo.list(PostListQuery(page=4, limit=4)).items == []


def test_filters_are_exact_and_combine() -> None:
    repo = InMemoryPostRepository()
    assert repo.list(PostListQuery(author="grace")).total == 4
    assert repo.list(PostListQuery(tag="http")).total == 5
    assert repo.list(PostListQuery(status="draft")).total == 3
    combined = repo.list(PostListQuery(author="barbara", status="draft"))
    assert combined.total == 1
    assert combined.items[0].id == "drafting-the-grpc-chapter"
    # Exact, not case-insensitive: an unknown casing matches nothing.
    assert repo.list(PostListQuery(author="Grace")).total == 0


def test_sort_orders_with_a_stable_tiebreak() -> None:
    repo = InMemoryPostRepository()
    newest = repo.list(PostListQuery(limit=100)).items
    oldest = repo.list(PostListQuery(limit=100, sort="oldest")).items
    by_title = repo.list(PostListQuery(limit=100, sort="title")).items
    assert [p.id for p in newest] == [p.id for p in reversed(oldest)]
    assert [p.title for p in by_title] == sorted(p.title for p in by_title)


def test_get_returns_snapshots_or_none() -> None:
    repo = InMemoryPostRepository()
    post = repo.get("the-envelope-is-the-error-model")
    assert post is not None and post.author == "grace"
    assert repo.get("missing") is None


def test_create_mints_slug_from_title_and_stamps_clock() -> None:
    repo = InMemoryPostRepository()
    post = repo.create(
        PostCreate(title="A Brand New Post!", author="tester", tags=["x"])
    )
    assert post.id == "a-brand-new-post"
    assert post.status == "draft"  # the documented default
    assert post.created_at == post.updated_at
    assert repo.get("a-brand-new-post") is not None
    # Created now sorts ahead of the September seeds.
    assert repo.list(PostListQuery()).items[0].id == "a-brand-new-post"


def test_create_slug_collisions_get_suffixes() -> None:
    repo = InMemoryPostRepository()
    first = repo.create(PostCreate(title="Same Title", author="a"))
    second = repo.create(PostCreate(title="Same Title", author="b"))
    third = repo.create(PostCreate(title="Same Title", author="c"))
    assert first.id == "same-title"
    assert second.id == "same-title-2"
    assert third.id == "same-title-3"


def test_create_punctuation_only_title_falls_back() -> None:
    repo = InMemoryPostRepository(seed=False)
    assert repo.create(PostCreate(title="!!!", author="a")).id == "post"
    assert repo.create(PostCreate(title="???", author="a")).id == "post-2"


def test_replace_preserves_identity_and_refreshes_the_stamp() -> None:
    repo = InMemoryPostRepository()
    before = repo.get("filtering-without-surprises")
    assert before is not None
    replaced = repo.replace(
        "filtering-without-surprises",
        PostCreate(
            title="Filtering without surprises, revised",
            author="barbara",
            tags=["api", "design"],
            status="draft",
        ),
    )
    assert replaced is not None
    assert replaced.id == before.id
    assert replaced.created_at == before.created_at
    assert replaced.updated_at >= before.updated_at
    assert replaced.title != before.title
    assert repo.replace("missing", PostCreate(title="x", author="a")) is None
