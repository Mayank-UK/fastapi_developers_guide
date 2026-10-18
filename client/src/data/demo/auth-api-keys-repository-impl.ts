import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type {
  ApiKeyCallOutcome,
  ApiKeyCreated,
  ApiKeyRevokeOutcome,
  ApiKeysPanel,
} from '../../domain/demo/auth-api-keys';
import type { AuthApiKeysRepository } from '../../domain/demo/auth-api-keys-repository';
import type { AuthApiKeysApi } from './auth-api-keys-api';

/**
 * AuthApiKeysRepositoryImpl — adapts the key lab API to the domain port.
 * Every thrown transport error (including the 401 envelope a bad key
 * produces on the protected call) is guarded into a Failed Result.
 */
export class AuthApiKeysRepositoryImpl implements AuthApiKeysRepository {
  private readonly api: AuthApiKeysApi;

  constructor(api: AuthApiKeysApi) {
    this.api = api;
  }

  panel(): Promise<Result<ApiKeysPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  generate(name: string, scopes: string[]): Promise<Result<ApiKeyCreated>> {
    return safeRepositoryCall(() => this.api.generate(name, scopes));
  }

  call(key: string): Promise<Result<ApiKeyCallOutcome>> {
    return safeRepositoryCall(() => this.api.call(key));
  }

  revoke(prefix: string): Promise<Result<ApiKeyRevokeOutcome>> {
    return safeRepositoryCall(() => this.api.revoke(prefix));
  }
}
