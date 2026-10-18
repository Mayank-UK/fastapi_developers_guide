import { useEffect, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type { GetRuntimeTypesDemoUseCase } from '../../../domain/demo/get-runtime-types-demo-usecase';
import type {
  RuntimeTypesDemoData,
  SymbolHints,
} from '../../../domain/demo/runtime-types';

/**
 * RuntimeTypesDemo — the python-language topic's live demo (demo block id
 * `py:runtime-types`). It renders the payload of
 * GET /api/demo/py/runtime-types, which the server computes from this
 * repo's real objects: raw annotations vs get_type_hints, get_origin /
 * get_args, the dataclass-vs-pydantic field face-off, the enforcement
 * proof (a wrong-typed call that runs anyway), and the pydantic boundary
 * check that rejects what the language let through.
 *
 * Dependency flow mirrors the views: the hook resolves the use case from
 * the container (its default parameter is the spec seam — tests substitute
 * fakes through the container token instead), failures arrive as typed
 * Failures inside Results, and `retry` re-runs the load.
 */

type RuntimeTypesDemoStatus =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'ready'; data: RuntimeTypesDemoData }
  | { state: 'error'; failure: Failure };

export function useRuntimeTypesDemo(
  useCase: GetRuntimeTypesDemoUseCase = container.getRuntimeTypesDemoUseCase,
): { status: RuntimeTypesDemoStatus; retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState<RuntimeTypesDemoStatus>({ state: 'idle' });

  useEffect(() => {
    let cancelled = false;
    setStatus({ state: 'loading' });

    void useCase.execute().then((result) => {
      if (cancelled) return;
      if (result.ok) {
        setStatus({ state: 'ready', data: result.value });
      } else {
        setStatus({ state: 'error', failure: result.failure });
      }
    });

    return () => {
      cancelled = true;
    };
  }, [useCase, attempt]);

  const retry = () => setAttempt((current) => current + 1);
  return { status, retry };
}

export function RuntimeTypesDemo() {
  const { status, retry } = useRuntimeTypesDemo();

  if (status.state === 'idle' || status.state === 'loading') {
    return (
      <p data-testid="runtime-types-loading" className="text-body-sm text-on-surface-variant">
        computing runtime types…
      </p>
    );
  }

  if (status.state === 'error') {
    return <ErrorPanel subject="the runtime-types demo" failure={status.failure} onRetry={retry} />;
  }

  const { hintsVsRaw, originArgs, faceOff, enforcement, boundary } = status.data;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="rt-hints" className="flex flex-col gap-sm">
        <h4 className="font-display text-title-sm text-on-surface">Stored vs resolved</h4>
        {hintsVsRaw.map((symbol) => (
          <SymbolHintsTable key={symbol.symbol} symbol={symbol} />
        ))}
      </section>

      <section data-testid="rt-origins" className="flex flex-col gap-sm">
        <h4 className="font-display text-title-sm text-on-surface">Origins and args</h4>
        <div className="overflow-x-auto rounded-md border border-outline">
          <table className="w-full text-left font-mono text-caption">
            <thead className="bg-surface-tint text-on-surface-variant">
              <tr>
                <th scope="col" className="px-sm py-xxs">annotation</th>
                <th scope="col" className="px-sm py-xxs">origin</th>
                <th scope="col" className="px-sm py-xxs">args</th>
              </tr>
            </thead>
            <tbody>
              {originArgs.map((row) => (
                <tr key={row.symbol} className="border-t border-outline">
                  <td className="px-sm py-xxs text-on-surface">{row.alias}</td>
                  <td className="px-sm py-xxs text-secondary">{row.origin}</td>
                  <td className="px-sm py-xxs text-on-surface-variant">
                    {row.args.join(', ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section data-testid="rt-faceoff" className="flex flex-col gap-sm">
        <h4 className="font-display text-title-sm text-on-surface">
          dataclasses vs pydantic — same annotations, two readers
        </h4>
        <div className="grid gap-sm md:grid-cols-2">
          <FieldTable
            testId="rt-faceoff-dataclass"
            heading={faceOff.dataclassSymbol}
            fields={faceOff.dataclassFields}
          />
          <FieldTable
            testId="rt-faceoff-pydantic"
            heading={faceOff.pydanticSymbol}
            fields={faceOff.pydanticFields}
          />
        </div>
      </section>

      <section
        data-testid="rt-enforcement"
        className="flex flex-col gap-xs rounded-md border border-outline bg-surface-tint px-md py-sm"
      >
        <h4 className="font-display text-title-sm text-on-surface">It runs anyway</h4>
        <p className="font-mono text-body-sm text-on-surface">
          {enforcement.signature}
        </p>
        <p className="font-mono text-body-sm">
          <span className="text-on-surface">{enforcement.call}</span>
          <span className="text-on-surface-variant"> → </span>
          <span data-testid="rt-returned-value" className="text-error">
            {enforcement.returnedValue}
          </span>
        </p>
        <p className="text-body-sm text-on-surface-variant">
          declared return <code className="font-mono">{enforcement.declaredReturn}</code>,
          actual return <code className="font-mono text-error">{enforcement.actualReturn}</code> —
          the interpreter never read the annotation.
        </p>
        <p className="font-mono text-caption text-on-surface-variant">
          {enforcement.mypyVerdict}
        </p>
      </section>

      <section
        data-testid="rt-boundary"
        className="flex flex-col gap-xs rounded-md border border-outline bg-surface-tint px-md py-sm"
      >
        <h4 className="font-display text-title-sm text-on-surface">
          The boundary enforces — when asked
        </h4>
        <p className="text-body-sm text-on-surface">
          {boundary.model} with {boundary.badInput} →{' '}
          <span className="font-mono text-error">{boundary.outcome}</span>
        </p>
        <p className="font-mono text-caption text-on-surface-variant">
          {boundary.errorType} · {boundary.message}
        </p>
      </section>
    </div>
  );
}

function SymbolHintsTable({ symbol }: { symbol: SymbolHints }) {
  return (
    <div className="flex flex-col gap-xxs">
      <p className="font-mono text-caption text-on-surface-variant">
        <span className="text-on-surface">{symbol.symbol}</span>
        {' · '}
        {symbol.mode === 'deferred' ? 'annotations deferred (strings)' : 'annotations eager (objects)'}
      </p>
      <div className="overflow-x-auto rounded-md border border-outline">
        <table className="w-full text-left font-mono text-caption">
          <thead className="bg-surface-tint text-on-surface-variant">
            <tr>
              <th scope="col" className="px-sm py-xxs">name</th>
              <th scope="col" className="px-sm py-xxs">raw</th>
              <th scope="col" className="px-sm py-xxs">get_type_hints</th>
            </tr>
          </thead>
          <tbody>
            {symbol.rows.map((row) => (
              <tr key={row.name} className="border-t border-outline">
                <td className="px-sm py-xxs text-on-surface">{row.name}</td>
                <td className="px-sm py-xxs text-on-surface-variant">{row.raw}</td>
                <td className="px-sm py-xxs text-secondary">{row.resolved}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FieldTable({
  testId,
  heading,
  fields,
}: {
  testId: string;
  heading: string;
  fields: readonly { name: string; annotation: string; required: boolean }[];
}) {
  return (
    <div data-testid={testId} className="flex flex-col gap-xxs">
      <p className="font-mono text-caption text-on-surface">{heading}</p>
      <div className="overflow-x-auto rounded-md border border-outline">
        <table className="w-full text-left font-mono text-caption">
          <thead className="bg-surface-tint text-on-surface-variant">
            <tr>
              <th scope="col" className="px-sm py-xxs">field</th>
              <th scope="col" className="px-sm py-xxs">type</th>
              <th scope="col" className="px-sm py-xxs">required</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((field) => (
              <tr key={field.name} className="border-t border-outline">
                <td className="px-sm py-xxs text-on-surface">{field.name}</td>
                <td className="px-sm py-xxs text-on-surface-variant">{field.annotation}</td>
                <td className="px-sm py-xxs">
                  {field.required ? (
                    <span className="text-secondary">required</span>
                  ) : (
                    <span className="text-on-surface-variant">has default</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default RuntimeTypesDemo;
