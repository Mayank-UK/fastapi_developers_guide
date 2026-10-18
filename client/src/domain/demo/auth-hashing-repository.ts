import type { Result } from '../../core/result';
import type {
  HashingPanel,
  PasswordHashOutcome,
  PasswordVerifyOutcome,
} from './auth-hashing';

/**
 * AuthHashingRepository — the domain-facing port for the authentication
 * topic's hashing lab. Demo components depend on this interface only; the
 * HTTP adapter lives in data/demo and is wired at the composition root.
 */
export interface AuthHashingRepository {
  /** The contract: active cost, legacy cost, the seeded credentials. */
  panel(): Promise<Result<HashingPanel>>;
  /** Hash a password: fresh salt, stamped parameters, honest milliseconds. */
  hash(password: string): Promise<Result<PasswordHashOutcome>>;
  /** Verify a candidate: match verdict, rehash verdict, same cost either way. */
  verify(password: string, hash: string): Promise<Result<PasswordVerifyOutcome>>;
}
