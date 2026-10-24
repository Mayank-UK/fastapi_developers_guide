"""The scaling port: a counter whose value lives outside the process.

``SharedCounterStore`` is deliberately tiny — increment, delete, set an
expiry — because those three verbs ARE the state-placement lesson's entire
contract with its store: two "replicas" (two per-process worlds, exactly
what a second process would construct) each increment ONE key, and the
second increment's answer includes the first's write, proving the value
lives in the store rather than in either process. The adapter
(``guide.data.scaling``) implements the port over the shared redis client
under the optional-service discipline; a second implementation (a PG
sequence, an HTTP counter service) would change nothing above this line.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SharedCounterStore(Protocol):
    """A shared, atomic counter — the smallest externalized state there is."""

    async def incr(self, key: str) -> int:
        """Increment ``key`` atomically and return the new value.

        The return value is the whole proof: a caller that sees another
        caller's write in its own increment has just observed state that
        lives outside both of them.
        """
        ...

    async def delete(self, key: str) -> int:
        """Delete ``key``; answer how many keys actually died (0 or 1)."""
        ...

    async def expire(self, key: str, seconds: int) -> bool:
        """Set ``key``'s expiry — the demo namespace self-cleans."""
        ...
