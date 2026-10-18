import type { Result } from '../../core/result';
import type { FastApiAppInfoData } from './fastapi-app-info';

/**
 * FastApiAppInfoRepository — the domain-facing port for the app-info demo.
 * Demo components depend on this interface only; the HTTP adapter lives in
 * data/demo and is wired at the composition root.
 */
export interface FastApiAppInfoRepository {
  /** Fetch the running app's introspection payload. */
  get(): Promise<Result<FastApiAppInfoData>>;
}
