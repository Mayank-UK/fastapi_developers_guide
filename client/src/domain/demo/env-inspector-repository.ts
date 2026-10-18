import type { Result } from '../../core/result';
import type { DataMode, EnvInspectorPanel, FailureInjection, ScenarioSnapshot } from './env-inspector';

/**
 * EnvInspectorRepository — the domain-facing port for the environments
 * topic's inspector. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 *
 * The panel is one live read of the server's real configuration; the two
 * write methods drive the scenario store's PATCH (the flag write path the
 * panel's flags sub-panel documents) and answer with the store's new
 * snapshot.
 */
export interface EnvInspectorRepository {
  /** The panel: every setting, its source, the redacted secrets, the flags. */
  panel(): Promise<Result<EnvInspectorPanel>>;
  /** PATCH the scenario's data-mode flag (fake ↔ live). */
  setDataMode(mode: DataMode): Promise<Result<ScenarioSnapshot>>;
  /** PATCH the scenario's failure-injection flag (none / error / latency). */
  setInjectFailure(mode: FailureInjection): Promise<Result<ScenarioSnapshot>>;
}
