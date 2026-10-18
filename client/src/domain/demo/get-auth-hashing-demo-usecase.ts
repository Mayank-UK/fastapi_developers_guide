import type { Result } from '../../core/result';
import type {
  HashingPanel,
  PasswordHashOutcome,
  PasswordVerifyOutcome,
} from './auth-hashing';
import type { AuthHashingRepository } from './auth-hashing-repository';

/**
 * GetAuthHashingDemoUseCase — the hashing lab's use case: hash (fresh
 * salt, honest milliseconds), verify (match + rehash verdict at the same
 * cost), over the contract panel.
 */
export class GetAuthHashingDemoUseCase {
  private readonly repository: AuthHashingRepository;

  constructor(repository: AuthHashingRepository) {
    this.repository = repository;
  }

  /** The contract: active cost, legacy cost, the seeded credentials. */
  panel(): Promise<Result<HashingPanel>> {
    return this.repository.panel();
  }

  /** Hash a password: fresh salt, stamped parameters, honest milliseconds. */
  hash(password: string): Promise<Result<PasswordHashOutcome>> {
    return this.repository.hash(password);
  }

  /** Verify a candidate: match verdict, rehash verdict, same cost either way. */
  verify(password: string, hash: string): Promise<Result<PasswordVerifyOutcome>> {
    return this.repository.verify(password, hash);
  }
}
