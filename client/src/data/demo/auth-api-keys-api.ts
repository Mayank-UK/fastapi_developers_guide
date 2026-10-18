import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type {
  ApiKeyCallOutcome,
  ApiKeyCreated,
  ApiKeyRevokeOutcome,
  ApiKeysPanel,
} from '../../domain/demo/auth-api-keys';
import {
  apiKeyCallFromJson,
  apiKeyCreatedFromJson,
  apiKeyRevokeFromJson,
  apiKeysPanelFromJson,
} from './auth-api-keys-dto';

/**
 * AuthApiKeysApi — the transport for the key lab's four endpoints. The
 * protected call sends the key in the x-api-key header; every failure
 * (missing, malformed, unknown prefix, wrong secret, revoked) arrives as
 * the shared 401 envelope → a Failed Result.
 */

const KEYS_PATH = '/demo/auth/keys';
const CALL_PATH = '/demo/auth/keys/call';
const REVOKE_PATH = '/demo/auth/keys/revoke';

export class AuthApiKeysApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/auth/keys — the roster (prefixes only). */
  async panel(): Promise<ApiKeysPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, KEYS_PATH);
      return parseDto(body, status, apiKeysPanelFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/keys — generate; raw key shown once. */
  async generate(name: string, scopes: string[]): Promise<ApiKeyCreated> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, KEYS_PATH, {
        method: 'POST',
        body: JSON.stringify({ name, scopes }),
      });
      return parseDto(body, status, apiKeyCreatedFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/keys/call — the x-api-key header authenticates. */
  async call(key: string): Promise<ApiKeyCallOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, CALL_PATH, {
        method: 'POST',
        headers: { 'x-api-key': key },
      });
      return parseDto(body, status, apiKeyCallFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/keys/revoke — prefix-keyed delete. */
  async revoke(prefix: string): Promise<ApiKeyRevokeOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, REVOKE_PATH, {
        method: 'POST',
        body: JSON.stringify({ prefix }),
      });
      return parseDto(body, status, apiKeyRevokeFromJson);
    });
  }
}
