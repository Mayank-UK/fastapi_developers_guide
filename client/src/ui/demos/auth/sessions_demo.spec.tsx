import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SessionsDemo } from './sessions_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { ServerFailure } from '../../../core/error-handling/failures';
import { failed, success, type Result } from '../../../core/result';
import type { GetAuthSessionsDemoUseCase } from '../../../domain/demo/get-auth-sessions-demo-usecase';
import type {
  SessionInspection,
  SessionLoginOutcome,
  SessionLogoutOutcome,
  SessionsPanel,
} from '../../../domain/demo/auth-sessions';

/**
 * SessionsDemo spec — fixture-driven (happy + failure): the roster renders
 * the cookie contract; the login shows the sealed value's anatomy; /me
 * shows the resolved session; logout shows the revocation; the unauthenticated
 * /me degrades to the action error line; a failed roster degrades to the
 * shared error panel with recovery.
 */

const panel: SessionsPanel = {
  cookieName: 'fdg_session',
  cookiePath: '/api',
  maxAgeSeconds: 900,
  flagsSet: ['HttpOnly', 'SameSite=Lax'],
  secureNote: 'Secure is a production flag.',
  sealNote: 'the cookie carries the session id sealed with itsdangerous.',
  activeSessions: [],
  loginEndpoint: '/api/demo/auth/sessions/login',
  meEndpoint: '/api/demo/auth/sessions/me',
  logoutEndpoint: '/api/demo/auth/sessions/logout',
  reasoning: 'The cookie contract, set for real on every login.',
};

const loginOutcome: SessionLoginOutcome = {
  username: 'ada',
  displayName: 'Ada Lovelace',
  scopes: ['posts:read', 'posts:write'],
  cookie: {
    name: 'fdg_session',
    value: 'abc123.sig',
    maxAgeSeconds: 900,
    path: '/api',
    httponly: true,
    samesite: 'lax',
    secure: false,
  },
  cookieValueAnatomy: 'abc123… . <40 signature chars> — the session id sealed.',
  detail: 'logged in as Ada Lovelace',
};

const inspection: SessionInspection = {
  sessionIdPreview: 'deadbeef…',
  username: 'ada',
  displayName: 'Ada Lovelace',
  scopes: ['posts:read'],
  issuedAt: '2026-10-17T00:00:00+00:00',
  expiresAt: '2026-10-17T00:15:00+00:00',
  detail: 'the cookie resolved server-side',
};

const logoutOutcome: SessionLogoutOutcome = {
  revoked: true,
  cookie: { ...loginOutcome.cookie, value: '', maxAgeSeconds: 0 },
  detail: 'session deleted server-side',
};

type Stubs = {
  panel?: () => Promise<Result<SessionsPanel>>;
  inspect?: () => Promise<Result<SessionInspection>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetAuthSessionsDemoUseCase, {
    panel: stubs.panel ?? (async () => success(panel)),
    login: async () => success(loginOutcome),
    inspect: stubs.inspect ?? (async () => success(inspection)),
    logout: async () => success(logoutOutcome),
  } as unknown as GetAuthSessionsDemoUseCase);
}

describe('SessionsDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['auth:sessions']).toBeDefined();
  });

  it('renders the cookie contract and the login round', async () => {
    stubUseCase({});
    render(<SessionsDemo />);
    await waitFor(() => expect(screen.getByTestId('auth-sessions-state')).toBeInTheDocument());
    expect(screen.getByTestId('auth-sessions-flags')).toHaveTextContent(
      'HttpOnly + SameSite=Lax',
    );
    expect(screen.getByTestId('auth-sessions-reasoning')).toBeInTheDocument();

    screen.getByRole('button', { name: 'login (sets the cookie)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-sessions-login')).toBeInTheDocument());
    expect(screen.getByTestId('auth-sessions-login')).toHaveTextContent('Ada Lovelace');

    screen.getByRole('button', { name: '/me (cookie resolves)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-sessions-me')).toBeInTheDocument());

    screen.getByRole('button', { name: 'logout (delete the row)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-sessions-logout')).toBeInTheDocument());
    expect(screen.getByTestId('auth-sessions-logout')).toHaveTextContent('revoked: true');
  });

  it('shows the 401 envelope as the action error line when /me is unauthenticated', async () => {
    stubUseCase({
      inspect: async () =>
        failed(
          new ServerFailure('not authenticated — no valid session', {
            code: 'unauthorized',
            status: 401,
            requestId: 'req-a1',
          }),
        ),
    });
    render(<SessionsDemo />);
    await waitFor(() => expect(screen.getByTestId('auth-sessions-state')).toBeInTheDocument());
    screen.getByRole('button', { name: '/me (cookie resolves)' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-sessions-action-error')).toHaveTextContent(
      'not authenticated',
    ));
  });

  it('degrades to the shared error panel on a Failed roster, with recovery', async () => {
    let calls = 0;
    stubUseCase({
      panel: async () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('Could not reach the server.', {
                code: 'unknown_error',
                status: 0,
                requestId: 'req-a2',
              }),
            )
          : success(panel);
      },
    });
    render(<SessionsDemo />);
    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() => expect(screen.getByTestId('auth-sessions-state')).toBeInTheDocument());
  });
});
