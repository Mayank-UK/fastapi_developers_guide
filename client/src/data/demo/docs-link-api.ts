import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { DocsHub } from '../../domain/demo/docs-link';
import { docsHubFromJson } from './docs-link-dto';

/**
 * DocsLinkApi — the transport for the api-documentation hub: GET
 * /api/demo/api/docs-link, through the shared guarded fetch pipeline.
 * The payload is a straight read of the running app's generated
 * documentation, so there is no request body and no teaching failure
 * path beyond the guards' own (network faults, non-2xx envelopes,
 * malformed payloads).
 */

const DOCS_LINK_PATH = '/demo/api/docs-link';

export class DocsLinkApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** Fetch the documentation hub: links, counts, areas, the schema slice. */
  async hub(): Promise<DocsHub> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, DOCS_LINK_PATH);
      return parseDto(body, status, docsHubFromJson);
    });
  }
}
