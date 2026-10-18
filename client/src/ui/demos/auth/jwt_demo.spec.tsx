import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { JwtDemo } from './jwt_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success } from '../../../core/result';
import type { GetAuthJwtDemoUseCase } from '../../../domain/demo/get-auth-jwt-demo-usecase';
import type {
  JwtPanel,
  MintedToken,
  TokenLoginOutcome,
  TokenVerifyOutcome,
} from '../../../domain/demo/auth-jwt';

/**
 * JwtDemo spec — fixture-driven (happy + failure): the anatomy renders the
 * claim set; the login form flow fills the token; mint reports the signing
 * secret honestly (including the wrong-secret forgery); verify classifies
 * the failure modes; the protected endpoint's 401 degrades to the action
 * error line.
 */

const panel: JwtPanel = {
  algorithm: 'HS256',
  issuer: 'guide.demo',
  defaultTtlSeconds: 900,
  claims: [
    { claim: 'sub', meaning: 'the subject — WHO the token speaks for' },
    { claim: 'exp', meaning: 'expiry — the hard lease' },
  ],
  loginEndpoint: '/api/demo/auth/jwt/login',
  mintEndpoint: '/api/demo/auth/jwt/mint',
  verifyEndpoint: '/api/demo/auth/jwt/verify',
  protectedEndpoint: '/api/demo/auth/jwt/protected',
  reasoning: 'One HS256 secret signs and verifies.',
};

const loginOutcome: TokenLoginOutcome = {
  accessToken: 'login.token.value',
  tokenType: 'bearer',
  expiresIn: 900,
  scope: 'posts:read',
  username: 'grace',
  detail: 'login form accepted',
};

const minted: MintedToken = {
  token: 'minted.token.value',
  header: { alg: 'HS256', typ: 'JWT' },
  payload: { sub: 'ada', scopes: ['posts:read'] },
  signedWith: 'wrong',
  expiresAt: '2026-10-17T00:15:00+00:00',
  detail: 'minted for ada',
};

const verdict: TokenVerifyOutcome = {
  outcome: 'bad-signature',
  username: null,
  scopes: null,
  expiresAt: null,
  detail: 'the signature does not match the server secret',
};

function stubUseCase(): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetAuthJwtDemoUseCase, {
    panel: async () => success(panel),
    login: async () => success(loginOutcome),
    mint: async () => success(minted),
    verify: async () => success(verdict),
    protectedResource: async () =>
      failed(
        new ServerFailure('invalid token — bad-signature', {
          code: 'unauthorized',
          status: 401,
          requestId: 'req-j1',
        }),
      ),
  } as unknown as GetAuthJwtDemoUseCase);
}

describe('JwtDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['auth:jwt']).toBeDefined();
  });

  it('renders the anatomy, the login flow, and the mint + verify verdicts', async () => {
    stubUseCase();
    render(<JwtDemo />);
    await waitFor(() => expect(screen.getByTestId('auth-jwt-state')).toBeInTheDocument());
    expect(screen.getByTestId('auth-jwt-state')).toHaveTextContent('HS256');

    screen.getByRole('button', { name: 'login form (grace)' }).click();
    await waitFor(() =>
      expect(screen.getByLabelText('token')).toHaveValue(loginOutcome.accessToken),
    );

    screen.getByRole('button', { name: 'mint (forged: wrong secret)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-jwt-minted')).toBeInTheDocument());
    expect(screen.getByTestId('auth-jwt-minted')).toHaveTextContent('WRONG (attacker) secret');

    screen.getByRole('button', { name: 'verify' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-jwt-verdict')).toBeInTheDocument());
    expect(screen.getByTestId('auth-jwt-verdict')).toHaveTextContent('bad-signature');
  });

  it('renders the protected endpoint 401 as the action error line', async () => {
    stubUseCase();
    render(<JwtDemo />);
    await waitFor(() => expect(screen.getByTestId('auth-jwt-state')).toBeInTheDocument());
    screen.getByRole('button', { name: 'protected (Bearer)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-jwt-action-error')).toHaveTextContent(
      'invalid token — bad-signature',
    ));
  });
});
