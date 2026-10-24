import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { ThirdPartyHubPanel } from '../../domain/demo/thirdparty-hub';
import type { ThirdPartyHubRepository } from '../../domain/demo/thirdparty-hub-repository';
import type { ThirdPartyHubApi } from './thirdparty-hub-api';

/**
 * ThirdPartyHubRepositoryImpl — adapts the hub API to the domain port. A
 * Failed Result means the panel itself broke (network down, unparseable
 * body); the hub's own rows arrive as DATA, not as failures.
 */
export class ThirdPartyHubRepositoryImpl implements ThirdPartyHubRepository {
  private readonly api: ThirdPartyHubApi;

  constructor(api: ThirdPartyHubApi) {
    this.api = api;
  }

  hub(): Promise<Result<ThirdPartyHubPanel>> {
    return safeRepositoryCall(() => this.api.hub());
  }
}
