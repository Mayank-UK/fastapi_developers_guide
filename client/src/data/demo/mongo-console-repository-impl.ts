import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { MongoConsoleDemo } from '../../domain/demo/mongo-console';
import type { MongoConsoleRepository } from '../../domain/demo/mongo-console-repository';
import type { MongoConsoleApi } from './mongo-console-api';

/**
 * MongoConsoleRepositoryImpl — adapts the mongo console API to the
 * domain port. Every thrown transport error is guarded by
 * safeRepositoryCall into a Failed Result.
 */
export class MongoConsoleRepositoryImpl implements MongoConsoleRepository {
  private readonly api: MongoConsoleApi;

  constructor(api: MongoConsoleApi) {
    this.api = api;
  }

  console(tag: string): Promise<Result<MongoConsoleDemo>> {
    return safeRepositoryCall(() => this.api.console(tag));
  }
}
