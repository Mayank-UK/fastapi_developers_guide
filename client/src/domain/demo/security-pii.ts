/**
 * Domain models for the security topic's PII lab (demo block id
 * `security:pii`) — the client-side shape of the /api/demo/security/pii*
 * endpoints. Field names match the server's camelCase wire contract 1:1.
 *
 * The panel carries the seeded subjects, the field-classification catalog
 * (with every tier and rationale), and the role→mask-level map. The
 * subject view renders one record AS THE CALLER SEES IT; export and erase
 * are admin-gated rounds whose 401/403 surface as Failures carrying the
 * reason. `null` credential = the anonymous caller at the fail-closed
 * full mask.
 */

/** The credential a gated call carries; null = anonymous (full mask). */
export type PiiCredential = { kind: 'bearer'; token: string } | null;

/** One seeded subject as the PUBLIC roster shows them: id + country. */
export interface SubjectRow {
  customerId: string;
  country: string;
}

/** One classified field: category, tier, partial rules, and the rationale. */
export interface ClassificationRow {
  field: string;
  category: string;
  tier: string;
  allowsPartial: boolean;
  rationale: string;
}

/** One mask level: what survives — nothing, the honest residue, or all. */
export type MaskLevel = 'none' | 'partial' | 'full';

/** One role (or the anonymous caller) and the mask level it earns. */
export interface RoleMaskRow {
  role: string;
  maskLevel: MaskLevel;
  note: string;
}

/** Wire shape of GET /api/demo/security/pii — the lab panel's contract. */
export interface PiiPanel {
  subjects: SubjectRow[];
  classification: ClassificationRow[];
  roleMasks: RoleMaskRow[];
  storeCount: number;
  subjectEndpoint: string;
  exportEndpoint: string;
  eraseEndpoint: string;
  resetEndpoint: string;
  minimizationNote: string;
  reasoning: string;
}

/** One field as a given viewer sees it: the value (masked or raw) + why. */
export interface PiiFieldView {
  field: string;
  category: string;
  tier: string;
  value: string;
  masked: boolean;
  applied: MaskLevel;
}

/** Wire shape of one subject AS ONE VIEWER SEES THEM. */
export interface MaskedSubject {
  customerId: string;
  principal: string;
  principalRole: string | null;
  maskLevel: MaskLevel;
  fields: PiiFieldView[];
  detail: string;
}

/** The raw record — the export a data-portability request earns. */
export interface CustomerRecord {
  customerId: string;
  fullName: string;
  email: string;
  phone: string;
  dateOfBirth: string;
  nationalId: string;
  cardNumber: string;
  country: string;
  signupAt: string;
}

/** Wire shape of the admin-gated export: raw record + classification map. */
export interface ExportedSubject {
  customerId: string;
  principal: string;
  record: CustomerRecord;
  classification: ClassificationRow[];
  detail: string;
}

/** Wire shape of the erasure proof: gone, and countable. */
export interface EraseProof {
  customerId: string;
  principal: string;
  recordsBefore: number;
  recordsAfter: number;
  detail: string;
}

/** Wire shape of the lab reset: the demo records, reseeded. */
export interface ResetOutcome {
  seeded: number;
  detail: string;
}
