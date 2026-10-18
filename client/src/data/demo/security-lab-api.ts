import type { AppConfig } from '../../core/config/app-config';
import { NetworkException } from '../../core/error-handling/exceptions';
import {
  errorEnvelopeException,
  guardedApiCall,
  guardedGetJson,
  parseDto,
  readHeader,
  responseEnvelopeException,
} from '../../core/error-handling/guards';
import type { BurnResult, ObservedHeaders, SecurityLabLoad } from '../../domain/demo/security-lab';
import { burnOutcomeFromJson, securityLabPanelFromJson } from './security-lab-dto';

/**
 * SecurityLabApi — the transport for the security lab's two endpoints.
 * The panel rides the shared guarded JSON pipeline and ALSO reports the
 * headers its own response carried (the lab shows them beside the
 * documented table — what the live middleware actually stamped). The
 * burner is ONE raw round, shaped exactly as a curl would see it, because
 * the 429 with its Retry-After header is the lab's lesson: a 429 has no
 * 2xx body, and the JSON pipeline structurally cannot represent it.
 */

const PANEL_PATH = '/demo/security';
const BURN_PATH = '/demo/security/rate-limit/burn';

/** Header names the lab surfaces from the observed live response. */
export const OBSERVED_HEADER_NAMES = [
  'x-content-type-options',
  'x-frame-options',
  'referrer-policy',
  'content-security-policy',
  'strict-transport-security',
  'x-request-id',
] as const;

export class SecurityLabApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/security — the panel + the observed headers. */
  async panel(): Promise<SecurityLabLoad> {
    return guardedApiCall(async () => {
      const { body, status, headers } = await guardedGetJson(this.config, PANEL_PATH);
      const panel = parseDto(body, status, securityLabPanelFromJson);
      const observedHeaders: Record<string, string> = {};
      for (const name of OBSERVED_HEADER_NAMES) {
        const value = headers[name];
        if (typeof value === 'string') observedHeaders[name] = value;
      }
      return { panel, observedHeaders: observedHeaders as ObservedHeaders };
    });
  }

  /**
   * POST {apiBaseUrl}/demo/security/rate-limit/burn — one raw round.
   * 200 answers the remaining budget; 429 is shaped as the typed throttle
   * (Retry-After header + envelope message); anything else is guarded
   * back into the shared failure taxonomy.
   */
  async burn(): Promise<BurnResult> {
    return guardedApiCall(async () => {
      let response: Response;
      try {
        response = await fetch(`${this.config.apiBaseUrl}${BURN_PATH}`, {
          method: 'POST',
          headers: { accept: 'application/json' },
        });
      } catch (error) {
        throw new NetworkException('Could not reach the server.', { cause: error });
      }
      if (response.status === 200) {
        const body = await response.json();
        return { kind: 'allowed', outcome: burnOutcomeFromJson(body) };
      }
      if (response.status === 429) {
        const retryAfter = readHeader(response.headers, 'retry-after');
        const parsed = retryAfter === undefined ? null : Number(retryAfter);
        const message = await envelopeMessage(response);
        return {
          kind: 'throttled',
          throttled: {
            status: 429 as const,
            retryAfterSeconds:
              parsed !== null && Number.isFinite(parsed) && parsed > 0 ? parsed : null,
            message,
          },
        };
      }
      throw await responseEnvelopeException(response);
    });
  }
}

/**
 * The envelope's message, when the body carries one; a fallback otherwise.
 * Shaped from the guards' shared classifier so the typed throttle row and
 * the failure taxonomy never drift apart.
 */
async function envelopeMessage(response: Response): Promise<string> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  return errorEnvelopeException(body, response.status).message;
}
