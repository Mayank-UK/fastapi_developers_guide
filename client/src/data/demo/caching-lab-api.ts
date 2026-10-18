import type { AppConfig } from '../../core/config/app-config';
import { NetworkException, ServerException } from '../../core/error-handling/exceptions';
import {
  guardedApiCall,
  guardedGetJson,
  guardedSendJson,
  parseDto,
  readHeader,
  responseEnvelopeException,
} from '../../core/error-handling/guards';
import type {
  CachingLabDemo,
  ConditionalRound,
  InvalidationOutcome,
  StampedeOutcome,
} from '../../domain/demo/caching-lab';
import {
  cachingLabFromJson,
  cacheOutcomeFromJson,
  invalidationFromJson,
  stampedeFromJson,
} from './caching-lab-dto';

/**
 * CachingLabApi — the transport for the caching lab's four endpoints.
 * Three ride the shared guarded JSON pipeline (roster, invalidate,
 * stampede). The fourth is the lab's whole point: ONE raw conditional
 * round against the REAL endpoint, shaped exactly as a curl would see
 * it — status, validators, cache telemetry headers, body byte length —
 * because a 304 has no body and the JSON pipeline structurally cannot
 * represent it. The raw round still guards network failures and error
 * envelopes the same way; only the happy 200/304 shapes differ.
 */

const LAB_PATH = '/demo/caching/lab';
const POSTS_PATH = '/demo/caching/posts';
const INVALIDATE_PATH = '/demo/caching/invalidate';
const STAMPEDE_PATH = '/demo/caching/stampede';

export class CachingLabApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/caching/lab — the state panel's roster. */
  async lab(): Promise<CachingLabDemo> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, LAB_PATH);
      return parseDto(body, status, cachingLabFromJson);
    });
  }

  /**
   * One conditional round against the real endpoint. `ifNoneMatch` is
   * the ETag to send back (omit for a fresh round). `cache: 'no-store'`
   * keeps the BROWSER's HTTP cache out of the experiment — the lab's
   * subject is the server's exchange, and the endpoint's own
   * Cache-Control stays visible in the reported headers.
   */
  async conditionalRound(ifNoneMatch?: string): Promise<ConditionalRound> {
    return guardedApiCall(async () => {
      let response: Response;
      try {
        response = await fetch(`${this.config.apiBaseUrl}${POSTS_PATH}`, {
          headers: {
            accept: 'application/json',
            ...(ifNoneMatch === undefined ? {} : { 'if-none-match': ifNoneMatch }),
          },
          cache: 'no-store',
        });
      } catch (error) {
        throw new NetworkException('Could not reach the server.', { cause: error });
      }
      return this.shapeConditionalRound(response);
    });
  }

  /** POST {apiBaseUrl}/demo/caching/invalidate — the invalidate button. */
  async invalidate(): Promise<InvalidationOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, INVALIDATE_PATH, {
        method: 'POST',
      });
      return parseDto(body, status, invalidationFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/caching/stampede — the stampede button. */
  async stampede(requests: number): Promise<StampedeOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, STAMPEDE_PATH, {
        method: 'POST',
        body: JSON.stringify({ requests }),
      });
      return parseDto(body, status, stampedeFromJson);
    });
  }

  /**
   * Shape one raw exchange into the round a curl would report. 200 and
   * 304 are the two answers the conditional endpoint gives; anything
   * else is an error envelope (e.g. the 503 when Redis is down) and is
   * parsed back into the shared failure taxonomy. Header reads go through
   * the guards' shared `readHeader` (a real Headers instance or the fetch
   * stub's plain record — both answer).
   */
  private async shapeConditionalRound(response: Response): Promise<ConditionalRound> {
    const etag = readHeader(response.headers, 'etag');
    if (response.status === 304) {
      return {
        status: 304,
        etag: required(etag, 'etag'),
        cacheControl: required(readHeader(response.headers, 'cache-control'), 'cache-control'),
        cache: cacheOutcomeFromJson(required(readHeader(response.headers, 'x-cache'), 'x-cache')),
        elapsedMs: numberHeader(response.headers, 'x-cache-elapsed-ms'),
        ageMs: optionalNumberHeader(response.headers, 'x-cache-age-ms'),
        originFetches: numberHeader(response.headers, 'x-cache-origin-fetches'),
        hits: numberHeader(response.headers, 'x-cache-hits'),
        bodyBytes: 0, // a 304 never carries a body
      };
    }
    if (response.status !== 200) {
      throw await responseEnvelopeException(response);
    }
    const text = await response.text();
    return {
      status: 200,
      etag: required(etag, 'etag'),
      cacheControl: required(readHeader(response.headers, 'cache-control'), 'cache-control'),
      cache: cacheOutcomeFromJson(required(readHeader(response.headers, 'x-cache'), 'x-cache')),
      elapsedMs: numberHeader(response.headers, 'x-cache-elapsed-ms'),
      ageMs: optionalNumberHeader(response.headers, 'x-cache-age-ms'),
      originFetches: numberHeader(response.headers, 'x-cache-origin-fetches'),
      hits: numberHeader(response.headers, 'x-cache-hits'),
      bodyBytes: new TextEncoder().encode(text).length,
    };
  }
}

function required(value: string | undefined, name: string): string {
  if (value === undefined) {
    throw new ServerException(`Response is missing ${name}.`, {
      code: 'invalid_response',
      status: 200,
    });
  }
  return value;
}

function numberHeader(
  headers: Response['headers'] | Record<string, string>,
  name: string,
): number {
  const raw = required(readHeader(headers, name), name);
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    throw headerNumberException(name, raw);
  }
  return parsed;
}

function optionalNumberHeader(
  headers: Response['headers'] | Record<string, string>,
  name: string,
): number | null {
  const raw = readHeader(headers, name);
  if (raw === undefined) return null;
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    throw headerNumberException(name, raw);
  }
  return parsed;
}

function headerNumberException(name: string, raw: string): ServerException {
  return new ServerException(`Header ${name} is not a number: ${raw}.`, {
    code: 'invalid_response',
    status: 200,
  });
}
