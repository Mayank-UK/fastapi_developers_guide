import type { Result } from '../../core/result';
import type { FastApiAppInfoRepository } from './fastapi-app-info-repository';
import type { FastApiAppInfoData } from './fastapi-app-info';

/**
 * GetFastApiAppInfoDemoUseCase — fetches the fastapi-fundamentals topic's
 * app-introspection payload (react-guide use-case style): a thin
 * orchestration seam over the repository port. Carries no parameters —
 * the demo is observational; the server reports the app as it stands.
 */
export class GetFastApiAppInfoDemoUseCase {
  private readonly repository: FastApiAppInfoRepository;

  constructor(repository: FastApiAppInfoRepository) {
    this.repository = repository;
  }

  execute(): Promise<Result<FastApiAppInfoData>> {
    return this.repository.get();
  }
}
