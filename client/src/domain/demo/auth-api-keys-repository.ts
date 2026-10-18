import type { Result } from '../../core/result';
import type {
  ApiKeyCallOutcome,
  ApiKeyCreated,
  ApiKeyRevokeOutcome,
  ApiKeysPanel,
} from './auth-api-keys';

/**
 * AuthApiKeysRepository — the domain-facing port for the authentication
 * topic's key lab. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root.
 */
export interface AuthApiKeysRepository {
  /** The roster: prefixes and hash previews, never secrets. */
  panel(): Promise<Result<ApiKeysPanel>>;
  /** Generate a key — the raw value's ONLY appearance. */
  generate(name: string, scopes: string[]): Promise<Result<ApiKeyCreated>>;
  /** The protected call with the x-api-key header. */
  call(key: string): Promise<Result<ApiKeyCallOutcome>>;
  /** Revoke by prefix — instantly dead. */
  revoke(prefix: string): Promise<Result<ApiKeyRevokeOutcome>>;
}
