import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { DbMigrationsDemo } from './migrations_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetDbMigrationsDemoUseCase } from '../../../domain/demo/get-db-migrations-demo-usecase';
import type { MigrationsDemo } from '../../../domain/demo/db-migrations';

/**
 * DbMigrationsDemo spec — fixture-driven (happy + failure): both runs
 * render with their steps (applied / failed / rolled back), the failing
 * run's real error text shows, and failures degrade to the shared
 * error panel with recovery.
 */

const demo: MigrationsDemo = {
  scratchTable: 'migration_lab_scratch',
  failing: {
    scenario: 'failing',
    scratchTable: 'migration_lab_scratch',
    steps: [
      { description: 'create the scratch table', sql: 'CREATE TABLE …', outcome: 'applied' },
      { description: 'seed one row', sql: 'INSERT …', outcome: 'applied' },
      {
        description: 'add a NOT NULL column — fails',
        sql: 'ALTER TABLE … ADD COLUMN size integer NOT NULL',
        outcome: 'failed',
      },
    ],
    failure: 'column "size" of relation "migration_lab_scratch" contains null values',
    committed: false,
    tableExistsAfter: false,
  },
  succeeding: {
    scenario: 'succeeding',
    scratchTable: 'migration_lab_scratch',
    steps: [
      { description: 'create the scratch table', sql: 'CREATE TABLE …', outcome: 'applied' },
      { description: 'seed one row', sql: 'INSERT …', outcome: 'applied' },
      {
        description: 'the fixed step',
        sql: 'ALTER TABLE … ADD COLUMN size integer NOT NULL DEFAULT 0',
        outcome: 'applied',
      },
    ],
    committed: true,
    tableExistsAfter: true,
    rowCountAfter: 1,
  },
  cleanupNote: 'After the proof, the demo drops migration_lab_scratch again.',
  reasoning: 'Transactional DDL: all or nothing.',
};

function stubUseCase(result: () => Promise<Result<MigrationsDemo>>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetDbMigrationsDemoUseCase, {
    run: result,
  } as unknown as GetDbMigrationsDemoUseCase);
}

describe('DbMigrationsDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['db:migrations']).toBeDefined();
  });

  it('renders both runs with their steps and the real failure', async () => {
    stubUseCase(async () => success(demo));

    render(<DbMigrationsDemo />);

    await waitFor(() => expect(screen.getAllByTestId('mig-run')).toHaveLength(2));
    expect(screen.getAllByTestId('mig-step')).toHaveLength(6);
    expect(screen.getByTestId('mig-failure')).toHaveTextContent('contains null values');
    expect(screen.getByTestId('mig-cleanup')).toHaveTextContent('drops migration_lab_scratch');
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(async () => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('PostgreSQL is unreachable.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-18',
            }),
          )
        : success(demo);
    });

    render(<DbMigrationsDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getAllByTestId('mig-run')).toHaveLength(2));
  });
});
