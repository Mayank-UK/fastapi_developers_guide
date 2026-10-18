import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { I18nPanel, NegotiatorRound } from '../../domain/demo/i18n-negotiator';
import type { I18nNegotiatorRepository } from '../../domain/demo/i18n-negotiator-repository';
import type { I18nNegotiatorApi } from './i18n-negotiator-api';

/**
 * I18nNegotiatorRepositoryImpl — adapts the negotiator API to the domain
 * port. Expected failures resolve as Failed Results; the view never sees
 * a thrown transport error.
 */
export class I18nNegotiatorRepositoryImpl implements I18nNegotiatorRepository {
  private readonly api: I18nNegotiatorApi;

  constructor(api: I18nNegotiatorApi) {
    this.api = api;
  }

  panel(): Promise<Result<I18nPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  negotiate(acceptLanguage: string | null): Promise<Result<NegotiatorRound>> {
    return safeRepositoryCall(() => this.api.negotiate(acceptLanguage));
  }
}
