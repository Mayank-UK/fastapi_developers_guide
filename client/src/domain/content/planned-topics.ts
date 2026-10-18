import type { ContentIndex, TopicGroup, TopicSummary } from './content';

/**
 * The planned-topic map — the client-side half of the curriculum promise.
 *
 * The content API serves only AUTHORED topics (the server registry is the
 * single source of truth), so the curriculum topics that are scheduled but not
 * yet written would otherwise be invisible: the topic map would silently skip
 * them, and the `ship` group would not exist at all. This module closes that
 * gap purely in the presentation shell — a static map of the nine planned
 * entries, merged into the served index for the home screen so the map reads
 * like the full curriculum: every group present, unauthored topics rendered as
 * disabled "coming soon" cards. The wire contract and the server are
 * untouched; nothing here ever reaches a request.
 *
 * The merge is one-directional and self-retiring against authoring: the moment
 * the API serves a topic id (or a group) listed here, the static entry drops
 * out — authored content always wins, so this map can never shadow or
 * duplicate the server. Once every planned topic is authored the merge is a
 * no-op and this module can be deleted.
 */

/**
 * The `ship` group — the only curriculum group that exists client-side alone,
 * because none of its topics are authored yet. Its `order` (9) sits between
 * the served `platform` (8) and `capstones` (10) groups; the view sorts groups
 * by `order`, so the merged map reads … → platform → ship → capstones.
 */
const SHIP_GROUP: TopicGroup = { id: 'ship', title: 'Ship', order: 9 };

/**
 * The nine planned topics as zero-section summaries — `sectionCount: 0` is
 * exactly what the topic card renders as a disabled, non-navigable
 * "coming soon" affordance. `order` follows the curriculum numbering
 * (31–43) so planned entries interleave with the served topics of their group.
 */
const PLANNED_TOPICS: readonly TopicSummary[] = [
  {
    id: 'dependency-management',
    title: 'Dependency management',
    subtitle:
      'The dependency surface as product — pyproject.toml, uv lock and groups, upgrades and audits, Docker layer caching.',
    group: 'platform',
    order: 31,
    sectionCount: 0,
  },
  {
    id: 'observability',
    title: 'Observability',
    subtitle:
      'The three questions — structured JSON logs, health versus readiness, metrics, tracing, and alerting.',
    group: 'platform',
    order: 33,
    sectionCount: 0,
  },
  {
    id: 'debugging',
    title: 'Debugging',
    subtitle:
      "From print's limits to pdb, py-spy, tracemalloc, and pyinstrument — in development and in production.",
    group: 'platform',
    order: 35,
    sectionCount: 0,
  },
  {
    id: 'deployment',
    title: 'Deployment',
    subtitle:
      'Multi-stage Docker with uv, compose, reverse proxy and TLS, worker processes, graceful shutdown, CI/CD, Kubernetes.',
    group: 'ship',
    order: 37,
    sectionCount: 0,
  },
  {
    id: 'performance',
    title: 'Performance',
    subtitle:
      'Measure first — async hygiene, connection pooling, uvloop, GC tuning, and the checklist.',
    group: 'ship',
    order: 38,
    sectionCount: 0,
  },
  {
    id: 'reliability',
    title: 'Reliability',
    subtitle:
      'Timeouts, retries, circuit breakers, degradation, bulkheads, and chaos — surviving distributed failure.',
    group: 'ship',
    order: 39,
    sectionCount: 0,
  },
  {
    id: 'scaling',
    title: 'Scaling',
    subtitle:
      'Statelessness, load balancing, replicas, data at scale, CDN and edge, capacity planning.',
    group: 'ship',
    order: 40,
    sectionCount: 0,
  },
  {
    id: 'third-party',
    title: 'Third-party services',
    subtitle:
      'Integrating versus building — email, Stripe, cloud storage, and the keys, quotas, and blast radius they bring.',
    group: 'capstones',
    order: 42,
    sectionCount: 0,
  },
  {
    id: 'advanced-architecture',
    title: 'Advanced architecture',
    subtitle:
      'Consistency across boundaries — DDD vocabulary, sagas, CQRS, event sourcing, and tracing across services.',
    group: 'capstones',
    order: 43,
    sectionCount: 0,
  },
];

/**
 * Merges the planned entries into a served index. Pure and non-mutating: the
 * served groups and topics pass through verbatim (authored content is never
 * rewritten or reordered), planned entries are appended, and anything the
 * server already serves — by topic id or group id — is skipped. Callers own
 * the emptiness policy: an EMPTY served registry is a distinct state the home
 * screen renders separately, so this merge only runs on a non-empty index.
 */
export function mergePlannedTopics(served: ContentIndex): ContentIndex {
  const servedTopicIds = new Set(served.topics.map((topic) => topic.id));
  const plannedTopics = PLANNED_TOPICS.filter((topic) => !servedTopicIds.has(topic.id));

  // The ship group joins only while planned ship topics remain and the server
  // does not serve it yet — belt and braces: the registry would serve the
  // group together with its first authored topic anyway.
  const plannedGroupIds = new Set(plannedTopics.map((topic) => topic.group));
  const servedGroupIds = new Set(served.groups.map((group) => group.id));
  const plannedGroups =
    plannedGroupIds.has(SHIP_GROUP.id) && !servedGroupIds.has(SHIP_GROUP.id)
      ? [SHIP_GROUP]
      : [];

  return {
    ...served,
    groups: [...served.groups, ...plannedGroups],
    topics: [...served.topics, ...plannedTopics],
  };
}
