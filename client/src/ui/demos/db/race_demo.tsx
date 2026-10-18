import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { RaceDemo, RaceRunCard } from '../../../domain/demo/db-race';

/**
 * DbRaceDemo — the databases-sql topic's race lab (demo block id
 * `db:race`). Two deterministic choreographies over the same post's
 * comment count, side by side: unlocked (both transactions read the
 * same count, both write the same slot — the lost update) and locked
 * (SELECT … FOR UPDATE serializes them). Every timeline step on screen,
 * verdicts computed from the final evidence, and re-running answers
 * identically — the interleave is ordered awaits, not sleeps.
 */

type RaceStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: RaceDemo }
  | { state: 'failed'; failure: Failure };

export function DbRaceDemo() {
  const useCase = container.getDbRaceDemoUseCase;
  const [status, setStatus] = useState<RaceStatus>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    void useCase.run().then((result) => {
      if (cancelled) return;
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
    return () => {
      cancelled = true;
    };
  }, [useCase]);

  const runAgain = () => {
    setStatus({ state: 'loading' });
    void useCase.run().then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  if (status.state === 'loading') {
    return (
      <p data-testid="race-loading" className="text-body-sm text-on-surface-variant">
        choreographing the race…
      </p>
    );
  }

  if (status.state === 'failed') {
    return <ErrorPanel subject="the race lab" failure={status.failure} onRetry={runAgain} />;
  }

  const { data } = status;

  return (
    <div className="flex flex-col gap-md">
      <p data-testid="race-subject" className="text-caption text-on-surface-variant">
        both runs raced over{' '}
        <span className="text-secondary">{data.postTitle}</span> (baseline{' '}
        {data.baselineComments} comments) under READ COMMITTED.
      </p>
      <RunCard run={data.unlocked} lostUpdate />
      <RunCard run={data.locked} lostUpdate={false} />
      <p data-testid="race-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

function RunCard({ run, lostUpdate }: { run: RaceRunCard; lostUpdate: boolean }) {
  return (
    <section
      data-testid="race-run"
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
    >
      <p className={`font-mono text-caption ${lostUpdate ? 'text-error' : 'text-primary'}`}>
        {run.mode}
      </p>
      {run.timeline.map((step, index) => (
        <p key={index} data-testid="race-step" className="font-mono text-caption text-on-surface-variant">
          {index + 1}. {step}
        </p>
      ))}
      <p data-testid="race-slots" className="font-mono text-caption text-on-surface">
        final:{' '}
        {run.finalSlots.map((slot, index) => (
          <span key={index} className="mr-sm">
            <span className="text-secondary">{slot.author}</span> wrote “{slot.body}”
          </span>
        ))}
      </p>
      <p className={`text-caption ${lostUpdate ? 'text-error' : 'text-primary'}`}>
        {run.verdict}
      </p>
    </section>
  );
}

export default DbRaceDemo;
