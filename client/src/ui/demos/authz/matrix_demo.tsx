import { useCallback, useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type {
  AuthzCheckOutcome,
  AuthzPanel,
  EditedPostOutcome,
  ModeratedCommentOutcome,
} from '../../../domain/demo/authz-matrix';

/**
 * MatrixDemo — the authorization topic's lab (demo block id `authz:matrix`).
 * The panel carries the seeded principals, the roles→grants matrix, and the
 * ownership targets; the check runs the REAL policy engine as a what-if;
 * "try it for real" mints a token as the chosen principal and calls a
 * genuinely guarded endpoint — the 200 shows the allowing reason, the 403
 * surfaces as the error envelope's message carrying the deny reason.
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: AuthzPanel };

type RealOutcome =
  | { state: 'idle' }
  | { state: 'failed'; failure: Failure }
  | { state: 'allowed'; principal: string; reason: string }
  | { state: 'denied'; message: string };

const ACTIONS = ['posts:read', 'posts:write', 'comments:read', 'comments:moderate'] as const;
/** The check's action vocabulary — the engine denies anything else anyway. */

export function MatrixDemo() {
  const useCase = container.getAuthzMatrixDemoUseCase;
  const mintUseCase = container.getAuthJwtDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [principal, setPrincipal] = useState('grace');
  const [action, setAction] = useState('posts:write');
  const [resource, setResource] = useState('');
  const [scopes, setScopes] = useState('');
  const [check, setCheck] = useState<AuthzCheckOutcome | null>(null);
  const [checkFailed, setCheckFailed] = useState<Failure | null>(null);
  const [real, setReal] = useState<RealOutcome>({ state: 'idle' });
  const [busy, setBusy] = useState(false);

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

  if (panel.state === 'loading') {
    return (
      <p data-testid="authz-matrix-loading" className="text-body-sm text-on-surface-variant">
        reading the matrix lab…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return <ErrorPanel subject="the matrix lab" failure={panel.failure} onRetry={refreshPanel} />;
  }

  const { data } = panel;

  const parsedScopes = (): string[] | null => {
    const parts = scopes
      .split(',')
      .map((part) => part.trim())
      .filter((part) => part.length > 0);
    return parts.length > 0 ? parts : null;
  };

  const [resourceKind, resourceId] = resource.length > 0 ? resource.split(':', 2) : [null, null];

  function runCheck(): void {
    setCheckFailed(null);
    void useCase
      .check(principal, action, parsedScopes(), resourceKind as 'post' | 'comment' | null, resourceId)
      .then((result) => {
        if (result.ok) {
          setCheck(result.value);
        } else {
          setCheck(null);
          setCheckFailed(result.failure);
        }
      });
  }

  const realEnabled =
    (action === 'posts:write' && resourceKind === 'post') ||
    (action === 'comments:moderate' && resourceKind === 'comment');

  function runForReal(): void {
    setBusy(true);
    setReal({ state: 'idle' });
    const tokenScopes = parsedScopes() ?? ['*'];
    void mintUseCase
      .mint(principal, tokenScopes, 900, 0, 'real')
      .then((minted) => {
        if (!minted.ok) {
          setReal({ state: 'failed', failure: minted.failure });
          setBusy(false);
          return;
        }
        const credential = { kind: 'bearer' as const, token: minted.value.token };
        const call: Promise<Result<EditedPostOutcome> | Result<ModeratedCommentOutcome>> =
          resourceKind === 'post'
            ? useCase.editPost(credential, resourceId ?? '')
            : useCase.moderateComment(credential, resourceId ?? '', 'hidden');
        void call.then((result) => {
          setReal(
            result.ok
              ? { state: 'allowed', principal: result.value.principal, reason: result.value.reason }
              : {
                  state: 'denied',
                  message: `${result.failure.code}: ${result.failure.message}`,
                },
          );
          setBusy(false);
        });
      });
  }

  return (
    <div className="flex flex-col gap-md">
      <section
        data-testid="authz-matrix-principals"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        {data.principals.map((row) => (
          <p key={row.name} className="text-caption text-on-surface">
            <span className="font-mono text-primary">
              {row.name} · {row.role ?? 'no role'}
            </span>{' '}
            — {row.note}
          </p>
        ))}
      </section>

      <section
        data-testid="authz-matrix-matrix"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        {data.roles.map((row) => (
          <p key={row.role} className="font-mono text-caption text-on-surface-variant">
            {row.role.padEnd(8)}{' '}
            {row.grants
              .map((cell) => `${cell.action}=${cell.level ?? '—'}`)
              .join('  ')}
          </p>
        ))}
      </section>

      <section
        data-testid="authz-matrix-targets"
        className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
      >
        {data.seededPosts.slice(0, 6).map((post) => (
          <p key={post.id} className="font-mono text-caption text-on-surface-variant">
            post {post.id} · owner {post.author}
          </p>
        ))}
        {data.seededComments.map((comment) => (
          <p key={comment.id} className="font-mono text-caption text-on-surface-variant">
            comment {comment.id} · owner {comment.author} · {comment.status}
          </p>
        ))}
      </section>

      <section data-testid="authz-matrix-check" className="flex flex-col gap-xs">
        <div className="flex flex-wrap items-center gap-xs">
          <select
            value={principal}
            onChange={(event) => setPrincipal(event.target.value)}
            aria-label="principal"
            className="rounded-md border border-outline bg-transparent px-sm py-xxs text-caption text-on-surface"
          >
            {data.principals.map((row) => (
              <option key={row.name} value={row.name}>
                {row.name} ({row.role ?? 'no role'})
              </option>
            ))}
          </select>
          <select
            value={action}
            onChange={(event) => setAction(event.target.value)}
            aria-label="action"
            className="rounded-md border border-outline bg-transparent px-sm py-xxs text-caption text-on-surface"
          >
            {ACTIONS.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          <select
            value={resource}
            onChange={(event) => setResource(event.target.value)}
            aria-label="resource"
            className="rounded-md border border-outline bg-transparent px-sm py-xxs text-caption text-on-surface"
          >
            <option value="">(no object)</option>
            {data.seededPosts.map((post) => (
              <option key={post.id} value={`post:${post.id}`}>
                post · {post.id} ({post.author})
              </option>
            ))}
            {data.seededComments.map((comment) => (
              <option key={comment.id} value={`comment:${comment.id}`}>
                comment · {comment.id} ({comment.author})
              </option>
            ))}
          </select>
          <input
            type="text"
            value={scopes}
            maxLength={64}
            placeholder={`scopes (empty = ${data.wildcardScope})`}
            onChange={(event) => setScopes(event.target.value)}
            aria-label="credential scopes"
            className="w-52 rounded-md border border-outline bg-transparent px-sm py-xxs text-caption text-on-surface"
          />
          <button
            type="button"
            onClick={runCheck}
            className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary"
          >
            run the check
          </button>
          <button
            type="button"
            disabled={!realEnabled || busy}
            onClick={runForReal}
            className="rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50"
          >
            try it for real
          </button>
        </div>

        {checkFailed && (
          <p data-testid="authz-matrix-check-error" className="text-caption text-error">
            {checkFailed.message}
          </p>
        )}

        {check && (
          <section
            data-testid="authz-matrix-check-result"
            className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
          >
            <p
              className={`font-mono text-caption ${
                check.decision.allowed ? 'text-primary' : 'text-error'
              }`}
            >
              {check.decision.allowed ? 'ALLOW' : 'DENY'} — {check.decision.reason}
            </p>
            <p className="text-caption text-on-surface-variant">{check.detail}</p>
          </section>
        )}

        {real.state === 'allowed' && (
          <section
            data-testid="authz-matrix-real-result"
            className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
          >
            <p className="font-mono text-caption text-primary">
              200 · {real.principal} — {real.reason}
            </p>
          </section>
        )}
        {real.state === 'denied' && (
          <section
            data-testid="authz-matrix-real-result"
            className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
          >
            <p className="font-mono text-caption text-error">{real.message}</p>
          </section>
        )}
        {real.state === 'failed' && (
          <p data-testid="authz-matrix-real-error" className="text-caption text-error">
            {real.failure.message}
          </p>
        )}
      </section>

      <p data-testid="authz-matrix-reasoning" className="text-body-sm text-on-surface-variant">
        {data.denyNote} {data.scopeNote} {data.ownershipNote} {data.reasoning}
      </p>
    </div>
  );
}

export default MatrixDemo;
