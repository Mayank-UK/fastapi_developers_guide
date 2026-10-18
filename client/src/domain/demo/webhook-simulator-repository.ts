import type { Result } from '../../core/result';
import type {
  SignedDelivery,
  WebhookReceipt,
  WebhookSimulation,
  WebhookSimulatorRequest,
  WebhookSimulatorRoster,
} from './webhook-simulator';

/**
 * WebhookSimulatorRepository — the domain-facing port for the webhooks
 * topic's simulator demo. Demo components depend on this interface only;
 * the HTTP adapter lives in data/demo and is wired at the composition
 * root. Four methods, three endpoints: the roster and the simulation are
 * the simulator itself, while the two deliver methods fire the SAME
 * signed round at the LIVE receive endpoint — once honestly (expect a
 * 202 receipt) and once with one body byte flipped (expect the family's
 * 401 unauthorized envelope, which arrives as a Failed Result carrying
 * the envelope's code and status).
 */
export interface WebhookSimulatorRepository {
  /** Fetch the roster: scenarios, event catalog, secret, schedule. */
  roster(): Promise<Result<WebhookSimulatorRoster>>;

  /** Register a subscription + fire an event; walk the simulated lifecycle. */
  simulate(request: WebhookSimulatorRequest): Promise<Result<WebhookSimulation>>;

  /** Fire a signed round at the live receive endpoint (expect 202). */
  deliver(signed: SignedDelivery): Promise<Result<WebhookReceipt>>;

  /** Fire the same round with one tampered body byte (expect the 401 envelope). */
  deliverTampered(signed: SignedDelivery): Promise<Result<WebhookReceipt>>;
}
