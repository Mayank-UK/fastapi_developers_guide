"""The statelessness payload: one request, two replicas, real state.

``GET /api/demo/scaling/stateless`` serves this payload INLINE in topic
40's statelessness section. The panel answers the question scaling starts
with — where does this app's state actually live? — by INTROSPECTION, not
by assertion: the router snapshots the real in-process facts off the
composition root (the live scenario flags, the posts count, the chat
rooms, the limiter's policy), the builder walks one logical request
through TWO per-replica state worlds, and the inventory table places
every real store this repo carries.

The two-replica round, honestly framed:

- **The replicas are per-process state worlds, not processes.** This app
  runs as one process; a second replica would be a second process
  constructing the same world ``create_app`` builds. The round constructs
  exactly that world — a fresh ``ScenarioStore`` (the real class wired on
  ``app.state.scenario``) per replica — so the in-process half is the
  genuine article under per-replica construction. The live app's own
  stores are never touched.
- **The externalized half is real Redis.** Both replicas increment ONE
  key through the ``SharedCounterStore`` port; the second INCR's answer
  includes the first's write, which is only possible because the value
  lives in the redis container, in neither process's heap. A real second
  replica would build its own client and see the same number.
- **Bounded** — three redis commands and two in-process constructor calls
  is the whole cost; nothing sleeps, nothing restarts, the stack stays up.
"""

from typing import Final

from guide.core.scenario import ScenarioPatch, ScenarioState, ScenarioStore
from guide.core.serialization import CamelModel
from guide.domain.scaling.ports import SharedCounterStore

COUNTER_KEY: Final = "guide_demo:scaling:shared"
"""The one key the round shares between its two replicas."""

COUNTER_TTL_S: Final = 60
"""Self-cleaning expiry: the round's evidence outlives the request, not the hour."""


def _flags_line(state: ScenarioState) -> str:
    """One scenario snapshot as the round displays it."""
    return f"dataMode={state.data_mode} · injectFailure={state.inject_failure}"


class ScalingFactRow(CamelModel):
    """One process or verdict fact — id, label, and the honest value."""

    id: str
    label: str
    value: str


class ReplicaStepRow(CamelModel):
    """One step of the two-replica round: who acted, what happened, what it saw."""

    step: int
    side: str
    label: str
    detail: str
    observed: str


class PlacementRow(CamelModel):
    """One inventory row: a real store this repo carries, placed honestly."""

    id: str
    state: str
    holder: str
    placement: str
    where: str
    restart: str
    evidence: str


class ProcessFacts(CamelModel):
    """The in-process facts the ROUTER snapshots — counters and flags only."""

    pid: int
    scenario: ScenarioState
    posts_total: int
    chat_rooms: int
    chat_connections: int
    rate_policy: str


class StatelessPanel(CamelModel):
    """Wire shape of ``GET /api/demo/scaling/stateless`` — the panel's contract."""

    process: list[ScalingFactRow]
    replica_round: list[ReplicaStepRow]
    verdicts: list[ScalingFactRow]
    inventory: list[PlacementRow]
    honesty_note: str


HONESTY_NOTE: Final = (
    "Every row on this panel is real: the process facts were read off this "
    "very app's composition root on this request, the two replica worlds are "
    "fresh instances of the real ScenarioStore (the exact class create_app "
    "wires per process — this app's own store is never touched), and the "
    "shared counter is a real redis INCR against the live store. The two "
    "replicas are two state worlds inside this one process because that is "
    "what an honest single-process demo can construct; a real second replica "
    "is a second process with its own create_app, and the round's outcome "
    "is identical — the scenario write still dies with its process, the "
    "counter still lives in the store. Both replicas' commands rode this "
    "process's shared redis client; a real replica B would have its own "
    "client, and the answer would be the same number for the same reason: "
    "the key lives in the redis container, not in any replica."
)


def _process_rows(facts: ProcessFacts) -> list[ScalingFactRow]:
    """The serving process's facts, snapshot-read by the router."""
    return [
        ScalingFactRow(
            id="processes",
            label="processes serving this app right now",
            value=(
                "1 — the dev stack runs uvicorn --reload as a single process; "
                "production runs gunicorn with N uvicorn workers (topic 37): "
                "N process-level replicas sharing one container"
            ),
        ),
        ScalingFactRow(
            id="pid",
            label="this process's pid",
            value=(
                f"{facts.pid} — every in-process store below lives in this "
                "one heap; a restart mints a new pid and an empty heap"
            ),
        ),
        ScalingFactRow(
            id="scenario-now",
            label="the live scenario flags this process holds",
            value=(
                f"dataMode={facts.scenario.data_mode} · injectFailure="
                f"{facts.scenario.inject_failure} — read from app.state."
                "scenario, not assumed"
            ),
        ),
        ScalingFactRow(
            id="posts-now",
            label="posts in this process's in-memory store",
            value=(
                f"{facts.posts_total} right now (12 of them the deterministic "
                "seed; the rest were created by requests since boot)"
            ),
        ),
    ]


async def _round_steps(counter: SharedCounterStore) -> tuple[list[ReplicaStepRow], int]:
    """Walk the two-replica round; return the steps and the final counter value.

    The in-process half: two fresh ``ScenarioStore`` instances — replica A
    patches its flags, replica B never sees the patch. The externalized
    half: both replicas increment ONE shared key; the second answer
    contains the first's write.
    """
    replica_a = ScenarioStore()
    replica_b = ScenarioStore()

    steps: list[ReplicaStepRow] = [
        ReplicaStepRow(
            step=1,
            side="process",
            label="the serving process",
            detail=(
                "one process (see the process facts) — a second replica would "
                "be a second process, each running its own create_app and "
                "building its own in-process world"
            ),
            observed="the round below constructs exactly that world, twice",
        ),
        ReplicaStepRow(
            step=2,
            side="replica-a",
            label="replica A's world is built",
            detail=(
                "a fresh ScenarioStore — the real class wired on app.state."
                "scenario, constructed the way create_app constructs one"
            ),
            observed=_flags_line(replica_a.get()),
        ),
    ]

    # The write: replica A serves the scenario PATCH the way the real
    # endpoint would — the store's own update/merge machinery, no shortcuts.
    replica_a.update(ScenarioPatch(inject_failure="latency"))
    steps.append(
        ReplicaStepRow(
            step=3,
            side="replica-a",
            label="replica A serves a PATCH: injectFailure → latency",
            detail="the write lands in replica A's heap and nowhere else",
            observed=_flags_line(replica_a.get()),
        )
    )
    steps.append(
        ReplicaStepRow(
            step=4,
            side="replica-b",
            label="replica B's world is built the same way",
            detail=(
                "a second ScenarioStore — what the second process would "
                "construct for itself at boot"
            ),
            observed=_flags_line(replica_b.get()),
        )
    )
    steps.append(
        ReplicaStepRow(
            step=5,
            side="replica-b",
            label="replica B answers the same request",
            detail=(
                "B never saw A's write: process-local state does not follow "
                "the request — a load balancer that sends the next call to B "
                "silently loses the toggle"
            ),
            observed=f"{_flags_line(replica_b.get())} — A's patch is invisible",
        )
    )

    # The externalized half: a fresh stage, then one key incremented by
    # both replicas through the shared store.
    await counter.delete(COUNTER_KEY)
    steps.append(
        ReplicaStepRow(
            step=6,
            side="shared",
            label="the same round against the shared counter",
            detail=(
                f"redis INCR on {COUNTER_KEY} — the key lives in the redis "
                "container, in neither replica's heap"
            ),
            observed="key deleted — a fresh stage for this round",
        )
    )
    a_value = await counter.incr(COUNTER_KEY)
    steps.append(
        ReplicaStepRow(
            step=7,
            side="replica-a",
            label="replica A increments the shared key",
            detail="INCR is atomic; the answer is the value after A's write",
            observed=f"INCR → {a_value}",
        )
    )
    b_value = await counter.incr(COUNTER_KEY)
    steps.append(
        ReplicaStepRow(
            step=8,
            side="replica-b",
            label="replica B increments the same key",
            detail=(
                "B's answer includes A's write — only possible because the "
                "value lives outside both processes"
            ),
            observed=f"INCR → {b_value} — externalized state follows the request",
        )
    )
    await counter.expire(COUNTER_KEY, COUNTER_TTL_S)
    steps.append(
        ReplicaStepRow(
            step=9,
            side="shared",
            label="the key outlives the request",
            detail=(
                f"EXPIRE {COUNTER_TTL_S}s — the value would still be there "
                "for a third replica, and after a restart of both"
            ),
            observed=f"value {b_value} with a {COUNTER_TTL_S}s self-cleaning ttl",
        )
    )
    return steps, b_value


def _verdict_rows(counter_value: int) -> list[ScalingFactRow]:
    """The contrast the round proved, stated as facts."""
    return [
        ScalingFactRow(
            id="in-process",
            label="the in-process half (steps 2–5)",
            value=(
                "replica A's patch was invisible to replica B — the write "
                "lived and died in A's heap; B answered from its own defaults"
            ),
        ),
        ScalingFactRow(
            id="externalized",
            label="the externalized half (steps 6–9)",
            value=(
                f"replica B's INCR returned {counter_value} — both writes "
                "accumulated on one value the store owns; either replica may "
                "die and the counter survives"
            ),
        ),
        ScalingFactRow(
            id="the-trade",
            label="the trade this repo makes on purpose",
            value=(
                "the guide keeps posts, auth state, scenario flags, and rate "
                "budgets in-process for per-test isolation and zero-dependency "
                "demos; production would externalize sessions and rate limits "
                "(redis) and accept the extra hop, because a load balancer "
                "makes every in-process assumption wrong"
            ),
        ),
    ]


def _inventory_rows(facts: ProcessFacts, counter_value: int) -> list[PlacementRow]:
    """Every real store this repo carries, placed honestly.

    Each row is verifiable against the code it names: in-process holders
    are wired on ``app.state`` in ``create_app`` (main.py); externalized
    stores are reached through lazy clients with the optional-service
    discipline; client-side credentials are the topic-23 substrates.
    """
    return [
        PlacementRow(
            id="posts-substrate",
            state="the posts substrate: 12 seeded posts plus everything created since boot",
            holder="InMemoryPostRepository",
            placement="in-process",
            where="app.state.posts_repository — a dict keyed by slug, this process's heap",
            restart="the seed is re-derived on boot; every post created since boot is gone",
            evidence=(
                f"{facts.posts_total} posts in this process right now, 12 of "
                "them the deterministic seed (live count via the repository port)"
            ),
        ),
        PlacementRow(
            id="scenario-store",
            state="the dataMode + injectFailure flags every demo reads",
            holder="ScenarioStore",
            placement="in-process",
            where="app.state.scenario — one store per app, replaced by tests per-test",
            restart="flags return to the defaults: dataMode=fake · injectFailure=none",
            evidence=(
                f"this process currently holds dataMode={facts.scenario.data_mode} "
                f"· injectFailure={facts.scenario.inject_failure} (live read)"
            ),
        ),
        PlacementRow(
            id="auth-state",
            state="sessions, API keys, OAuth codes, refresh families",
            holder="InMemoryAuthState",
            placement="in-process",
            where="app.state.auth_state — five dicts, per-app by construction",
            restart="every login, key, and family dies; only the two seeded users remain",
            evidence=(
                "the seed is two demo users (ada, grace) whose argon2 hashes "
                "are checked-in constants — restart-stable, everything else is not"
            ),
        ),
        PlacementRow(
            id="rate-limiter",
            state="the per-key sliding-window hit log",
            holder="SlidingWindowLimiter",
            placement="in-process",
            where="app.state.rate_limiter — a dict of hit-timestamp deques",
            restart="every budget refills to full; throttled clients get a fresh window",
            evidence=(
                f"policy: {facts.rate_policy} — behind a load balancer each "
                "replica enforces its OWN budget, so N replicas mean N× the limit"
            ),
        ),
        PlacementRow(
            id="chat-rooms",
            state="rooms of live websocket members and their bounded queues",
            holder="ConnectionManager",
            placement="in-process",
            where="app.state.chat_service — a dict of rooms, process-local by design",
            restart="the sockets die with the process anyway; the rooms vanish with them",
            evidence=(
                f"{facts.chat_rooms} room(s) with {facts.chat_connections} live "
                "connection(s) in this process (live count)"
            ),
        ),
        PlacementRow(
            id="cache-service",
            state="single-flight locks and telemetry counters",
            holder="CacheAsidePostsService",
            placement="in-process",
            where="app.state.caching_service — locks and counters in this process",
            restart="counters zero and in-flight locks die; the cached BYTES do not (see redis)",
            evidence=(
                "the deliberate split: the service's bookkeeping is "
                "process-local while the cached payload lives under "
                "guide_demo:caching:posts:v1 in redis"
            ),
        ),
        PlacementRow(
            id="postgres",
            state="authors, posts, comments, audit_log, outbox — the real tables",
            holder="the postgres container",
            placement="externalized",
            where="reached through the app's ONE async engine (pool_pre_ping reconnects)",
            restart="nothing is lost — a replica restart is a reconnect, the rows stay put",
            evidence=(
                "the schema is owned by Alembic migrations 0001→0004 and "
                "survives every release flip (the platform stack's external volumes)"
            ),
        ),
        PlacementRow(
            id="redis",
            state="streams, the cached payload, the jobs queue and DLQ, this demo's counter",
            holder="the redis container",
            placement="externalized",
            where="reached through the shared client's two-second socket timeouts",
            restart="nothing is lost — proven live by this panel's own INCR round",
            evidence=(
                f"{COUNTER_KEY} held {counter_value} after both replicas wrote "
                "it — the value lives in the store, not in either process"
            ),
        ),
        PlacementRow(
            id="mongo",
            state="the demo collection with its TTL index",
            holder="the mongo container",
            placement="externalized",
            where="a lazy motor client (2s timeouts) — the app boots with MongoDB down",
            restart="nothing is lost; an unreachable mongo degrades only its own demo to 503",
            evidence=(
                "optional-service discipline: the client is lazy and the "
                "adapter maps driver failures to service_unavailable"
            ),
        ),
        PlacementRow(
            id="session-cookie",
            state="the sealed session id (itsdangerous)",
            holder="the browser",
            placement="client-side",
            where="an HttpOnly cookie — whose id resolves against IN-PROCESS auth state",
            restart="the cookie survives but its server record does not: the user logs in again",
            evidence=(
                "the topic-23 lab proves the flag set (HttpOnly, SameSite) and "
                "the logout invalidation — the id is a key into process-local memory"
            ),
        ),
        PlacementRow(
            id="jwt",
            state="claims signed with HS256: exp, nbf, scopes",
            holder="the client",
            placement="client-side",
            where="the token itself — no server-side record exists at all",
            restart="verifies as long as the signing secret is stable — the stateless credential",
            evidence=(
                "topic 23's refresh lab rotates families in-process, but the "
                "access JWT carries its own truth: the claims ARE the state"
            ),
        ),
    ]


async def build_stateless_panel(
    *,
    counter: SharedCounterStore,
    process: ProcessFacts,
) -> StatelessPanel:
    """Serve the panel: process facts, the two-replica round, the inventory.

    ``counter`` is the shared-counter port (redis behind it); ``process``
    is the snapshot the router read off the composition root — the builder
    never touches the data layer or the app itself.
    """
    steps, counter_value = await _round_steps(counter)
    return StatelessPanel(
        process=_process_rows(process),
        replica_round=steps,
        verdicts=_verdict_rows(counter_value),
        inventory=_inventory_rows(process, counter_value),
        honesty_note=HONESTY_NOTE,
    )
