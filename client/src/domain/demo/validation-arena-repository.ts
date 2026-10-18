import type { Result } from '../../core/result';
import type { ArenaRound, ArenaRoster, ArenaVerdict } from './validation-arena';

/**
 * ValidationArenaRepository — the domain-facing port for the validation
 * arena demo. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root. Two
 * methods, one per endpoint: the roster (what may be judged) and the
 * round (what the judgment said). Failures — including the 422 the edge
 * answers a malformed round body with — resolve as Failed Results.
 */
export interface ValidationArenaRepository {
  /** Fetch the roster: the real models, their fields, their rules. */
  roster(): Promise<Result<ArenaRoster>>;
  /** Submit one round; resolve the real pydantic verdict for it. */
  run(round: ArenaRound): Promise<Result<ArenaVerdict>>;
}
