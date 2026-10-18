import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type {
  HashingPanel,
  PasswordHashOutcome,
  PasswordVerifyOutcome,
} from '../../domain/demo/auth-hashing';
import type { AuthHashingRepository } from '../../domain/demo/auth-hashing-repository';
import type { AuthHashingApi } from './auth-hashing-api';

/**
 * AuthHashingRepositoryImpl — adapts the hashing lab API to the domain
 * port. Every thrown transport error is guarded into a Failed Result.
 */
export class AuthHashingRepositoryImpl implements AuthHashingRepository {
  private readonly api: AuthHashingApi;

  constructor(api: AuthHashingApi) {
    this.api = api;
  }

  panel(): Promise<Result<HashingPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  hash(password: string): Promise<Result<PasswordHashOutcome>> {
    return safeRepositoryCall(() => this.api.hash(password));
  }

  verify(password: string, hash: string): Promise<Result<PasswordVerifyOutcome>> {
    return safeRepositoryCall(() => this.api.verify(password, hash));
  }
}
