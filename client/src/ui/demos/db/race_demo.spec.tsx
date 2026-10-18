import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { DbRaceDemo } from './race_demo';
import { demoRegistry } from '../../demos/demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetDbRaceDemoUseCase } from '../../../domain/demo/get-db-race-demo-usecase';
import type { RaceDemo } from '../../../domain/demo/db-race';

/**
 * DbRaceDemo spec — fixture-driven (happy + failure): both runs render
 * with their timelines, the final slots show the lost update vs the
 * serialized pair, and failures degrade to the shared error panel with
 * recovery.
 */

const race: RaceDemo = {
  postId: 1,
  postTitle: 'Designing URLs people can read',
  baselineComments: 2,
  unlocked: {
    mode: 'read-modify-write',
    timeline: ['A BEGIN · B BEGIN', 'A reads COUNT(*) = 2', 'B reads COUNT(*) = 2'],
    finalSlots: [
      { author: 'race-runner-a', body: 'slot #3 (unlocked run)' },
      { author: 'race-runner-b', body: 'slot #3 (unlocked run)' },
    ],
    verdict: 'LOST UPDATE: both transactions wrote slot #3.',
  },
  locked: {
    mode: 'select-for-update',
    timeline: ['A locks the post row', 'B requests the same lock and BLOCKS'],
    finalSlots: [
      { author: 'race-runner-a', body: 'slot #3 (locked run)' },
      { author: 'race-runner-b', body: 'slot #4 (locked run)' },
    ],
    verdict: 'SERIALIZED: the lock ordered the runs.',
  },
  reasoning: 'Same statements; the difference is the lock.',
};

function stubUseCase(result: () => Promise<Result<RaceDemo>>): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetDbRaceDemoUseCase, {
    run: result,
  } as unknown as GetDbRaceDemoUseCase);
}

describe('DbRaceDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['db:race']).toBeDefined();
  });

  it('renders both runs with timelines, slots, and verdicts', async () => {
    stubUseCase(async () => success(race));

    render(<DbRaceDemo />);

    await waitFor(() => expect(screen.getAllByTestId('race-run')).toHaveLength(2));
    expect(screen.getAllByTestId('race-step')).toHaveLength(5);
    const slots = screen.getAllByTestId('race-slots');
    expect(slots[0]).toHaveTextContent('slot #3 (unlocked run)');
    expect(slots[1]).toHaveTextContent('slot #4 (locked run)');
    expect(screen.getByText(/LOST UPDATE/)).toBeInTheDocument();
    expect(screen.getByText(/SERIALIZED/)).toBeInTheDocument();
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
              requestId: 'req-21',
            }),
          )
        : success(race);
    });

    render(<DbRaceDemo />);

    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getAllByTestId('race-run')).toHaveLength(2));
  });
});
