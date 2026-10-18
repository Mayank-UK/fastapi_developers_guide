import { useEffect, useRef, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  GrpcConsoleCall,
  GrpcConsoleRoster,
  GrpcConsoleRound,
  GrpcMethod,
  ViewEventInput,
  ChatNoteInput,
} from '../../../domain/demo/grpc-console';

/**
 * GrpcConsoleDemo — the gRPC topic's console (demo block id
 * `api:grpc-console`). Loads the roster (the live satellite's address,
 * the service stanza of the real guide.proto, the four methods with
 * their stream kinds), then fires REAL rounds: pick a method, bring its
 * arguments (slug for unary, tag filter for server-streaming, one
 * `slug|viewer` view event per line for client-streaming, one
 * `sender|text` note per line for bidirectional), optionally set a
 * deadline in milliseconds, and the payload reports what actually
 * happened — the response messages in arrival order (proto field maps),
 * the status code in grpc's own vocabulary, and elapsed time.
 *
 * A NOT_FOUND or DEADLINE_EXCEEDED round renders INLINE as the round's
 * honest answer (the console's HTTP call succeeded; the status IS the
 * payload) — including the partial messages a mid-stream deadline kept.
 * Only transport failures degrade to the shared ErrorPanel.
 */

type RosterStatus =
  | { state: 'loading' }
  | { state: 'ready'; roster: GrpcConsoleRoster }
  | { state: 'failed'; failure: Failure };

type RoundStatus =
  | { state: 'idle' }
  | { state: 'busy' }
  | { state: 'done'; round: GrpcConsoleRound }
  | { state: 'failed'; failure: Failure };

const inputClass =
  'rounded-md border border-outline bg-surface-tint px-sm py-xxs font-mono ' +
  'text-caption text-on-surface focus:border-primary focus:outline-none';

const chipClass = (active: boolean): string =>
  active
    ? 'rounded-pill border border-primary bg-surface-tint px-sm py-xxs font-mono text-caption text-primary'
    : 'rounded-pill border border-outline px-sm py-xxs font-mono text-caption ' +
      'text-on-surface-variant transition-colors hover:border-primary hover:text-primary';

const actionClass =
  'self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption ' +
  'uppercase tracking-wide text-on-surface transition-colors hover:border-primary ' +
  'hover:text-primary disabled:cursor-not-allowed disabled:opacity-50';

const statusClass = (ok: boolean): string =>
  ok
    ? 'rounded-md border border-outline px-sm py-xs font-mono text-caption text-on-surface'
    : 'rounded-md border border-error px-sm py-xs font-mono text-caption text-on-surface';

/** Parse one `left|right` line; blank and malformed lines are skipped. */
function parsePairs(lines: string): [string, string][] {
  const pairs: [string, string][] = [];
  for (const line of lines.split('\n')) {
    const parts = line.split('|');
    const left = parts[0]?.trim() ?? '';
    const right = parts[1]?.trim() ?? '';
    if (left !== '' && right !== '') {
      pairs.push([left, right]);
    }
  }
  return pairs;
}

function RoundResult({ round }: { round: GrpcConsoleRound }) {
  const ok = round.statusCode === 'OK';
  return (
    <section data-testid="gc-result" className="flex flex-col gap-sm">
      <p data-testid="gc-status" className={statusClass(ok)}>
        <span className={ok ? 'text-secondary' : 'text-error'}>{round.statusCode}</span>
        <span className="text-on-surface-variant">
          {' '}· {round.method.name} ({round.method.kind}) · sent {String(round.sentMessages)} ·
          received {String(round.messages.length)} · {String(round.elapsedMs)}ms ·{' '}
          {round.serverAddress}
        </span>
        {round.deadlineMs !== undefined && (
          <span className="text-on-surface-variant"> · deadline {String(round.deadlineMs)}ms</span>
        )}
      </p>

      {round.statusDetail !== '' && (
        <p data-testid="gc-detail" className="font-mono text-caption text-on-surface-variant">
          detail: {round.statusDetail}
        </p>
      )}

      <div data-testid="gc-messages" className="flex flex-col gap-xxs">
        {round.messages.map((message) => (
          <p
            key={message.index}
            data-testid="gc-message"
            className="font-mono text-caption text-on-surface"
          >
            <span className="text-on-surface-variant">#{String(message.index)}</span>{' '}
            {JSON.stringify(message.fields)}
          </p>
        ))}
      </div>

      <p data-testid="gc-reasoning" className="text-body-sm text-on-surface-variant">
        {round.reasoning}
      </p>
    </section>
  );
}

export function GrpcConsoleDemo() {
  const useCase = container.getGrpcConsoleDemoUseCase;
  const [roster, setRoster] = useState<RosterStatus>({ state: 'loading' });
  const [method, setMethod] = useState<GrpcMethod>('get-post');
  const [slug, setSlug] = useState('drafting-the-grpc-chapter');
  const [tag, setTag] = useState('');
  const [viewLines, setViewLines] = useState('idempotency-retold|mak\nidempotency-retold|ada');
  const [noteLines, setNoteLines] = useState('you|hello\nme|is this thing on?');
  const [deadline, setDeadline] = useState('');
  const [round, setRound] = useState<RoundStatus>({ state: 'idle' });
  const loadedOnce = useRef(false);

  useEffect(() => {
    if (loadedOnce.current) return;
    loadedOnce.current = true;
    // Mount-once: the roster loads the moment the demo renders; the use
    // case is container-resolved so specs swap the token.
    void useCase.roster().then((result) => {
      setRoster(
        result.ok
          ? { state: 'ready', roster: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  }, []);

  const retryRoster = () => {
    setRoster({ state: 'loading' });
    void useCase.roster().then((result) => {
      setRoster(
        result.ok
          ? { state: 'ready', roster: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  const fire = () => {
    const parsedViews: ViewEventInput[] = parsePairs(viewLines).map(([eventSlug, viewer]) => ({
      slug: eventSlug,
      viewer,
    }));
    const parsedNotes: ChatNoteInput[] = parsePairs(noteLines).map(([sender, text]) => ({
      sender,
      text,
    }));
    const deadlineMs = Number.parseInt(deadline, 10);
    const call: GrpcConsoleCall = {
      method,
      slug,
      tag,
      viewEvents: parsedViews,
      chatNotes: parsedNotes,
      ...(Number.isFinite(deadlineMs) ? { deadlineMs } : {}),
    };
    setRound({ state: 'busy' });
    void useCase.run(call).then((result) => {
      setRound(
        result.ok
          ? { state: 'done', round: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  if (roster.state === 'loading') {
    return (
      <p data-testid="gc-loading" className="text-body-sm text-on-surface-variant">
        reading the roster — satellite address, contract, methods…
      </p>
    );
  }

  if (roster.state === 'failed') {
    return <ErrorPanel subject="the gRPC console" failure={roster.failure} onRetry={retryRoster} />;
  }

  const { roster: loaded } = roster;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="gc-roster" className="flex flex-col gap-sm">
        <p data-testid="gc-facts" className="font-mono text-caption text-on-surface">
          <span className="text-secondary">{loaded.service}</span>
          <span className="text-on-surface-variant">
            {' '}live at {loaded.serverAddress} · {String(loaded.streamPauseMs)}ms between streamed
            messages
          </span>
        </p>

        <pre
          data-testid="gc-proto"
          className="overflow-x-auto rounded-md border border-outline bg-surface-tint px-sm py-xs font-mono text-caption text-on-surface"
        >
          {loaded.protoExcerpt}
        </pre>

        <div className="flex flex-wrap items-center gap-xxs">
          <span className="text-caption text-on-surface-variant">method:</span>
          {loaded.methods.map((card) => (
            <button
              key={card.id}
              type="button"
              data-testid="gc-method"
              title={card.description}
              onClick={() => setMethod(card.id)}
              className={chipClass(card.id === method)}
            >
              {card.name} · {card.kind}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-sm">
          {method === 'get-post' && (
            <label className="flex items-center gap-xxs">
              <span className="text-caption text-on-surface-variant">slug</span>
              <input
                data-testid="gc-slug"
                className={inputClass}
                value={slug}
                maxLength={120}
                onChange={(event) => setSlug(event.target.value)}
              />
            </label>
          )}
          {method === 'stream-posts' && (
            <label className="flex items-center gap-xxs">
              <span className="text-caption text-on-surface-variant">tag filter</span>
              <input
                data-testid="gc-tag"
                className={inputClass}
                value={tag}
                maxLength={40}
                placeholder="empty = the whole collection"
                onChange={(event) => setTag(event.target.value)}
              />
            </label>
          )}
          <label className="flex items-center gap-xxs">
            <span className="text-caption text-on-surface-variant">deadline ms</span>
            <input
              data-testid="gc-deadline"
              className={inputClass}
              value={deadline}
              inputMode="numeric"
              placeholder="none"
              onChange={(event) => setDeadline(event.target.value.replace(/[^0-9]/g, ''))}
            />
          </label>
          <button
            type="button"
            data-testid="gc-fire"
            onClick={fire}
            disabled={round.state === 'busy'}
            className={actionClass}
          >
            Fire the call
          </button>
        </div>

        {method === 'count-views' && (
          <label className="flex flex-col gap-xxs">
            <span className="text-caption text-on-surface-variant">
              view events — one per line, slug|viewer
            </span>
            <textarea
              data-testid="gc-views"
              className={`${inputClass} min-h-16`}
              value={viewLines}
              onChange={(event) => setViewLines(event.target.value)}
            />
          </label>
        )}
        {method === 'echo-chat' && (
          <label className="flex flex-col gap-xxs">
            <span className="text-caption text-on-surface-variant">
              chat notes — one per line, sender|text
            </span>
            <textarea
              data-testid="gc-notes"
              className={`${inputClass} min-h-16`}
              value={noteLines}
              onChange={(event) => setNoteLines(event.target.value)}
            />
          </label>
        )}

        <p data-testid="gc-reasoning-roster" className="text-body-sm text-on-surface-variant">
          {loaded.reasoning}
        </p>
      </section>

      {round.state === 'failed' && (
        <ErrorPanel subject="the gRPC round" failure={round.failure} onRetry={fire} />
      )}

      {round.state === 'busy' && (
        <p data-testid="gc-busy" className="text-body-sm text-on-surface-variant">
          performing the real grpc.aio round…
        </p>
      )}

      {round.state === 'done' && <RoundResult round={round.round} />}
    </div>
  );
}

export default GrpcConsoleDemo;
