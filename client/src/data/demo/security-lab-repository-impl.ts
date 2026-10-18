import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { BurnResult, SecurityLabLoad } from '../../domain/demo/security-lab';
import type { SecurityLabRepository } from '../../domain/demo/security-lab-repository';
import type { SecurityLabApi } from './security-lab-api';

/**
 * SecurityLabRepositoryImpl — adapts the security lab API to the domain
 * port. Expected failures resolve as Failed Results; the 429 never throws
 * at all (the API shapes it as the typed throttle the lab teaches).
 */
export class SecurityLabRepositoryImpl implements SecurityLabRepository {
  private readonly api: SecurityLabApi;

  constructor(api: SecurityLabApi) {
    this.api = api;
  }

  panel(): Promise<Result<SecurityLabLoad>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  burn(): Promise<Result<BurnResult>> {
    return safeRepositoryCall(() => this.api.burn());
  }
}
