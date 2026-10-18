import { describe, expect, it } from 'vitest';
import type { ContentIndex, TopicGroup, TopicSummary } from './content';
import { mergePlannedTopics } from './planned-topics';

/**
 * planned-topics spec — the merge policy, pinned against the registry's real
 * shape: the 34 authored topic ids and 9 groups the content API serves today.
 * The pins that follow the curriculum (43 topics total, ship at order 9) hold
 * under future authoring too — a planned topic that lands on the server drops
 * out of the static map, so the merged total stays 43 until all of them land.
 */

const PLANNED_TOPIC_IDS = [
  'dependency-management',
  'observability',
  'debugging',
  'deployment',
  'performance',
  'reliability',
  'scaling',
  'third-party',
  'advanced-architecture',
] as const;

const SERVED_TOPIC_IDS = [
  'python-language',
  'python-runtime',
  'http-web',
  'fastapi-fundamentals',
  'pydantic',
  'fastapi-dependencies',
  'routing',
  'middleware',
  'request-response',
  'validation',
  'api-design',
  'api-documentation',
  'graphql',
  'webhooks',
  'grpc',
  'sql-schema',
  'databases-sql',
  'sqlalchemy-orm',
  'mongodb',
  'redis',
  'caching',
  'messaging',
  'authentication',
  'authorization',
  'security',
  'files-media',
  'internationalization',
  'realtime',
  'background-jobs',
  'exception-handling',
  'architecture',
  'testing',
  'environments',
  'best-practices',
] as const;

const SERVED_GROUPS: TopicGroup[] = [
  { id: 'foundations', title: 'Foundations', order: 1 },
  { id: 'framework', title: 'Framework', order: 2 },
  { id: 'request-handling', title: 'Request handling', order: 3 },
  { id: 'apis', title: 'APIs', order: 4 },
  { id: 'data', title: 'Data', order: 5 },
  { id: 'state-auth', title: 'State & auth', order: 6 },
  { id: 'media-realtime', title: 'Media & realtime', order: 7 },
  { id: 'platform', title: 'Platform', order: 8 },
  { id: 'capstones', title: 'Capstones', order: 10 },
];

/** The served index as the content API returns it today: 9 groups and the 34
 * authored topic ids (topic fields abridged to what the merge reads — the
 * rendered behavior is covered by the home view spec). */
function servedIndex(): ContentIndex {
  return {
    version: 1,
    groups: SERVED_GROUPS.map((group) => ({ ...group })),
    topics: SERVED_TOPIC_IDS.map(
      (id, index): TopicSummary => ({
        id,
        title: id,
        group: 'foundations',
        order: index + 1,
        sectionCount: 7,
      }),
    ),
  };
}

describe('mergePlannedTopics', () => {
  it('appends the nine planned topics and the ship group to the served index without touching it', () => {
    const served = servedIndex();
    const merged = mergePlannedTopics(served);

    // All 34 authored topics pass through verbatim and untouched…
    expect(merged.topics.slice(0, served.topics.length)).toEqual(served.topics);
    expect(served.topics).toHaveLength(34);
    expect(served.groups).toHaveLength(9);

    // …all nine planned topics join with zero sections (the disabled-card
    // affordance) — 43 total, the full curriculum, with no id duplicated.
    expect(merged.topics).toHaveLength(43);
    const ids = merged.topics.map((topic) => topic.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of PLANNED_TOPIC_IDS) {
      const planned = merged.topics.find((topic) => topic.id === id);
      expect(planned, id).toBeDefined();
      expect(planned?.sectionCount).toBe(0);
    }

    // The ship group joins as the tenth group.
    expect(merged.groups).toHaveLength(10);
    expect(merged.groups.at(-1)).toEqual({ id: 'ship', title: 'Ship', order: 9 });
  });

  it('gives ship an order that reads platform → ship → capstones once sorted', () => {
    const merged = mergePlannedTopics(servedIndex());
    const orders = [...merged.groups].sort((a, b) => a.order - b.order).map((group) => group.id);

    expect(orders.slice(-3)).toEqual(['platform', 'ship', 'capstones']);
  });

  it('drops planned entries the server already serves — authored content wins, never duplicates', () => {
    const served = servedIndex();
    // Topic 37 ships for real, together with its group…
    served.topics.push({
      id: 'deployment',
      title: 'Deployment (authored)',
      group: 'ship',
      order: 37,
      sectionCount: 12,
    });
    served.groups.push({ id: 'ship', title: 'Ship', order: 9 });

    const merged = mergePlannedTopics(served);

    // Exactly one deployment topic — the served one — and no duplicate group.
    const deployments = merged.topics.filter((topic) => topic.id === 'deployment');
    expect(deployments).toHaveLength(1);
    expect(deployments[0]?.title).toBe('Deployment (authored)');
    expect(merged.topics).toHaveLength(43);
    expect(merged.groups.filter((group) => group.id === 'ship')).toHaveLength(1);
    // The other eight planned topics still join.
    expect(merged.topics.filter((topic) => topic.sectionCount === 0)).toHaveLength(8);
  });

  it('is pure — the served index is never mutated', () => {
    const served = servedIndex();
    const snapshot = structuredClone(served);

    mergePlannedTopics(served);

    expect(served).toEqual(snapshot);
  });
});
