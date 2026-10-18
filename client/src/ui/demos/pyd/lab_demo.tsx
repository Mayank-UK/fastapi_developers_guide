import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  PydLabFieldOutcome,
  PydLabReportData,
  PydLabSchemaData,
} from '../../../domain/demo/pyd-lab';

/**
 * PydLabDemo — the pydantic topic's validation laboratory (demo block id
 * `pyd:lab`). An editable JSON payload, three one-click experiments, and a
 * fire button: the server answers with a per-field report (what the wire
 * carried, what lax coercion made of it — clean / coerced / rejected with
 * pydantic's own error types) plus the whole-specimen verdict, and the lab
 * model's generated JSON Schema rides alongside.
 *
 * Dependency flow mirrors the other demos: the use case resolves from the
 * container at render time (specs substitute fakes through the container
 * token — the documented replace-a-singleton seam); failures arrive as
 * typed Failures inside Results — including the 422 the server answers a
 * refused body with, rendered through the shared ErrorPanel exactly like
 * every other failure, because it IS the lesson.
 */

type ReportStatus =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'ready'; data: PydLabReportData }
  | { state: 'error'; failure: Failure };

type SchemaStatus =
  | { state: 'loading' }
  | { state: 'ready'; data: PydLabSchemaData }
  | { state: 'unavailable' };

interface Preset {
  key: 'coercion' | 'bounds' | 'shape';
  label: string;
  text: string;
}

/** A non-empty tuple: the first preset is always the editor's default. */
const PRESETS: readonly [Preset, ...Preset[]] = [
  {
    key: 'coercion',
    label: 'coercion-rich',
    text: JSON.stringify(
      {
        count: '42',
        flag: 'true',
        tags: ['boundary', 'types'],
        score: '100',
        handle: '  Grace Hopper ',
      },
      null,
      2,
    ),
  },
  {
    key: 'bounds',
    label: 'constraint violation',
    text: JSON.stringify(
      { count: 7, flag: true, tags: ['x'], score: 0, handle: 'ok' },
      null,
      2,
    ),
  },
  {
    key: 'shape',
    label: 'wrong shape → 422',
    text: JSON.stringify(
      { count: 7, flag: true, tags: 'oops', score: 5, handle: 'ok' },
      null,
      2,
    ),
  },
];

const inputClass =
  'w-full rounded-md border border-outline bg-surface-tint px-sm py-xxs ' +
  'font-mono text-caption text-on-surface placeholder:text-on-surface-variant ' +
  'focus:border-primary focus:outline-none';

export function PydLabDemo() {
  const useCase = container.getPydLabDemoUseCase;
  const [payloadText, setPayloadText] = useState(PRESETS[0].text);
  const [parseError, setParseError] = useState<string | null>(null);
  const [status, setStatus] = useState<ReportStatus>({ state: 'idle' });
  const [schema, setSchema] = useState<SchemaStatus>({ state: 'loading' });
  const [lastPayload, setLastPayload] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    void useCase.schema().then((result) => {
      if (cancelled) return;
      setSchema(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'unavailable' },
      );
    });
    return () => {
      cancelled = true;
    };
  }, [useCase]);

  const fire = (payload: unknown) => {
    setLastPayload(payload);
    setStatus({ state: 'loading' });
    void useCase.validate(payload).then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'error', failure: result.failure },
      );
    });
  };

  const send = () => {
    let payload: unknown;
    try {
      payload = JSON.parse(payloadText);
    } catch (error) {
      setParseError(
        error instanceof Error ? error.message : 'This is not valid JSON.',
      );
      return;
    }
    setParseError(null);
    fire(payload);
  };

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="pyd-form" className="flex flex-col gap-sm">
        <div className="flex flex-wrap items-center gap-xs">
          <span className="text-caption text-on-surface-variant">experiments</span>
          {PRESETS.map((preset) => (
            <button
              key={preset.key}
              type="button"
              data-testid={`pyd-preset-${preset.key}`}
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
            request body (JSON) — POST /api/demo/pyd/lab/validate
          </span>
          <textarea
            data-testid="pyd-payload"
            className={`${inputClass} min-h-[10rem]`}
            value={payloadText}
            onChange={(event) => setPayloadText(event.target.value)}
            spellCheck={false}
          />
        </label>
        {parseError !== null && (
          <p data-testid="pyd-parse-warning" className="text-caption text-error">
            Cannot send — the editor is not valid JSON: {parseError}
          </p>
        )}

        <div className="flex items-center gap-sm">
          <button
            type="button"
            data-testid="pyd-fire"
            onClick={send}
            disabled={status.state === 'loading'}
            className="self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption uppercase tracking-wide text-on-surface transition-colors hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            Validate
          </button>
          {status.state === 'loading' && (
            <span data-testid="pyd-loading" className="text-caption text-on-surface-variant">
              validating…
            </span>
          )}
        </div>
      </section>

      {schema.state === 'ready' && <SchemaViewer data={schema.data} />}
      {schema.state === 'unavailable' && (
        <p data-testid="pyd-schema-unavailable" className="text-caption text-on-surface-variant">
          The model's JSON Schema could not be fetched — the lab still works.
        </p>
      )}

      {status.state === 'error' && (
        <ErrorPanel
          subject="the validation lab"
          failure={status.failure}
          onRetry={() => fire(lastPayload)}
        />
      )}

      {status.state === 'ready' && <Report data={status.data} />}

      {status.state === 'idle' && (
        <p data-testid="pyd-idle" className="text-body-sm text-on-surface-variant">
          Edit the payload (or pick an experiment) and validate — every field
          reports what the wire carried and what pydantic's pipeline made of it.
        </p>
      )}
    </div>
  );
}

function Report({ data }: { data: PydLabReportData }) {
  return (
    <section data-testid="pyd-report" className="flex flex-col gap-sm">
      <div className="overflow-x-auto rounded-md border border-outline">
        <table data-testid="pyd-table" className="w-full text-left font-mono text-caption">
          <thead className="bg-surface-tint text-on-surface-variant">
            <tr>
              <th scope="col" className="px-sm py-xxs">field</th>
              <th scope="col" className="px-sm py-xxs">received</th>
              <th scope="col" className="px-sm py-xxs">outcome</th>
              <th scope="col" className="px-sm py-xxs">rule</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row) => (
              <tr key={row.field} data-testid={`pyd-row-${row.field}`} className="border-t border-outline">
                <td className="px-sm py-xxs text-on-surface">{row.field}</td>
                <td className="px-sm py-xxs text-on-surface-variant">
                  <span className="text-on-surface">{row.received.type}</span>{' '}
                  {row.received.repr}
                </td>
                <td className="px-sm py-xxs">
                  <OutcomeCell outcome={row.outcome} />
                </td>
                <td className="px-sm py-xxs text-on-surface-variant">{row.rule}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <SpecimenVerdict data={data} />
    </section>
  );
}

function OutcomeCell({ outcome }: { outcome: PydLabFieldOutcome }) {
  const badgeClass =
    outcome.status === 'rejected'
      ? 'rounded-pill border border-outline px-sm py-xxs text-error'
      : outcome.status === 'coerced'
        ? 'rounded-pill border border-outline px-sm py-xxs text-secondary'
        : 'rounded-pill border border-outline px-sm py-xxs text-on-surface-variant';
  switch (outcome.status) {
    case 'clean':
      return (
        <span className="flex flex-wrap items-center gap-xxs">
          <span className={badgeClass}>clean</span>
          <span className="text-on-surface-variant">
            {formatValue(outcome.value)} ({outcome.valueType})
          </span>
        </span>
      );
    case 'coerced':
      return (
        <span className="flex flex-wrap items-center gap-xxs">
          <span className={badgeClass}>coerced</span>
          <span className="text-on-surface-variant">
            {outcome.fromType} → <span className="text-on-surface">{formatValue(outcome.value)}</span>{' '}
            ({outcome.valueType})
          </span>
        </span>
      );
    case 'rejected':
      return (
        <span className="flex flex-wrap items-center gap-xxs">
          <span className={badgeClass}>rejected</span>
          <span className="text-on-surface-variant">
            <span className="text-error">{outcome.errorType}</span> · {outcome.message}
          </span>
        </span>
      );
  }
}

function SpecimenVerdict({ data }: { data: PydLabReportData }) {
  if (data.specimenValid) {
    return (
      <div data-testid="pyd-specimen" className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs">
        <p className="text-caption text-on-surface">
          <span className="text-secondary">specimen validates</span> — the typed,
          normalized model your submission became:
        </p>
        <pre data-testid="pyd-specimen-dump" className="overflow-x-auto font-mono text-caption text-on-surface-variant">
          {JSON.stringify(data.specimen, null, 2)}
        </pre>
      </div>
    );
  }
  return (
    <div data-testid="pyd-specimen" className="flex flex-col gap-xxs rounded-md border border-outline px-sm py-xs">
      <p className="text-caption text-error">
        specimen rejected — the strict model refused this submission:
      </p>
      <ul data-testid="pyd-specimen-errors" className="flex flex-col gap-xxs">
        {(data.specimenErrors ?? []).map((error, index) => (
          <li key={index} className="font-mono text-caption text-on-surface-variant">
            <span className="text-error">{error.type}</span>
            {error.loc.length > 0 && <> [{error.loc.join(' → ')}]</>} · {error.msg}
          </li>
        ))}
      </ul>
    </div>
  );
}

function SchemaViewer({ data }: { data: PydLabSchemaData }) {
  return (
    <details data-testid="pyd-schema" className="rounded-md border border-outline px-sm py-xs">
      <summary className="cursor-pointer text-caption text-on-surface-variant">
        the model's JSON Schema — generated from <span className="text-on-surface">{data.model}</span>
      </summary>
      <pre className="mt-xs overflow-x-auto font-mono text-caption text-on-surface-variant">
        {JSON.stringify(data.jsonSchema, null, 2)}
      </pre>
    </details>
  );
}

function formatValue(value: unknown): string {
  const text = JSON.stringify(value);
  return text === undefined ? String(value) : text;
}

export default PydLabDemo;
