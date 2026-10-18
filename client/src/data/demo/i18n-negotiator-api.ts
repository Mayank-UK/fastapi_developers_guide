import type { AppConfig } from '../../core/config/app-config';
import {
  guardedApiCall,
  guardedGetJson,
  guardedSendJson,
  parseDto,
} from '../../core/error-handling/guards';
import type { I18nPanel, NegotiatorRound } from '../../domain/demo/i18n-negotiator';
import { i18nPanelFromJson, negotiatorRoundFromJson } from './i18n-negotiator-dto';

/**
 * I18nNegotiatorApi — the transport for the negotiator's endpoints. Both
 * rounds ride the shared guarded JSON pipeline; the negotiate round is a
 * GET with one extra request header (the Accept-Language value being
 * tested), which `guardedSendJson` carries natively. Sending null OMITS
 * the header, so the browser's own default (or none, in a stubbed
 * transport) answers — the absent-header case is a normal round, not an
 * error, mirroring the server's lenient stance on the preference header.
 */

const PANEL_PATH = '/demo/i18n';
const NEGOTIATE_PATH = '/demo/i18n/negotiate';

export class I18nNegotiatorApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/i18n — the panel (policy, catalog, tour). */
  async panel(): Promise<I18nPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PANEL_PATH);
      return parseDto(body, status, i18nPanelFromJson);
    });
  }

  /**
   * GET {apiBaseUrl}/demo/i18n/negotiate with the tested Accept-Language:
   * the ranked parse, the negotiated locale, and every layer it changes.
   */
  async negotiate(acceptLanguage: string | null): Promise<NegotiatorRound> {
    return guardedApiCall(async () => {
      const request =
        acceptLanguage === null
          ? { method: 'GET' as const }
          : {
              method: 'GET' as const,
              headers: { 'accept-language': acceptLanguage },
            };
      const { body, status } = await guardedSendJson(this.config, NEGOTIATE_PATH, request);
      return parseDto(body, status, negotiatorRoundFromJson);
    });
  }
}
