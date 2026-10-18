import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { type Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { GetEnvInspectorDemoUseCase } from '../../../domain/demo/get-env-inspector-demo-usecase';
import type {
  DataMode,
  EnvInspectorPanel,
  FailureInjection,
  ScenarioSnapshot,
  SettingRow,
} from '../../../domain/demo/env-inspector';

/**
 * EnvInspectorDemo — the environments topic's inspector (demo block id
 * `env:inspector`). One live read of the server's REAL configuration:
 * every setting with its env-var name, type, effective value, and source
 * badge ('env' when the process environment provides it, 'default' when
 * it fell back); secret-bearing rows arrive redacted server-side and show
 * only the length hint. The flags sub-panel drives the scenario store's
 * real PATCH — the runtime feature flags the last section teaches — and
 * re-reads the panel so the flipped flag is seen live.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: EnvInspectorPanel };

type WriteStatus =
  | { state: 'idle' }
  | { state: 'busy'; label: string }
  | { state: 'failed'; failure: Failure };

const DATA_MODES: readonly DataMode[] = ['fake', 'live'];
const INJECT_MODES: readonly FailureInjection[] = ['none', 'error', 'latency'];

function SourceBadge({ row }: { row: SettingRow }) {
  const tone =
    row.source === 'env'
      ? 'border-primary text-primary'
      : 'border-outline text-on-surface-variant';
  return (
    <span
      data-testid={`ei-source-${row.name}`}
      className={`rounded-sm border px-xxs font-mono text-caption ${tone}`}
    >
      {row.source}
    </span>
  );
}

function SettingRowLine({ row }: { row: SettingRow }) {
  return (
    <div
      data-testid={`ei-setting-${row.name}`}
      className="flex flex-wrap items-baseline gap-x-sm gap-y-xxs font-mono text-caption"
    >
      <span className="text-on-surface">{row.envVar}</span>
      <SourceBadge row={row} />
      <span className={row.secret ? 'text-warning' : 'text-on-surface-variant'}>
        {row.value}
      </span>
      {row.shapeHint !== null && (
        <span className="text-on-surface-variant">({row.shapeHint})</span>
      )}
      <span className="text-outline">[{row.type}]</span>
    </div>
  );
}

export default function EnvInspectorDemo() {
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [write, setWrite] = useState<WriteStatus>({ state: 'idle' });

  const loadPanel = useCallback(async () => {
    const useCase = container.getEnvInspectorDemoUseCase;
    const result: Result<EnvInspectorPanel> = await useCase.panel();
    if (result.ok) {
      setPanel({ state: 'ready', data: result.value });
    } else {
      setPanel({ state: 'failed', failure: result.failure });
    }
  }, []);

  useEffect(() => {
    void loadPanel();
  }, [loadPanel]);

  const patchFlag = useCallback(
    async (
      label: string,
      fire: (useCase: GetEnvInspectorDemoUseCase) => Promise<Result<ScenarioSnapshot>>,
    ) => {
      const useCase = container.getEnvInspectorDemoUseCase;
      setWrite({ state: 'busy', label });
      const result = await fire(useCase);
      if (!result.ok) {
        setWrite({ state: 'failed', failure: result.failure });
        return;
      }
      setWrite({ state: 'idle' });
      // Re-read the panel so the flipped flag is seen live, not assumed.
      await loadPanel();
    },
    [loadPanel],
  );

  if (panel.state === 'loading') {
    return <p data-testid="ei-loading">Reading the live configuration…</p>;
  }
  if (panel.state === 'failed') {
    return (
      <ErrorPanel
        subject="the configuration panel"
        failure={panel.failure}
        onRetry={() => {
          setPanel({ state: 'loading' });
          void loadPanel();
        }}
      />
    );
  }

  const data = panel.data;
  const busy = write.state === 'busy' ? write.label : null;

  return (
    <section className="flex flex-col gap-sm" data-testid="ei-panel">
      <header className="flex flex-wrap items-baseline gap-x-sm gap-y-xxs">
        <p className="font-mono text-caption text-primary" data-testid="ei-environment">
          environment: {data.environment} ({data.envVar})
        </p>
        <p className="font-mono text-caption text-on-surface-variant" data-testid="ei-facts">
          prefix {data.facts.envPrefix} · frozen: {String(data.facts.frozen)} · {data.facts.cache}
        </p>
      </header>

      <div className="flex flex-col gap-xxs" data-testid="ei-settings">
        {data.settings.map((row) => (
          <SettingRowLine key={row.name} row={row} />
        ))}
      </div>

      <p className="text-caption text-on-surface-variant" data-testid="ei-source-note">
        {data.sourceNote}
      </p>
      <p className="text-caption text-warning" data-testid="ei-redaction-note">
        {data.redactionNote}
      </p>

      <section className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs">
        <p className="text-caption text-on-surface" data-testid="ei-flags">
          flags · dataMode: {data.flags.dataMode} · injectFailure: {data.flags.injectFailure}
        </p>
        <div className="flex flex-wrap gap-xxs">
          {DATA_MODES.map((mode) => (
            <button
              key={mode}
              type="button"
              data-testid={`ei-mode-${mode}`}
              disabled={busy !== null || data.flags.dataMode === mode}
              className={`rounded-sm border px-xs py-xxs font-mono text-caption ${
                data.flags.dataMode === mode
                  ? 'border-primary text-primary'
                  : 'border-outline text-on-surface-variant'
              }`}
              onClick={() => void patchFlag(`dataMode:${mode}`, (u) => u.setDataMode(mode))}
            >
              dataMode {mode}
            </button>
          ))}
          {INJECT_MODES.map((mode) => (
            <button
              key={mode}
              type="button"
              data-testid={`ei-inject-${mode}`}
              disabled={busy !== null || data.flags.injectFailure === mode}
              className={`rounded-sm border px-xs py-xxs font-mono text-caption ${
                data.flags.injectFailure === mode
                  ? 'border-primary text-primary'
                  : 'border-outline text-on-surface-variant'
              }`}
              onClick={() =>
                void patchFlag(`injectFailure:${mode}`, (u) => u.setInjectFailure(mode))
              }
            >
              injectFailure {mode}
            </button>
          ))}
        </div>
        {busy !== null && (
          <p className="font-mono text-caption text-on-surface-variant" data-testid="ei-busy">
            patching {busy}…
          </p>
        )}
        {write.state === 'failed' && (
          <ErrorPanel
            subject="the flag patch"
            failure={write.failure}
            onRetry={() => setWrite({ state: 'idle' })}
          />
        )}
        <p className="text-caption text-on-surface-variant" data-testid="ei-flags-note">
          {data.flags.note} (write: {data.flags.patchEndpoint})
        </p>
      </section>
    </section>
  );
}
