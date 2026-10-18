import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import { UnknownFailure, type Failure } from '../../../core/error-handling/failures';
import { failed, type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetErrorsExplorerDemoUseCase } from '../../../domain/demo/get-errors-explorer-demo-usecase';
import type {
  ErrorKindRow,
  ErrorsPanel,
  InjectedRound,
  ObservedFailure,
  ProbeRound,
  ScenarioSnapshot,
} from '../../../domain/demo/errors-explorer';

/**
 * ExplorerDemo — the exception-handling topic's lab (demo block id
 * `errors:explorer`). The panel serves the eight kinds from the taxonomy's
 * own tables; each LIVE kind fires its real trigger against existing
 * endpoints and the observed round shows the envelope BESIDE the
 * x-request-id header with a match badge; the two RECIPE kinds state
 * plainly why no live trigger exists. The scenario sub-panel drives the
 * real GET/PATCH /api/demo/scenario and the probe — inject error, probe
 * (the 500), reset, probe (the healthy 200).
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: ErrorsPanel };

type FireStatus =
  | { state: 'idle' }
  | { state: 'busy'; kind: string }
  | { state: 'failed'; failure: Failure }
  | { state: 'observed'; round: ObservedFailure }
  | { state: 'injected'; round: InjectedRound };

type ScenarioStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; snapshot: ScenarioSnapshot };

type ProbeStatus =
  | { state: 'idle' }
  | { state: 'busy' }
  | { state: 'failed'; failure: Failure }
  | { state: 'round'; round: ProbeRound };

const INJECT_MODES = ['none', 'error', 'latency'] as const;

function shortId(id: string | null): string {
  return id === null ? '—' : id.length > 12 ? `${id.slice(0, 12)}…` : id;
}

function ObservedFailureCard({ round }: { round: ObservedFailure }) {
  return (
    <section
      data-testid="errors-explorer-result"
      className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
    >
      <p className="font-mono text-caption text-error">
        {round.httpStatus} · {round.code ?? 'no envelope code'} — {round.kind}
      </p>
      <p className="text-caption text-on-surface">{round.message ?? '(no message)'}</p>
      <p className="font-mono text-caption text-on-surface-variant">
        requestId (body): {shortId(round.requestId)} · (header):{' '}
        {shortId(round.requestIdHeader)}{' '}
        <span className={round.headerMatchesBody ? 'text-primary' : 'text-error'}>
          {round.headerMatchesBody ? '✓ match' : '✗ mismatch'}
        </span>
      </p>
      {round.retryAfterSeconds !== null && (
        <p className="font-mono text-caption text-on-surface-variant">
          Retry-After: {String(round.retryAfterSeconds)}s
        </p>
      )}
      {round.detailLine !== null && (
        <p className="font-mono text-caption text-on-surface-variant">
          details[0]: {round.detailLine}
        </p>
      )}
      {round.attempts !== null && (
        <p className="font-mono text-caption text-on-surface-variant">
          ladder: {round.attempts.map((status) => String(status)).join(' → ')}
        </p>
      )}
    </section>
  );
}

function fireCall(
  useCase: GetErrorsExplorerDemoUseCase,
  kind: string,
): Promise<Result<ObservedFailure> | Result<InjectedRound>> {
  switch (kind) {
    case 'validation_failed':
      return useCase.fireValidationFailure();
    case 'unauthorized':
      return useCase.fireUnauthorizedFailure();
    case 'forbidden':
      return useCase.fireForbiddenFailure();
    case 'not_found':
      return useCase.fireNotFoundFailure();
    case 'rate_limited':
      return useCase.fireRateLimitedFailure();
    case 'internal':
      return useCase.fireInternalFailure();
    default: {
      // Unreachable while the panel's kinds drive the buttons — kept as an
      // honest never-fire fallback rather than a cast.
      return Promise.resolve(
        failed(
          new UnknownFailure(`no live trigger for ${kind}`, {
            code: 'unknown_error',
            status: 0,
          }),
        ),
      );
    }
  }
}

export function ExplorerDemo() {
  const useCase = container.getErrorsExplorerDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [fire, setFire] = useState<FireStatus>({ state: 'idle' });
  const [scenario, setScenario] = useState<ScenarioStatus>({ state: 'loading' });
  const [probe, setProbe] = useState<ProbeStatus>({ state: 'idle' });
  const [switching, setSwitching] = useState(false);

  const refreshPanel = useCallback(() => {
    void useCase.panel().then((result) => {
      setPanel(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  }, [useCase]);

  const refreshScenario = useCallback(() => {
    void useCase.readScenario().then((result) => {
      setScenario(
        result.ok
          ? { state: 'ready', snapshot: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  }, [useCase]);

  useEffect(() => {
    refreshPanel();
    refreshScenario();
  }, [refreshPanel, refreshScenario]);

  if (panel.state === 'loading') {
    return (
      <p data-testid="errors-explorer-loading" className="text-body-sm text-on-surface-variant">
        reading the errors explorer…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return (
      <ErrorPanel subject="the errors explorer" failure={panel.failure} onRetry={refreshPanel} />
    );
  }

  const { data } = panel;

  function fireKind(kind: string): void {
    setFire({ state: 'busy', kind });
    void fireCall(useCase, kind).then((result) => {
      if (!result.ok) {
        setFire({ state: 'failed', failure: result.failure });
        return;
      }
      if ('failure' in result.value && 'recovered' in result.value) {
        setFire({ state: 'injected', round: result.value });
      } else {
        setFire({ state: 'observed', round: result.value });
      }
      refreshScenario();
    });
  }

  function runProbe(): void {
    setProbe({ state: 'busy' });
    void useCase.probe().then((result) => {
      setProbe(
        result.ok
          ? { state: 'round', round: result.value }
          : { state: 'failed', failure: result.failure },
      );
      refreshScenario();
    });
  }

  function switchMode(mode: (typeof INJECT_MODES)[number]): void {
    setSwitching(true);
    void useCase.setInjectFailure(mode).then(() => {
      refreshScenario();
      setSwitching(false);
    });
  }

  const renderKindRow = (row: ErrorKindRow) => (
    <div key={row.kind} className="flex flex-col gap-xxs">
      <p className="font-mono text-caption text-on-surface">
        <span className="text-primary">
          {row.kind} · {String(row.httpStatus)}
        </span>{' '}
        — {row.defaultMessage}
      </p>
      <p className="text-caption text-on-surface-variant">raised by: {row.raisedBy}</p>
      <p className="text-caption text-on-surface-variant">logged as: {row.loggedAs}</p>
      <p className="text-caption text-on-surface-variant">
        {row.trigger.mode === 'live' ? (
          <>
            trigger: {row.trigger.method} {row.trigger.path}
            {row.trigger.body !== null ? ` ${row.trigger.body}` : ''}
            {row.trigger.prep !== null ? ` — ${row.trigger.prep}` : ''}
          </>
        ) : (
          <>
            recipe only: {row.trigger.method} {row.trigger.path} — {row.trigger.note}
          </>
        )}
      </p>
      {row.trigger.mode === 'live' && (
        <button
          type="button"
          disabled={fire.state === 'busy'}
          onClick={() => fireKind(row.kind)}
          className="self-start rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
        >
          fire the real trigger
        </button>
      )}
    </div>
  );

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="errors-explorer-kinds"
        className="flex flex-col gap-sm rounded-md border border-outline px-sm py-xs"
      >
        {data.kinds.map(renderKindRow)}
      </section>

      {fire.state === 'busy' && (
        <p data-testid="errors-explorer-firing" className="text-caption text-on-surface-variant">
          firing {fire.kind}…
        </p>
      )}
      {fire.state === 'failed' && (
        <p data-testid="errors-explorer-error" className="text-caption text-error">
          {fire.failure.message}
        </p>
      )}
      {fire.state === 'observed' && <ObservedFailureCard round={fire.round} />}
      {fire.state === 'injected' && (
        <section
          data-testid="errors-explorer-injected"
          className="flex flex-col gap-xs rounded-md border border-outline px-sm py-xs"
        >
          <ObservedFailureCard round={fire.round.failure} />
          <p className="font-mono text-caption text-primary">
            reset → probe {fire.round.recovered.status} · injectFailure{' '}
            {fire.round.recovered.injectFailure} — recovered
          </p>
        </section>
      )}

      <section
        data-testid="errors-explorer-scenario"
        className="flex flex-col gap-xs rounded-md border border-outline px-sm py-xs"
      >
        <p className="text-caption text-on-surface">
          the scenario store ({data.scenario.getEndpoint}) —{' '}
          {scenario.state === 'ready'
            ? `dataMode ${scenario.snapshot.dataMode} · injectFailure ${scenario.snapshot.injectFailure}`
            : scenario.state === 'failed'
              ? scenario.failure.message
              : 'reading…'}
        </p>
        <div className="flex flex-wrap items-center gap-xs">
          {INJECT_MODES.map((mode) => (
            <button
              key={mode}
              type="button"
              disabled={switching}
              onClick={() => switchMode(mode)}
              className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
            >
              {mode}
            </button>
          ))}
          <button
            type="button"
            disabled={probe.state === 'busy'}
            onClick={runProbe}
            className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
          >
            probe
          </button>
        </div>
        <p className="text-caption text-on-surface-variant">{data.scenario.note}</p>
        {probe.state === 'failed' && (
          <p data-testid="errors-explorer-probe-error" className="text-caption text-error">
            {probe.failure.message}
          </p>
        )}
        {probe.state === 'round' && probe.round.outcome !== null && (
          <p data-testid="errors-explorer-probe-result" className="font-mono text-caption text-primary">
            200 · {probe.round.outcome.status} · injectFailure {probe.round.outcome.injectFailure}
          </p>
        )}
        {probe.state === 'round' && probe.round.failure !== null && (
          <ObservedFailureCard round={probe.round.failure} />
        )}
      </section>

      <p data-testid="errors-explorer-reasoning" className="text-body-sm text-on-surface-variant">
        {data.envelopeNote} {data.reasoning}
      </p>
    </div>
  );
}

export default ExplorerDemo;
