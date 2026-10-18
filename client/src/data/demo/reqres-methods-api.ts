import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { MethodsExchange, NoteDraft } from '../../domain/demo/reqres-methods';
import { noteFromJson, notesListingFromJson } from './reqres-methods-dto';

/**
 * ReqresMethodsApi — the transport for the /api/demo/reqres/notes
 * playground, one method per HTTP verb. The 2xx answers are composed into
 * MethodsExchange records that carry what the wire actually said: the
 * status, the Location header on 201s (read from the collected response
 * headers), and the parsed body when one rode along. 204 No Content has
 * no body by definition — the guarded pipeline hands it back as a null
 * body, which stays an exchange with no note attached. Non-2xx envelopes
 * (the 404s and 422s the playground teaches) throw through the shared
 * guards and resolve as Failed Results at the repository.
 */

const NOTES_PATH = '/demo/reqres/notes';

const JSON_HEADERS: Record<string, string> = { 'content-type': 'application/json' };

export class ReqresMethodsApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET /demo/reqres/notes — the whole filtered collection. */
  async list(): Promise<MethodsExchange> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, NOTES_PATH, {
        method: 'GET',
      });
      return {
        method: 'GET',
        path: NOTES_PATH,
        status,
        listing: parseDto(body, status, notesListingFromJson),
      };
    });
  }

  /** POST /demo/reqres/notes — create; 201 + Location on success. */
  async create(draft: NoteDraft): Promise<MethodsExchange> {
    return guardedApiCall(async () => {
      const { body, status, headers } = await guardedSendJson(this.config, NOTES_PATH, {
        method: 'POST',
        headers: JSON_HEADERS,
        body: JSON.stringify(draft),
      });
      return {
        method: 'POST',
        path: NOTES_PATH,
        status,
        ...(status === 201 && headers['location'] !== undefined
          ? { location: headers['location'] }
          : {}),
        note: parseDto(body, status, noteFromJson),
      };
    });
  }

  /** PUT /demo/reqres/notes/{id} — full replace; 200 on success. */
  async replace(id: number, draft: NoteDraft): Promise<MethodsExchange> {
    const path = `${NOTES_PATH}/${id}`;
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, path, {
        method: 'PUT',
        headers: JSON_HEADERS,
        body: JSON.stringify(draft),
      });
      return { method: 'PUT', path, status, note: parseDto(body, status, noteFromJson) };
    });
  }

  /** DELETE /demo/reqres/notes/{id} — 204 No Content on success. */
  async remove(id: number): Promise<MethodsExchange> {
    const path = `${NOTES_PATH}/${id}`;
    return guardedApiCall(async () => {
      const { status } = await guardedSendJson(this.config, path, { method: 'DELETE' });
      return { method: 'DELETE', path, status };
    });
  }
}
