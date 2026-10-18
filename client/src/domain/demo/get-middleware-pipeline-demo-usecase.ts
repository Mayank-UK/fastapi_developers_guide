import type { Result } from '../../core/result';
import type { MiddlewarePipelineRepository } from './middleware-pipeline-repository';
import type { MiddlewarePipelineData } from './middleware-pipeline';

/**
 * GetMiddlewarePipelineDemoUseCase — fetches the middleware topic's live
 * onion (react-guide use-case style): a thin orchestration seam over the
 * repository port. Carries no parameters because the demo's subject is
 * the request itself — each execution is one fresh walk of the running
 * chain, with a fresh request id to prove the round trip.
 */
export class GetMiddlewarePipelineDemoUseCase {
  private readonly repository: MiddlewarePipelineRepository;

  constructor(repository: MiddlewarePipelineRepository) {
    this.repository = repository;
  }

  execute(): Promise<Result<MiddlewarePipelineData>> {
    return this.repository.read();
  }
}
