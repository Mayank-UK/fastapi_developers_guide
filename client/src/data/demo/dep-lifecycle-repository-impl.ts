import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type {
  DepLifecycleLogData,
  DepLifecycleSpanData,
} from '../../domain/demo/dep-lifecycle';
import type { DepLifecycleRepository } from '../../domain/demo/dep-lifecycle-repository';
import { toDepLifecycleLog, toDepLifecycleSpan } from './dep-lifecycle-dto';
import type { DepLifecycleApi } from './dep-lifecycle-api';

/**
 * DepLifecycleRepositoryImpl — adapts the lifecycle API to the domain port.
 * Every thrown transport error (network, non-2xx envelope, malformed
 * payload) is guarded by safeRepositoryCall into a Failed Result, so the
 * demo component never needs try/catch and no rejection goes unhandled.
 */
export class DepLifecycleRepositoryImpl implements DepLifecycleRepository {
  private readonly api: DepLifecycleApi;

  constructor(api: DepLifecycleApi) {
    this.api = api;
  }

  fire(): Promise<Result<DepLifecycleSpanData>> {
    return safeRepositoryCall(async () => toDepLifecycleSpan(await this.api.fire()));
  }

  log(): Promise<Result<DepLifecycleLogData>> {
    return safeRepositoryCall(async () => toDepLifecycleLog(await this.api.log()));
  }
}
