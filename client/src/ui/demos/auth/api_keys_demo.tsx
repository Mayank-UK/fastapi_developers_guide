import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type {
  ApiKeyCallOutcome,
  ApiKeyCreated,
  ApiKeyRevokeOutcome,
  ApiKeysPanel,
} from '../../../domain/demo/auth-api-keys';

/**
 * ApiKeysDemo — the authentication topic's key lab (demo block id
 * `auth:api-keys`). Generate shows the raw key exactly once (copy it —
 * the roster never sees it again), the protected call authenticates the
 * x-api-key header or degrades to the shared error panel (401 envelope),
 * and revoke is an instant prefix-keyed delete.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: ApiKeysPanel };

export function ApiKeysDemo() {
  const useCase = container.getAuthApiKeysDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const [key, setKey] = useState('');
  const [call, setCall] = useState<ApiKeyCallOutcome | null>(null);
  const [revoked, setRevoked] = useState<ApiKeyRevokeOutcome | null>(null);
  const [prefix, setPrefix] = useState('');
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
      <p data-testid="auth-keys-loading" className="text-body-sm text-on-surface-variant">
        reading the key lab…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return <ErrorPanel subject="the key lab" failure={panel.failure} onRetry={refreshPanel} />;
  }

  const { data } = panel;

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="auth-keys-state"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">
          {data.records.length} key record(s) at rest — SHA-256 only
        </p>
        {data.records.map((record) => (
          <p key={record.prefix} className="font-mono text-caption text-on-surface-variant">
            {record.prefix} · {record.name} · {record.scopes.join(' ')} · hash{' '}
            {record.keyHashPreview}
          </p>
        ))}
      </section>

      <div className="flex flex-wrap items-center gap-xs">
        <button
          type="button"
          onClick={() =>
            runAction(() => useCase.generate('demo key', ['posts:read']), (row) => {
              setCreated(row);
              setKey(row.key);
              setPrefix(row.prefix);
            })
          }
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          generate key (raw shown once)
        </button>
        <input
          type="text"
          value={key}
          onChange={(event) => setKey(event.target.value)}
          placeholder="paste a key…"
          aria-label="api key"
          className="w-72 rounded-md border border-outline bg-transparent px-sm py-xxs font-mono text-caption text-on-surface"
        />
        <button
          type="button"
          onClick={() => runAction(() => useCase.call(key), setCall)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          call protected (x-api-key)
        </button>
        <input
          type="text"
          value={prefix}
          onChange={(event) => setPrefix(event.target.value)}
          placeholder="prefix"
          aria-label="key prefix"
          className="w-40 rounded-md border border-outline bg-transparent px-sm py-xxs font-mono text-caption text-on-surface"
        />
        <button
          type="button"
          onClick={() => runAction(() => useCase.revoke(prefix), setRevoked)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          revoke by prefix
        </button>
      </div>

      {actionFailed && (
        <p data-testid="auth-keys-action-error" className="text-caption text-error">
          {actionFailed.message}
        </p>
      )}

      {created && (
        <section
          data-testid="auth-keys-created"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            {created.prefix} — copy it now, this is the only appearance
          </p>
          <p className="break-all font-mono text-caption text-on-surface">{created.key}</p>
          <p className="font-mono text-caption text-on-surface-variant">
            stored as {created.keyHash.slice(0, 16)}…
          </p>
        </section>
      )}

      {call && (
        <section
          data-testid="auth-keys-call"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            authenticated: {call.prefix} ({call.name}) · scopes {call.scopes.join(' ')}
          </p>
        </section>
      )}

      {revoked && (
        <section
          data-testid="auth-keys-revoked"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            revoked {revoked.prefix}: {String(revoked.revoked)} — instantly dead
          </p>
        </section>
      )}

      <p data-testid="auth-keys-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

export default ApiKeysDemo;
