import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type {
  ErrorsPanel,
  InjectedRound,
  ObservedFailure,
  ProbeRound,
  ScenarioSnapshot,
} from '../../domain/demo/errors-explorer';
import type { ErrorsExplorerRepository } from '../../domain/demo/errors-explorer-repository';
import type { ErrorsExplorerApi } from './errors-explorer-api';

/**
 * ErrorsExplorerRepositoryImpl — adapts the explorer API to the domain port.
 * The fire* calls resolve SUCCEEDED with their observed failure (that is
 * the lab's payload); only a broken observation (network down, unparseable
 * body, a setup step that failed unexpectedly) becomes a Failed Result.
 */
export class ErrorsExplorerRepositoryImpl implements ErrorsExplorerRepository {
  private readonly api: ErrorsExplorerApi;

  constructor(api: ErrorsExplorerApi) {
    this.api = api;
  }

  panel(): Promise<Result<ErrorsPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  fireValidationFailure(): Promise<Result<ObservedFailure>> {
    return safeRepositoryCall(() => this.api.fireValidationFailure());
  }

  fireUnauthorizedFailure(): Promise<Result<ObservedFailure>> {
    return safeRepositoryCall(() => this.api.fireUnauthorizedFailure());
  }

  fireForbiddenFailure(): Promise<Result<ObservedFailure>> {
    return safeRepositoryCall(() => this.api.fireForbiddenFailure());
  }

  fireNotFoundFailure(): Promise<Result<ObservedFailure>> {
    return safeRepositoryCall(() => this.api.fireNotFoundFailure());
  }

  fireRateLimitedFailure(): Promise<Result<ObservedFailure>> {
    return safeRepositoryCall(() => this.api.fireRateLimitedFailure());
  }

  fireInternalFailure(): Promise<Result<InjectedRound>> {
    return safeRepositoryCall(() => this.api.fireInternalFailure());
  }

  readScenario(): Promise<Result<ScenarioSnapshot>> {
    return safeRepositoryCall(() => this.api.readScenario());
  }

  setInjectFailure(
    mode: ScenarioSnapshot['injectFailure'],
  ): Promise<Result<ScenarioSnapshot>> {
    return safeRepositoryCall(() => this.api.setInjectFailure(mode));
  }

  probe(): Promise<Result<ProbeRound>> {
    return safeRepositoryCall(() => this.api.probe());
  }
}
