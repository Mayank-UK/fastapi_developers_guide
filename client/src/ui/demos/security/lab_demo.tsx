import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { BurnResult, ObservedHeaders, SecurityLabPanel } from '../../../domain/demo/security-lab';
import { ErrorPanel } from '../../components/error-panel';

/**
 * LabDemo — the security topic's lab (demo block id `security:lab`).
 * The panel shows the header table (documented WHY beside what the live
 * response actually carried — the fetch that rendered this panel), the
 * real CORS policy, and the throttle policy; the burner spends the REAL
 * budget until the dependency raises the 429 with Retry-After — shown as
 * the typed throttle it is, not an error.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: SecurityLabPanel; observed: ObservedHeaders };

type BurnLogEntry = { index: number; result: BurnResult };

export function LabDemo() {
  const useCase = container.getSecurityLabDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [burnLog, setBurnLog] = useState<BurnLogEntry[]>([]);
  const [burnBusy, setBurnBusy] = useState(false);

  const refreshPanel = useCallback(() => {
    void useCase.panel().then((result) => {
      setPanel(
        result.ok
          ? { state: 'ready', data: result.value.panel, observed: result.value.observedHeaders }
          : { state: 'failed', failure: result.failure },
      );
    });
  }, [useCase]);

  useEffect(() => {
    refreshPanel();
  }, [refreshPanel]);

  function burn(): void {
    setBurnBusy(true);
    void useCase.burn().then((result) => {
      if (result.ok) {
        setBurnLog((entries) => [...entries, { index: entries.length + 1, result: result.value }]);
      } else {
        setBurnLog((entries) => [
          ...entries,
          {
            index: entries.length + 1,
            result: {
              kind: 'throttled',
              throttled: {
                status: 429,
                retryAfterSeconds: null,
                message: `${result.failure.code}: ${result.failure.message}`,
              },
            },
          },
        ]);
      }
      setBurnBusy(false);
    });
  }

  if (panel.state === 'loading') {
    return (
      <p data-testid="security-lab-loading" className="text-body-sm text-on-surface-variant">
        reading the security lab…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return <ErrorPanel subject="the security lab" failure={panel.failure} onRetry={refreshPanel} />;
  }

  const { data, observed } = panel;
  const throttle = [...burnLog].reverse().find((entry) => entry.result.kind === 'throttled');

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="security-lab-headers"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        {data.headers.map((row) => (
          <p key={row.header} className="text-caption text-on-surface">
            <span className="font-mono text-primary">{row.header}</span> — {row.why}
            <span className="block font-mono text-caption text-on-surface-variant">
              live: {observed[row.header.toLowerCase()] ?? '(not on this response — e.g. HSTS is https-only)'}
            </span>
          </p>
        ))}
      </section>

      <section
        data-testid="security-lab-cors"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-on-surface">
          origins {data.cors.allowedOrigins.join(', ')} · credentials {String(data.cors.allowCredentials)}
        </p>
        <p className="font-mono text-caption text-on-surface-variant">
          methods {data.cors.allowedMethods.join(' ')} · headers {data.cors.allowedHeaders.join(' ')}
        </p>
        <p className="text-caption text-on-surface-variant">{data.cors.misconfigNote}</p>
      </section>

      <section data-testid="security-lab-burn" className="flex flex-col gap-xs">
        <p className="font-mono text-caption text-on-surface">
          burner: {data.rateLimit.budget} per {data.rateLimit.windowSeconds}s, keyed by{' '}
          {data.rateLimit.keying} — {data.rateLimit.whyPublicEndpoints}
        </p>
        <button
          type="button"
          onClick={burn}
          disabled={burnBusy}
          className="w-fit rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
        >
          burn one unit
        </button>
        {burnLog.slice(-6).map((entry) => (
          <p
            key={entry.index}
            data-testid="security-lab-burn-entry"
            className={`font-mono text-caption ${
              entry.result.kind === 'allowed' ? 'text-primary' : 'text-error'
            }`}
          >
            {entry.result.kind === 'allowed'
              ? `hit ${entry.result.outcome.attempt}: 200 · ${entry.result.outcome.remaining} left`
              : `hit: 429 · retry-after ${entry.result.throttled.retryAfterSeconds ?? '?'}s — ${entry.result.throttled.message}`}
          </p>
        ))}
        {throttle && (
          <p data-testid="security-lab-throttled" className="text-caption text-error">
            the handler never ran — the dependency raised the 429 before it; wait the
            Retry-After seconds and the budget slides open again
          </p>
        )}
      </section>

      <p data-testid="security-lab-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

export default LabDemo;
