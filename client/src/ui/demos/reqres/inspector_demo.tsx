import { useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  InspectorProbe,
  QueryParamView,
  RequestInspectorData,
  SeenHeader,
} from '../../../domain/demo/reqres-inspector';

/**
 * RequestInspectorDemo — the request-response topic's live reflection
 * (demo block id `reqres:inspector`). Shape a request — a query string
 * (repeat a key: tag=a&tag=b), an optional custom x- header, and for POST
 * a small JSON body — send it, and read back the server's own view: the
 * request line, the query with every occurrence collected, the selected
 * headers, the body contract (content type + length + parsed message),
 * the client address, and the request id the middleware assigned on the
 * way in (the response's own x-request-id header carries the same value).
 *
 * Dependency flow mirrors the other demos: the use case resolves from the
 * container at render time (specs substitute fakes through the container
 * token), failures arrive as typed Failures inside Results, and the
 * shared ErrorPanel offers recovery.
 */

type ProbeStatus =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'ready'; data: RequestInspectorData }
  | { state: 'error'; failure: Failure };

const inputClass =
  'w-full rounded-md border border-outline bg-surface-tint px-sm py-xxs ' +
  'font-mono text-caption text-on-surface placeholder:text-on-surface-variant ' +
  'focus:border-primary focus:outline-none';

export function RequestInspectorDemo() {
  const useCase = container.getReqresInspectorDemoUseCase;
  const [method, setMethod] = useState<'GET' | 'POST'>('GET');
  const [query, setQuery] = useState('tag=a&tag=b&zoom=2');
  const [headerName, setHeaderName] = useState('x-probe');
  const [headerValue, setHeaderValue] = useState('hello');
  const [bodyMessage, setBodyMessage] = useState('a body the server will parse');
  const [status, setStatus] = useState<ProbeStatus>({ state: 'idle' });
  const [lastProbe, setLastProbe] = useState<InspectorProbe | null>(null);

  const trimmedHeaderName = headerName.trim().toLowerCase();
  const trimmedHeaderValue = headerValue.trim();
  const headerReady = trimmedHeaderName === '' || trimmedHeaderValue !== '';
  const sendDisabled = status.state === 'loading' || !headerReady;

  const fire = (probe: InspectorProbe) => {
    setLastProbe(probe);
    setStatus({ state: 'loading' });
    void useCase.execute(probe).then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'error', failure: result.failure },
      );
    });
  };

  const send = () => {
    const trimmedQuery = query.trim();
    fire({
      method,
      query: trimmedQuery,
      ...(trimmedHeaderName === ''
        ? {}
        : { headerName: trimmedHeaderName, headerValue: trimmedHeaderValue }),
      ...(method === 'POST' ? { bodyMessage: bodyMessage.trim() } : {}),
    });
  };

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="ri-form" className="flex flex-col gap-sm">
        <div className="flex flex-wrap items-center gap-xs">
          <span className="text-caption text-on-surface-variant">method</span>
          {(['GET', 'POST'] as const).map((candidate) => (
            <button
              key={candidate}
              type="button"
              data-testid={`ri-method-${candidate.toLowerCase()}`}
              aria-pressed={method === candidate}
              onClick={() => setMethod(candidate)}
              className={
                method === candidate
                  ? 'rounded-pill border border-primary bg-surface-tint px-sm py-xxs font-mono text-caption uppercase tracking-wide text-primary'
                  : 'rounded-pill border border-outline px-sm py-xxs font-mono text-caption uppercase tracking-wide text-on-surface-variant transition-colors hover:border-primary hover:text-primary'
              }
            >
              {candidate}
            </button>
          ))}
        </div>

        <label className="flex flex-col gap-xxs">
          <span className="text-caption text-on-surface-variant">
            query string (repeat a key — tag=a&amp;tag=b — to watch values collect)
          </span>
          <input
            data-testid="ri-query"
            className={inputClass}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="tag=a&tag=b"
          />
        </label>

        <div className="flex flex-wrap gap-sm">
          <label className="flex flex-1 flex-col gap-xxs">
            <span className="text-caption text-on-surface-variant">header name</span>
            <input
              data-testid="ri-header-name"
              className={inputClass}
              value={headerName}
              onChange={(event) => setHeaderName(event.target.value)}
              placeholder="x-probe (leave empty to send none)"
            />
          </label>
          <label className="flex flex-1 flex-col gap-xxs">
            <span className="text-caption text-on-surface-variant">header value</span>
            <input
              data-testid="ri-header-value"
              className={inputClass}
              value={headerValue}
              onChange={(event) => setHeaderValue(event.target.value)}
              placeholder="hello"
            />
          </label>
        </div>

        {method === 'POST' && (
          <label className="flex flex-col gap-xxs">
            <span className="text-caption text-on-surface-variant">
              POST body message (content-type and content-length will appear)
            </span>
            <input
              data-testid="ri-body"
              className={inputClass}
              value={bodyMessage}
              onChange={(event) => setBodyMessage(event.target.value)}
              placeholder="a body the server will parse"
            />
          </label>
        )}

        <div className="flex items-center gap-sm">
          <button
            type="button"
            data-testid="ri-send"
            onClick={send}
            disabled={sendDisabled}
            className="self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption uppercase tracking-wide text-on-surface transition-colors hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
          {status.state === 'loading' && (
            <span data-testid="ri-loading" className="text-caption text-on-surface-variant">
              probing the server…
            </span>
          )}
        </div>
      </section>

      {status.state === 'error' && (
        <ErrorPanel
          subject="the request inspector"
          failure={status.failure}
          onRetry={lastProbe === null ? undefined : () => fire(lastProbe)}
        />
      )}

      {status.state === 'ready' && <Reflection data={status.data} />}

      {status.state === 'idle' && (
        <p data-testid="ri-idle" className="text-body-sm text-on-surface-variant">
          Shape a request and send it — the server reflects the Request
          object's own view of exactly that request. Try repeating a query
          key, or switching to POST.
        </p>
      )}
    </div>
  );
}

function Reflection({ data }: { data: RequestInspectorData }) {
  return (
    <section data-testid="ri-result" className="flex flex-col gap-sm">
      <p data-testid="ri-request-line" className="font-mono text-body-sm text-on-surface">
        <span className="text-secondary">{data.method}</span> {data.path}
        {data.rawQuery !== undefined && (
          <span className="text-on-surface-variant">?{data.rawQuery}</span>
        )}
      </p>

      {data.queryParams.length > 0 && (
        <div data-testid="ri-query-params" className="flex flex-col gap-xxs">
          <p className="text-caption text-on-surface-variant">query as the server parsed it:</p>
          {data.queryParams.map((param) => (
            <QueryRow key={param.name} param={param} />
          ))}
        </div>
      )}

      {data.headers.length > 0 && (
        <div data-testid="ri-headers" className="flex flex-col gap-xxs">
          <p className="text-caption text-on-surface-variant">selected headers received:</p>
          {data.headers.map((header) => (
            <HeaderRow key={header.name} header={header} />
          ))}
        </div>
      )}

      <p data-testid="ri-body-facts" className="font-mono text-caption text-on-surface">
        {data.contentType !== undefined && <span>content-type: {data.contentType}</span>}
        {data.contentType !== undefined && data.contentLength !== undefined && (
          <span className="text-on-surface-variant"> · </span>
        )}
        {data.contentLength !== undefined && <span>content-length: {data.contentLength}</span>}
        {data.bodyMessage !== undefined && (
          <span className="text-on-surface-variant"> · body message: “{data.bodyMessage}”</span>
        )}
      </p>

      {data.client !== undefined && (
        <p data-testid="ri-client" className="font-mono text-caption text-on-surface">
          client address:{' '}
          <span className="text-primary">
            {data.client.host}:{data.client.port}
          </span>
        </p>
      )}

      <p data-testid="ri-request-id" className="font-mono text-caption text-on-surface">
        {data.requestIdHeader}:{' '}
        <span className="text-primary">{data.requestId}</span>
        <span className="text-on-surface-variant"> — stamped on this response too</span>
      </p>

      <p data-testid="ri-reasoning" className="text-body-sm text-on-surface-variant">
        {data.reasoning}
      </p>
    </section>
  );
}

function QueryRow({ param }: { param: QueryParamView }) {
  return (
    <p className="font-mono text-caption text-on-surface">
      <span
        className={
          param.isRepeated
            ? 'rounded-pill border border-primary px-sm py-xxs text-primary'
            : 'rounded-pill border border-outline px-sm py-xxs text-on-surface-variant'
        }
      >
        {param.name}
      </span>{' '}
      = [{param.values.join(', ')}]
      {param.isRepeated && (
        <span className="ml-xs text-primary">repeated — {param.values.length} values</span>
      )}
    </p>
  );
}

function HeaderRow({ header }: { header: SeenHeader }) {
  return (
    <p className="font-mono text-caption text-on-surface">
      <span className="rounded-pill border border-outline px-sm py-xxs text-on-surface-variant">
        {header.name}
      </span>{' '}
      {header.value}
    </p>
  );
}

export default RequestInspectorDemo;
