import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { DeployStackPanel } from '../../domain/demo/deploy-stack';
import type { DeployStackRepository } from '../../domain/demo/deploy-stack-repository';
import type { DeployStackApi } from './deploy-stack-api';

/**
 * DeployStackRepositoryImpl — adapts the deploy-stack API to the domain
 * port. A Failed Result means the panel itself broke (network down,
 * unparseable body); the inspection's own degraded rows arrive as DATA
 * (manual verdicts with reasons), not as failures.
 */
export class DeployStackRepositoryImpl implements DeployStackRepository {
  private readonly api: DeployStackApi;

  constructor(api: DeployStackApi) {
    this.api = api;
  }

  panel(): Promise<Result<DeployStackPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }
}
