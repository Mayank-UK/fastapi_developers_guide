import type { Result } from '../../core/result';
import type { OrmProbeDemo } from './db-orm-probe';
import type { DbOrmProbeRepository } from './db-orm-probe-repository';

/**
 * GetDbOrmProbeDemoUseCase — fetches the sqlalchemy-orm topic's probe
 * (react-guide use-case style): a thin orchestration seam over the
 * repository port. `run` re-runs the probe — the proofs roll back, so
 * repeated runs answer identically.
 */
export class GetDbOrmProbeDemoUseCase {
  private readonly repository: DbOrmProbeRepository;

  constructor(repository: DbOrmProbeRepository) {
    this.repository = repository;
  }

  /** Run the three strategies + both session proofs, once. */
  run(): Promise<Result<OrmProbeDemo>> {
    return this.repository.probe();
  }
}
