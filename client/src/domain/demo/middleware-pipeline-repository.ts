import type { Result } from '../../core/result';
import type { MiddlewarePipelineData } from './middleware-pipeline';

/**
 * MiddlewarePipelineRepository — the domain-facing port for the middleware
 * pipeline demo. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root.
 */
export interface MiddlewarePipelineRepository {
  /** Walk the live middleware chain once: stack, traced order, request id. */
  read(): Promise<Result<MiddlewarePipelineData>>;
}
