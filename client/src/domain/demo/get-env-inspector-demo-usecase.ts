import type { Result } from '../../core/result';
import type { EnvInspectorRepository } from './env-inspector-repository';
import type { DataMode, EnvInspectorPanel, FailureInjection, ScenarioSnapshot } from './env-inspector';

/**
 * GetEnvInspectorDemoUseCase — the environments topic's inspector: one
 * live panel over the server's REAL configuration (settings, honest
 * source attribution, server-side-redacted secrets) plus the flag write
 * path over the scenario store the whole guide shares.
 */
export class GetEnvInspectorDemoUseCase {
  private readonly repository: EnvInspectorRepository;

  constructor(repository: EnvInspectorRepository) {
    this.repository = repository;
  }

  /** The panel: every setting, its source, the redacted secrets, the flags. */
  panel(): Promise<Result<EnvInspectorPanel>> {
    return this.repository.panel();
  }

  /** Set the data-mode flag (fake ↔ live); answers the store's snapshot. */
  setDataMode(mode: DataMode): Promise<Result<ScenarioSnapshot>> {
    return this.repository.setDataMode(mode);
  }

  /** Set the failure-injection flag; answers the store's snapshot. */
  setInjectFailure(mode: FailureInjection): Promise<Result<ScenarioSnapshot>> {
    return this.repository.setInjectFailure(mode);
  }
}
