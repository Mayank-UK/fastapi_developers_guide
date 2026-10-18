import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { DbMongoConsoleDemo } from './mongo_console_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetMongoConsoleDemoUseCase } from '../../../domain/demo/get-mongo-console-demo-usecase';
import type { MongoConsoleDemo as MongoConsoleDemoModel } from '../../../domain/demo/mongo-console';

/**
 * MongoConsoleDemo spec — fixture-driven (happy + failure): the seed,
 * the boundary refusal, all five lifecycle operations, and both
 * exhibits (COLLSCAN vs IXSCAN, TTL definition) render with their real
 * outcomes, and failures degrade to the shared error panel with
 * recovery.
 */

const run: MongoConsoleDemoModel = {
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
    errors: [
      'title: String should have at least 3 characters',
      'status: Input should be one of the allowed values',
    ],
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
      command: 'db.console_notes.find({tags: "indexes"}, {…}).sort({created_at: -1})',
      outcome: '3 document(s) match',
      documents: [{ key: 'mongo-note-ttl', title: 'Expiry belongs in the index layer' }],
    },
    {
      op: 'update',
      description: '$set a field.',
      command: 'db.console_notes.update_one({…}, {$set: {…}})',
      outcome: 'matched 1, modified 1',
      documents: [],
    },
    {
      op: 'count',
      description: 'Same filter.',
      command: 'db.console_notes.count_documents({…})',
      outcome: '3 document(s)',
      documents: [],
    },
    {
      op: 'delete',
      description: 'Reset the stage.',
      command: 'db.console_notes.delete_one({…})',
      outcome: 'deletedCount 1',
      documents: [],
    },
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
    scratchDocuments: [{ label: 'ephemeral', expires_at: '2026-10-16T12:00:10+00:00' }],
    evictionNote: "mongod's TTL monitor sweeps roughly every 60 s …",
  },
  reasoning: 'Every row above is what the live guide_demo database answered.',
};

function stubUseCase(result: (tag: string) => Promise<Result<MongoConsoleDemoModel>>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetMongoConsoleDemoUseCase, {
    run: result,
  } as unknown as GetMongoConsoleDemoUseCase);
}

describe('MongoConsoleDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['db:mongo-console']).toBeDefined();
  });

  it('renders the seed, the refusal, the five operations, and both exhibits', async () => {
    stubUseCase(async () => success(run));

    render(<DbMongoConsoleDemo />);

    await waitFor(() => expect(screen.getByTestId('mongo-console-seed')).toBeInTheDocument());
    expect(screen.getByTestId('mongo-console-seed-proof')).toHaveTextContent(
      '6 already present · 0 planted · 6 total',
    );
    expect(screen.getAllByTestId('mongo-console-refusal')[0]).toHaveTextContent(
      'title: String should have at least 3 characters',
    );
    expect(screen.getByTestId('mongo-console-insert')).toHaveTextContent(
      'acknowledged — insertedId 6ad2104326caa2d2f80e8c67',
    );
    expect(screen.getByTestId('mongo-console-find')).toHaveTextContent('3 document(s) match');
    expect(screen.getByTestId('mongo-console-update')).toHaveTextContent('matched 1, modified 1');
    expect(screen.getByTestId('mongo-console-count')).toHaveTextContent('3 document(s)');
    expect(screen.getByTestId('mongo-console-delete')).toHaveTextContent('deletedCount 1');
    const explains = screen.getAllByTestId('mongo-console-explain');
    expect(explains[0]).toHaveTextContent('COLLSCAN');
    expect(explains[1]).toHaveTextContent('IXSCAN · keys=1 docs=1');
    expect(screen.getByTestId('mongo-console-ttl-definition')).toHaveTextContent(
      'name: expires_at_1',
    );
  });

  it('re-runs with the picked tag from the picker', async () => {
    const tags: string[] = [];
    stubUseCase(async (tag) => {
      tags.push(tag);
      return success(run);
    });

    render(<DbMongoConsoleDemo />);
    await waitFor(() => expect(screen.getByTestId('mongo-console-seed')).toBeInTheDocument());
    screen.getByRole('button', { name: 'modeling' }).click();
    await waitFor(() => expect(tags).toEqual(['indexes', 'modeling']));
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(async () => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('MongoDB is unreachable.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-64',
            }),
          )
        : success(run);
    });

    render(<DbMongoConsoleDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('mongo-console-seed')).toBeInTheDocument());
  });
});
