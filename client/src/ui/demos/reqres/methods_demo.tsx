import { useEffect, useRef, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import type { Result } from '../../../core/result';
import { ErrorPanel } from '../../components/error-panel';
import type { MethodsExchange, NoteDraft, NotesListing } from '../../../domain/demo/reqres-methods';

/**
 * RequestMethodsDemo — the request-response topic's methods playground
 * (demo block id `reqres:methods`). One in-memory resource, the whole
 * contract: POST the draft (201 Created, Location shown, body filtered —
 * no revision field, though the server tracks one per note); GET the
 * collection; PUT a full replace on the selected note (200 — content
 * replaced wholesale); DELETE it (204 No Content, then 404 on a second
 * try). "Send invalid body" posts an empty title on purpose and renders
 * the 422 validation_failed envelope through the shared error panel — the
 * contract's refusal path, live.
 *
 * Dependency flow mirrors the other demos: the use case resolves from the
 * container at render time (specs substitute fakes through the container
 * token), failures arrive as typed Failures inside Results, and the
 * shared ErrorPanel offers recovery.
 */

type WorkStatus =
  | { state: 'quiet' }
  | { state: 'busy' }
  | { state: 'failed'; failure: Failure };

const inputClass =
  'w-full rounded-md border border-outline bg-surface-tint px-sm py-xxs ' +
  'font-mono text-caption text-on-surface placeholder:text-on-surface-variant ' +
  'focus:border-primary focus:outline-none';

const actionClass =
  'self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption ' +
  'uppercase tracking-wide text-on-surface transition-colors hover:border-primary ' +
  'hover:text-primary disabled:cursor-not-allowed disabled:opacity-50';

const draftOf = (title: string, body: string, tags: string): NoteDraft => ({
  title: title.trim(),
  body: body.trim(),
  tags: tags
    .split(',')
    .map((tag) => tag.trim())
    .filter((tag) => tag !== ''),
});

export function RequestMethodsDemo() {
  const useCase = container.reqresMethodsDemoUseCase;
  const [listing, setListing] = useState<NotesListing | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [tags, setTags] = useState('');
  const [exchange, setExchange] = useState<MethodsExchange | null>(null);
  const [work, setWork] = useState<WorkStatus>({ state: 'quiet' });
  const loadedOnce = useRef(false);

  /** Reload the collection only — never disturbs the exchange line. */
  const refresh = () => {
    void useCase.list().then((result) => {
      if (result.ok) {
        setListing(result.value.listing ?? null);
        setWork({ state: 'quiet' });
      } else {
        setWork({ state: 'failed', failure: result.failure });
      }
    });
  };

  useEffect(() => {
    if (loadedOnce.current) return;
    loadedOnce.current = true;
    // Mount-once: the collection loads the moment the demo renders, and the
    // exchange line starts with that GET; the use case is container-resolved
    // so specs swap the token, not the hook.
    void useCase.list().then((result) => {
      if (result.ok) {
        setListing(result.value.listing ?? null);
        setExchange(result.value);
      } else {
        setWork({ state: 'failed', failure: result.failure });
      }
    });
  }, []);

  const run = (operation: () => Promise<Result<MethodsExchange>>) => {
    setWork({ state: 'busy' });
    void operation().then((result) => {
      if (result.ok) {
        setExchange(result.value);
        if (result.value.note !== undefined) {
          setTitle(result.value.note.title);
          setBody(result.value.note.body);
          setTags(result.value.note.tags.join(', '));
          setSelectedId(result.value.note.id);
        }
        if (result.value.method === 'DELETE') {
          setSelectedId(null);
        }
        setWork({ state: 'quiet' });
        refresh();
      } else {
        setWork({ state: 'failed', failure: result.failure });
      }
    });
  };

  const draft = draftOf(title, body, tags);
  const selected = listing?.notes.find((note) => note.id === selectedId) ?? null;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="rm-form" className="flex flex-col gap-sm">
        <div className="flex flex-wrap gap-sm">
          <label className="flex flex-1 flex-col gap-xxs">
            <span className="text-caption text-on-surface-variant">title (1–80 chars)</span>
            <input
              data-testid="rm-title"
              className={inputClass}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="a note the server will validate"
            />
          </label>
          <label className="flex flex-1 flex-col gap-xxs">
            <span className="text-caption text-on-surface-variant">tags (comma-separated)</span>
            <input
              data-testid="rm-tags"
              className={inputClass}
              value={tags}
              onChange={(event) => setTags(event.target.value)}
              placeholder="terminal, demo"
            />
          </label>
        </div>
        <label className="flex flex-col gap-xxs">
          <span className="text-caption text-on-surface-variant">body</span>
          <input
            data-testid="rm-body"
            className={inputClass}
            value={body}
            onChange={(event) => setBody(event.target.value)}
            placeholder="the full representation travels on POST and PUT"
          />
        </label>

        <div className="flex flex-wrap items-center gap-sm">
          <button
            type="button"
            data-testid="rm-create"
            onClick={() => run(() => useCase.create(draft))}
            disabled={work.state === 'busy' || draft.title === ''}
            className={actionClass}
          >
            POST — create
          </button>
          <button
            type="button"
            data-testid="rm-replace"
            onClick={() => selectedId !== null && run(() => useCase.replace(selectedId, draft))}
            disabled={work.state === 'busy' || selectedId === null || draft.title === ''}
            className={actionClass}
          >
            PUT — replace #{selectedId ?? '…'}
          </button>
          <button
            type="button"
            data-testid="rm-delete"
            onClick={() => selectedId !== null && run(() => useCase.remove(selectedId))}
            disabled={work.state === 'busy' || selectedId === null}
            className={actionClass}
          >
            DELETE — remove #{selectedId ?? '…'}
          </button>
          <button
            type="button"
            data-testid="rm-invalid"
            onClick={() => run(() => useCase.create({ title: '', body: '', tags: [] }))}
            disabled={work.state === 'busy'}
            className={actionClass}
          >
            Send invalid body (empty title → 422)
          </button>
          {work.state === 'busy' && (
            <span data-testid="rm-loading" className="text-caption text-on-surface-variant">
              on the wire…
            </span>
          )}
        </div>
      </section>

      {work.state === 'failed' && (
        <ErrorPanel subject="the methods playground" failure={work.failure} onRetry={refresh} />
      )}

      {exchange !== null && (
        <section data-testid="rm-exchange" className="flex flex-col gap-xxs">
          <p className="text-caption text-on-surface-variant">last exchange on the wire:</p>
          <p className="font-mono text-body-sm text-on-surface">
            <span className="text-secondary">{exchange.method}</span> {exchange.path}{' '}
            <span className="text-primary">{exchange.status}</span>
            {exchange.location !== undefined && (
              <span className="text-on-surface-variant"> · location: {exchange.location}</span>
            )}
            {exchange.method === 'DELETE' && exchange.status === 204 && (
              <span className="text-on-surface-variant"> · no content, by design</span>
            )}
          </p>
        </section>
      )}

      {listing !== null && (
        <section data-testid="rm-listing" className="flex flex-col gap-sm">
          <p className="text-caption text-on-surface-variant">
            {listing.count} note{listing.count === 1 ? '' : 's'} — every one filtered through
            NotePublic: no revision field exists on the wire, though the server tracks one per
            note.
          </p>
          <div className="flex flex-col gap-xxs">
            {listing.notes.map((note) => (
              <button
                key={note.id}
                type="button"
                data-testid={`rm-note-${note.id}`}
                onClick={() => {
                  setSelectedId(note.id);
                  setTitle(note.title);
                  setBody(note.body);
                  setTags(note.tags.join(', '));
                }}
                className={
                  note.id === selectedId
                    ? 'rounded-md border border-primary bg-surface-tint px-sm py-xxs text-left font-mono text-caption text-primary'
                    : 'rounded-md border border-outline px-sm py-xxs text-left font-mono text-caption text-on-surface transition-colors hover:border-primary hover:text-primary'
                }
              >
                #{note.id} {note.title} · {note.tags.join(', ') || 'no tags'} · revision:
                filtered by response_model
                {selected?.id === note.id && <span className="ml-xs">· selected</span>}
              </button>
            ))}
          </div>
          <p className="text-body-sm text-on-surface-variant">{listing.reasoning}</p>
        </section>
      )}

      {exchange?.note !== undefined && (
        <section data-testid="rm-note" className="flex flex-col gap-xxs">
          <p className="text-caption text-on-surface-variant">
            the body that answered the last POST/PUT — the filtered representation:
          </p>
          <p className="font-mono text-body-sm text-on-surface">
            #{exchange.note.id} {exchange.note.title}
          </p>
          <p className="font-mono text-caption text-on-surface-variant">
            {exchange.note.body || '(empty body)'} · created {exchange.note.createdAt} · tags:[
            {exchange.note.tags.join(', ')}]
          </p>
        </section>
      )}
    </div>
  );
}

export default RequestMethodsDemo;
