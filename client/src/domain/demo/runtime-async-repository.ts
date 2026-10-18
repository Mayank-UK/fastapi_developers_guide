import type { Result } from '../../core/result';
import type { RuntimeAsyncDemoData } from './runtime-async';

/**
 * RuntimeAsyncRepository — the domain-facing port for the async-timing
 * demo payload. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root.
 */
export interface RuntimeAsyncRepository {
  /** The measured sequential-vs-gathered timing payload, computed per request. */
  get(): Promise<Result<RuntimeAsyncDemoData>>;
}
