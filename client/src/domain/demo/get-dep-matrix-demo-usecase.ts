import type { Result } from '../../core/result';
import type { DepMatrixData } from './dep-matrix';
import type { DepMatrixRepository } from './dep-matrix-repository';

/**
 * GetDepMatrixDemoUseCase — the dependency topic's matrix demo (react-guide
 * use-case style): a thin orchestration seam over the repository port.
 * Every flavor resolves server-side in ONE request; this use case hands the
 * identity proofs to the component, which renders the verdicts.
 */
export class GetDepMatrixDemoUseCase {
  private readonly repository: DepMatrixRepository;

  constructor(repository: DepMatrixRepository) {
    this.repository = repository;
  }

  matrix(): Promise<Result<DepMatrixData>> {
    return this.repository.matrix();
  }
}
