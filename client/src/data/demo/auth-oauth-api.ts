import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { BearerResource } from '../../domain/demo/auth-jwt';
import type {
  AuthorizeOutcome,
  ExchangeOutcome,
  OAuthPanel,
  PkcePair,
} from '../../domain/demo/auth-oauth';
import { bearerResourceFromJson } from './auth-jwt-dto';
import {
  authorizeOutcomeFromJson,
  exchangeOutcomeFromJson,
  oauthPanelFromJson,
  pkcePairFromJson,
} from './auth-oauth-dto';

/**
 * AuthOauthApi — the transport for the OAuth lab's five endpoints. The
 * exchange sends code + verifier + the registered redirect_uri; a wrong
 * verifier (or a replayed code) arrives as the 401 envelope.
 */

const PANEL_PATH = '/demo/auth/oauth';
const PKCE_PATH = '/demo/auth/oauth/pkce';
const AUTHORIZE_PATH = '/demo/auth/oauth/authorize';
const TOKEN_PATH = '/demo/auth/oauth/token';
const PROTECTED_PATH = '/demo/auth/oauth/protected';

const REDIRECT_URI = 'https://client.example/callback';
/** The registered client's exact callback — the one URI the server accepts. */

export class AuthOauthApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/auth/oauth — the flow's map. */
  async panel(): Promise<OAuthPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PANEL_PATH);
      return parseDto(body, status, oauthPanelFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/oauth/pkce — a verifier/challenge pair. */
  async pkce(): Promise<PkcePair> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PKCE_PATH, {
        method: 'POST',
      });
      return parseDto(body, status, pkcePairFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/oauth/authorize — consent + one-time code. */
  async authorize(challenge: string): Promise<AuthorizeOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, AUTHORIZE_PATH, {
        method: 'POST',
        body: JSON.stringify({
          clientId: 'guide-cli',
          redirectUri: REDIRECT_URI,
          state: 'demo',
          codeChallenge: challenge,
          codeChallengeMethod: 'S256',
        }),
      });
      return parseDto(body, status, authorizeOutcomeFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/auth/oauth/token — the PKCE exchange. */
  async exchange(code: string, verifier: string): Promise<ExchangeOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, TOKEN_PATH, {
        method: 'POST',
        body: JSON.stringify({ code, verifier, redirectUri: REDIRECT_URI }),
      });
      return parseDto(body, status, exchangeOutcomeFromJson);
    });
  }

  /** GET {apiBaseUrl}/demo/auth/oauth/protected — the resource, scope-checked. */
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
