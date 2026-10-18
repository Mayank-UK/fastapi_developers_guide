import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { DepMatrixData, DepMatrixVerdict } from '../../../domain/demo/dep-matrix';

/**
 * DepMatrixDemo — the dependency topic's matrix demo (demo block id
 * `dep:matrix`). One request resolves every dependency flavor server-side
 * and answers with identity proofs: instance tokens derived from id()
 * (equal tokens = same instance, per-request cache) and thread names for
 * the sync-provider row (threadpool vs event loop). The table renders the
 * verdicts; refresh and the verdicts hold while the tokens change — new
 * request, new instances, same rules.
 *
 * Dependency flow mirrors the other demos: the use case resolves from the
 * container at render time (specs substitute fakes through the container
 * token — the documented replace-a-singleton seam); failures arrive as
 * typed Failures inside Results and render through the shared ErrorPanel.
 */

type MatrixStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: DepMatrixData }
  | { state: 'error'; failure: Failure };

const VERDICT_CLASS: Record<DepMatrixVerdict, string> = {
  single: 'text-on-surface-variant',
  'same-instance': 'text-secondary',
  'distinct-instances': 'text-primary',
  'shared-middle': 'text-secondary',
  threadpool: 'text-error',
  'event-loop': 'text-error',
};

const buttonClass =
  'self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption uppercase tracking-wide ' +
  'text-on-surface transition-colors hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-50';

export function DepMatrixDemo() {
  const useCase = container.getDepMatrixDemoUseCase;
  const [status, setStatus] = useState<MatrixStatus>({ state: 'loading' });

  const resolve = useCallback(() => {
    setStatus({ state: 'loading' });
    void useCase.matrix().then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'error', failure: result.failure },
      );
    });
  }, [useCase]);

  useEffect(() => {
    resolve();
  }, [resolve]);

  return (
    <div className="flex flex-col gap-md">
      <section className="flex flex-wrap items-center gap-sm">
        <button
          type="button"
          data-testid="dep-matrix-resolve"
          onClick={resolve}
          disabled={status.state === 'loading'}
          className={buttonClass}
        >
          Resolve again
        </button>
        {status.state === 'loading' && (
          <span data-testid="dep-matrix-loading" className="text-caption text-on-surface-variant">
            resolving the matrix…
          </span>
        )}
      </section>

      {status.state === 'error' && (
        <ErrorPanel subject="the dependency matrix" failure={status.failure} onRetry={resolve} />
      )}

      {status.state === 'ready' && (
        <section data-testid="dep-matrix-table-section" className="flex flex-col gap-xs">
          <p className="text-caption text-on-surface-variant">
            every flavor resolved in ONE request — equal tokens mean the same
            instance (the per-request cache); refresh and the verdicts hold
            while the tokens change
          </p>
          <div className="overflow-x-auto rounded-md border border-outline">
            <table data-testid="dep-matrix-table" className="w-full text-left font-mono text-caption">
              <thead className="bg-surface-tint text-on-surface-variant">
                <tr>
                  <th scope="col" className="px-sm py-xxs">flavor</th>
                  <th scope="col" className="px-sm py-xxs">verdict</th>
                  <th scope="col" className="px-sm py-xxs">tokens</th>
                  <th scope="col" className="px-sm py-xxs">what it proves</th>
                </tr>
              </thead>
              <tbody>
                {status.data.rows.map((row) => (
                  <tr
                    key={row.flavor}
                    data-testid={`dep-matrix-row-${row.flavor}`}
                    className="border-t border-outline"
                  >
                    <td className="px-sm py-xxs text-on-surface">{row.flavor}</td>
                    <td className={`px-sm py-xxs ${VERDICT_CLASS[row.verdict]}`}>
                      {row.verdict}
                    </td>
                    <td className="px-sm py-xxs text-on-surface-variant">
                      {row.tokens.join(' / ')}
                    </td>
                    <td className="px-sm py-xxs text-on-surface-variant">{row.label}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

export default DepMatrixDemo;
