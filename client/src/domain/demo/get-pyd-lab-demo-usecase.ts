import type { Result } from '../../core/result';
import type { PydLabRepository } from './pyd-lab-repository';
import type { PydLabReportData, PydLabSchemaData } from './pyd-lab';

/**
 * GetPydLabDemoUseCase — the pydantic topic's validation lab (react-guide
 * use-case style): a thin orchestration seam over the repository port.
 * Carries the interactive half too: the user edits a JSON payload, the
 * use case submits it verbatim so the SERVER's boundary decides —
 * including FastAPI's own 422 when the request model refuses the body.
 */
export class GetPydLabDemoUseCase {
  private readonly repository: PydLabRepository;

  constructor(repository: PydLabRepository) {
    this.repository = repository;
  }

  schema(): Promise<Result<PydLabSchemaData>> {
    return this.repository.schema();
  }

  validate(payload: unknown): Promise<Result<PydLabReportData>> {
    return this.repository.validate(payload);
  }
}
