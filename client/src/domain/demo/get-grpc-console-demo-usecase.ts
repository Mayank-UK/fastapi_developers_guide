import type { Result } from '../../core/result';
import type { GrpcConsoleCall, GrpcConsoleRoster, GrpcConsoleRound } from './grpc-console';
import type { GrpcConsoleRepository } from './grpc-console-repository';

/**
 * GetGrpcConsoleDemoUseCase — fetches the gRPC console's roster and
 * fires real rounds (react-guide use-case style): a thin orchestration
 * seam over the repository port. Rounds carry whatever outcome the
 * protocol answered — OK, NOT_FOUND, DEADLINE_EXCEEDED — because a
 * status code is the call's ANSWER, not an exception; only transport
 * failure resolves as a Failed Result for the error panel.
 */
export class GetGrpcConsoleDemoUseCase {
  private readonly repository: GrpcConsoleRepository;

  constructor(repository: GrpcConsoleRepository) {
    this.repository = repository;
  }

  roster(): Promise<Result<GrpcConsoleRoster>> {
    return this.repository.roster();
  }

  run(call: GrpcConsoleCall): Promise<Result<GrpcConsoleRound>> {
    return this.repository.run(call);
  }
}
