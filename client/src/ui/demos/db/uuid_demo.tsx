import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { UuidLab } from '../../../domain/demo/uuid-lab';

/**
 * UuidDemo — the sql-schema topic's id-strategy lab (demo block id
 * `db:uuid`). Renders the freshly minted comparison: one card per run
 * (uuid4, uuid7, sequence) with its values, the sortRanks proof, and
 * the sortable verdict; the layout card dissects one real UUIDv7 into
 * its five RFC 9562 fields (hex slice by hex slice, timestamp read
 * back); and the strategy cards compare locality, randomness,
 * coordination, and timing leakage. "Run it again" re-fetches — every
 * load is a new experiment.
 */

type LabStatus =
  | { state: 'loading' }
  | { state: 'ready'; lab: UuidLab }
  | { state: 'failed'; failure: Failure };

export function UuidDemo() {
  const useCase = container.getUuidLabDemoUseCase;
  const [status, setStatus] = useState<LabStatus>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    void useCase.lab().then((result) => {
      if (cancelled) return;
      setStatus(
        result.ok
          ? { state: 'ready', lab: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
    return () => {
      cancelled = true;
    };
  }, [useCase]);

  const runAgain = () => {
    setStatus({ state: 'loading' });
    void useCase.lab().then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', lab: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  if (status.state === 'loading') {
    return (
      <p data-testid="uuid-loading" className="text-body-sm text-on-surface-variant">
        minting fresh ids…
      </p>
    );
  }

  if (status.state === 'failed') {
    return <ErrorPanel subject="the UUID lab" failure={status.failure} onRetry={runAgain} />;
  }

  const { lab } = status;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="uuid-runs" className="flex flex-col gap-xs">
        {lab.runs.map((run) => (
          <article
            key={run.kind}
            data-testid="uuid-run"
            className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
          >
            <p className="font-mono text-caption text-on-surface">
              <span className="text-secondary">{run.kind}</span> — sorted == generated?{' '}
              <span className={run.sortable ? 'text-primary' : 'text-on-surface-variant'}>
                {String(run.sortable)}
              </span>
            </p>
            <p data-testid="uuid-ranks" className="font-mono text-caption text-on-surface-variant">
              ranks {run.sortRanks.join(', ')}
            </p>
            <p className="font-mono text-caption text-on-surface-variant">
              {run.values.slice(0, 4).join(' · ')}
              {run.values.length > 4 ? ` · … (${run.values.length} total)` : ''}
            </p>
          </article>
        ))}
      </section>

      <section
        data-testid="uuid-layout"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-on-surface">
          <span className="text-secondary">{lab.layout.value}</span> — timestamp{' '}
          {lab.layout.unixMs} ms
        </p>
        {lab.layout.segments.map((segment) => (
          <p key={segment.label} className="font-mono text-caption text-on-surface-variant">
            <span className="text-secondary">{segment.hexValue}</span> · {segment.label} (
            {segment.bits}b) — {segment.meaning}
          </p>
        ))}
        <p className="font-mono text-caption text-on-surface-variant">
          shared prefix of the uuid7 run: {lab.sharedPrefixHex}
        </p>
      </section>

      <section data-testid="uuid-strategies" className="flex flex-col gap-xxs">
        {lab.strategies.map((strategy) => (
          <p key={strategy.id} className="text-caption text-on-surface-variant">
            <span className="font-mono text-secondary">{strategy.name}</span> — {strategy.indexLocality}
            {strategy.randomBits !== undefined ? ` · ${strategy.randomBits} random bits` : ''} ·{' '}
            {strategy.coordination}
            {strategy.leaksTiming ? ' · leaks timing' : ' · hides timing'}
          </p>
        ))}
      </section>

      <p data-testid="uuid-reasoning" className="text-body-sm text-on-surface-variant">
        {lab.reasoning}
      </p>
    </div>
  );
}

export default UuidDemo;
