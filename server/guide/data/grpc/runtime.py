"""The in-process gRPC satellite: one server + one channel, lazily started.

``GrpcRuntime`` owns the lifecycle so the rest of the app never thinks
about it: on first use it binds a ``grpc.aio`` server to an EPHEMERAL
port on 127.0.0.1 (port 0 — the OS picks; per-app instances never
collide, tests included), hosts the ``PostServiceServicer`` over the
wired posts use cases, opens ONE channel to itself, and hands out that
address. ``stop()`` closes channel then server and is what the app's
lifespan shutdown calls (a no-op when the satellite was never started).

Why lazy and not at startup: a ``grpc.aio`` server is bound to the
RUNNING event loop, and FastAPI's lifespan startup is the first moment
one exists under uvicorn — but tests build apps without entering any
lifespan, and import time has no loop at all. First-use start means the
satellite always lands in the loop that will serve it; the ephemeral
port means a second app in the same process is harmless. The ASGI app
and the gRPC server share the process by design — one substrate, two
front doors.
"""

import asyncio
from typing import Any

import grpc

from guide.data.grpc.servicer import PostServiceServicer
from guide.domain.posts.use_cases import PostUseCases
from guide.grpcapi import guide_pb2_grpc

BIND_HOST: str = "127.0.0.1"
"""The satellite's bind host — loopback; the app is the front door."""


class GrpcRuntime:
    """Lifecycle owner of the in-process server + its channel."""

    def __init__(self, posts: PostUseCases) -> None:
        self._posts = posts
        self._server: Any = None
        self._channel: grpc.aio.Channel | None = None
        self._address: str | None = None
        self._start_lock = asyncio.Lock()

    @property
    def address(self) -> str | None:
        """The bound address, or None while the satellite has not started."""
        return self._address

    @property
    def channel(self) -> grpc.aio.Channel:
        """The shared channel to the satellite (set once, at first start)."""
        if self._channel is None:
            raise RuntimeError("gRPC satellite not started — call ensure_started() first")
        return self._channel

    async def ensure_started(self) -> str:
        """Start on first use and return the bound ``host:port`` (idempotent).

        The lock makes concurrent first calls safe — exactly one server
        binds; the double-checked ``_address`` keeps repeat calls free.
        """
        if self._address is not None:
            return self._address
        async with self._start_lock:
            if self._address is not None:
                return self._address
            server = grpc.aio.server()
            guide_pb2_grpc.add_PostServiceServicer_to_server(
                PostServiceServicer(self._posts), server
            )
            port = server.add_insecure_port(f"{BIND_HOST}:0")
            if port == 0:
                raise RuntimeError("gRPC satellite failed to bind an ephemeral port")
            await server.start()
            self._server = server
            self._address = f"{BIND_HOST}:{port}"
            # One shared channel for every console call — channels are the
            # expensive, multiplexed object; stubs over it are free.
            self._channel = grpc.aio.insecure_channel(self._address)
            return self._address

    async def stop(self) -> None:
        """Close channel then server; a no-op when never started."""
        channel, server = self._channel, self._server
        self._channel = None
        self._server = None
        self._address = None
        if channel is not None:
            await channel.close()
        if server is not None:
            await server.stop(grace=None)
