import type { Result } from '../../core/result';
import type { AuditDemo } from './db-audit';
import type { DbAuditRepository } from './db-audit-repository';

/**
 * GetDbAuditDemoUseCase — fetches the databases-sql topic's audit proof
 * (react-guide use-case style): a thin orchestration seam over the
 * repository port. `run` re-proves both halves; each run appends one
 * more row to the post's audited history.
 */
export class GetDbAuditDemoUseCase {
  private readonly repository: DbAuditRepository;

  constructor(repository: DbAuditRepository) {
    this.repository = repository;
  }

  /** Prove the pattern: one commit with its row, one rollback without. */
  run(): Promise<Result<AuditDemo>> {
    return this.repository.prove();
  }
}
