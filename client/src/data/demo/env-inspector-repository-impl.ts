import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { DataMode, EnvInspectorPanel, FailureInjection, ScenarioSnapshot } from '../../domain/demo/env-inspector';
import type { EnvInspectorRepository } from '../../domain/demo/env-inspector-repository';
import type { EnvInspectorApi } from './env-inspector-api';

/**
 * EnvInspectorRepositoryImpl — adapts the inspector API to the domain port.
 * A Failed Result means the round itself broke (network down, unparseable
 * body); a successful panel is always the server's honest read, redacted
 * secrets included.
 */
export class EnvInspectorRepositoryImpl implements EnvInspectorRepository {
  private readonly api: EnvInspectorApi;

  constructor(api: EnvInspectorApi) {
    this.api = api;
  }

  panel(): Promise<Result<EnvInspectorPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  setDataMode(mode: DataMode): Promise<Result<ScenarioSnapshot>> {
    return safeRepositoryCall(() => this.api.setDataMode(mode));
  }

  setInjectFailure(mode: FailureInjection): Promise<Result<ScenarioSnapshot>> {
    return safeRepositoryCall(() => this.api.setInjectFailure(mode));
  }
}
