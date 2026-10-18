import type { Result } from '../../core/result';
import type { OrmProbeDemo } from './db-orm-probe';

/**
 * DbOrmProbeRepository — the domain-facing port for the sqlalchemy-orm
 * topic's probe demo. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 * One method, one endpoint: run the probe (repeatable — the proofs roll
 * back, so repeated runs answer identically).
 */
export interface DbOrmProbeRepository {
  /** Run the loading-strategy probe plus both session proofs. */
  probe(): Promise<Result<OrmProbeDemo>>;
}
