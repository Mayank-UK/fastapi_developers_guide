import type { Result } from '../../core/result';
import type { DepMatrixData } from './dep-matrix';

/**
 * DepMatrixRepository — the domain-facing port for the dependency-matrix
 * demo. Demo components depend on this interface only; the HTTP adapter
 * lives in data/demo and is wired at the composition root.
 */
export interface DepMatrixRepository {
  /** Resolve the whole dependency matrix in one request. */
  matrix(): Promise<Result<DepMatrixData>>;
}
