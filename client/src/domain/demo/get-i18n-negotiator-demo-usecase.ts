import type { Result } from '../../core/result';
import type { I18nNegotiatorRepository } from './i18n-negotiator-repository';
import type { I18nPanel, NegotiatorRound } from './i18n-negotiator';

/**
 * GetI18nNegotiatorDemoUseCase — the negotiator's use case: the panel and
 * the negotiation rounds over the real endpoint. Every method is a thin
 * delegation today (the demo's logic is the server's); the use case exists
 * for the same reason every other demo's does — the view depends on one
 * named capability, not on an HTTP client, and client-side shaping (the
 * preset header list) has an obvious home beside it.
 */
export class GetI18nNegotiatorDemoUseCase {
  private readonly repository: I18nNegotiatorRepository;

  constructor(repository: I18nNegotiatorRepository) {
    this.repository = repository;
  }

  /** The panel: policy, catalog table, endpoint tour, honesty notes. */
  panel(): Promise<Result<I18nPanel>> {
    return this.repository.panel();
  }

  /** One negotiation round — send an Accept-Language, get every answer. */
  negotiate(acceptLanguage: string | null): Promise<Result<NegotiatorRound>> {
    return this.repository.negotiate(acceptLanguage);
  }
}
