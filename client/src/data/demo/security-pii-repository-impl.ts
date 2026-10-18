import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { Result } from '../../core/result';
import type { PiiCredential } from '../../domain/demo/security-pii';
import type { SecurityPiiRepository } from '../../domain/demo/security-pii-repository';
import type {
  EraseProof,
  ExportedSubject,
  MaskedSubject,
  PiiPanel,
  ResetOutcome,
} from '../../domain/demo/security-pii';
import type { SecurityPiiApi } from './security-pii-api';

/**
 * SecurityPiiRepositoryImpl — adapts the PII lab API to the domain port.
 * Every thrown transport error (including the 401/403 envelopes the gated
 * rounds answer) is guarded into a Failed Result whose message carries the
 * reason — the lab's teaching payload, same as the authz guards.
 */
export class SecurityPiiRepositoryImpl implements SecurityPiiRepository {
  private readonly api: SecurityPiiApi;

  constructor(api: SecurityPiiApi) {
    this.api = api;
  }

  panel(): Promise<Result<PiiPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  subject(
    customerId: string,
    credential: PiiCredential,
  ): Promise<Result<MaskedSubject>> {
    return safeRepositoryCall(() => this.api.subject(customerId, credential));
  }

  exportSubject(
    customerId: string,
    credential: PiiCredential,
  ): Promise<Result<ExportedSubject>> {
    return safeRepositoryCall(() => this.api.exportSubject(customerId, credential));
  }

  eraseSubject(
    customerId: string,
    credential: PiiCredential,
  ): Promise<Result<EraseProof>> {
    return safeRepositoryCall(() => this.api.eraseSubject(customerId, credential));
  }

  reset(): Promise<Result<ResetOutcome>> {
    return safeRepositoryCall(() => this.api.reset());
  }
}
