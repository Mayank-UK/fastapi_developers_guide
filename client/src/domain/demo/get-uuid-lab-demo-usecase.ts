import type { Result } from '../../core/result';
import type { UuidLab } from './uuid-lab';
import type { UuidLabRepository } from './uuid-lab-repository';

/**
 * GetUuidLabDemoUseCase — fetches the sql-schema topic's UUID lab
 * (react-guide use-case style): a thin orchestration seam over the
 * repository port. The lab is observational — every call brings a
 * freshly minted comparison, so "run it again" is the experiment.
 */
export class GetUuidLabDemoUseCase {
  private readonly repository: UuidLabRepository;

  constructor(repository: UuidLabRepository) {
    this.repository = repository;
  }

  /** Fetch the freshly minted uuid4/uuid7/sequence comparison. */
  lab(): Promise<Result<UuidLab>> {
    return this.repository.lab();
  }
}
