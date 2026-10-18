import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { FastApiAppInfoData } from '../../domain/demo/fastapi-app-info';
import type { FastApiAppInfoRepository } from '../../domain/demo/fastapi-app-info-repository';
import { toFastApiAppInfo } from './fastapi-app-info-dto';
import type { FastApiAppInfoApi } from './fastapi-app-info-api';

/**
 * FastApiAppInfoRepositoryImpl — adapts the app-info API to the domain
 * port. Every thrown transport error (network, non-2xx, malformed payload)
 * is guarded by safeRepositoryCall into a Failed Result, so the demo
 * component never needs try/catch and no rejection goes unhandled.
 */
export class FastApiAppInfoRepositoryImpl implements FastApiAppInfoRepository {
  private readonly api: FastApiAppInfoApi;

  constructor(api: FastApiAppInfoApi) {
    this.api = api;
  }

  get(): Promise<Result<FastApiAppInfoData>> {
    return safeRepositoryCall(async () => toFastApiAppInfo(await this.api.get()));
  }
}
