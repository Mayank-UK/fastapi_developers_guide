import { useEffect, useMemo, useRef, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  ArenaModelKey,
  ArenaModelSummary,
  ArenaOutcome,
  ArenaVerdict,
} from '../../../domain/demo/validation-arena';

/**
 * ValidationArenaDemo — the validation topic's arena (demo block id
 * `validation:arena`). Pick one of the roster's REAL wire models (the
 * notes playground's POST body, the pyd lab's strict specimen, the
 * scenario PATCH), feed it candidate field values as JSON, and fire: the
 * server runs that model's own pydantic validation — not a simulation —
 * and every field reports accepted, coerced (original → coerced), or
 * rejected with the exact {loc, msg, type} triple the 422 envelope would
 * carry, body-prefixed the way FastAPI reports a request model. A bogus
 * model key cannot even leave this component: the picker only offers the
 * roster, and a non-object candidates value demonstrates the edge's own
 * 422 through the shared error panel.
 *
 * Dependency flow mirrors the other demos: the use case resolves from the
 * container at render time (specs substitute fakes through the container
 * token — the documented replace-a-singleton seam), failures arrive as
 * typed Failures inside Results, and the shared ErrorPanel offers
 * recovery.
 */

type RosterStatus =
  | { state: 'loading' }
  | { state: 'ready'; models: ArenaModelSummary[]; reasoning: string }
  | { state: 'failed'; failure: Failure };

type RoundStatus =
  | { state: 'idle' }
  | { state: 'busy' }
  | { state: 'done'; verdict: ArenaVerdict }
  | { state: 'failed'; failure: Failure };

interface Preset {
  key: string;
  label: string;
  text: string;
}

/** Per model: three one-click candidate payloads, first is the default. */
const PRESETS: Record<ArenaModelKey, readonly [Preset, ...Preset[]]> = {
  'note-create': [
    {
      key: 'accepted',
      label: 'valid body',
      text: JSON.stringify({ title: 'a note the arena judged', tags: ['arena'] }, null, 2),
    },
    {
      key: 'missing',
      label: 'required field omitted',
      text: JSON.stringify({ body: 'no title was sent' }, null, 2),
    },
    {
      key: 'too-short',
      label: 'constraint violation',
      text: JSON.stringify({ title: '' }, null, 2),
    },
  ],
  'lab-specimen': [
    {
      key: 'coerced',
      label: 'coercion-rich',
      text: JSON.stringify(
        {
          count: '3',
          flag: 'true',
          tags: ['boundary'],
          score: '100',
          handle: '  Validation Arena ',
        },
        null,
        2,
      ),
    },
    {
      key: 'bounds',
      label: 'score out of bounds',
      text: JSON.stringify(
        { count: 1, flag: true, tags: ['x'], score: 101, handle: 'ok' },
        null,
        2,
      ),
    },
    {
      key: 'cross-field',
      label: 'cross-field rule',
      text: JSON.stringify(
        { count: 1, flag: true, tags: [], score: 5, handle: 'ok' },
        null,
        2,
      ),
    },
  ],
  'scenario-patch': [
    {
      key: 'accepted',
      label: 'enum member',
      text: JSON.stringify({ dataMode: 'live' }, null, 2),
    },
    {
      key: 'literal',
      label: 'literal_error',
      text: JSON.stringify({ dataMode: 'loud' }, null, 2),
    },
    {
      key: 'null',
      label: 'explicit null',
      text: JSON.stringify({ dataMode: null }, null, 2),
    },
  ],
};

const inputClass =
  'w-full rounded-md border border-outline bg-surface-tint px-sm py-xxs ' +
  'font-mono text-caption text-on-surface placeholder:text-on-surface-variant ' +
  'focus:border-primary focus:outline-none';

const actionClass =
  'self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption ' +
  'uppercase tracking-wide text-on-surface transition-colors hover:border-primary ' +
  'hover:text-primary disabled:cursor-not-allowed disabled:opacity-50';

export function ValidationArenaDemo() {
  const useCase = container.getValidationArenaDemoUseCase;
  const [roster, setRoster] = useState<RosterStatus>({ state: 'loading' });
  const [selected, setSelected] = useState<ArenaModelKey>('note-create');
  const [payloadText, setPayloadText] = useState<string>(PRESETS['note-create'][0].text);
  const [parseError, setParseError] = useState<string | null>(null);
  const [round, setRound] = useState<RoundStatus>({ state: 'idle' });
  const [lastPayload, setLastPayload] = useState<unknown>(null);
  const loadedOnce = useRef(false);

  useEffect(() => {
    if (loadedOnce.current) return;
    loadedOnce.current = true;
    // Mount-once: the roster loads the moment the demo renders; the use
    // case is container-resolved so specs swap the token, not the hook.
    void useCase.roster().then((result) => {
      setRoster(
        result.ok
          ? { state: 'ready', models: result.value.models, reasoning: result.value.reasoning }
          : { state: 'failed', failure: result.failure },
      );
    });
  }, []);

  const selectedModel = useMemo(
    () =>
      roster.state === 'ready'
        ? (roster.models.find((model) => model.key === selected) ?? null)
        : null,
    [roster, selected],
  );

  const switchModel = (key: ArenaModelKey) => {
    setSelected(key);
    setPayloadText(PRESETS[key][0].text);
    setParseError(null);
    setRound({ state: 'idle' });
  };

  const fire = (candidates: Record<string, unknown>) => {
    const payload = { model: selected, candidates };
    setLastPayload(payload);
    setRound({ state: 'busy' });
    void useCase.run(payload).then((result) => {
      setRound(
        result.ok
          ? { state: 'done', verdict: result.value }
          : { state: 'failed', failure: result.failure },
      );
    });
  };

  const send = () => {
    let candidates: unknown;
    try {
      candidates = JSON.parse(payloadText);
    } catch (error) {
      setParseError(
        error instanceof Error ? error.message : 'This is not valid JSON.',
      );
      return;
    }
    setParseError(null);
    if (typeof candidates !== 'object' || candidates === null || Array.isArray(candidates)) {
      // Demonstrate the edge's own 422 deliberately: candidates must be an
      // object, and the server's request model says so with loc ["body",
      // "candidates"] — rendered through the shared error panel below.
      setLastPayload({ model: selected, candidates });
      setRound({ state: 'busy' });
      void useCase.run({ model: selected, candidates: candidates as Record<string, unknown> }).then(
        (result) => {
          setRound(
            result.ok
              ? { state: 'done', verdict: result.value }
              : { state: 'failed', failure: result.failure },
          );
        },
      );
      return;
    }
    fire(candidates as Record<string, unknown>);
  };

  const retry = () => {
    if (lastPayload === null) return;
    setRound({ state: 'busy' });
    void useCase.run(lastPayload as { model: ArenaModelKey; candidates: Record<string, unknown> }).then(
      (result) => {
        setRound(
          result.ok
            ? { state: 'done', verdict: result.value }
            : { state: 'failed', failure: result.failure },
        );
      },
    );
  };

  return (
    <div className="flex flex-col gap-md">
      {roster.state === 'loading' && (
        <p data-testid="va-loading" className="text-caption text-on-surface-variant">
          loading the roster…
        </p>
      )}
      {roster.state === 'failed' && (
        <ErrorPanel
          subject="the validation arena"
          failure={roster.failure}
          onRetry={() => {
            setRoster({ state: 'loading' });
            void useCase.roster().then((result) => {
              setRoster(
                result.ok
                  ? { state: 'ready', models: result.value.models, reasoning: result.value.reasoning }
                  : { state: 'failed', failure: result.failure },
              );
            });
          }}
        />
      )}

      {roster.state === 'ready' && (
        <section data-testid="va-form" className="flex flex-col gap-sm">
          <div className="flex flex-wrap items-center gap-xs">
            <span className="text-caption text-on-surface-variant">roster</span>
            {roster.models.map((model) => (
              <button
                key={model.key}
                type="button"
                data-testid={`va-model-${model.key}`}
                onClick={() => switchModel(model.key)}
                className={
                  model.key === selected
                    ? 'rounded-pill border border-primary bg-surface-tint px-sm py-xxs font-mono text-caption text-primary'
                    : 'rounded-pill border border-outline px-sm py-xxs font-mono text-caption text-on-surface-variant transition-colors hover:border-primary hover:text-primary'
                }
              >
                {model.model}
              </button>
            ))}
          </div>

          {selectedModel !== null && (
            <div data-testid="va-rules" className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs">
              <p className="text-caption text-on-surface">
                <span className="text-secondary">{selectedModel.model}</span> — {selectedModel.source}
              </p>
              <ul className="flex flex-col gap-xxs">
                {selectedModel.fields.map((field) => (
                  <li key={field.name} className="font-mono text-caption text-on-surface-variant">
                    {field.name}: {field.rule}
                  </li>
                ))}
              </ul>
              <p className="text-body-sm text-on-surface-variant">{selectedModel.description}</p>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-xs">
            <span className="text-caption text-on-surface-variant">experiments</span>
            {PRESETS[selected].map((preset) => (
              <button
                key={preset.key}
                type="button"
                data-testid={`va-preset-${preset.key}`}
                onClick={() => {
                  setPayloadText(preset.text);
                  setParseError(null);
                }}
                className="rounded-pill border border-outline px-sm py-xxs font-mono text-caption text-on-surface-variant transition-colors hover:border-primary hover:text-primary"
              >
                {preset.label}
              </button>
            ))}
          </div>

          <label className="flex flex-col gap-xxs">
            <span className="text-caption text-on-surface-variant">
              candidates (JSON object) — POST /api/demo/validation/arena
            </span>
            <textarea
              data-testid="va-payload"
              className={`${inputClass} min-h-[8rem]`}
              value={payloadText}
              onChange={(event) => setPayloadText(event.target.value)}
              spellCheck={false}
            />
          </label>
          {parseError !== null && (
            <p data-testid="va-parse-warning" className="text-caption text-error">
              Cannot send — the editor is not valid JSON: {parseError}
            </p>
          )}

          <div className="flex items-center gap-sm">
            <button
              type="button"
              data-testid="va-fire"
              onClick={send}
              disabled={round.state === 'busy'}
              className={actionClass}
            >
              Run the arena
            </button>
            {round.state === 'busy' && (
              <span data-testid="va-busy" className="text-caption text-on-surface-variant">
                judging…
              </span>
            )}
          </div>
        </section>
      )}

      {round.state === 'failed' && (
        <ErrorPanel subject="the validation arena" failure={round.failure} onRetry={retry} />
      )}

      {round.state === 'done' && <Verdict verdict={round.verdict} />}

      {round.state === 'idle' && roster.state === 'ready' && (
        <p data-testid="va-idle" className="text-body-sm text-on-surface-variant">
          {roster.reasoning}
        </p>
      )}
    </div>
  );
}

function Verdict({ verdict }: { verdict: ArenaVerdict }) {
  return (
    <section data-testid="va-verdict" className="flex flex-col gap-sm">
      <p className="font-mono text-body-sm text-on-surface">
        {verdict.model.model} ·{' '}
        {verdict.verdict === 'accepted' ? (
          <span className="text-secondary">accepted</span>
        ) : (
          <span className="text-error">rejected</span>
        )}
        {verdict.extraKeysIgnored.length > 0 && (
          <span className="text-on-surface-variant">
            {' '}
            · ignored extras: {verdict.extraKeysIgnored.join(', ')}
          </span>
        )}
      </p>

      <div className="overflow-x-auto rounded-md border border-outline">
        <table data-testid="va-table" className="w-full text-left font-mono text-caption">
          <thead className="bg-surface-tint text-on-surface-variant">
            <tr>
              <th scope="col" className="px-sm py-xxs">field</th>
              <th scope="col" className="px-sm py-xxs">received</th>
              <th scope="col" className="px-sm py-xxs">outcome</th>
            </tr>
          </thead>
          <tbody>
            {verdict.rows.map((row) => (
              <tr key={row.field} data-testid={`va-row-${row.field}`} className="border-t border-outline">
                <td className="px-sm py-xxs text-on-surface">
                  {row.field}
                  <span className="text-on-surface-variant">{row.required ? '' : ' (optional)'}</span>
                </td>
                <td className="px-sm py-xxs text-on-surface-variant">
                  {row.received === undefined ? (
                    '— absent'
                  ) : (
                    <>
                      <span className="text-on-surface">{row.received.type}</span>{' '}
                      {row.received.repr}
                    </>
                  )}
                </td>
                <td className="px-sm py-xxs">
                  <OutcomeCell outcome={row.outcome} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {verdict.verdict === 'rejected' && verdict.errors !== undefined && (
        <div data-testid="va-errors" className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs">
          <p className="text-caption text-error">
            the 422 envelope's details — exactly what the wire would carry:
          </p>
          <ul className="flex flex-col gap-xxs">
            {verdict.errors.map((error, index) => (
              <li key={index} className="font-mono text-caption text-on-surface-variant">
                <span className="text-error">{error.type}</span> [{error.loc.join(' → ')}] ·{' '}
                {error.msg}
              </li>
            ))}
          </ul>
        </div>
      )}

      {verdict.validated !== undefined && (
        <div data-testid="va-validated" className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs">
          <p className="text-caption text-on-surface">
            <span className="text-secondary">accepted</span> — the exact instance the endpoint
            would hand its handler:
          </p>
          <pre className="overflow-x-auto font-mono text-caption text-on-surface-variant">
            {JSON.stringify(verdict.validated, null, 2)}
          </pre>
        </div>
      )}

      <p className="text-body-sm text-on-surface-variant">{verdict.reasoning}</p>
    </section>
  );
}

function OutcomeCell({ outcome }: { outcome: ArenaOutcome }) {
  const badgeClass =
    outcome.status === 'rejected'
      ? 'rounded-pill border border-outline px-sm py-xxs text-error'
      : outcome.status === 'coerced'
        ? 'rounded-pill border border-outline px-sm py-xxs text-secondary'
        : 'rounded-pill border border-outline px-sm py-xxs text-on-surface-variant';
  switch (outcome.status) {
    case 'accepted':
      return (
        <span className="flex flex-wrap items-center gap-xxs">
          <span className={badgeClass}>accepted</span>
          <span className="text-on-surface-variant">
            <span className="text-on-surface">{formatValue(outcome.value)}</span> ({outcome.valueType})
          </span>
        </span>
      );
    case 'coerced':
      return (
        <span className="flex flex-wrap items-center gap-xxs">
          <span className={badgeClass}>coerced</span>
          <span className="text-on-surface-variant">
            {formatValue(outcome.original)} ({outcome.originalType}) →{' '}
            <span className="text-on-surface">{formatValue(outcome.value)}</span> ({outcome.valueType})
          </span>
        </span>
      );
    case 'rejected':
      return (
        <span className="flex flex-wrap items-center gap-xxs">
          <span className={badgeClass}>rejected</span>
          <span className="text-on-surface-variant">
            <span className="text-error">{outcome.type}</span> [{outcome.loc.join(' → ')}] ·{' '}
            {outcome.msg}
          </span>
        </span>
      );
    case 'absent':
      return (
        <span className="flex flex-wrap items-center gap-xxs">
          <span className={badgeClass}>absent</span>
          <span className="text-on-surface-variant">
            default: {outcome.default === undefined ? '(null)' : formatValue(outcome.default)}
          </span>
        </span>
      );
  }
}

function formatValue(value: unknown): string {
  const text = JSON.stringify(value);
  return text === undefined ? String(value) : text;
}

export default ValidationArenaDemo;
