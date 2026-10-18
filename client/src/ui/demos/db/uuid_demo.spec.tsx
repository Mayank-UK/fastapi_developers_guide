import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { UuidDemo } from './uuid_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetUuidLabDemoUseCase } from '../../../domain/demo/get-uuid-lab-demo-usecase';
import type { UuidLab } from '../../../domain/demo/uuid-lab';

/**
 * UuidDemo spec — fixture-driven (happy + failure): the three runs
 * render with their ranks and sortable verdicts, the layout card
 * dissects the real UUIDv7 (five segments, timestamp, shared prefix),
 * the strategy cards compare the candidates, and failures degrade to
 * the shared error panel with recovery.
 */

const lab: UuidLab = {
  sampleCount: 12,
  runs: [
    {
      kind: 'uuid4',
      values: ['93e32229-e07a-467f-b136-2640ab681caa', '086fdb6a-7dcd-4a73-809e-ebd3436be5a5'],
      sortRanks: [1, 0],
      sortable: false,
    },
    {
      kind: 'uuid7',
      values: ['01a14438-4d32-72e5-8000-000000087d33', '01a14438-4d32-72e5-8000-000040878f2a'],
      sortRanks: [0, 1],
      sortable: true,
    },
    {
      kind: 'sequence',
      values: ['1', '2', '10'],
      sortRanks: [0, 2, 1],
      sortable: false,
    },
  ],
  sharedPrefixHex: '01a14438-4d32-72e5-8000-0000',
  layout: {
    value: '01a14438-4d32-72e5-8000-000000087d33',
    unixMs: 1792145902898,
    generatedAtIso: '2026-10-16T10:18:22.898000+00:00',
    segments: [
      { label: 'unix_ms', hexValue: '01a144384d32', bits: 48, meaning: 'milliseconds since epoch' },
      { label: 'version', hexValue: '7', bits: 4, meaning: 'always 7' },
      { label: 'rand_a', hexValue: '2e5', bits: 12, meaning: 'random base' },
    ],
  },
  strategies: [
    {
      id: 'sequence',
      name: 'bigserial (sequence)',
      sortableAsText: false,
      indexLocality: 'perfect appends',
      randomBits: 0,
      coordination: 'the database mints it',
      leaksTiming: true,
    },
    {
      id: 'uuid7',
      name: 'UUIDv7 (time-ordered)',
      sortableAsText: true,
      indexLocality: 'good clustering',
      randomBits: 74,
      coordination: 'none',
      leaksTiming: true,
    },
  ],
  reasoning: 'The uuid7 run sorts in generation order; the sequence falls into the text trap.',
};

function stubUseCase(labResult: () => Promise<Result<UuidLab>>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetUuidLabDemoUseCase, {
    lab: labResult,
  } as unknown as GetUuidLabDemoUseCase);
}

describe('UuidDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['db:uuid']).toBeDefined();
  });

  it('renders loading first, then the three runs with their ordering proofs', async () => {
    stubUseCase(async () => success(lab));

    render(<UuidDemo />);

    expect(screen.getByTestId('uuid-loading')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('uuid-runs')).toBeInTheDocument());

    const runs = screen.getAllByTestId('uuid-run');
    expect(runs).toHaveLength(3);
    expect(runs[0]).toHaveTextContent('uuid4');
    expect(runs[0]).toHaveTextContent('false');
    expect(runs[1]).toHaveTextContent('uuid7');
    expect(runs[1]).toHaveTextContent('true');
    expect(runs[2]).toHaveTextContent('sequence');
  });

  it('dissects the real uuid7 into segments with its timestamp and shared prefix', async () => {
    stubUseCase(async () => success(lab));

    render(<UuidDemo />);

    await waitFor(() => expect(screen.getByTestId('uuid-layout')).toBeInTheDocument());
    const layout = screen.getByTestId('uuid-layout');
    expect(layout).toHaveTextContent('01a14438-4d32-72e5-8000-000000087d33');
    expect(layout).toHaveTextContent('1792145902898');
    expect(layout).toHaveTextContent('unix_ms');
    expect(layout).toHaveTextContent('01a144384d32');
    expect(layout).toHaveTextContent('shared prefix');
  });

  it('renders the strategy comparison cards', async () => {
    stubUseCase(async () => success(lab));

    render(<UuidDemo />);

    await waitFor(() => expect(screen.getByTestId('uuid-strategies')).toBeInTheDocument());
    const strategies = screen.getByTestId('uuid-strategies');
    expect(strategies).toHaveTextContent('bigserial (sequence)');
    expect(strategies).toHaveTextContent('74 random bits');
    expect(strategies).toHaveTextContent('leaks timing');
  });

  it('degrades to the shared error panel on a Failed Result, with recovery', async () => {
    let calls = 0;
    stubUseCase(async () => {
      calls += 1;
      return calls === 1
        ? failed(
            new ServerFailure('The lab endpoint is down.', {
              code: 'service_unavailable',
              status: 503,
              requestId: 'req-88',
            }),
          )
        : success(lab);
    });

    render(<UuidDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    expect(screen.getByTestId('error-panel')).toHaveTextContent('service_unavailable');

    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('uuid-runs')).toBeInTheDocument());
    expect(screen.queryByTestId('error-panel')).not.toBeInTheDocument();
  });
});
