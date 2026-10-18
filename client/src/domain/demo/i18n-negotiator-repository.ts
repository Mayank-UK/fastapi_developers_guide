import type { Result } from '../../core/result';
import type { I18nPanel, NegotiatorRound } from './i18n-negotiator';

/**
 * I18nNegotiatorRepository — the domain-facing port for the i18n topic's
 * negotiator. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root.
 *
 * `negotiate` takes the Accept-Language value to SEND (null omits the
 * header — the browser default rides instead); the server-side parser is
 * deliberately lenient, so no value here can fail the round — the worst
 * case is a visible fallback to the default locale, which is itself part
 * of the lesson.
 */
export interface I18nNegotiatorRepository {
  /** The panel: policy, catalog table, endpoint tour, honesty notes. */
  panel(): Promise<Result<I18nPanel>>;
  /** One negotiation round: send an Accept-Language, get every answer. */
  negotiate(acceptLanguage: string | null): Promise<Result<NegotiatorRound>>;
}
