import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { StatelessPanel } from '../../domain/demo/scaling-stateless';
import type { ScalingStatelessRepository } from '../../domain/demo/scaling-stateless-repository';
import type { ScalingStatelessApi } from './scaling-stateless-api';

/**
 * ScalingStatelessRepositoryImpl — adapts the statelessness API to the
 * domain port. A Failed Result means the panel itself broke (network
 * down, unparseable body); the round's own observations arrive as DATA,
 * not as failures.
 */
export class ScalingStatelessRepositoryImpl implements ScalingStatelessRepository {
  private readonly api: ScalingStatelessApi;

  constructor(api: ScalingStatelessApi) {
    this.api = api;
  }

  panel(): Promise<Result<StatelessPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }
}
