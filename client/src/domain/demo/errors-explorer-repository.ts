import type { Result } from '../../core/result';
import type {
  ErrorsPanel,
  InjectedRound,
  ObservedFailure,
  ProbeRound,
  ScenarioSnapshot,
} from './errors-explorer';

/**
 * ErrorsExplorerRepository — the domain-facing port for the exception-
 * handling topic's explorer. Demo components depend on this interface only;
 * the HTTP adapter lives in data/demo and is wired at the composition root.
 *
 * The fire* methods run REAL rounds against existing endpoints (the
 * authz-guarded edit, the posts resource, the security burner, the scenario
 * store, the probe) and resolve SUCCEEDED with the observed failure — the
 * observed envelope is the lab's teaching payload, never a Failed Result.
 * A Failed Result here means the observation itself broke (network down,
 * unparseable body), which is a different thing from the round failing.
 */
export interface ErrorsExplorerRepository {
  /** The panel: the eight kinds from the taxonomy's own tables. */
  panel(): Promise<Result<ErrorsPanel>>;
  /** Fire validation_failed: PATCH the scenario with an enum it refuses. */
  fireValidationFailure(): Promise<Result<ObservedFailure>>;
  /** Fire unauthorized: the guarded edit with no credential at all. */
  fireUnauthorizedFailure(): Promise<Result<ObservedFailure>>;
  /** Fire forbidden: a really minted token that lacks the authority. */
  fireForbiddenFailure(): Promise<Result<ObservedFailure>>;
  /** Fire not_found: a well-formed id that names nothing. */
  fireNotFoundFailure(): Promise<Result<ObservedFailure>>;
  /** Fire rate_limited: drain the burner's budget until the 429 answers. */
  fireRateLimitedFailure(): Promise<Result<ObservedFailure>>;
  /** Fire internal: inject, watch the 500, reset, watch the healthy probe. */
  fireInternalFailure(): Promise<Result<InjectedRound>>;
  /** The scenario store's current state (GET /api/demo/scenario). */
  readScenario(): Promise<Result<ScenarioSnapshot>>;
  /** PATCH the scenario's failure injection to one of the three modes. */
  setInjectFailure(mode: ScenarioSnapshot['injectFailure']): Promise<Result<ScenarioSnapshot>>;
  /** One probe round: healthy outcome or the observed injected failure. */
  probe(): Promise<Result<ProbeRound>>;
}
