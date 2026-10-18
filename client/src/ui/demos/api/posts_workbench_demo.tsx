import { useEffect, useRef, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  PostSort,
  PostStatus,
  WorkbenchMethod,
  WorkbenchOutcome,
  WorkbenchQuery,
  WorkbenchRoster,
  WorkbenchRound,
  WorkbenchTemplate,
} from '../../../domain/demo/posts-workbench';

/**
 * PostsWorkbenchDemo — the api-design topic's workbench (demo block id
 * `api:posts-workbench`). Assemble a request against the REAL /api/posts
 * substrate: pick a method (GET/POST/PUT/DELETE) and a path template
 * (collection or item), tune the collection query (page, limit, author,
 * tag, status, sort — authors and tags offered from the substrate's live
 * facets) or a create/replace body, and fire. The server executes the
 * round through the same use cases the real router resolves, and the
 * outcome reports the request it would send, the status line, the
 * page/post/envelope payload it earns, the pagination headers a list
 * would carry, and the layer stack (routing → validation → use case →
 * repository → response) that served it. POST/PUT genuinely mutate the
 * store; DELETE earns its honest 405 through the shared envelope.
 *
 * Dependency flow mirrors the other demos: the use case resolves from
 * the container at render time (specs substitute fakes through the
 * container token), failures arrive as typed Failures inside Results,
 * and the shared ErrorPanel offers recovery.
 */

type RosterStatus =
  | { state: 'loading' }
  | { state: 'ready'; roster: WorkbenchRoster }
  | { state: 'failed'; failure: Failure };

type RoundStatus =
  | { state: 'idle' }
  | { state: 'busy' }
  | { state: 'done'; outcome: WorkbenchOutcome }
  | { state: 'failed'; failure: Failure };

const METHODS: readonly WorkbenchMethod[] = ['GET', 'POST', 'PUT', 'DELETE'];
const TEMPLATES: readonly { value: WorkbenchTemplate; label: string }[] = [
  { value: '/api/posts', label: 'collection' },
  { value: '/api/posts/{postId}', label: 'item' },
];
const LIMITS: readonly number[] = [3, 6, 12];
const SORTS: readonly PostSort[] = ['newest', 'oldest', 'title'];

const CREATE_BODY = JSON.stringify(
  { title: 'A post from the workbench', author: 'grace', tags: ['api'], status: 'published' },
  null,
  2,
);
const REPLACE_BODY = JSON.stringify(
  {
    title: 'Idempotency, retold again',
    body: 'Replaced through PUT.',
    author: 'alan',
    tags: ['http'],
    status: 'draft',
  },
  null,
  2,
);

const inputClass =
  'rounded-md border border-outline bg-surface-tint px-sm py-xxs font-mono ' +
  'text-caption text-on-surface focus:border-primary focus:outline-none';

const selectClass = inputClass + ' pr-sm';

const chipClass = (active: boolean): string =>
  active
    ? 'rounded-pill border border-primary bg-surface-tint px-sm py-xxs font-mono text-caption text-primary'
    : 'rounded-pill border border-outline px-sm py-xxs font-mono text-caption ' +
      'text-on-surface-variant transition-colors hover:border-primary hover:text-primary';

const actionClass =
  'self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption ' +
  'uppercase tracking-wide text-on-surface transition-colors hover:border-primary ' +
  'hover:text-primary disabled:cursor-not-allowed disabled:opacity-50';

export function PostsWorkbenchDemo() {
  const useCase = container.getPostsWorkbenchDemoUseCase;
  const [roster, setRoster] = useState<RosterStatus>({ state: 'loading' });
  const [method, setMethod] = useState<WorkbenchMethod>('GET');
  const [template, setTemplate] = useState<WorkbenchTemplate>('/api/posts');
  const [postId, setPostId] = useState('idempotency-retold');
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(6);
  const [author, setAuthor] = useState('');
  const [tag, setTag] = useState('');
  const [status, setStatus] = useState<'' | PostStatus>('');
  const [sort, setSort] = useState<PostSort>('newest');
  const [bodyText, setBodyText] = useState(CREATE_BODY);
  const [parseError, setParseError] = useState<string | null>(null);
  const [round, setRound] = useState<RoundStatus>({ state: 'idle' });
  const [lastRound, setLastRound] = useState<WorkbenchRound | null>(null);
  const loadedOnce = useRef(false);

  useEffect(() => {
    if (loadedOnce.current) return;
    loadedOnce.current = true;
    // Mount-once: the facets load the moment the demo renders; the use
    // case is container-resolved so specs swap the token, not the hook.
    void useCase.roster().then((result) => {
      setRoster(result.ok ? { state: 'ready', roster: result.value } : { state: 'failed', failure: result.failure });
    });
  }, []);

  const item = template === '/api/posts/{postId}';
  const showsQuery = method === 'GET' && !item;
  const showsBody = method === 'POST' || method === 'PUT';

  const reset = () => setRound({ state: 'idle' });

  const buildRound = (): WorkbenchRound | string => {
    const round: WorkbenchRound = { method, template };
    if (item) round.postId = postId.trim();
    if (showsQuery) {
      const query: WorkbenchQuery = { page, limit, sort };
      if (author !== '') query.author = author;
      if (tag !== '') query.tag = tag;
      if (status !== '') query.status = status;
      round.query = query;
    }
    if (showsBody) {
      let parsed: unknown;
      try {
        parsed = JSON.parse(bodyText);
      } catch (error) {
        return error instanceof Error ? error.message : 'This is not valid JSON.';
      }
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        return 'The body must be a JSON object.';
      }
      round.body = parsed as WorkbenchRound['body'];
    }
    return round;
  };

  const fire = (candidate: WorkbenchRound) => {
    setLastRound(candidate);
    setRound({ state: 'busy' });
    void useCase.run(candidate).then((result) => {
      setRound(
        result.ok
          ? { state: 'done', outcome: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  const send = () => {
    const candidate = buildRound();
    if (typeof candidate === 'string') {
      setParseError(candidate);
      return;
    }
    setParseError(null);
    fire(candidate);
  };

  const retry = () => {
    if (lastRound === null) return;
    fire(lastRound);
  };

  return (
    <div className="flex flex-col gap-md">
      {roster.state === 'loading' && (
        <p data-testid="pw-loading" className="text-caption text-on-surface-variant">
          loading the substrate's facets…
        </p>
      )}
      {roster.state === 'failed' && (
        <ErrorPanel
          subject="the posts workbench"
          failure={roster.failure}
          onRetry={() => {
            setRoster({ state: 'loading' });
            void useCase.roster().then((result) => {
              setRoster(
                result.ok
                  ? { state: 'ready', roster: result.value }
                  : { state: 'failed', failure: result.failure },
              );
            });
          }}
        />
      )}

      {roster.state === 'ready' && (
        <section data-testid="pw-form" className="flex flex-col gap-sm">
          <div className="flex flex-wrap items-center gap-xs">
            <span className="text-caption text-on-surface-variant">method</span>
            {METHODS.map((value) => (
              <button
                key={value}
                type="button"
                data-testid={`pw-method-${value}`}
                onClick={() => {
                  setMethod(value);
                  reset();
                }}
                className={chipClass(method === value)}
              >
                {value}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-xs">
            <span className="text-caption text-on-surface-variant">path template</span>
            {TEMPLATES.map((entry) => (
              <button
                key={entry.value}
                type="button"
                data-testid={`pw-template-${entry.value === '/api/posts' ? 'collection' : 'item'}`}
                onClick={() => {
                  setTemplate(entry.value);
                  if (entry.value === '/api/posts/{postId}') setBodyText(REPLACE_BODY);
                  reset();
                }}
                className={chipClass(template === entry.value)}
              >
                {entry.label}
              </button>
            ))}
          </div>

          {item && (
            <label className="flex flex-col gap-xxs">
              <span className="text-caption text-on-surface-variant">
                postId (a real slug from the seed, or invent one to earn the 404)
              </span>
              <input
                data-testid="pw-post-id"
                className={inputClass}
                value={postId}
                onChange={(event) => {
                  setPostId(event.target.value);
                  reset();
                }}
                spellCheck={false}
              />
            </label>
          )}

          {showsQuery && (
            <div
              data-testid="pw-query"
              className="grid grid-cols-2 gap-xs rounded-md border border-outline px-sm py-xs sm:grid-cols-3"
            >
              <label className="flex flex-col gap-xxs">
                <span className="text-caption text-on-surface-variant">page</span>
                <input
                  data-testid="pw-page"
                  type="number"
                  min={1}
                  className={inputClass}
                  value={page}
                  onChange={(event) => {
                    setPage(Math.max(1, Number(event.target.value) || 1));
                    reset();
                  }}
                />
              </label>
              <label className="flex flex-col gap-xxs">
                <span className="text-caption text-on-surface-variant">limit</span>
                <select
                  data-testid="pw-limit"
                  className={selectClass}
                  value={limit}
                  onChange={(event) => {
                    setLimit(Number(event.target.value));
                    reset();
                  }}
                >
                  {LIMITS.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-xxs">
                <span className="text-caption text-on-surface-variant">sort</span>
                <select
                  data-testid="pw-sort"
                  className={selectClass}
                  value={sort}
                  onChange={(event) => {
                    setSort(event.target.value as PostSort);
                    reset();
                  }}
                >
                  {SORTS.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-xxs">
                <span className="text-caption text-on-surface-variant">author</span>
                <select
                  data-testid="pw-author"
                  className={selectClass}
                  value={author}
                  onChange={(event) => {
                    setAuthor(event.target.value);
                    reset();
                  }}
                >
                  <option value="">(any)</option>
                  {roster.roster.authors.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-xxs">
                <span className="text-caption text-on-surface-variant">tag</span>
                <select
                  data-testid="pw-tag"
                  className={selectClass}
                  value={tag}
                  onChange={(event) => {
                    setTag(event.target.value);
                    reset();
                  }}
                >
                  <option value="">(any)</option>
                  {roster.roster.tags.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-xxs">
                <span className="text-caption text-on-surface-variant">status</span>
                <select
                  data-testid="pw-status-filter"
                  className={selectClass}
                  value={status}
                  onChange={(event) => {
                    setStatus(event.target.value as '' | PostStatus);
                    reset();
                  }}
                >
                  <option value="">(any)</option>
                  {roster.roster.statuses.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {showsBody && (
            <label className="flex flex-col gap-xxs">
              <span className="text-caption text-on-surface-variant">
                body (JSON object) — validated through PostCreate at the edge
              </span>
              <textarea
                data-testid="pw-body"
                className={`${inputClass} min-h-[7rem]`}
                value={bodyText}
                onChange={(event) => {
                  setBodyText(event.target.value);
                  reset();
                }}
                spellCheck={false}
              />
            </label>
          )}

          {parseError !== null && (
            <p data-testid="pw-parse-warning" className="text-caption text-error">
              Cannot send — the editor is not a valid JSON object: {parseError}
            </p>
          )}

          <div className="flex items-center gap-sm">
            <button
              type="button"
              data-testid="pw-fire"
              onClick={send}
              disabled={round.state === 'busy'}
              className={actionClass}
            >
              Fire the round
            </button>
            {round.state === 'busy' && (
              <span data-testid="pw-busy" className="text-caption text-on-surface-variant">
                running through the real pipeline…
              </span>
            )}
          </div>
        </section>
      )}

      {round.state === 'failed' && (
        <ErrorPanel subject="the posts workbench" failure={round.failure} onRetry={retry} />
      )}

      {round.state === 'done' && <Outcome outcome={round.outcome} />}

      {round.state === 'idle' && roster.state === 'ready' && (
        <p data-testid="pw-idle" className="text-body-sm text-on-surface-variant">
          {roster.roster.reasoning}
        </p>
      )}
    </div>
  );
}

function Outcome({ outcome }: { outcome: WorkbenchOutcome }) {
  return (
    <section data-testid="pw-outcome" className="flex flex-col gap-sm">
      <p data-testid="pw-status" className="font-mono text-body-sm text-on-surface">
        <span className={outcome.kind === 'envelope' ? 'text-error' : 'text-secondary'}>
          {outcome.statusReason}
        </span>
        {' · '}
        <span data-testid="pw-request">
          {outcome.request.method} {outcome.request.path}
        </span>
      </p>

      {outcome.kind === 'page' && outcome.page !== undefined && (
        <div data-testid="pw-page-payload" className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs">
          <ul className="flex flex-col gap-xxs">
            {outcome.page.items.map((post) => (
              <li key={post.id} className="font-mono text-caption text-on-surface">
                <span className="text-secondary">{post.id}</span>
                <span className="text-on-surface-variant">
                  {' '}
                  · {post.title} · {post.author} · {post.status}
                </span>
              </li>
            ))}
          </ul>
          {outcome.pagination !== undefined && (
            <p data-testid="pw-pagination" className="font-mono text-caption text-on-surface-variant">
              page {outcome.pagination.page} of {outcome.pagination.pages} ·{' '}
              {outcome.pagination.total} match in total
              {outcome.pagination.next !== undefined && <> · next: {outcome.pagination.next}</>}
              {outcome.pagination.prev !== undefined && <> · prev: {outcome.pagination.prev}</>}
            </p>
          )}
        </div>
      )}

      {outcome.kind === 'post' && outcome.post !== undefined && (
        <div data-testid="pw-post" className="rounded-md border border-outline px-sm py-xs">
          <pre className="overflow-x-auto font-mono text-caption text-on-surface-variant">
            {JSON.stringify(outcome.post, null, 2)}
          </pre>
        </div>
      )}

      {outcome.kind === 'envelope' && outcome.envelope !== undefined && (
        <div
          data-testid="pw-envelope"
          className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs"
        >
          <p className="font-mono text-caption">
            <span className="text-error">{outcome.envelope.code}</span>
            <span className="text-on-surface-variant"> · requestId: {outcome.envelope.requestId}</span>
          </p>
          <p className="text-body-sm text-on-surface">{outcome.envelope.message}</p>
        </div>
      )}

      <div data-testid="pw-layers" className="flex flex-col gap-xxs">
        <p className="text-caption text-on-surface-variant">the layers that served it:</p>
        <ol className="flex flex-col gap-xxs">
          {outcome.layers.map((layer, index) => (
            <li key={index} className="font-mono text-caption text-on-surface-variant">
              <span className="text-secondary">{layer.name}</span> — {layer.detail}
            </li>
          ))}
        </ol>
      </div>

      <p className="text-body-sm text-on-surface-variant">{outcome.reasoning}</p>
    </section>
  );
}

export default PostsWorkbenchDemo;
