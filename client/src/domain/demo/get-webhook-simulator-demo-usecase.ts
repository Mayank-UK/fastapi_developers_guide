import type { Result } from '../../core/result';
import type {
  SignedDelivery,
  WebhookReceipt,
  WebhookSimulation,
  WebhookSimulatorRequest,
  WebhookSimulatorRoster,
} from './webhook-simulator';
import type { WebhookSimulatorRepository } from './webhook-simulator-repository';

/**
 * GetWebhookSimulatorDemoUseCase — fetches the webhooks topic's roster,
 * fires simulated deliveries, and fires REAL signed rounds at the live
 * receive endpoint (react-guide use-case style): a thin orchestration
 * seam over the repository port. The two deliver methods are the §5
 * lesson made clickable — the honest round earns a 202 receipt, the
 * tampered one earns the 401 envelope (a Failed Result carrying the
 * envelope's code and status, which the demo renders inline as the
 * protocol's honest answer rather than a broken screen).
 */
export class GetWebhookSimulatorDemoUseCase {
  private readonly repository: WebhookSimulatorRepository;

  constructor(repository: WebhookSimulatorRepository) {
    this.repository = repository;
  }

  roster(): Promise<Result<WebhookSimulatorRoster>> {
    return this.repository.roster();
  }

  simulate(request: WebhookSimulatorRequest): Promise<Result<WebhookSimulation>> {
    return this.repository.simulate(request);
  }

  deliver(signed: SignedDelivery): Promise<Result<WebhookReceipt>> {
    return this.repository.deliver(signed);
  }

  deliverTampered(signed: SignedDelivery): Promise<Result<WebhookReceipt>> {
    return this.repository.deliverTampered(signed);
  }
}
