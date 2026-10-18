import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { RedisPlaygroundDemo } from '../../domain/demo/redis-playground';
import type { RedisPlaygroundRepository } from '../../domain/demo/redis-playground-repository';
import type { RedisPlaygroundApi } from './redis-playground-api';

/**
 * RedisPlaygroundRepositoryImpl — adapts the redis playground API to the
 * domain port. Every thrown transport error is guarded by
 * safeRepositoryCall into a Failed Result.
 */
export class RedisPlaygroundRepositoryImpl implements RedisPlaygroundRepository {
  private readonly api: RedisPlaygroundApi;

  constructor(api: RedisPlaygroundApi) {
    this.api = api;
  }

  playground(tag: string): Promise<Result<RedisPlaygroundDemo>> {
    return safeRepositoryCall(() => this.api.playground(tag));
  }
}
