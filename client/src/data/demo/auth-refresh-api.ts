import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type {
  RefreshExchangeOutcome,
  RefreshLoginOutcome,
  RefreshPanel,
} from '../../domain/demo/auth-refresh';
import {
  refreshExchangeFromJson,
  refreshLoginFromJson,
  refreshPanelFromJson,
} from './auth-refresh-dto';

/**
 * AuthRefreshApi — the transport for the refresh lab's three endpoints.
 * The exchange presents one raw refresh token; rotated answers carry the
 * successor (raw, once) and reuse-detected answers carry the kill count.
 */

const PANEL_PATH = '/demo/auth/refresh';
const LOGIN_PATH = '/demo/auth/refresh/login';
const EXCHANGE_PATH = '/demo/auth/refresh/exchange';

export class AuthRefreshApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/auth/refresh — the family board. */
  async panel(): Promise<RefreshPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PANEL_PATH);
      return parseDto(body, status, refreshPanelFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/refresh/login — family birth. */
  async login(username: string, password: string): Promise<RefreshLoginOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, LOGIN_PATH, {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      return parseDto(body, status, refreshLoginFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/refresh/exchange — rotate or trip the alarm. */
  async exchange(refreshToken: string): Promise<RefreshExchangeOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, EXCHANGE_PATH, {
        method: 'POST',
        body: JSON.stringify({ refreshToken }),
      });
      return parseDto(body, status, refreshExchangeFromJson);
    });
  }
}
