import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SqlLabDemo } from './sql_lab_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetSqlLabDemoUseCase } from '../../../domain/demo/get-sql-lab-demo-usecase';
import type { SqlLab } from '../../../domain/demo/sql-lab';

/**
 * SqlLabDemo spec — fixture-driven (happy + failure): the exhibit
 * picker renders all three cards, the answer table carries the exhibit's
 * rows, and failures degrade to the shared error panel with recovery.
 */

const lab: SqlLab = {
  exhibit: 'thread',
  exhibits: [
    { id: 'ranked', name: 'CTE + ranking windows', teaches: 'ROW_NUMBER per author.' },
    { id: 'window', name: 'Running totals', teaches: 'SUM OVER a frame.' },
    { id: 'thread', name: 'Recursive CTE', teaches: 'WITH RECURSIVE hop by hop.' },
  ],
  sql: 'WITH RECURSIVE thread AS (…)',
  columns: ['depth', 'author'],
  rows: [
    { depth: '1', author: 'maya' },
    { depth: '2', author: 'tom' },
  ],
  rowCount: 2,
  reading: 'depth counts the recursion hops.',
  reasoning: 'One statement, real rows.',
};

function stubUseCase(result: (exhibit?: string) => Promise<Result<SqlLab>>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetSqlLabDemoUseCase, {
    run: result,
  } as unknown as GetSqlLabDemoUseCase);
}

describe('SqlLabDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['db:sql-lab']).toBeDefined();
  });

  it('renders the picker and the exhibit table with its rows', async () => {
    stubUseCase(async () => success(lab));

    render(<SqlLabDemo />);

    await waitFor(() => expect(screen.getByTestId('lab-answer')).toBeInTheDocument());
    expect(screen.getAllByTestId('lab-exhibit-btn')).toHaveLength(3);
    expect(screen.getAllByTestId('lab-row')).toHaveLength(2);
    expect(screen.getByTestId('lab-reading')).toHaveTextContent('recursion hops');
  });

  it('switches exhibits through the use case when a picker button is clicked', async () => {
    stubUseCase(async (exhibit?: string) =>
      success(exhibit === 'window' ? { ...lab, exhibit: 'window', rowCount: 12 } : lab),
    );

    render(<SqlLabDemo />);

    await waitFor(() => expect(screen.getByTestId('lab-answer')).toBeInTheDocument());
    const windowButton = screen.getAllByTestId('lab-exhibit-btn')[1];
    expect(windowButton).toBeDefined();
    windowButton?.click();
    await waitFor(() =>
      expect(screen.getByTestId('lab-answer')).toHaveTextContent('12 row(s)'),
    );
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
              requestId: 'req-19',
            }),
          )
        : success(lab);
    });

    render(<SqlLabDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('lab-answer')).toBeInTheDocument());
  });
});
