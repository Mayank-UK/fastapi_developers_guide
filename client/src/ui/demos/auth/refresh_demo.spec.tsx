import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { RefreshDemo } from './refresh_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetAuthRefreshDemoUseCase } from '../../../domain/demo/get-auth-refresh-demo-usecase';
import type {
  RefreshExchangeOutcome,
  RefreshLoginOutcome,
  RefreshPanel,
} from '../../../domain/demo/auth-refresh';

/**
 * RefreshDemo spec — fixture-driven (happy + failure): the board renders
 * the counters and timelines; login starts a family and shows the token
 * once; the rotate exchange advances the position; the replay outcome
 * shows reuse-detected with the kill count; a dead family's 401 degrades
 * to the action error line.
 */

const loginOutcome: RefreshLoginOutcome = {
  familyId: 'fam_start',
  username: 'ada',
  accessToken: 'access.one',
  accessExpiresIn: 900,
  refreshToken: 'rt_first',
  detail: 'family born at position 1',
};

const rotated: RefreshExchangeOutcome = {
  outcome: 'rotated',
  familyId: 'fam_start',
  accessToken: 'access.two',
  accessExpiresIn: 900,
  refreshToken: 'rt_second',
  rotatedFromPosition: 1,
  familyTokensRevoked: 0,
  detail: 'rotated 1 → 2',
};

const reuseDetected: RefreshExchangeOutcome = {
  outcome: 'reuse-detected',
  familyId: 'fam_start',
  accessToken: null,
  accessExpiresIn: null,
  refreshToken: null,
  rotatedFromPosition: 1,
  familyTokensRevoked: 2,
  detail: 'REUSE: the whole family is revoked',
};

const panel: RefreshPanel = {
  families: [
    {
      familyId: 'fam_start',
      username: 'ada',
      status: 'revoked',
      createdAt: '2026-10-17T00:00:00+00:00',
      tokens: [
        { position: 1, status: 'used', issuedAt: '2026-10-17T00:00:00+00:00', usedAt: '2026-10-17T00:01:00+00:00' },
        { position: 2, status: 'revoked', issuedAt: '2026-10-17T00:01:00+00:00', usedAt: null },
      ],
    },
  ],
  telemetry: { logins: 1, rotations: 1, reuseEvents: 1 },
  patternNote: 'a refresh token is one-time',
  loginEndpoint: '/api/demo/auth/refresh/login',
  exchangeEndpoint: '/api/demo/auth/refresh/exchange',
  reasoning: 'No families yet — log in.',
};

type Stubs = {
  exchange?: (token: string) => Promise<Result<RefreshExchangeOutcome>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetAuthRefreshDemoUseCase, {
    panel: async () => success(panel),
    login: async () => success(loginOutcome),
    exchange:
      stubs.exchange ??
      (async (token: string) =>
        token === 'rt_first'
          ? failed(
              new ServerFailure('invalid refresh token — this family was revoked', {
                code: 'unauthorized',
                status: 401,
                requestId: 'req-r1',
              }),
            )
          : success(rotated)),
  } as unknown as GetAuthRefreshDemoUseCase);
}

describe('RefreshDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['auth:refresh']).toBeDefined();
  });

  it('starts a family, rotates, and shows the reuse alarm', async () => {
    let calls = 0;
    stubUseCase({
      exchange: async () => success(calls++ === 0 ? rotated : reuseDetected),
    });
    render(<RefreshDemo />);
    await waitFor(() => expect(screen.getByTestId('auth-refresh-state')).toBeInTheDocument());
    expect(screen.getByTestId('auth-refresh-state')).toHaveTextContent(
      'logins 1 · rotations 1 · reuse events 1',
    );

    screen.getByRole('button', { name: 'login (start a family)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-refresh-login')).toBeInTheDocument());
    expect(screen.getByTestId('auth-refresh-login')).toHaveTextContent('fam_start');

    screen.getByRole('button', { name: 'exchange (rotate)' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('auth-refresh-exchange')).toHaveTextContent('rotated'),
    );

    screen.getByRole('button', { name: 'replay OLD token (trip the alarm)' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('auth-refresh-exchange')).toHaveTextContent('reuse-detected'),
    );
    expect(screen.getByTestId('auth-refresh-exchange')).toHaveTextContent(
      'family tokens revoked 2',
    );
  });

  it('renders a dead family 401 as the action error line', async () => {
    stubUseCase({});
    render(<RefreshDemo />);
    await waitFor(() => expect(screen.getByTestId('auth-refresh-state')).toBeInTheDocument());
    screen.getByRole('button', { name: 'login (start a family)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-refresh-login')).toBeInTheDocument());
    screen.getByRole('button', { name: 'exchange (rotate)' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('auth-refresh-action-error')).toHaveTextContent(
        'this family was revoked',
      ),
    );
  });
});
