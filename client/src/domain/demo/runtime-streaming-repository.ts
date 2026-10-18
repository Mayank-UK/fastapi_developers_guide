import type { Result } from '../../core/result';
import type { RuntimeStreamingDemoData, StreamChunk } from './runtime-streaming';

/**
 * RuntimeStreamingRepository — the domain-facing port for the streaming
 * demo. The optional observer receives each chunk AS IT ARRIVES from the
 * wire (progressive rendering); the returned Result always carries the
 * complete collected stream, so consumers that ignore the observer see the
 * same data.
 */
export interface RuntimeStreamingRepository {
  get(onChunk?: (chunk: StreamChunk) => void): Promise<Result<RuntimeStreamingDemoData>>;
}
