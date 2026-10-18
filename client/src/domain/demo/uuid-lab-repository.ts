import type { Result } from '../../core/result';
import type { UuidLab } from './uuid-lab';

/**
 * UuidLabRepository — the domain-facing port for the sql-schema topic's
 * UUID lab demo. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition
 * root. One method, one observational endpoint: the server mints the
 * three comparison runs at request time.
 */
export interface UuidLabRepository {
  /** Fetch the uuid4 vs uuid7 vs sequence comparison, freshly minted. */
  lab(): Promise<Result<UuidLab>>;
}
