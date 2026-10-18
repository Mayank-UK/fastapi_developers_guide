import type { Result } from '../../core/result';
import type { SecurityPiiRepository } from './security-pii-repository';
import type {
  EraseProof,
  ExportedSubject,
  MaskedSubject,
  PiiCredential,
  PiiPanel,
  ResetOutcome,
} from './security-pii';

/**
 * GetSecurityPiiDemoUseCase — the PII lab's use case: the panel, one
 * subject viewed through a chosen caller's eyes (anonymous by default,
 * any of the seeded principals via a minted token), and the two
 * admin-gated rounds — export (data portability) and erase (erasure with
 * counts as proof) — whose 403 reasons surface as Failures.
 */
export class GetSecurityPiiDemoUseCase {
  private readonly repository: SecurityPiiRepository;

  constructor(repository: SecurityPiiRepository) {
    this.repository = repository;
  }

  /** The panel: subjects, classification, role→mask levels, endpoints. */
  panel(): Promise<Result<PiiPanel>> {
    return this.repository.panel();
  }

  /** One subject through the caller's eyes. */
  subject(
    customerId: string,
    credential: PiiCredential,
  ): Promise<Result<MaskedSubject>> {
    return this.repository.subject(customerId, credential);
  }

  /** The admin-gated export — the raw record plus its classification. */
  exportSubject(
    customerId: string,
    credential: PiiCredential,
  ): Promise<Result<ExportedSubject>> {
    return this.repository.exportSubject(customerId, credential);
  }

  /** The admin-gated erasure — counts as proof, the next read a 404. */
  eraseSubject(
    customerId: string,
    credential: PiiCredential,
  ): Promise<Result<EraseProof>> {
    return this.repository.eraseSubject(customerId, credential);
  }

  /** Reseed the demo records. */
  reset(): Promise<Result<ResetOutcome>> {
    return this.repository.reset();
  }
}
