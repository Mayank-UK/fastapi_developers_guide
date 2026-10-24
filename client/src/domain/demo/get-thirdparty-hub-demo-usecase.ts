import type { Result } from '../../core/result';
import type { ThirdPartyHubPanel } from './thirdparty-hub';
import type { ThirdPartyHubRepository } from './thirdparty-hub-repository';

/**
 * GetThirdPartyHubDemoUseCase — the third-party topic's hub panel: one
 * read where the server lays out everything the app uses that it did
 * not build — the integrate-vs-build walk (verified against the real
 * manifest and server tree), the backing-service inventory with its
 * timeout/503 discipline, the key/secret surface as names never values,
 * and the real quotas.
 */
export class GetThirdPartyHubDemoUseCase {
  private readonly repository: ThirdPartyHubRepository;

  constructor(repository: ThirdPartyHubRepository) {
    this.repository = repository;
  }

  /** The third-party hub: decisions, integrations, secrets, quotas. */
  hub(): Promise<Result<ThirdPartyHubPanel>> {
    return this.repository.hub();
  }
}
