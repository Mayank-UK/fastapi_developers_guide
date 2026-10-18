"""Real gRPC round-trips: the satellite, all four kinds, status, deadlines.

No mocks anywhere in this file: every test starts the REAL in-process
satellite (``grpc.aio`` server on an OS-picked ephemeral loopback port),
opens the REAL shared channel, and performs the calls exactly the console
endpoint does — through the same ``InProcessGrpcConsole`` adapter behind
the same domain port. Runtimes are created INSIDE each async test so the
server binds the test's own running event loop (grpc.aio requirement),
and stopped explicitly at the end (the app's lifespan does this in
production).
"""

import re
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from guide.data.grpc.console import InProcessGrpcConsole
from guide.data.grpc.runtime import GrpcRuntime
from guide.data.posts.in_memory import InMemoryPostRepository
from guide.domain.demos.grpc_console import SERVICE_EXCERPT
from guide.domain.grpc.entities import ChatNoteFact, GrpcConsoleRequest, ViewEventFact
from guide.domain.posts.use_cases import (
    CreatePostUseCase,
    GetPostUseCase,
    ListPostsUseCase,
    PostUseCases,
    ReplacePostUseCase,
)

_ADDRESS_PATTERN = re.compile(r"^127\.0\.0\.1:\d+$")


@pytest.fixture
async def satellite() -> AsyncIterator[tuple[GrpcRuntime, InProcessGrpcConsole]]:
    """A runtime + its console over the seeded substrate, stopped after."""
    repository = InMemoryPostRepository()
    runtime = GrpcRuntime(
        PostUseCases(
            list_posts=ListPostsUseCase(repository),
            get_post=GetPostUseCase(repository),
            create_post=CreatePostUseCase(repository),
            replace_post=ReplacePostUseCase(repository),
        )
    )
    yield runtime, InProcessGrpcConsole(runtime)
    await runtime.stop()


async def test_all_four_stream_kinds_round_trip_over_one_satellite(
    satellite: tuple[GrpcRuntime, InProcessGrpcConsole],
) -> None:
    _, console = satellite
    # UNARY: one answer, real fields off the seeded substrate.
    unary = await console.call(GrpcConsoleRequest(method="get-post", slug="idempotency-retold"))
    assert unary.status_code == "OK"
    assert unary.status_detail == ""
    assert len(unary.messages) == 1
    assert unary.messages[0].fields["title"] == "Idempotency, retold"
    assert unary.messages[0].fields["tags"] == ["http"]

    # SERVER-STREAMING: the design tag matches five posts, oldest first.
    stream = await console.call(GrpcConsoleRequest(method="stream-posts", tag="design"))
    assert stream.status_code == "OK"
    assert [m.fields["slug"] for m in stream.messages] == [
        "designing-urls-people-can-read",
        "status-codes-are-a-contract",
        "content-negotiation-in-practice",
        "why-pagination-is-a-resource-problem",
        "the-envelope-is-the-error-model",
    ]

    # CLIENT-STREAMING: three events in, one summary back.
    upload = await console.call(
        GrpcConsoleRequest(
            method="count-views",
            view_events=[
                ViewEventFact(slug="idempotency-retold", viewer="mak"),
                ViewEventFact(slug="idempotency-retold", viewer="mak"),
                ViewEventFact(slug="notes-on-rfc-9457", viewer="ada"),
            ],
        )
    )
    assert upload.status_code == "OK"
    assert upload.messages[0].fields["events"] == 3
    assert upload.messages[0].fields["unique_posts"] == 2
    assert upload.messages[0].fields["unique_viewers"] == 2
    assert upload.messages[0].fields["views_per_post"] == {
        "idempotency-retold": 2,
        "notes-on-rfc-9457": 1,
    }

    # BIDIRECTIONAL: every note echoed back, in order.
    echo = await console.call(
        GrpcConsoleRequest(
            method="echo-chat",
            chat_notes=[
                ChatNoteFact(sender="you", text="hello"),
                ChatNoteFact(sender="me", text="echo back"),
            ],
        )
    )
    assert echo.status_code == "OK"
    assert [m.fields["text"] for m in echo.messages] == ["hello", "echo back"]

    # One satellite served all four: same bound address throughout.
    addresses = {
        unary.server_address,
        stream.server_address,
        upload.server_address,
        echo.server_address,
    }
    assert len(addresses) == 1
    assert _ADDRESS_PATTERN.match(next(iter(addresses)))


async def test_unknown_slug_propagates_not_found_with_the_domain_message(
    satellite: tuple[GrpcRuntime, InProcessGrpcConsole],
) -> None:
    _, console = satellite
    outcome = await console.call(GrpcConsoleRequest(method="get-post", slug="no-such-post"))
    assert outcome.status_code == "NOT_FOUND"
    assert outcome.status_detail == "Post 'no-such-post' not found"
    assert outcome.messages == []
    assert outcome.elapsed_ms >= 0


async def test_short_deadline_exceeds_midstream_and_keeps_partial_messages(
    satellite: tuple[GrpcRuntime, InProcessGrpcConsole],
) -> None:
    _, console = satellite
    # Twelve posts at 50ms apart ≈ 600ms; 120ms buys exactly two messages.
    outcome = await console.call(GrpcConsoleRequest(method="stream-posts", deadline_ms=120))
    assert outcome.status_code == "DEADLINE_EXCEEDED"
    assert 1 <= len(outcome.messages) < 12
    assert outcome.elapsed_ms < 2000
    # The messages that DID arrive are complete, ordered, real.
    assert outcome.messages[0].fields["slug"] == "designing-urls-people-can-read"


async def test_slow_stream_succeeds_with_a_generous_deadline(
    satellite: tuple[GrpcRuntime, InProcessGrpcConsole],
) -> None:
    _, console = satellite
    outcome = await console.call(GrpcConsoleRequest(method="stream-posts", deadline_ms=10_000))
    assert outcome.status_code == "OK"
    assert len(outcome.messages) == 12


async def test_empty_uploads_and_unmatched_filters_are_answers_not_errors(
    satellite: tuple[GrpcRuntime, InProcessGrpcConsole],
) -> None:
    _, console = satellite
    empty_views = await console.call(GrpcConsoleRequest(method="count-views"))
    assert empty_views.status_code == "OK"
    assert empty_views.messages[0].fields == {
        "events": 0,
        "unique_posts": 0,
        "unique_viewers": 0,
        "views_per_post": {},
    }

    empty_chat = await console.call(GrpcConsoleRequest(method="echo-chat"))
    assert empty_chat.status_code == "OK"
    assert empty_chat.messages == []

    no_matches = await console.call(GrpcConsoleRequest(method="stream-posts", tag="no-such-tag"))
    assert no_matches.status_code == "OK"
    assert no_matches.messages == []


async def test_stop_retires_the_satellite_and_a_restart_binds_a_new_port(
    satellite: tuple[GrpcRuntime, InProcessGrpcConsole],
) -> None:
    runtime, console = satellite
    first = await console.ensure_ready()
    await runtime.stop()
    assert runtime.address is None
    await runtime.stop()  # idempotent — never started twice, never double-closed
    second = await console.ensure_ready()
    assert _ADDRESS_PATTERN.match(second)
    assert second != first  # a fresh bind picks a fresh ephemeral port
    await runtime.stop()


def test_roster_excerpt_is_verbatim_the_real_service_stanza() -> None:
    """The demo's proto excerpt cannot drift from the compiled contract."""
    proto = Path(__file__).resolve().parents[2] / "guide" / "grpcapi" / "guide.proto"
    stanza = re.search(
        r"^service PostService \{.*?^\}", proto.read_text(encoding="utf-8"), re.M | re.S
    )
    assert stanza is not None
    assert SERVICE_EXCERPT == stanza.group(0)
