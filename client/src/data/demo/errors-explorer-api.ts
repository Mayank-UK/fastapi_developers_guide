import type { AppConfig } from '../../core/config/app-config';
import { NetworkException } from '../../core/error-handling/exceptions';
import {
  collectHeaders,
  guardedApiCall,
  guardedSendJson,
  parseDto,
} from '../../core/error-handling/guards';
import type {
  ErrorsPanel,
  InjectedRound,
  ObservedFailure,
  ProbeRound,
  ScenarioSnapshot,
} from '../../domain/demo/errors-explorer';
import {
  errorsPanelFromJson,
  probeOutcomeFromJson,
  scenarioSnapshotFromJson,
} from './errors-explorer-dto';

/**
 * ErrorsExplorerApi — the transport for the explorer's panel plus the real
 * trigger rounds. The panel and the scenario PATCHes ride the shared guarded
 * JSON pipeline (they are honest 2xx calls); every fire* method runs RAW
 * rounds shaped exactly as curl would see them, because the failure IS the
 * payload — a non-2xx envelope with its x-request-id header is the lesson,
 * and the shared JSON pipeline structurally cannot represent it (it throws
 * on the first non-2xx). The security lab's 429 handling is the precedent,
 * generalized to this lab's whole trigger table.
 */

const PANEL_PATH = '/demo/errors';
const PROBE_PATH = '/demo/errors/probe';
const SCENARIO_PATH = '/demo/scenario';
const MINT_PATH = '/demo/auth/jwt/mint';
const GUARDED_EDIT_PATH = '/demo/authz/posts/designing-urls-people-can-read';
const MISSING_POST_PATH = '/posts/no-such-post';
const BURN_PATH = '/demo/security/rate-limit/burn';

const BURN_ATTEMPTS = 8;
/** Enough POSTs to drain the 5-per-window budget even from mid-window. */

/** One raw HTTP round as the wire sees it; json() failures become null. */
interface RawRound {
  status: number;
  headers: Record<string, string>;
  body: unknown;
}

/** The envelope object parsed out of a raw round, when the body carries one. */
interface ParsedEnvelope {
  code: string | null;
  message: string | null;
  requestId: string | null;
  details: unknown;
}

async function rawRound(
  config: AppConfig,
  method: 'GET' | 'POST' | 'PUT' | 'PATCH',
  path: string,
  body?: string,
  headers?: Record<string, string>,
): Promise<RawRound> {
  let response: Response;
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, {
      method,
      headers: { accept: 'application/json', ...headers },
      ...(body === undefined ? {} : { body }),
    });
  } catch (error) {
    throw new NetworkException('Could not reach the server.', { cause: error });
  }
  let parsed: unknown = null;
  try {
    parsed = await response.json();
  } catch {
    parsed = null;
  }
  return { status: response.status, headers: collectHeaders(response), body: parsed };
}

function parseEnvelope(body: unknown): ParsedEnvelope {
  if (isRecord(body) && isRecord(body.error)) {
    const envelope = body.error;
    return {
      code: typeof envelope.code === 'string' ? envelope.code : null,
      message: typeof envelope.message === 'string' ? envelope.message : null,
      requestId: typeof envelope.requestId === 'string' ? envelope.requestId : null,
      details: envelope.details,
    };
  }
  return { code: null, message: null, requestId: null, details: null };
}

function firstDetailLine(details: unknown): string | null {
  if (!Array.isArray(details) || details.length === 0) return null;
  const first = details[0];
  if (!isRecord(first)) return null;
  const loc = Array.isArray(first.loc)
    ? first.loc.map((part) => String(part)).join('.')
    : null;
  const msg = typeof first.msg === 'string' ? first.msg : null;
  if (loc === null || msg === null) return null;
  return `${loc}: ${msg}`;
}

function retryAfterSeconds(headers: Record<string, string>): number | null {
  const raw = headers['retry-after'];
  if (raw === undefined) return null;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function observe(kind: string, round: RawRound, attempts: number[] | null = null): ObservedFailure {
  const envelope = parseEnvelope(round.body);
  const requestIdHeader = round.headers['x-request-id'] ?? null;
  return {
    kind,
    httpStatus: round.status,
    code: envelope.code,
    message: envelope.message,
    requestId: envelope.requestId,
    requestIdHeader,
    headerMatchesBody:
      requestIdHeader !== null &&
      envelope.requestId !== null &&
      requestIdHeader === envelope.requestId,
    retryAfterSeconds: retryAfterSeconds(round.headers),
    detailLine: firstDetailLine(envelope.details),
    attempts,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export class ErrorsExplorerApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/errors — the panel (an honest 2xx call). */
  async panel(): Promise<ErrorsPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PANEL_PATH, { method: 'GET' });
      return parseDto(body, status, errorsPanelFromJson);
    });
  }

  /** PATCH the scenario with a body its enums refuse → the 422 envelope. */
  async fireValidationFailure(): Promise<ObservedFailure> {
    return guardedApiCall(async () =>
      observe(
        'validation_failed',
        await rawRound(
          this.config,
          'PATCH',
          SCENARIO_PATH,
          JSON.stringify({ injectFailure: 'bogus' }),
          { 'content-type': 'application/json' },
        ),
      ),
    );
  }

  /** PUT the guarded edit with no credential → the 401 envelope. */
  async fireUnauthorizedFailure(): Promise<ObservedFailure> {
    return guardedApiCall(async () =>
      observe('unauthorized', await rawRound(this.config, 'PUT', GUARDED_EDIT_PATH)),
    );
  }

  /** Mint alan's token, then PUT the guarded edit with it → the 403. */
  async fireForbiddenFailure(): Promise<ObservedFailure> {
    return guardedApiCall(async () => {
      const mint = await rawRound(
        this.config,
        'POST',
        MINT_PATH,
        JSON.stringify({ username: 'alan', scopes: ['*'] }),
        { 'content-type': 'application/json' },
      );
      if (mint.status !== 200) {
        // The observation is still honest: show the round that failed.
        return observe('forbidden', mint);
      }
      const token = isRecord(mint.body) && typeof mint.body.token === 'string'
        ? mint.body.token
        : null;
      if (token === null) {
        throw new Error('the mint answered 200 with no token');
      }
      return observe(
        'forbidden',
        await rawRound(this.config, 'PUT', GUARDED_EDIT_PATH, undefined, {
          authorization: `Bearer ${token}`,
        }),
      );
    });
  }

  /** GET a well-formed id that names nothing → the 404 envelope. */
  async fireNotFoundFailure(): Promise<ObservedFailure> {
    return guardedApiCall(async () =>
      observe('not_found', await rawRound(this.config, 'GET', MISSING_POST_PATH)),
    );
  }

  /** Drain the burner's budget until the 429 with Retry-After answers. */
  async fireRateLimitedFailure(): Promise<ObservedFailure> {
    return guardedApiCall(async () => {
      const attempts: number[] = [];
      let last: RawRound | null = null;
      for (let i = 0; i < BURN_ATTEMPTS; i += 1) {
        last = await rawRound(this.config, 'POST', BURN_PATH);
        attempts.push(last.status);
        if (last.status !== 200) break;
      }
      return observe('rate_limited', last as RawRound, attempts);
    });
  }

  /** Inject error → probe (the 500) → reset → probe (the healthy 200). */
  async fireInternalFailure(): Promise<InjectedRound> {
    return guardedApiCall(async () => {
      const injected = await rawRound(
        this.config,
        'PATCH',
        SCENARIO_PATH,
        JSON.stringify({ injectFailure: 'error' }),
        { 'content-type': 'application/json' },
      );
      if (injected.status !== 200) {
        throw new Error(`the scenario PATCH failed: ${String(injected.status)}`);
      }
      const failure = observe('internal', await rawRound(this.config, 'GET', PROBE_PATH));
      await rawRound(
        this.config,
        'PATCH',
        SCENARIO_PATH,
        JSON.stringify({ injectFailure: 'none' }),
        { 'content-type': 'application/json' },
      );
      const recovered = await rawRound(this.config, 'GET', PROBE_PATH);
      if (recovered.status !== 200) {
        throw new Error(`the probe did not recover: ${String(recovered.status)}`);
      }
      return { failure, recovered: probeOutcomeFromJson(recovered.body) };
    });
  }

  /** GET /api/demo/scenario — the store's current snapshot. */
  async readScenario(): Promise<ScenarioSnapshot> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, SCENARIO_PATH, { method: 'GET' });
      return parseDto(body, status, scenarioSnapshotFromJson);
    });
  }

  /** PATCH /api/demo/scenario — set the failure injection mode. */
  async setInjectFailure(mode: ScenarioSnapshot['injectFailure']): Promise<ScenarioSnapshot> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, SCENARIO_PATH, {
        method: 'PATCH',
        body: JSON.stringify({ injectFailure: mode }),
      });
      return parseDto(body, status, scenarioSnapshotFromJson);
    });
  }

  /** One probe round: the healthy row, or the observed injected failure. */
  async probe(): Promise<ProbeRound> {
    return guardedApiCall(async () => {
      const round = await rawRound(this.config, 'GET', PROBE_PATH);
      if (round.status === 200) {
        return { outcome: probeOutcomeFromJson(round.body), failure: null };
      }
      return { outcome: null, failure: observe('internal', round) };
    });
  }
}
