import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { DbSearchDemo } from './search_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetDbSearchDemoUseCase } from '../../../domain/demo/get-db-search-demo-usecase';
import type { SearchDemo } from '../../../domain/demo/db-search';

/**
 * DbSearchDemo spec — fixture-driven (happy + empty + failure): the
 * parsed query renders, ranked matches show with scores and headlines,
 * both plans render, a zero-hit payload stays data (not an error), and
 * failures degrade to the shared error panel with recovery.
 */

const search: SearchDemo = {
  query: 'error envelope',
  parsedQuery: "'error' & 'envelop'",
  sql: 'SELECT …',
  matchCount: 2,
  matches: [
    {
      id: 7,
      slug: 'the-envelope-is-the-error-model',
      title: 'The envelope is the error model',
      rank: 0.10472721606492996,
      headline: 'The <b>envelope</b> is the <b>error</b> model',
    },
    {
      id: 2,
      slug: 'status-codes-are-a-contract',
      title: 'Status codes are a contract',
      rank: 0.09910321980714798,
      headline: 'the <b>error</b> envelope was never needed',
    },
  ],
  indexedPlan: ['Bitmap Heap Scan on posts p (actual time=0.018..0.020 rows=3 loops=1)'],
  naivePlan: ['Seq Scan on posts p (actual time=0.061..0.323 rows=3 loops=1)'],
  planNote: 'The indexed plan used SET LOCAL enable_seqscan = off — disclosed.',
  reasoning: 'Stems and ranks, both plans real.',
};

function stubUseCase(result: (q?: string) => Promise<Result<SearchDemo>>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetDbSearchDemoUseCase, {
    run: result,
  } as unknown as GetDbSearchDemoUseCase);
}

describe('DbSearchDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['db:search']).toBeDefined();
  });

  it('renders the parsed query, ranked matches, and both plans', async () => {
    stubUseCase(async () => success(search));

    render(<DbSearchDemo />);

    await waitFor(() => expect(screen.getByTestId('search-matches')).toBeInTheDocument());
    expect(screen.getByTestId('search-matches')).toHaveTextContent("'error' & 'envelop'");
    expect(screen.getAllByTestId('search-match')).toHaveLength(2);
    expect(screen.getByTestId('search-matches')).toHaveTextContent('0.1047');
    expect(screen.getByTestId('search-plans')).toHaveTextContent('Bitmap Heap Scan');
    expect(screen.getByTestId('search-plans')).toHaveTextContent('Seq Scan');
  });

  it('keeps a zero-hit payload as data, not an error', async () => {
    stubUseCase(async () =>
      success({ ...search, matches: [], matchCount: 0, parsedQuery: "'kubernetes'" }),
    );

    render(<DbSearchDemo />);

    await waitFor(() => expect(screen.getByTestId('search-matches')).toBeInTheDocument());
    expect(screen.getByTestId('search-matches')).toHaveTextContent('0 match(es)');
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
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
              requestId: 'req-20',
            }),
          )
        : success(search);
    });

    render(<DbSearchDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('search-matches')).toBeInTheDocument());
  });
});
