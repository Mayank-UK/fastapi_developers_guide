import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type {
  BearerResource,
  JwtPanel,
  MintedToken,
  TokenLoginOutcome,
  TokenVerifyOutcome,
} from '../../domain/demo/auth-jwt';
import {
  bearerResourceFromJson,
  jwtPanelFromJson,
  mintedTokenFromJson,
  tokenLoginFromJson,
  tokenVerifyFromJson,
} from './auth-jwt-dto';

/**
 * AuthJwtApi — the transport for the token lab's five endpoints. The login
 * is the OAuth2 password form flow: the body is urlencoded (the form the
 * spec defines), not JSON. Protected calls carry the Bearer header.
 */

const PANEL_PATH = '/demo/auth/jwt';
const LOGIN_PATH = '/demo/auth/jwt/login';
const MINT_PATH = '/demo/auth/jwt/mint';
const VERIFY_PATH = '/demo/auth/jwt/verify';
const PROTECTED_PATH = '/demo/auth/jwt/protected';

export class AuthJwtApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/auth/jwt — the anatomy panel. */
  async panel(): Promise<JwtPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PANEL_PATH);
      return parseDto(body, status, jwtPanelFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/jwt/login — form-encoded credentials in. */
  async login(username: string, password: string): Promise<TokenLoginOutcome> {
    return guardedApiCall(async () => {
      const form = new URLSearchParams({ username, password }).toString();
      const { body, status } = await guardedSendJson(this.config, LOGIN_PATH, {
        method: 'POST',
        headers: { 'content-type': 'application/x-www-form-urlencoded' },
        body: form,
      });
      return parseDto(body, status, tokenLoginFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/jwt/mint — claims on demand. */
  async mint(
    username: string,
    scopes: string[],
    ttlSeconds: number,
    notBeforeSeconds: number,
    signWith: 'real' | 'wrong',
  ): Promise<MintedToken> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, MINT_PATH, {
        method: 'POST',
        body: JSON.stringify({
          username,
          scopes,
          ttlSeconds,
          notBeforeSeconds,
          signWith,
        }),
      });
      return parseDto(body, status, mintedTokenFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/jwt/verify — every failure classified. */
  async verify(token: string): Promise<TokenVerifyOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, VERIFY_PATH, {
        method: 'POST',
        body: JSON.stringify({ token }),
      });
      return parseDto(body, status, tokenVerifyFromJson);
    });
  }

  /** GET {apiBaseUrl}/demo/auth/jwt/protected — behind the Bearer guard. */
  async protectedResource(token: string): Promise<BearerResource> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PROTECTED_PATH, {
        method: 'GET',
        headers: { authorization: `Bearer ${token}` },
      });
      return parseDto(body, status, bearerResourceFromJson);
    });
  }
}
