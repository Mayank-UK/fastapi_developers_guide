import type { Result } from '../../core/result';
import { safeRepositoryCall } from '../../core/error-handling/guards';
import type { GrpcConsoleCall, GrpcConsoleRoster, GrpcConsoleRound } from '../../domain/demo/grpc-console';
import type { GrpcConsoleRepository } from '../../domain/demo/grpc-console-repository';
import type { GrpcConsoleApi } from './grpc-console-api';

/**
 * GrpcConsoleRepositoryImpl — adapts the console API to the domain port.
 * Every thrown transport error is guarded by safeRepositoryCall into a
 * Failed Result, so the demo component never needs try/catch. There is
 * deliberately no failure MAPPING here: grpc status codes (NOT_FOUND,
 * DEADLINE_EXCEEDED) arrive as successful payload facts — the lesson IS
 * the payload — and only genuine HTTP/transport trouble becomes a
 * Failed Result.
 */
export class GrpcConsoleRepositoryImpl implements GrpcConsoleRepository {
  private readonly api: GrpcConsoleApi;

  constructor(api: GrpcConsoleApi) {
    this.api = api;
  }

  roster(): Promise<Result<GrpcConsoleRoster>> {
    return safeRepositoryCall(() => this.api.roster());
  }

  run(call: GrpcConsoleCall): Promise<Result<GrpcConsoleRound>> {
    return safeRepositoryCall(() => this.api.run(call));
  }
}
