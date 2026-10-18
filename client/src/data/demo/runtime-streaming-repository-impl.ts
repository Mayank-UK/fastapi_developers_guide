import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { RuntimeStreamingRepository } from '../../domain/demo/runtime-streaming-repository';
import type { RuntimeStreamingDemoData, StreamChunk } from '../../domain/demo/runtime-streaming';
import type { RuntimeStreamingApi } from './runtime-streaming-api';

/**
 * RuntimeStreamingRepositoryImpl — adapts the streaming demo API to the
 * domain port. The observer passes straight through (progressive chunks),
 * and every thrown transport error (network, non-2xx, malformed line) is
 * guarded by safeRepositoryCall into a Failed Result — the component never
 * needs try/catch and no rejection goes unhandled.
 */
export class RuntimeStreamingRepositoryImpl implements RuntimeStreamingRepository {
  private readonly api: RuntimeStreamingApi;

  constructor(api: RuntimeStreamingApi) {
    this.api = api;
  }

  get(onChunk?: (chunk: StreamChunk) => void): Promise<Result<RuntimeStreamingDemoData>> {
    return safeRepositoryCall(() => this.api.get(onChunk));
  }
}
