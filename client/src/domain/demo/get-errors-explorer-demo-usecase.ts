import type { Result } from '../../core/result';
import type { ErrorsExplorerRepository } from './errors-explorer-repository';
import type {
  ErrorsPanel,
  InjectedRound,
  ObservedFailure,
  ProbeRound,
  ScenarioSnapshot,
} from './errors-explorer';

/**
 * GetErrorsExplorerDemoUseCase — the exception-handling topic's lab: the
 * panel of eight kinds (from the taxonomy's own tables), the six real
 * trigger rounds against existing endpoints, and the scenario sub-panel
 * (read, inject, probe) over the store the whole guide shares. Observed
 * failures are SUCCESS results — the round failing is the point; a Failed
 * Result means the observation itself broke.
 */
export class GetErrorsExplorerDemoUseCase {
  private readonly repository: ErrorsExplorerRepository;

  constructor(repository: ErrorsExplorerRepository) {
    this.repository = repository;
  }

  /** The panel: the eight kinds, their triggers, their log events. */
  panel(): Promise<Result<ErrorsPanel>> {
    return this.repository.panel();
  }

  /** Fire validation_failed — a body the scenario model refuses (422). */
  fireValidationFailure(): Promise<Result<ObservedFailure>> {
    return this.repository.fireValidationFailure();
  }

  /** Fire unauthorized — the guarded edit with no credential (401). */
  fireUnauthorizedFailure(): Promise<Result<ObservedFailure>> {
    return this.repository.fireUnauthorizedFailure();
  }

  /** Fire forbidden — a minted token lacking the authority (403). */
  fireForbiddenFailure(): Promise<Result<ObservedFailure>> {
    return this.repository.fireForbiddenFailure();
  }

  /** Fire not_found — a well-formed id that names nothing (404). */
  fireNotFoundFailure(): Promise<Result<ObservedFailure>> {
    return this.repository.fireNotFoundFailure();
  }

  /** Fire rate_limited — the burner's budget drained to the 429. */
  fireRateLimitedFailure(): Promise<Result<ObservedFailure>> {
    return this.repository.fireRateLimitedFailure();
  }

  /** Fire internal — inject, watch the 500, reset, watch the 200. */
  fireInternalFailure(): Promise<Result<InjectedRound>> {
    return this.repository.fireInternalFailure();
  }

  /** The scenario store's current state. */
  readScenario(): Promise<Result<ScenarioSnapshot>> {
    return this.repository.readScenario();
  }

  /** Set the scenario's failure injection mode. */
  setInjectFailure(mode: ScenarioSnapshot['injectFailure']): Promise<Result<ScenarioSnapshot>> {
    return this.repository.setInjectFailure(mode);
  }

  /** One probe round: healthy outcome or the observed injected failure. */
  probe(): Promise<Result<ProbeRound>> {
    return this.repository.probe();
  }
}
