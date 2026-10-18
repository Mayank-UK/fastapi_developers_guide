import type { Result } from '../../core/result';
import type {
  ApiKeyCallOutcome,
  ApiKeyCreated,
  ApiKeyRevokeOutcome,
  ApiKeysPanel,
} from './auth-api-keys';
import type { AuthApiKeysRepository } from './auth-api-keys-repository';

/**
 * GetAuthApiKeysDemoUseCase — the key lab's use case: generate (the raw
 * key's only appearance), the protected call with the header, revoke by
 * prefix — the hashed-key lifecycle in three actions.
 */
export class GetAuthApiKeysDemoUseCase {
  private readonly repository: AuthApiKeysRepository;

  constructor(repository: AuthApiKeysRepository) {
    this.repository = repository;
  }

  /** The roster: prefixes and hash previews, never secrets. */
  panel(): Promise<Result<ApiKeysPanel>> {
    return this.repository.panel();
  }

  /** Generate a key — the raw value's ONLY appearance. */
  generate(name: string, scopes: string[]): Promise<Result<ApiKeyCreated>> {
    return this.repository.generate(name, scopes);
  }

  /** The protected call with the x-api-key header. */
  call(key: string): Promise<Result<ApiKeyCallOutcome>> {
    return this.repository.call(key);
  }

  /** Revoke by prefix — instantly dead. */
  revoke(prefix: string): Promise<Result<ApiKeyRevokeOutcome>> {
    return this.repository.revoke(prefix);
  }
}
