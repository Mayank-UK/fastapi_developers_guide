"""The messaging domain area: streams, consumer groups, the outbox, dedupe.

Topic 22's subject, split the way it teaches: ``ports.py`` is the whole
vocabulary (stream producer/consumer protocols, the processed-set, outbox
access — plus every result row); ``stream_service.py`` is the consumer-
group lifecycle engine (produce, healthy/poison consume, pending,
XAUTOCLAIM reclaim); ``outbox_service.py`` is the transactional-outbox
relay (one-tx dual write, poll → publish → mark, the crash window,
idempotent consume); ``idempotence.py`` is the dedupe-by-event-id engine
with the remember-order trade made explicit. Everything here is
driver-free — redis and PostgreSQL vocabulary never cross into the
domain, and the engines run on ordered awaits with no sleeps.
"""

from guide.domain.messaging.idempotence import IdempotentConsumer
from guide.domain.messaging.outbox_service import OutboxRelayService
from guide.domain.messaging.stream_service import StreamLabService

__all__ = ["IdempotentConsumer", "OutboxRelayService", "StreamLabService"]
