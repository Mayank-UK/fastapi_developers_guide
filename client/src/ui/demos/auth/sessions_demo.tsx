import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type {
  SessionInspection,
  SessionLoginOutcome,
  SessionLogoutOutcome,
  SessionsPanel,
} from '../../../domain/demo/auth-sessions';

/**
 * SessionsDemo — the authentication topic's cookie lab (demo block id
 * `auth:sessions`). The browser's own cookie jar is part of the pipeline:
 * login answers Set-Cookie with HttpOnly + SameSite=Lax set for real,
 * /me resolves the sealed cookie to the live session row (or degrades to
 * the shared error panel with the 401 envelope), and logout deletes the
 * server row so any copy of the old cookie is dead.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: SessionsPanel };

export function SessionsDemo() {
  const useCase = container.getAuthSessionsDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [username, setUsername] = useState('ada');
  const [password, setPassword] = useState('analytical-engine');
  const [login, setLogin] = useState<SessionLoginOutcome | null>(null);
  const [me, setMe] = useState<SessionInspection | null>(null);
  const [logout, setLogout] = useState<SessionLogoutOutcome | null>(null);
  const [actionFailed, setActionFailed] = useState<Failure | null>(null);

  const refreshPanel = useCallback(() => {
    void useCase.panel().then((result) => {
      setPanel(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  }, [useCase]);

  useEffect(() => {
    refreshPanel();
  }, [refreshPanel]);

  function runAction<T>(action: () => Promise<Result<T>>, onDone: (value: T) => void): void {
    setActionFailed(null);
    void action().then((result) => {
      if (result.ok) {
        onDone(result.value);
        refreshPanel();
      } else {
        setActionFailed(result.failure);
      }
    });
  }

  if (panel.state === 'loading') {
    return (
      <p data-testid="auth-sessions-loading" className="text-body-sm text-on-surface-variant">
        reading the cookie lab…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return (
      <ErrorPanel subject="the cookie lab" failure={panel.failure} onRetry={refreshPanel} />
    );
  }

  const { data } = panel;

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="auth-sessions-state"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">
          cookie {data.cookieName} · path {data.cookiePath} · Max-Age {data.maxAgeSeconds}s
        </p>
        <p data-testid="auth-sessions-flags" className="font-mono text-caption text-on-surface">
          flags: {data.flagsSet.join(' + ')} (Secure: prod-only)
        </p>
        {data.activeSessions.length === 0 ? (
          <p className="font-mono text-caption text-on-surface-variant">no live sessions</p>
        ) : (
          data.activeSessions.map((session) => (
            <p key={session.sessionIdPreview} className="font-mono text-caption text-on-surface-variant">
              {session.sessionIdPreview} · {session.displayName} · expires {session.expiresAt}
            </p>
          ))
        )}
      </section>

      <div className="flex flex-wrap items-center gap-xs">
        <input
          type="text"
          value={username}
          maxLength={60}
          onChange={(event) => setUsername(event.target.value)}
          aria-label="username"
          className="rounded-md border border-outline bg-transparent px-sm py-xxs text-caption text-on-surface"
        />
        <input
          type="text"
          value={password}
          maxLength={128}
          onChange={(event) => setPassword(event.target.value)}
          aria-label="password"
          className="rounded-md border border-outline bg-transparent px-sm py-xxs text-caption text-on-surface"
        />
        <button
          type="button"
          onClick={() => runAction(() => useCase.login(username, password), setLogin)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          login (sets the cookie)
        </button>
        <button
          type="button"
          onClick={() => runAction(() => useCase.inspect(), setMe)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          /me (cookie resolves)
        </button>
        <button
          type="button"
          onClick={() => runAction(() => useCase.logout(), setLogout)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          logout (delete the row)
        </button>
      </div>

      {actionFailed && (
        <p data-testid="auth-sessions-action-error" className="text-caption text-error">
          {actionFailed.message}
        </p>
      )}

      {login && (
        <section
          data-testid="auth-sessions-login"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            logged in: {login.displayName} · scopes {login.scopes.join(' ')}
          </p>
          <p className="font-mono text-caption text-on-surface">{login.cookieValueAnatomy}</p>
        </section>
      )}

      {me && (
        <section
          data-testid="auth-sessions-me"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            /me: {me.displayName} ({me.sessionIdPreview})
          </p>
          <p className="text-caption text-on-surface-variant">{me.detail}</p>
        </section>
      )}

      {logout && (
        <section
          data-testid="auth-sessions-logout"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            revoked: {String(logout.revoked)} · cookie cleared (Max-Age 0)
          </p>
          <p className="text-caption text-on-surface-variant">{logout.detail}</p>
        </section>
      )}

      <p data-testid="auth-sessions-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

export default SessionsDemo;
