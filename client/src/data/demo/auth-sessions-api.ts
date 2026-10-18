import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type {
  SessionInspection,
  SessionLoginOutcome,
  SessionLogoutOutcome,
  SessionsPanel,
} from '../../domain/demo/auth-sessions';
import {
  sessionInspectionFromJson,
  sessionLoginFromJson,
  sessionLogoutFromJson,
  sessionsPanelFromJson,
} from './auth-sessions-dto';

/**
 * AuthSessionsApi — the transport for the cookie lab's four endpoints. The
 * login/logout responses carry Set-Cookie headers the browser stores
 * automatically (same-origin through the dev proxy), so no explicit
 * credential handling is needed client-side.
 */

const PANEL_PATH = '/demo/auth/sessions';
const LOGIN_PATH = '/demo/auth/sessions/login';
const ME_PATH = '/demo/auth/sessions/me';
const LOGOUT_PATH = '/demo/auth/sessions/logout';

export class AuthSessionsApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/auth/sessions — the roster panel. */
  async panel(): Promise<SessionsPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PANEL_PATH);
      return parseDto(body, status, sessionsPanelFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/sessions/login — verify + Set-Cookie. */
  async login(username: string, password: string): Promise<SessionLoginOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, LOGIN_PATH, {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      return parseDto(body, status, sessionLoginFromJson);
    });
  }

  /** GET {apiBaseUrl}/demo/auth/sessions/me — the cookie resolves or 401s. */
  async inspect(): Promise<SessionInspection> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, ME_PATH);
      return parseDto(body, status, sessionInspectionFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/sessions/logout — revoke + clear. */
  async logout(): Promise<SessionLogoutOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, LOGOUT_PATH, {
        method: 'POST',
      });
      return parseDto(body, status, sessionLogoutFromJson);
    });
  }
}
