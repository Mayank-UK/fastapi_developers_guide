import type { Result } from '../../core/result';
import type { ArchTracerData } from './arch-tracer';

/**
 * ArchTracerRepository — the domain-facing port for the architecture
 * topic's tracer. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root.
 */
export interface ArchTracerRepository {
  /** Trace one request through every layer: structure, wiring, two real rounds. */
  read(): Promise<Result<ArchTracerData>>;
}
