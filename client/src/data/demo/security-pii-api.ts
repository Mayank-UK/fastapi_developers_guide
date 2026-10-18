import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';

import type { PiiCredential } from '../../domain/demo/security-pii';
import type {
  EraseProof,
  ExportedSubject,
  MaskedSubject,
  PiiPanel,
  ResetOutcome,
} from '../../domain/demo/security-pii';
import {
  eraseProofFromJson,
  exportedSubjectFromJson,
  maskedSubjectFromJson,
  piiPanelFromJson,
  resetOutcomeFromJson,
} from './security-pii-dto';

/**
 * SecurityPiiApi — the transport for the PII lab's endpoints. The masked
 * view sends the caller's credential when one was chosen (null rides as NO
 * Authorization header — the anonymous caller); the gated rounds always
 * carry it, and their 401/403 envelopes become thrown ServerExceptions
 * whose message carries the reason.
 */

const PANEL_PATH = '/demo/security/pii';
const SUBJECT_PATH = '/demo/security/pii/subjects';
const RESET_PATH = '/demo/security/pii/reset';

function credentialHeaders(credential: PiiCredential): Record<string, string> {
  return credential === null
    ? {}
    : { authorization: `Bearer ${credential.token}` };
}

export class SecurityPiiApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/security/pii — the panel. */
  async panel(): Promise<PiiPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PANEL_PATH);
      return parseDto(body, status, piiPanelFromJson);
    });
  }

  /** GET {apiBaseUrl}/demo/security/pii/subjects/{id} — one viewer's view. */
  async subject(customerId: string, credential: PiiCredential): Promise<MaskedSubject> {
    return guardedApiCall(async () => {
      // The guarded pipeline's send form carries headers (the optional
      // credential rides its native one; anonymous sends none).
      const { body, status } = await guardedSendJson(
        this.config,
        `${SUBJECT_PATH}/${customerId}`,
        { method: 'GET', headers: credentialHeaders(credential) },
      );
      return parseDto(body, status, maskedSubjectFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/security/pii/subjects/{id}/export — admin-gated. */
  async exportSubject(
    customerId: string,
    credential: PiiCredential,
  ): Promise<ExportedSubject> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(
        this.config,
        `${SUBJECT_PATH}/${customerId}/export`,
        { method: 'POST', headers: credentialHeaders(credential) },
      );
      return parseDto(body, status, exportedSubjectFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/security/pii/subjects/{id}/erase — admin-gated. */
  async eraseSubject(customerId: string, credential: PiiCredential): Promise<EraseProof> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(
        this.config,
        `${SUBJECT_PATH}/${customerId}/erase`,
        { method: 'POST', headers: credentialHeaders(credential) },
      );
      return parseDto(body, status, eraseProofFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/security/pii/reset — reseed the demo records. */
  async reset(): Promise<ResetOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, RESET_PATH, {
        method: 'POST',
      });
      return parseDto(body, status, resetOutcomeFromJson);
    });
  }
}
