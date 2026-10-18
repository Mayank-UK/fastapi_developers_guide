import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type {
  HashingPanel,
  PasswordHashOutcome,
  PasswordVerifyOutcome,
} from '../../domain/demo/auth-hashing';
import {
  hashingPanelFromJson,
  passwordHashFromJson,
  passwordVerifyFromJson,
} from './auth-hashing-dto';

/**
 * AuthHashingApi — the transport for the hashing lab's three endpoints.
 * The hash and verify bodies carry the password once, over the proxy, and
 * the outcomes carry only hashes, verdicts, and honest timings.
 */

const PANEL_PATH = '/demo/auth/hashing';
const HASH_PATH = '/demo/auth/hashing/hash';
const VERIFY_PATH = '/demo/auth/hashing/verify';

export class AuthHashingApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/auth/hashing — the contract panel. */
  async panel(): Promise<HashingPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PANEL_PATH);
      return parseDto(body, status, hashingPanelFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/hashing/hash — real cost, fresh salt. */
  async hash(password: string): Promise<PasswordHashOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, HASH_PATH, {
        method: 'POST',
        body: JSON.stringify({ password }),
      });
      return parseDto(body, status, passwordHashFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/hashing/verify — match + rehash verdict. */
  async verify(password: string, hash: string): Promise<PasswordVerifyOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, VERIFY_PATH, {
        method: 'POST',
        body: JSON.stringify({ password, hash }),
      });
      return parseDto(body, status, passwordVerifyFromJson);
    });
  }
}
