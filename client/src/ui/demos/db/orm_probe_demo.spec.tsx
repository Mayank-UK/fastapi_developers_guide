import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { DbOrmProbeDemo } from './orm_probe_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetDbOrmProbeDemoUseCase } from '../../../domain/demo/get-db-orm-probe-demo-usecase';
import type { OrmProbeDemo } from '../../../domain/demo/db-orm-probe';

/**
 * DbOrmProbeDemo spec — fixture-driven (happy + failure): the three
 * strategies render with their measured counts (lazy 9 vs selectin 3 vs
 * joined 1), both session proofs show, and failures degrade to the
 * shared error panel with recovery.
 */

const probe: OrmProbeDemo = {
  postCount: 5,
  firstPostTitle: 'Designing URLs people can read',
  strategies: [
    {
      strategy: 'lazy',
      sqlCount: 9,
      statements: ['SELECT posts.id FROM posts', 'SELECT authors.id FROM authors'],
      elapsedMs: 3.2,
      authorCount: 5,
      commentTotal: 11,
    },
    {
      strategy: 'joinedload',
      sqlCount: 1,
      statements: ['SELECT … LEFT OUTER JOIN authors … LEFT OUTER JOIN comments'],
      elapsedMs: 1.1,
      authorCount: 5,
      commentTotal: 11,
    },
    {
      strategy: 'selectinload',
      sqlCount: 3,
      statements: ['SELECT posts.id FROM posts', 'SELECT comments.post_id FROM comments WHERE IN'],
      elapsedMs: 1.7,
      authorCount: 5,
      commentTotal: 11,
    },
  ],
  resultsMatch: true,
  identityMap: {
    postId: 1,
    selectCount: 1,
    sameObject: true,
    statements: ['SELECT posts.id FROM posts WHERE id = 1'],
  },
  dirtyCheck: {
    postId: 1,
    field: 'status',
    before: 'published',
    after: 'draft',
    updateCount: 1,
    updateSql: 'UPDATE posts SET status=$1 WHERE posts.version = $4',
    committed: false,
  },
  reasoning: 'The same objects, three different query bills.',
};

function stubUseCase(result: () => Promise<Result<OrmProbeDemo>>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetDbOrmProbeDemoUseCase, {
    run: result,
  } as unknown as GetDbOrmProbeDemoUseCase);
}

describe('DbOrmProbeDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['db:orm-probe']).toBeDefined();
  });

  it('renders the three strategies with their measured counts and both proofs', async () => {
    stubUseCase(async () => success(probe));

    render(<DbOrmProbeDemo />);

    await waitFor(() =>
      expect(screen.getAllByTestId('orm-probe-strategy')).toHaveLength(3),
    );
    const cards = screen.getAllByTestId('orm-probe-strategy');
    expect(cards[0]).toHaveTextContent('lazy — 9 statement(s)');
    expect(cards[1]).toHaveTextContent('joinedload — 1 statement(s)');
    expect(cards[2]).toHaveTextContent('selectinload — 3 statement(s)');
    expect(screen.getByTestId('orm-probe-identity-proof')).toHaveTextContent(
      '1 SELECT · same object: true',
    );
    expect(screen.getByTestId('orm-probe-dirty-proof')).toHaveTextContent(
      '1 UPDATE on flush · committed: false',
    );
    expect(screen.getByTestId('orm-probe-dirty-sql')).toHaveTextContent(
      'posts.version = $4',
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
              requestId: 'req-63',
            }),
          )
        : success(probe);
    });

    render(<DbOrmProbeDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() =>
      expect(screen.getAllByTestId('orm-probe-strategy')).toHaveLength(3),
    );
  });
});
