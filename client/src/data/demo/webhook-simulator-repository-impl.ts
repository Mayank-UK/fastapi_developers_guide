import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type {
  SignedDelivery,
  WebhookReceipt,
  WebhookSimulation,
  WebhookSimulatorRequest,
  WebhookSimulatorRoster,
} from '../../domain/demo/webhook-simulator';
import type { WebhookSimulatorRepository } from '../../domain/demo/webhook-simulator-repository';
import type { WebhookSimulatorApi } from './webhook-simulator-api';

/**
 * WebhookSimulatorRepositoryImpl — adapts the simulator API to the domain
 * port. Every thrown transport error is guarded by safeRepositoryCall into
 * a Failed Result, so the demo component never needs try/catch. The
 * tampered round is this adapter's one piece of theater: it flips the
 * FINAL body byte (a canonical JSON object ends with `}`), reusing the
 * same signed headers — one changed byte is enough for the receiver's
 * constant-time compare to refuse the delivery, which arrives as a
 * Failed Result carrying the 401 envelope's code and status.
 */

function tamperedBody(body: string): string {
  return body.endsWith('}') ? body.slice(0, -1) + '{' : body + 'x';
}

export class WebhookSimulatorRepositoryImpl implements WebhookSimulatorRepository {
  private readonly api: WebhookSimulatorApi;

  constructor(api: WebhookSimulatorApi) {
    this.api = api;
  }

  roster(): Promise<Result<WebhookSimulatorRoster>> {
    return safeRepositoryCall(() => this.api.roster());
  }

  simulate(request: WebhookSimulatorRequest): Promise<Result<WebhookSimulation>> {
    return safeRepositoryCall(() => this.api.simulate(request));
  }

  deliver(signed: SignedDelivery): Promise<Result<WebhookReceipt>> {
    return safeRepositoryCall(() => this.api.deliver(signed));
  }

  deliverTampered(signed: SignedDelivery): Promise<Result<WebhookReceipt>> {
    const tampered: SignedDelivery = { ...signed, body: tamperedBody(signed.body) };
    return safeRepositoryCall(() => this.api.deliver(tampered));
  }
}
