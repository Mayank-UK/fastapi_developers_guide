import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type {
  RefreshExchangeOutcome,
  RefreshLoginOutcome,
  RefreshPanel,
} from '../../../domain/demo/auth-refresh';

/**
 * RefreshDemo — the authentication topic's refresh lab (demo block id
 * `auth:refresh`). Families, one-time rotation, and the reuse alarm:
 * login starts a family (the raw token's only appearance), exchange
 * rotates to the next link while the demo remembers the current token,
 * and replaying the SAVED old token trips detection — the whole family
 * revokes, kill count in the response, timelines on the board.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: RefreshPanel };

export function RefreshDemo() {
  const useCase = container.getAuthRefreshDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [current, setCurrent] = useState('');
  const [savedOld, setSavedOld] = useState('');
  const [login, setLogin] = useState<RefreshLoginOutcome | null>(null);
  const [exchange, setExchange] = useState<RefreshExchangeOutcome | null>(null);
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
      <p data-testid="auth-refresh-loading" className="text-body-sm text-on-surface-variant">
        reading the refresh lab…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return (
      <ErrorPanel subject="the refresh lab" failure={panel.failure} onRetry={refreshPanel} />
    );
  }

  const { data } = panel;

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="auth-refresh-state"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">
          logins {data.telemetry.logins} · rotations {data.telemetry.rotations} · reuse events{' '}
          {data.telemetry.reuseEvents}
        </p>
        {data.families.map((family) => (
          <p key={family.familyId} className="font-mono text-caption text-on-surface-variant">
            {family.familyId} · {family.username} · {family.status} ·{' '}
            {family.tokens.map((token) => `#${token.position} ${token.status}`).join(' → ')}
          </p>
        ))}
      </section>

      <div className="flex flex-wrap items-center gap-xs">
        <button
          type="button"
          onClick={() =>
            runAction(() => useCase.login('ada', 'analytical-engine'), (row) => {
              setLogin(row);
              setCurrent(row.refreshToken);
              setSavedOld('');
              setExchange(null);
            })
          }
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          login (start a family)
        </button>
        <button
          type="button"
          disabled={current === ''}
          onClick={() =>
            runAction(() => useCase.exchange(current), (row) => {
              setExchange(row);
              if (row.outcome === 'rotated' && row.refreshToken) {
                setSavedOld(current);
                setCurrent(row.refreshToken);
              }
            })
          }
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
        >
          exchange (rotate)
        </button>
        <button
          type="button"
          disabled={savedOld === ''}
          onClick={() => runAction(() => useCase.exchange(savedOld), setExchange)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
        >
          replay OLD token (trip the alarm)
        </button>
      </div>

      {actionFailed && (
        <p data-testid="auth-refresh-action-error" className="text-caption text-error">
          {actionFailed.message}
        </p>
      )}

      {login && (
        <section
          data-testid="auth-refresh-login"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            family {login.familyId} · access ttl {login.accessExpiresIn}s
          </p>
          <p className="break-all font-mono text-caption text-on-surface-variant">
            refresh token (once): {login.refreshToken.slice(0, 16)}…
          </p>
        </section>
      )}

      {exchange && (
        <section
          data-testid="auth-refresh-exchange"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            {exchange.outcome}
            {exchange.outcome === 'rotated'
              ? ` · position ${exchange.rotatedFromPosition} → ${(exchange.rotatedFromPosition ?? 0) + 1}`
              : ''}{' '}
            · family tokens revoked {exchange.familyTokensRevoked}
          </p>
          <p className="text-caption text-on-surface-variant">{exchange.detail}</p>
        </section>
      )}

      <p data-testid="auth-refresh-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

export default RefreshDemo;
