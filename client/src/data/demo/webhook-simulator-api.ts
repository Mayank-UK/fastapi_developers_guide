import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type {
  SignedDelivery,
  WebhookReceipt,
  WebhookSimulation,
  WebhookSimulatorRequest,
  WebhookSimulatorRoster,
} from '../../domain/demo/webhook-simulator';
import {
  webhookReceiptFromJson,
  webhookSimulationFromJson,
  webhookSimulatorRosterFromJson,
} from './webhook-simulator-dto';

/**
 * WebhookSimulatorApi — the transport for the webhooks topic's console:
 * GET/POST /api/demo/api/webhook-simulator (roster + simulation) and the
 * REAL signed round at POST /api/demo/api/webhooks/receive. The deliver
 * method is deliberately raw: it sends the SignedDelivery's exact body
 * STRING with its own headers — the signature covers those bytes, so the
 * transport must not re-serialize or reformat anything (the same
 * discipline the terminal tour's --data-binary enforces). A 401 from the
 * tampered round is the EXPECTED envelope failure and becomes a typed
 * ServerFailure upstream — for this demo that failure is the lesson, not
 * a broken transport.
 */

const SIMULATOR_PATH = '/demo/api/webhook-simulator';

export class WebhookSimulatorApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** Fetch the roster: scenarios, event catalog, secret, schedule. */
  async roster(): Promise<WebhookSimulatorRoster> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, SIMULATOR_PATH);
      return parseDto(body, status, webhookSimulatorRosterFromJson);
    });
  }

  /** Register a subscription + fire an event; walk the simulated lifecycle. */
  async simulate(request: WebhookSimulatorRequest): Promise<WebhookSimulation> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, SIMULATOR_PATH, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          eventType: request.eventType,
          scenario: request.scenario,
          ...(request.note === undefined || request.note === ''
            ? {}
            : { note: request.note }),
        }),
      });
      return parseDto(body, status, webhookSimulationFromJson);
    });
  }

  /** Fire a signed round at the live receive endpoint (exact bytes, own headers). */
  async deliver(signed: SignedDelivery): Promise<WebhookReceipt> {
    return guardedApiCall(async () => {
      // The server hands an absolute in-app path ("/api/demo/api/webhooks/receive");
      // the shared pipeline prepends the configured base, so resolve the path
      // against that base first (a base of '' or a path outside it both pass
      // through untouched).
      const path = signed.url.startsWith(this.config.apiBaseUrl)
        ? signed.url.slice(this.config.apiBaseUrl.length)
        : signed.url;
      const { body, status } = await guardedSendJson(this.config, path, {
        method: 'POST',
        headers: { ...signed.headers },
        body: signed.body,
      });
      return parseDto(body, status, webhookReceiptFromJson);
    });
  }
}
