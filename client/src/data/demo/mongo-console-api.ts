import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { MongoConsoleDemo } from '../../domain/demo/mongo-console';
import { mongoConsoleFromJson } from './mongo-console-dto';

/**
 * MongoConsoleApi — the transport for GET /api/demo/db/mongo-console:
 * the whole scripted console against the live MongoDB (seed, boundary
 * refusal, find/update/count/delete, COLLSCAN-vs-IXSCAN explains, a
 * real TTL index). Through the shared guarded pipeline.
 */

const MONGO_CONSOLE_PATH = '/demo/db/mongo-console';

export class MongoConsoleApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/db/mongo-console?tag=… — the scripted console. */
  async console(tag: string): Promise<MongoConsoleDemo> {
    return guardedApiCall(async () => {
      const query = `?tag=${encodeURIComponent(tag)}`;
      const { body, status } = await guardedGetJson(this.config, `${MONGO_CONSOLE_PATH}${query}`);
      return parseDto(body, status, mongoConsoleFromJson);
    });
  }
}
