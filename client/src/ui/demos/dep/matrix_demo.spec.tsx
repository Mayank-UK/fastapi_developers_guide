import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { DepMatrixDemo } from './matrix_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetDepMatrixDemoUseCase } from '../../../domain/demo/get-dep-matrix-demo-usecase';
import type { DepMatrixData } from '../../../domain/demo/dep-matrix';

/**
 * DepMatrixDemo spec — fixture-driven (happy + failure): the component
 * resolves its use case through the container, so the spec swaps the token
 * registration (the container's documented replace-a-singleton seam)
 * instead of stubbing fetch. Behavior, not implementation: the matrix
 * loads on mount, every flavor row renders with its verdict and tokens,
 * resolving again keeps verdicts while tokens change, and a failure
 * degrades to the shared error panel with retry.
 */

const matrixFixture: DepMatrixData = {
  rows: [
    {
      flavor: 'function',
      label: 'plain function: asked once, cached for the whole request',
      tokens: ['Correlation#f1'],
      verdict: 'single',
    },
    {
      flavor: 'callable-class',
      label: '__call__ instance: provider at module scope, minted per request',
      tokens: ['ApiKeyIssuer#f2', 'matrix-ab12cd34'],
      verdict: 'single',
    },
    {
      flavor: 'cached-x2',
      label: 'same dependency asked twice (use_cache=True default)',
      tokens: ['RateBudget#f3', 'RateBudget#f3'],
      verdict: 'same-instance',
    },
    {
      flavor: 'uncached-x2',
      label: 'use_cache=False: the provider re-runs per parameter',
      tokens: ['Cursor#f4', 'Cursor#f5'],
      verdict: 'distinct-instances',
    },
    {
      flavor: 'chain-depth-3',
      label: 'top → middle → base; the handler also asks the middle directly',
      tokens: ['VerifiedRequest#f6', 'AuthenticatedActor#f7', 'ParsedToken#f8', 'AuthenticatedActor#f7'],
      verdict: 'shared-middle',
    },
    {
      flavor: 'sync-in-async',
      label: 'sync provider inside an async endpoint: threadpool vs event loop',
      tokens: ['dep-thread:AnyIO worker thread', 'handler-thread:asyncio-portal-x'],
      verdict: 'threadpool',
    },
  ],
};

function stubUseCase(respond: () => Result<DepMatrixData>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetDepMatrixDemoUseCase, {
    matrix: () => Promise.resolve(respond()),
  } as unknown as GetDepMatrixDemoUseCase);
}

describe('DepMatrixDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['dep:matrix']).toBeDefined();
  });

  it('loads the matrix on mount and renders every flavor with its verdict', async () => {
    stubUseCase(() => success(matrixFixture));

    render(<DepMatrixDemo />);
    await waitFor(() => {
      expect(screen.getByTestId('dep-matrix-table')).toBeInTheDocument();
    });

    const cached = screen.getByTestId('dep-matrix-row-cached-x2');
    expect(cached).toHaveTextContent('same-instance');
    expect(cached).toHaveTextContent('RateBudget#f3 / RateBudget#f3');

    const uncached = screen.getByTestId('dep-matrix-row-uncached-x2');
    expect(uncached).toHaveTextContent('distinct-instances');

    const chain = screen.getByTestId('dep-matrix-row-chain-depth-3');
    expect(chain).toHaveTextContent('shared-middle');

    const sync = screen.getByTestId('dep-matrix-row-sync-in-async');
    expect(sync).toHaveTextContent('threadpool');
    expect(sync).toHaveTextContent('dep-thread:AnyIO worker thread');

    expect(screen.getAllByTestId(/dep-matrix-row-/)).toHaveLength(6);
  });

  it('resolves again: verdicts hold while tokens change', async () => {
    let round = 0;
    stubUseCase(() =>
      success({
        rows: matrixFixture.rows.map((row) => ({
          ...row,
          tokens: row.tokens.map((token) => `${token}-r${round}`),
        })),
      }),
    );

    render(<DepMatrixDemo />);
    await waitFor(() => {
      expect(screen.getByTestId('dep-matrix-row-cached-x2')).toHaveTextContent(
        'RateBudget#f3-r0 / RateBudget#f3-r0',
      );
    });

    round = 1;
    fireEvent.click(screen.getByTestId('dep-matrix-resolve'));
    await waitFor(() => {
      expect(screen.getByTestId('dep-matrix-row-cached-x2')).toHaveTextContent(
        'RateBudget#f3-r1 / RateBudget#f3-r1',
      );
    });
    expect(screen.getByTestId('dep-matrix-row-cached-x2')).toHaveTextContent('same-instance');
  });

  it('degrades to the shared error panel with retry', async () => {
    let attempts = 0;
    stubUseCase(() => {
      attempts += 1;
      return failed(
        new ServerFailure('Request failed with status 503.', {
          code: 'service_unavailable',
          status: 503,
          requestId: 'req-66',
        }),
      );
    });

    render(<DepMatrixDemo />);
    await waitFor(() => {
      expect(screen.getByTestId('error-panel')).toBeInTheDocument();
    });
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');
    expect(screen.getByTestId('error-panel')).toHaveTextContent('request req-66');

    fireEvent.click(screen.getByText('Try again'));
    await waitFor(() => {
      expect(attempts).toBe(2);
    });
  });
});
