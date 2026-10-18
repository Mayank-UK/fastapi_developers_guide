import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { RuntimeAsyncRepository } from '../../domain/demo/runtime-async-repository';
import type { RuntimeAsyncDemoData } from '../../domain/demo/runtime-async';
import { toRuntimeAsyncDemo } from './runtime-async-dto';
import type { RuntimeAsyncApi } from './runtime-async-api';

/**
 * RuntimeAsyncRepositoryImpl — adapts the async-timing demo API to the
 * domain port. Every thrown transport error (network, non-2xx, malformed
 * payload) is guarded by safeRepositoryCall into a Failed Result, so the
 * demo component never needs try/catch and no rejection goes unhandled.
 */
export class RuntimeAsyncRepositoryImpl implements RuntimeAsyncRepository {
  private readonly api: RuntimeAsyncApi;

  constructor(api: RuntimeAsyncApi) {
    this.api = api;
  }

  async get(): Promise<Result<RuntimeAsyncDemoData>> {
    return safeRepositoryCall(async () => toRuntimeAsyncDemo(await this.api.get()));
  }
}
