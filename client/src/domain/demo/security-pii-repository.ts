import type { Result } from '../../core/result';
import type { PiiCredential } from './security-pii';
import type {
  EraseProof,
  ExportedSubject,
  MaskedSubject,
  PiiPanel,
  ResetOutcome,
} from './security-pii';

/**
 * SecurityPiiRepository — the domain-facing port for the security topic's
 * PII lab. Demo components depend on this interface only; the HTTP adapter
 * lives in data/demo and is wired at the composition root.
 *
 * `subject` takes an OPTIONAL credential: null is the anonymous caller
 * (full mask); a token rides the Bearer header and the server resolves the
 * role. `exportSubject`/`eraseSubject` are admin-gated — their 401/403
 * envelopes surface as Failed Results carrying the reason, which is the
 * lab's teaching payload, exactly like the authz guards.
 */
export interface SecurityPiiRepository {
  /** The panel: subjects, classification, role→mask levels, endpoints. */
  panel(): Promise<Result<PiiPanel>>;
  /** One subject through the caller's eyes (null credential = anonymous). */
  subject(customerId: string, credential: PiiCredential): Promise<Result<MaskedSubject>>;
  /** Data portability: the RAW record — admin-gated on the server. */
  exportSubject(customerId: string, credential: PiiCredential): Promise<Result<ExportedSubject>>;
  /** Right-to-erasure: gone, with before/after counts as proof. */
  eraseSubject(customerId: string, credential: PiiCredential): Promise<Result<EraseProof>>;
  /** Reseed the demo records — the erasure round can run again. */
  reset(): Promise<Result<ResetOutcome>>;
}
