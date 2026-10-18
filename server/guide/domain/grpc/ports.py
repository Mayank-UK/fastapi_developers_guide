"""The gRPC console port: what the data adapter must provide.

``GrpcConsole`` is the boundary the demo router depends on — like
``PostRepository``, a Protocol the composition root wires and FastAPI
resolves off ``app.state``. Two operations only: ``ensure_ready``
(starts the in-process gRPC satellite on first use and returns its bound
address — the roster payload reports it) and ``call`` (performs ONE real
``grpc.aio`` round over a channel and reports the outcome, deadline
included). The router never learns about channels, stubs, or protobuf.
"""

from typing import Protocol, runtime_checkable

from guide.domain.grpc.entities import GrpcCallOutcome, GrpcConsoleRequest


@runtime_checkable
class GrpcConsole(Protocol):
    """What every gRPC console adapter must do; outcomes, never raises."""

    async def ensure_ready(self) -> str:
        """Start the in-process satellite if needed; return host:port."""
        ...

    async def call(self, request: GrpcConsoleRequest) -> GrpcCallOutcome:
        """Perform one real gRPC round and report its outcome honestly."""
        ...
