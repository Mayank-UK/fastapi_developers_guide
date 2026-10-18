import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import type { RedisPlaygroundDemo } from '../../domain/demo/redis-playground';
import { redisPlaygroundFromJson } from './redis-playground-dto';

/**
 * RedisPlaygroundApi — the transport for GET /api/demo/redis/playground:
 * the whole scripted walk against the live Redis (five structures with
 * real read-backs, the honest TTL expiry proof, the real pub/sub
 * round-trip). Through the shared guarded pipeline.
 */

const REDIS_PLAYGROUND_PATH = '/demo/redis/playground';

export class RedisPlaygroundApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/redis/playground?tag=… — the scripted walk. */
  async playground(tag: string): Promise<RedisPlaygroundDemo> {
    return guardedApiCall(async () => {
      const query = `?tag=${encodeURIComponent(tag)}`;
      const { body, status } = await guardedGetJson(this.config, `${REDIS_PLAYGROUND_PATH}${query}`);
      return parseDto(body, status, redisPlaygroundFromJson);
    });
  }
}
