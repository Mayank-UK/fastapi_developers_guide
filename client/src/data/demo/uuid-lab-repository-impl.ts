import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { UuidLab } from '../../domain/demo/uuid-lab';
import type { UuidLabRepository } from '../../domain/demo/uuid-lab-repository';
import type { UuidLabApi } from './uuid-lab-api';

/**
 * UuidLabRepositoryImpl — adapts the lab API to the domain port. Every
 * thrown transport error (network, non-2xx envelope, malformed payload)
 * is guarded by safeRepositoryCall into a Failed Result, so the demo
 * component never needs try/catch and no rejection goes unhandled.
 */
export class UuidLabRepositoryImpl implements UuidLabRepository {
  private readonly api: UuidLabApi;

  constructor(api: UuidLabApi) {
    this.api = api;
  }

  lab(): Promise<Result<UuidLab>> {
    return safeRepositoryCall(() => this.api.lab());
  }
}
