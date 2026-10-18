import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { SqlLab } from '../../../domain/demo/sql-lab';

/**
 * SqlLabDemo — the databases-sql topic's hand-written SQL lab (demo
 * block id `db:sql-lab`). Three exhibits, each executed for real over
 * the seeded posts and comments: ranked (per-author ROW_NUMBER + global
 * RANK), window (running totals across the timeline), thread (a
 * recursive CTE walking one post's comment thread). The chosen
 * exhibit's verbatim SQL, its columns, and its rows — no ORM anywhere.
 */

type LabStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: SqlLab; switching: boolean }
  | { state: 'failed'; failure: Failure };

export function SqlLabDemo() {
  const useCase = container.getSqlLabDemoUseCase;
  const [status, setStatus] = useState<LabStatus>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    void useCase.run().then((result) => {
      if (cancelled) return;
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value, switching: false }
          : { state: 'failed', failure: result.failure },
      );
    });
    return () => {
      cancelled = true;
    };
  }, [useCase]);

  const pick = (exhibit: string) => {
    setStatus((current) =>
      current.state === 'ready' ? { ...current, switching: true } : current,
    );
    void useCase.run(exhibit).then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value, switching: false }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  if (status.state === 'loading') {
    return (
      <p data-testid="lab-loading" className="text-body-sm text-on-surface-variant">
        executing the exhibit…
      </p>
    );
  }

  if (status.state === 'failed') {
    return <ErrorPanel subject="the SQL lab" failure={status.failure} onRetry={() => pick('ranked')} />;
  }

  const { data } = status;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="lab-picker" className="flex flex-wrap gap-xxs">
        {data.exhibits.map((exhibit) => (
          <button
            key={exhibit.id}
            type="button"
            data-testid="lab-exhibit-btn"
            onClick={() => pick(exhibit.id)}
            className={`rounded-pill border px-sm py-xxs font-mono text-caption transition-colors ${
              exhibit.id === data.exhibit
                ? 'border-primary text-primary'
                : 'border-outline text-on-surface hover:border-primary hover:text-primary'
            }`}
          >
            {exhibit.name}
          </button>
        ))}
        {status.switching && (
          <span data-testid="lab-switching" className="text-caption text-on-surface-variant">
            switching…
          </span>
        )}
      </section>

      <section
        data-testid="lab-answer"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-on-surface">
          {data.rowCount} row(s) — real execution, one statement
        </p>
        <div className="overflow-x-auto rounded-md border border-outline">
          <table className="w-full text-left font-mono text-caption">
            <thead className="bg-surface-tint text-on-surface-variant">
              <tr>
                {data.columns.map((column) => (
                  <th key={column} scope="col" className="px-sm py-xxs">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, index) => (
                <tr key={index} data-testid="lab-row" className="border-t border-outline">
                  {data.columns.map((column) => (
                    <td key={column} className="px-sm py-xxs text-on-surface-variant">
                      {row[column] ?? '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p data-testid="lab-reading" className="text-caption text-on-surface-variant">
          {data.reading}
        </p>
      </section>

      <p data-testid="lab-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

export default SqlLabDemo;
