import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type {
  AuthorizeOutcome,
  ExchangeOutcome,
  OAuthPanel,
  PkcePair,
} from '../../../domain/demo/auth-oauth';
import type { BearerResource } from '../../../domain/demo/auth-jwt';

/**
 * OauthDemo — the authentication topic's OAuth lab (demo block id
 * `auth:oauth`). The code+PKCE grant as both parties: generate the pair,
 * authorize (consent + the redirect with the one-time code), exchange
 * with the verifier — and the wrong-verifier button proves the failed
 * attempt burns the code. The exchanged token then unlocks the protected
 * resource (with its scope check).
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: OAuthPanel };

function codeFromRedirect(redirectTo: string): string {
  return redirectTo.split('code=')[1]?.split('&')[0] ?? '';
}

export function OauthDemo() {
  const useCase = container.getAuthOauthDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [pair, setPair] = useState<PkcePair | null>(null);
  const [authorized, setAuthorized] = useState<AuthorizeOutcome | null>(null);
  const [code, setCode] = useState('');
  const [exchange, setExchange] = useState<ExchangeOutcome | null>(null);
  const [resource, setResource] = useState<BearerResource | null>(null);
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
      <p data-testid="auth-oauth-loading" className="text-body-sm text-on-surface-variant">
        reading the OAuth lab…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return <ErrorPanel subject="the OAuth lab" failure={panel.failure} onRetry={refreshPanel} />;
  }

  const { data } = panel;

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="auth-oauth-state"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        <p className="font-mono text-caption text-primary">
          client {data.clientId} ({data.clientKind}) · code ttl {data.codeTtlSeconds}s
        </p>
        <p className="font-mono text-caption text-on-surface-variant">
          redirect {data.redirectUris[0]} · scopes {data.clientScopes.join(' ')}
        </p>
        {data.steps.map((step, index) => (
          <p key={step} className="text-caption text-on-surface-variant">
            {index + 1}. {step}
          </p>
        ))}
      </section>

      <div className="flex flex-wrap items-center gap-xs">
        <button
          type="button"
          onClick={() => runAction(() => useCase.pkce(), setPair)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
        >
          1 · pkce pair
        </button>
        <button
          type="button"
          disabled={pair === null}
          onClick={() =>
            pair &&
            runAction(() => useCase.authorize(pair.codeChallenge), (row) => {
              setAuthorized(row);
              setCode(codeFromRedirect(row.redirectTo));
            })
          }
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
        >
          2 · authorize
        </button>
        <button
          type="button"
          disabled={pair === null || code === ''}
          onClick={() => pair && runAction(() => useCase.exchange(code, pair.verifier), setExchange)}
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
        >
          3 · exchange (right verifier)
        </button>
        <button
          type="button"
          disabled={pair === null || code === ''}
          onClick={() =>
            pair && runAction(() => useCase.exchange(code, 'x'.repeat(43)), setExchange)
          }
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
        >
          3 · exchange (WRONG verifier)
        </button>
        <button
          type="button"
          disabled={exchange === null}
          onClick={() =>
            exchange && runAction(() => useCase.protectedResource(exchange.accessToken), setResource)
          }
          className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
        >
          4 · protected resource
        </button>
      </div>

      {actionFailed && (
        <p data-testid="auth-oauth-action-error" className="text-caption text-error">
          {actionFailed.message}
        </p>
      )}

      {pair && (
        <section
          data-testid="auth-oauth-pair"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            verifier {pair.verifier.slice(0, 12)}… · challenge {pair.codeChallenge.slice(0, 12)}…
          </p>
        </section>
      )}

      {authorized && (
        <section
          data-testid="auth-oauth-authorized"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="break-all font-mono text-caption text-primary">
            {authorized.redirectTo}
          </p>
          <p className="text-caption text-on-surface-variant">{authorized.consent}</p>
        </section>
      )}

      {exchange && (
        <section
          data-testid="auth-oauth-exchange"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            exchanged: {exchange.username} · scope {exchange.scope} · ttl {exchange.expiresIn}s
          </p>
        </section>
      )}

      {resource && (
        <section
          data-testid="auth-oauth-resource"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption text-primary">
            resource: {resource.username} · scopes {resource.scopes.join(' ')}
          </p>
        </section>
      )}

      <p data-testid="auth-oauth-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </div>
  );
}

export default OauthDemo;
