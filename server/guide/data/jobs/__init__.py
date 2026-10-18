"""The jobs data layer: the redis/arq adapter behind every jobs port.

``ArqJobs`` implements the composed ``JobsStore`` (broker + attempt
trail + dead letters + mailbox + heartbeat + comparison ledger + reset)
over ONE lazily-created ``ArqRedis`` pool — ``enqueue_job`` for the
broker side, arq's documented key layout (queue zset, in-progress and
result keys) for lifecycle and the two observability numbers, and this
namespace's own JSON lists under ``guide_demo:jobs:*`` for trails, dead
letters, mailbox, and the comparison ledger. Unreachable Redis
degrades to the ``service_unavailable`` envelope; routers never see an
arq or redis import.
"""

from guide.data.jobs.arq_jobs import ArqJobs, create_arq_pool_factory

__all__ = ["ArqJobs", "create_arq_pool_factory"]
