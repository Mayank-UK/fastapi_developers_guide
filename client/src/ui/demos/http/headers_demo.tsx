import { useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
import { ErrorPanel } from '../../components/error-panel';
import type {
  EchoedHeader,
  HttpHeadersDemoRequest,
  HttpHeadersEchoData,
} from '../../../domain/demo/http-headers';

/**
 * HttpHeadersDemo — the http-web topic's echo demo (demo block id
 * `http:headers`). A mini request inspector: choose a method (GET/POST),
 * optionally add a custom header, (on POST) a message body, fire the
 * request — and read exactly what the server received: the request line,
 * the raw query, the content type, the parsed body message, and every
 * selected header classified end-to-end vs hop-by-hop, with the RFC 9110
 * reference list alongside.
 *
 * Dependency flow mirrors the other demos: the use case resolves from the
 * container at render time (specs substitute fakes through the container
 * token — the documented replace-a-singleton seam), failures arrive as
 * typed Failures inside Results, and the shared ErrorPanel offers recovery.
 * The header name is validated before sending: an invalid name would make
 * fetch itself throw, which the pipeline would honestly — but misleadingly
 * — classify as a network failure.
 */

type Method = 'GET' | 'POST';

type EchoStatus =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'ready'; data: HttpHeadersEchoData }
  | { state: 'error'; failure: Failure };

const HEADER_NAME_PATTERN = /^[\w-]+$/;
/** A pragmatic token guard: letters, digits, underscore, hyphen. */

const inputClass =
  'w-full rounded-md border border-outline bg-surface-tint px-sm py-xxs ' +
  'font-mono text-caption text-on-surface placeholder:text-on-surface-variant ' +
  'focus:border-primary focus:outline-none';

export function HttpHeadersDemo() {
  const useCase = container.getHttpHeadersDemoUseCase;
  const [method, setMethod] = useState<Method>('GET');
  const [headerName, setHeaderName] = useState('x-demo-trace');
  const [headerValue, setHeaderValue] = useState('');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState<EchoStatus>({ state: 'idle' });
  const [lastRequest, setLastRequest] = useState<HttpHeadersDemoRequest | null>(null);

  const trimmedName = headerName.trim();
  const trimmedValue = headerValue.trim();
  const nameIsInvalid = trimmedName !== '' && !HEADER_NAME_PATTERN.test(trimmedName);
  const sendDisabled = status.state === 'loading' || nameIsInvalid;

  const fire = (request: HttpHeadersDemoRequest) => {
    setLastRequest(request);
    setStatus({ state: 'loading' });
    void useCase.execute(request).then((result) => {
      setStatus(
        result.ok
          ? { state: 'ready', data: result.value }
          : { state: 'error', failure: result.failure },
      );
    });
  };

  const send = () => {
    fire({
      method,
      ...(trimmedName !== '' && trimmedValue !== ''
        ? { headerName: trimmedName, headerValue: trimmedValue }
        : {}),
      ...(method === 'POST' && message.trim() !== '' ? { message: message.trim() } : {}),
    });
  };

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="hh-form" className="flex flex-col gap-sm">
        <div className="flex flex-wrap items-center gap-xs">
          <span className="text-caption text-on-surface-variant">method</span>
          {(['GET', 'POST'] as const).map((candidate) => (
            <button
              key={candidate}
              type="button"
              data-testid={`hh-method-${candidate.toLowerCase()}`}
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

        <div className="grid gap-xs sm:grid-cols-2">
          <label className="flex flex-col gap-xxs">
            <span className="text-caption text-on-surface-variant">custom header name</span>
            <input
              data-testid="hh-name"
              className={inputClass}
              value={headerName}
              onChange={(event) => setHeaderName(event.target.value)}
              placeholder="x-demo-trace"
            />
          </label>
          <label className="flex flex-col gap-xxs">
            <span className="text-caption text-on-surface-variant">header value</span>
            <input
              data-testid="hh-value"
              className={inputClass}
              value={headerValue}
              onChange={(event) => setHeaderValue(event.target.value)}
              placeholder="hello-http"
            />
          </label>
        </div>
        {nameIsInvalid && (
          <p data-testid="hh-name-warning" className="text-caption text-error">
            Header names may contain only letters, digits, underscore, and hyphen.
          </p>
        )}

        {method === 'POST' && (
          <label className="flex flex-col gap-xxs">
            <span className="text-caption text-on-surface-variant">
              body message (sent as JSON, parsed and echoed back)
            </span>
            <input
              data-testid="hh-message"
              className={inputClass}
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="hello from the browser"
            />
          </label>
        )}

        <div className="flex items-center gap-sm">
          <button
            type="button"
            data-testid="hh-send"
            onClick={send}
            disabled={sendDisabled}
            className="self-start rounded-pill border border-outline px-md py-xxs font-mono text-caption uppercase tracking-wide text-on-surface transition-colors hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send request
          </button>
          {status.state === 'loading' && (
            <span data-testid="http-headers-loading" className="text-caption text-on-surface-variant">
              sending…
            </span>
          )}
        </div>
      </section>

      {status.state === 'error' && (
        <ErrorPanel
          subject="the headers echo"
          failure={status.failure}
          onRetry={lastRequest === null ? undefined : () => fire(lastRequest)}
        />
      )}

      {status.state === 'ready' && <EchoResult data={status.data} />}

      {status.state === 'idle' && (
        <p data-testid="hh-idle" className="text-body-sm text-on-surface-variant">
          Pick a method, add a header value, and send — the server answers with
          exactly what it received.
        </p>
      )}
    </div>
  );
}

function EchoResult({ data }: { data: HttpHeadersEchoData }) {
  return (
    <section data-testid="hh-echo" className="flex flex-col gap-sm">
      <p data-testid="hh-request-line" className="font-mono text-body-sm text-on-surface">
        <span className="text-secondary">{data.method}</span> {data.path}
        {data.query !== undefined && (
          <span className="text-on-surface-variant">?{data.query}</span>
        )}
      </p>

      {(data.contentType !== undefined || data.bodyMessage !== undefined) && (
        <p data-testid="hh-body" className="font-mono text-caption text-on-surface-variant">
          {data.contentType !== undefined && <>content-type: {data.contentType}</>}
          {data.contentType !== undefined && data.bodyMessage !== undefined && <> · </>}
          {data.bodyMessage !== undefined && <>body message: “{data.bodyMessage}”</>}
        </p>
      )}

      <div className="overflow-x-auto rounded-md border border-outline">
        <table data-testid="hh-headers" className="w-full text-left font-mono text-caption">
          <thead className="bg-surface-tint text-on-surface-variant">
            <tr>
              <th scope="col" className="px-sm py-xxs">header</th>
              <th scope="col" className="px-sm py-xxs">value</th>
              <th scope="col" className="px-sm py-xxs">scope</th>
              <th scope="col" className="px-sm py-xxs">note</th>
            </tr>
          </thead>
          <tbody>
            {data.headers.map((header) => (
              <EchoRow key={header.name} header={header} />
            ))}
          </tbody>
        </table>
      </div>

      <div data-testid="hh-hop-by-hop" className="flex flex-col gap-xxs">
        <p className="text-caption text-on-surface-variant">
          hop-by-hop reference list (RFC 9110 §7.6.1 + keep-alive) —
          consumed by the transport, never forwarded:
        </p>
        <div className="flex flex-wrap gap-xxs">
          {data.hopByHop.map((name) => (
            <span
              key={name}
              className="rounded-pill border border-outline px-sm py-xxs font-mono text-caption text-on-surface-variant"
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function EchoRow({ header }: { header: EchoedHeader }) {
  return (
    <tr className="border-t border-outline">
      <td className="px-sm py-xxs text-on-surface">{header.name}</td>
      <td className="max-w-[24rem] truncate px-sm py-xxs text-on-surface-variant" title={header.value}>
        {header.value}
      </td>
      <td className="px-sm py-xxs">
        <span
          className={
            header.scope === 'hop-by-hop'
              ? 'rounded-pill border border-outline px-sm py-xxs text-secondary'
              : 'rounded-pill border border-outline px-sm py-xxs text-on-surface-variant'
          }
        >
          {header.scope}
        </span>
      </td>
      <td className="px-sm py-xxs text-on-surface-variant">{header.note ?? '—'}</td>
    </tr>
  );
}

export default HttpHeadersDemo;
