import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAppConfig } from '../../core/config/app-config';
import { stubApiFetch, stubNetworkFailure } from '../../test/fetch_stub';
import { MongoConsoleApi } from './mongo-console-api';
import { MongoConsoleRepositoryImpl } from './mongo-console-repository-impl';

afterEach(() => {
  vi.unstubAllGlobals();
});

/**
 * MongoConsoleRepositoryImpl spec — fixture-driven: the console payload
 * (seed, refusal, lifecycle, both exhibits) round-trips, malformed
 * payloads resolve as Failed Results, never throw.
 */

const MONGO_CONSOLE_URL = '/api/demo/db/mongo-console?tag=indexes';

const payload = {
  database: 'guide_demo',
  seed: {
    collection: 'console_notes',
    seedKeys: ['mongo-note-documents', 'mongo-note-indexes'],
    countBefore: 6,
    upserted: 0,
    totalAfter: 6,
    indexesEnsured: ['key_1 (unique)', 'created_at_-1'],
  },
  refusal: {
    attempted: { title: '', status: 'embargoed' },
    errors: ['title: String should have at least 3 characters'],
  },
  operations: [
    {
      op: 'insert',
      description: 'Reset, validate, insert.',
      command: 'db.console_notes.insert_one({…})',
      outcome: 'acknowledged — insertedId 6ad2104326caa2d2f80e8c67',
      documents: [{ key: 'mongo-demo-insert', title: 'The document boundary' }],
    },
    {
      op: 'find',
      description: 'Filter, project, sort.',
      command: 'db.console_notes.find({tags: "indexes"}, {…})',
      outcome: '3 document(s) match',
      documents: [
        { key: 'mongo-note-ttl', title: 'Expiry belongs in the index layer' },
        { key: 'mongo-note-indexes', title: 'Indexes are B-trees here too' },
      ],
    },
    {
      op: 'update',
      description: '$set a field.',
      command: 'db.console_notes.update_one({…}, {$set: {…}})',
      outcome: 'matched 1, modified 1',
      documents: [],
    },
    { op: 'count', description: 'Same filter.', command: 'count_documents({…})', outcome: '3 document(s)', documents: [] },
    { op: 'delete', description: 'Reset the stage.', command: 'delete_one({…})', outcome: 'deletedCount 1', documents: [] },
  ],
  indexShowcase: {
    collection: 'explain_stage',
    documentCount: 8,
    indexCommand: 'db.explain_stage.createIndex({title: 1})',
    explains: [
      { label: 'without an index', query: '{title: "…"}', stage: 'COLLSCAN', keysExamined: 0, docsExamined: 8 },
      { label: 'with title_1', query: '{title: "…"}', stage: 'IXSCAN', indexName: 'title_1', keysExamined: 1, docsExamined: 1 },
    ],
  },
  ttlShowcase: {
    collection: 'ttl_stage',
    indexDefinition: {
      v: '2',
      key: "{'expires_at': 1}",
      name: 'expires_at_1',
      expireAfterSeconds: '10',
    },
    expireAfterSeconds: 10,
    scratchDocuments: [
      { label: 'ephemeral', expires_at: '2026-10-16T12:00:10+00:00' },
      { label: 'durable', expires_at: '2026-10-16T13:00:00+00:00' },
    ],
    evictionNote: "mongod's TTL monitor sweeps roughly every 60 s …",
  },
  reasoning: 'Every row above is what the live guide_demo database answered.',
};

function makeRepository(): MongoConsoleRepositoryImpl {
  return new MongoConsoleRepositoryImpl(new MongoConsoleApi(createAppConfig()));
}

describe('MongoConsoleRepositoryImpl', () => {
  it('fetches and parses the console with both exhibits', async () => {
    stubApiFetch([{ url: MONGO_CONSOLE_URL, method: 'GET', body: payload }]);

    const result = await makeRepository().console('indexes');

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.database).toBe('guide_demo');
      expect(result.value.seed.totalAfter).toBe(6);
      expect(result.value.operations).toHaveLength(5);
      expect(result.value.indexShowcase.explains[1]?.stage).toBe('IXSCAN');
      expect(result.value.indexShowcase.explains[1]?.indexName).toBe('title_1');
      expect(result.value.indexShowcase.explains[0]?.indexName).toBeUndefined();
      expect(result.value.ttlShowcase.expireAfterSeconds).toBe(10);
    }
  });

  it('rejects a payload whose explain stage is not a string', async () => {
    const poisoned = {
      ...payload,
      indexShowcase: {
        ...payload.indexShowcase,
        explains: [{ ...payload.indexShowcase.explains[0], stage: 42 }],
      },
    };
    stubApiFetch([{ url: MONGO_CONSOLE_URL, method: 'GET', body: poisoned }]);

    const result = await makeRepository().console('indexes');

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('invalid_response');
    }
  });

  it('guards a network failure into a Failed Result (network_error, status 0)', async () => {
    stubNetworkFailure();

    const result = await makeRepository().console('indexes');

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.code).toBe('network_error');
      expect(result.failure.status).toBe(0);
    }
  });
});
