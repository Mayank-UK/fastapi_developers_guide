import type { Result } from '../../core/result';
import type { GrpcConsoleCall, GrpcConsoleRoster, GrpcConsoleRound } from './grpc-console';

/**
 * GrpcConsoleRepository — the domain-facing port for the gRPC topic's
 * console demo. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root. Two
 * methods, two endpoints: the roster (live satellite address + the
 * contract + the four methods) and one real round (the outcome IS the
 * answer — grpc status codes arrive as payload facts, never as HTTP
 * errors, because the console's own call succeeded).
 */
export interface GrpcConsoleRepository {
  /** Fetch the roster: the live satellite, the proto stanza, the methods. */
  roster(): Promise<Result<GrpcConsoleRoster>>;

  /** Perform one real gRPC round and report its outcome. */
  run(call: GrpcConsoleCall): Promise<Result<GrpcConsoleRound>>;
}
