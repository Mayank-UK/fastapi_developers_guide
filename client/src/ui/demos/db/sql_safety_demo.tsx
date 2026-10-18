import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { SqlSafety } from '../../../domain/demo/sql-safety';

/**
 * SqlSafetyDemo — the databases-sql topic's injection probe (demo block
 * id `db:sql-safety`). One filter input, two query constructions: the
 * safe card REALLY EXECUTED with the input as a bind parameter (the
 * default input is the canonical injection payload, and it matches zero
 * rows as pure data), beside the interpolated statement rendered as
 * display text — executed: false, with the spliced SQL on screen.
 * Type any filter and replay it through both constructions.
 */

type SafetyStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: SqlSafety; replaying: boolean }
  | { state: 'failed'; failure: Failure };

export function SqlSafetyDemo() {
  const useCase = container.getSqlSafetyDemoUseCase;
  const [status, setStatus] = useState<SafetyStatus>({ state: 'loading' });
  const [filterDraft, setFilterDraft] = useState('');

  useEffect(() => {
    let cancelled = false;
    void useCase.run().then((result) => {
      if (cancelled) return;
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value, replaying: false }
          : { state: 'failed', failure: result.failure },
      );
    });
    return () => {
      cancelled = true;
    };
  }, [useCase]);

  const apply = (filter: string | undefined) => {
    setStatus((current) =>
      current.state === 'ready' ? { ...current, replaying: true } : current,
    );
    void useCase.run(filter).then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value, replaying: false }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  if (status.state === 'loading') {
    return (
      <p data-testid="safety-loading" className="text-body-sm text-on-surface-variant">
        running the filter both ways…
      </p>
    );
  }

  if (status.state === 'failed') {
    return <ErrorPanel subject="the safety probe" failure={status.failure} onRetry={() => apply(undefined)} />;
  }

  const { data } = status;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="safety-input" className="flex flex-col gap-xxs">
        <p className="text-caption text-on-surface-variant">
          filter value — type anything; quotes and semicolons are welcome:
        </p>
        <div className="flex gap-xxs">
          <input
            data-testid="safety-filter-field"
            type="text"
            value={filterDraft}
            maxLength={200}
            onChange={(event) => setFilterDraft(event.target.value)}
            placeholder={data.filterValue}
            className="w-full rounded-md border border-outline bg-surface px-sm py-xxs font-mono text-caption text-on-surface"
          />
          <button
            type="button"
            data-testid="safety-replay"
            onClick={() => apply(filterDraft === '' ? undefined : filterDraft)}
            className="rounded-pill border border-outline px-sm py-xxs text-caption text-on-surface transition-colors hover:border-primary hover:text-primary"
          >
            {status.replaying ? 'replaying…' : 'replay'}
          </button>
        </div>
      </section>

      <section
        data-testid="safety-safe"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-on-surface">
          <span className="text-primary">safe — executed</span> · bind{' '}
          {data.safe.parameterName} ={' '}
          <span className="text-secondary">{data.safe.parameterValue}</span>
        </p>
        <p className="font-mono text-caption text-on-surface-variant">
          {data.safe.sql.trim().split('\n')[2]}
        </p>
        <p data-testid="safety-row-count" className="text-caption text-on-surface-variant">
          {data.safe.rowCount} row(s) matched — the input arrived as DATA.
        </p>
        {data.safe.rows.slice(0, 3).map((row) => (
          <p key={row.id} className="font-mono text-caption text-on-surface-variant">
            {row.title} <span className="text-secondary">({row.status})</span>
          </p>
        ))}
      </section>

      <section
        data-testid="safety-unsafe"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-on-surface">
          <span className="text-error">unsafe — rendered only</span> · executed:{' '}
          {String(data.unsafe.executed)}
        </p>
        <p data-testid="safety-rendered" className="font-mono text-caption text-on-surface-variant">
          {data.unsafe.renderedSql}
        </p>
        <p className="text-caption text-on-surface-variant">{data.unsafe.why}</p>
      </section>

      <p data-testid="safety-wildcard" className="text-caption text-on-surface-variant">
        {data.wildcardNote}
      </p>
      <p data-testid="safety-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

export default SqlSafetyDemo;
