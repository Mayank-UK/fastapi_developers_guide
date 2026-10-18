import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { OauthDemo } from './oauth_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetAuthOauthDemoUseCase } from '../../../domain/demo/get-auth-oauth-demo-usecase';
import type {
  AuthorizeOutcome,
  ExchangeOutcome,
  OAuthPanel,
  PkcePair,
} from '../../../domain/demo/auth-oauth';
import type { BearerResource } from '../../../domain/demo/auth-jwt';

/**
 * OauthDemo spec — fixture-driven (happy + failure): the flow map renders
 * the registered client and its four steps; the pkce pair gates authorize;
 * authorize fills the code from the redirect; the right-verifier exchange
 * succeeds and unlocks the resource while the wrong verifier renders the
 * 401 envelope's message as the action error line.
 */

const panel: OAuthPanel = {
  clientId: 'guide-cli',
  clientKind: 'Guide CLI (public client)',
  redirectUris: ['https://client.example/callback'],
  clientScopes: ['posts:read', 'posts:write'],
  codeTtlSeconds: 600,
  pkceNote: 'the verifier never travels the redirect',
  steps: ['PKCE pair', 'authorize', 'token', 'use'],
  pkceEndpoint: '/api/demo/auth/oauth/pkce',
  authorizeEndpoint: '/api/demo/auth/oauth/authorize',
  tokenEndpoint: '/api/demo/auth/oauth/token',
  protectedEndpoint: '/api/demo/auth/oauth/protected',
  reasoning: 'One registered client, no secret to leak, PKCE replaces it.',
};

const pair: PkcePair = {
  verifier: 'v'.repeat(64),
  codeChallenge: 'c'.repeat(43),
  method: 'S256',
  detail: 'verifier stays on the client',
};

const authorized: AuthorizeOutcome = {
  redirectTo: 'https://client.example/callback?code=one-time-code&state=demo',
  state: 'demo',
  consent: 'consent granted (simulated): ada approved posts:read posts:write',
  codePreview: 'one-time…',
  expiresIn: 600,
  detail: 'the code rides the front channel',
};

const exchanged: ExchangeOutcome = {
  accessToken: 'exchanged.access.token',
  tokenType: 'Bearer',
  expiresIn: 900,
  scope: 'posts:read posts:write',
  username: 'ada',
  detail: 'verifier proved, code burned',
};

const resource: BearerResource = {
  username: 'ada',
  scopes: ['posts:read', 'posts:write'],
  via: 'the OAuth code+PKCE exchange',
  detail: 'scope check passed',
};

type Stubs = {
  exchange?: (code: string, verifier: string) => Promise<Result<ExchangeOutcome>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetAuthOauthDemoUseCase, {
    panel: async () => success(panel),
    pkce: async () => success(pair),
    authorize: async () => success(authorized),
    exchange:
      stubs.exchange ??
      (async () =>
        failed(
          new ServerFailure(
            'invalid_grant — S256(verifier) does not match the code_challenge',
            { code: 'unauthorized', status: 401, requestId: 'req-o1' },
          ),
        )),
    protectedResource: async () => success(resource),
  } as unknown as GetAuthOauthDemoUseCase);
}

describe('OauthDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['auth:oauth']).toBeDefined();
  });

  it('walks the four steps when the verifier is right', async () => {
    stubUseCase({ exchange: async () => success(exchanged) });
    render(<OauthDemo />);
    await waitFor(() => expect(screen.getByTestId('auth-oauth-state')).toBeInTheDocument());
    expect(screen.getByTestId('auth-oauth-state')).toHaveTextContent('guide-cli');

    screen.getByRole('button', { name: '1 · pkce pair' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-oauth-pair')).toBeInTheDocument());

    screen.getByRole('button', { name: '2 · authorize' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-oauth-authorized')).toBeInTheDocument());
    expect(screen.getByTestId('auth-oauth-authorized')).toHaveTextContent('code=one-time-code');

    screen.getByRole('button', { name: '3 · exchange (right verifier)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-oauth-exchange')).toBeInTheDocument());

    screen.getByRole('button', { name: '4 · protected resource' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-oauth-resource')).toBeInTheDocument());
    expect(screen.getByTestId('auth-oauth-resource')).toHaveTextContent('ada');
  });

  it('renders the wrong-verifier 401 as the action error line', async () => {
    stubUseCase({});
    render(<OauthDemo />);
    await waitFor(() => expect(screen.getByTestId('auth-oauth-state')).toBeInTheDocument());
    screen.getByRole('button', { name: '1 · pkce pair' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-oauth-pair')).toBeInTheDocument());
    screen.getByRole('button', { name: '2 · authorize' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-oauth-authorized')).toBeInTheDocument());
    screen.getByRole('button', { name: '3 · exchange (WRONG verifier)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-oauth-action-error')).toHaveTextContent(
      'invalid_grant',
    ));
  });
});
