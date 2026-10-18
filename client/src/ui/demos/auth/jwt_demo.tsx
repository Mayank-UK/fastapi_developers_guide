import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type {
  BearerResource,
  JwtPanel,
  MintedToken,
  TokenVerifyOutcome,
} from '../../../domain/demo/auth-jwt';

/**
 * JwtDemo — the authentication topic's token lab (demo block id
 * `auth:jwt`). The OAuth2 password form login answers a bearer token, the
 * mint dials build every claim shape (including the wrong-secret
 * forgery), verify classifies every failure mode, and the protected
 * endpoint demonstrates the Bearer guard — 401s degrade to the shared
 * error panel with the envelope's message.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: JwtPanel };

export function JwtDemo() {
  const useCase = container.getAuthJwtDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [minted, setMinted] = useState<MintedToken | null>(null);
  const [verdict, setVerdict] = useState<TokenVerifyOutcome | null>(null);
  const [resource, setResource] = useState<BearerResource | null>(null);
  const [token, setToken] = useState('');
  const [ttl, setTtl] = useState(1);
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
      <p data-testid="auth-jwt-loading" className="text-body-sm text-on-surface-variant">
        reading the token lab…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return <ErrorPanel subject="the token lab" failure={panel.failure} onRetry={refreshPanel} />;
  }

  const { data } = panel;

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="auth-jwt-state"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">
          {data.algorithm} · iss {data.issuer} · default ttl {data.defaultTtlSeconds}s
        </p>
        {data.claims.map((claim) => (
          <p key={claim.claim} className="font-mono text-caption text-on-surface-variant">
            {claim.claim} — {claim.meaning}
          </p>
        ))}
      </section>

      <div className="flex flex-wrap items-center gap-xs">
        <button
          type="button"
          onClick={() =>
            runAction(() => useCase.login('grace', 'nanosecond'), (row) => setToken(row.accessToken))
          }
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          login form (grace)
        </button>
        <label className="text-caption text-on-surface-variant">
          ttl
          <input
            type="number"
            min={1}
            max={3600}
            value={ttl}
            onChange={(event) => setTtl(Number(event.target.value))}
            className="ml-xxs w-16 rounded-md border border-outline bg-transparent px-xxs py-xxs text-caption text-on-surface"
          />
        </label>
        <button
          type="button"
          onClick={() =>
            runAction(() => useCase.mint('ada', ['posts:read'], ttl, 0, 'real'), (row) => {
              setMinted(row);
              setToken(row.token);
            })
          }
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          mint (real secret)
        </button>
        <button
          type="button"
          onClick={() =>
            runAction(() => useCase.mint('ada', ['posts:read'], ttl, 3600, 'real'), (row) => {
              setMinted(row);
              setToken(row.token);
            })
          }
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          mint (nbf +1h)
        </button>
        <button
          type="button"
          onClick={() =>
            runAction(() => useCase.mint('attacker', ['posts:write'], 900, 0, 'wrong'), (row) => {
              setMinted(row);
              setToken(row.token);
            })
          }
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          mint (forged: wrong secret)
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-xs">
        <input
          type="text"
          value={token}
          onChange={(event) => setToken(event.target.value)}
          placeholder="paste a token…"
          aria-label="token"
          className="w-72 rounded-md border border-outline bg-transparent px-sm py-xxs font-mono text-caption text-on-surface"
        />
        <button
          type="button"
          onClick={() => runAction(() => useCase.verify(token), setVerdict)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          verify
        </button>
        <button
          type="button"
          onClick={() => runAction(() => useCase.protectedResource(token), setResource)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          protected (Bearer)
        </button>
      </div>

      {actionFailed && (
        <p data-testid="auth-jwt-action-error" className="text-caption text-error">
          {actionFailed.message}
        </p>
      )}

      {minted && (
        <section
          data-testid="auth-jwt-minted"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            minted · signed with {minted.signedWith === 'real' ? 'the server secret' : 'the WRONG (attacker) secret'}
          </p>
          <p className="text-caption text-on-surface-variant">{minted.detail}</p>
        </section>
      )}

      {verdict && (
        <section
          data-testid="auth-jwt-verdict"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">verdict: {verdict.outcome}</p>
          <p className="text-caption text-on-surface-variant">{verdict.detail}</p>
        </section>
      )}

      {resource && (
        <section
          data-testid="auth-jwt-resource"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            protected: {resource.username} · scopes {resource.scopes.join(' ') || 'none'}
          </p>
        </section>
      )}

      <p data-testid="auth-jwt-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

export default JwtDemo;
