import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { DepMatrixData } from '../../domain/demo/dep-matrix';
import type { DepMatrixRepository } from '../../domain/demo/dep-matrix-repository';
import { toDepMatrix } from './dep-matrix-dto';
import type { DepMatrixApi } from './dep-matrix-api';

/**
 * DepMatrixRepositoryImpl — adapts the matrix API to the domain port.
 * Every thrown transport error (network, non-2xx envelope, malformed
 * payload) is guarded by safeRepositoryCall into a Failed Result, so the
 * demo component never needs try/catch and no rejection goes unhandled.
 */
export class DepMatrixRepositoryImpl implements DepMatrixRepository {
  private readonly api: DepMatrixApi;

  constructor(api: DepMatrixApi) {
    this.api = api;
  }

  matrix(): Promise<Result<DepMatrixData>> {
    return safeRepositoryCall(async () => toDepMatrix(await this.api.matrix()));
  }
}
