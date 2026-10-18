import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { MiddlewarePipelineData } from '../../domain/demo/middleware-pipeline';
import type { MiddlewarePipelineRepository } from '../../domain/demo/middleware-pipeline-repository';
import { toMiddlewarePipeline } from './middleware-pipeline-dto';
import type { MiddlewarePipelineApi } from './middleware-pipeline-api';

/**
 * MiddlewarePipelineRepositoryImpl — adapts the pipeline API to the domain
 * port. Every thrown transport error (network, non-2xx, malformed payload)
 * is guarded by safeRepositoryCall into a Failed Result, so the demo
 * component never needs try/catch and no rejection goes unhandled.
 */
export class MiddlewarePipelineRepositoryImpl implements MiddlewarePipelineRepository {
  private readonly api: MiddlewarePipelineApi;

  constructor(api: MiddlewarePipelineApi) {
    this.api = api;
  }

  read(): Promise<Result<MiddlewarePipelineData>> {
    return safeRepositoryCall(async () => toMiddlewarePipeline(await this.api.read()));
  }
}
