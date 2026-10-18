import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type {
  HashingPanel,
  PasswordHashOutcome,
  PasswordVerifyOutcome,
} from '../../../domain/demo/auth-hashing';

/**
 * HashingDemo — the authentication topic's hashing lab (demo block id
 * `auth:hashing`). argon2id with the cost shown honestly: hash mints a
 * fresh salted string every time, verify answers match + needsRehash at
 * the same cost for right and wrong candidates alike, and the panel
 * carries the active + legacy cost and the seeded credential previews.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: HashingPanel };

const LEGACY_HASH =
  '$argon2id$v=19$m=8192,t=1,p=2$MLNClM6LqCQvN7PDy20tLg$' +
  'gjaMkZv4WQD5SpTax5yhrisVedBjdhNmottcf5bCQd4';
/** The panel's 2015-cost hash of ada's password — the rehash lesson. */

export function HashingDemo() {
  const useCase = container.getAuthHashingDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [password, setPassword] = useState('correct-horse-battery-staple');
  const [hash, setHash] = useState('');
  const [hashed, setHashed] = useState<PasswordHashOutcome | null>(null);
  const [verified, setVerified] = useState<PasswordVerifyOutcome | null>(null);
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
      } else {
        setActionFailed(result.failure);
      }
    });
  }

  if (panel.state === 'loading') {
    return (
      <p data-testid="auth-hashing-loading" className="text-body-sm text-on-surface-variant">
        reading the hashing lab…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return (
      <ErrorPanel subject="the hashing lab" failure={panel.failure} onRetry={refreshPanel} />
    );
  }

  const { data } = panel;

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="auth-hashing-state"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">active: {data.parameters}</p>
        <p className="font-mono text-caption text-on-surface-variant">
          legacy: {data.legacyParameters}
        </p>
        {data.seedCredentials.map((credential) => (
          <p key={credential.username} className="font-mono text-caption text-on-surface-variant">
            {credential.username} ({credential.displayName}) · {credential.hashPreview}
          </p>
        ))}
      </section>

      <div className="flex flex-wrap items-center gap-xs">
        <input
          type="text"
          value={password}
          maxLength={128}
          onChange={(event) => setPassword(event.target.value)}
          aria-label="password to hash"
          className="w-64 rounded-md border border-outline bg-transparent px-sm py-xxs text-caption text-on-surface"
        />
        <button
          type="button"
          onClick={() =>
            runAction(() => useCase.hash(password), (row) => {
              setHashed(row);
              setHash(row.hash);
            })
          }
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          hash (fresh salt)
        </button>
        <button
          type="button"
          disabled={hash === ''}
          onClick={() => runAction(() => useCase.verify(password, hash), setVerified)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
        >
          verify (right password)
        </button>
        <button
          type="button"
          disabled={hash === ''}
          onClick={() => runAction(() => useCase.verify(`${password}!wrong`, hash), setVerified)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
        >
          verify (WRONG password)
        </button>
        <button
          type="button"
          onClick={() =>
            runAction(() => useCase.verify('analytical-engine', LEGACY_HASH), setVerified)
          }
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          verify legacy hash (rehash flag)
        </button>
      </div>

      {actionFailed && (
        <p data-testid="auth-hashing-action-error" className="text-caption text-error">
          {actionFailed.message}
        </p>
      )}

      {hashed && (
        <section
          data-testid="auth-hashing-hashed"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            hashed in {hashed.elapsedMs} ms · {hashed.parameters}
          </p>
          <p className="break-all font-mono text-caption text-on-surface-variant">
            {hashed.hash.slice(0, 48)}…
          </p>
        </section>
      )}

      {verified && (
        <section
          data-testid="auth-hashing-verified"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            ok: {String(verified.ok)} · needsRehash: {String(verified.needsRehash)} ·{' '}
            {verified.elapsedMs} ms
          </p>
          <p className="text-caption text-on-surface-variant">{verified.detail}</p>
        </section>
      )}

      <p data-testid="auth-hashing-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

export default HashingDemo;
