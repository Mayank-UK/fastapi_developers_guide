import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { GrpcConsoleCall, GrpcConsoleRoster, GrpcConsoleRound } from '../../domain/demo/grpc-console';
import { grpcConsoleCallToJson, grpcConsoleRosterFromJson, grpcConsoleRoundFromJson } from './grpc-console-dto';

/**
 * GrpcConsoleApi — the transport for the gRPC topic's console:
 * GET/POST /api/demo/api/grpc-console. The POST body is one console
 * call (method + arguments + optional deadlineMs); the honest failure
 * modes — NOT_FOUND, DEADLINE_EXCEEDED — arrive as 200 PAYLOAD facts
 * (the console's own HTTP call succeeded), so the transport's error
 * paths stay for genuine HTTP/transport trouble only.
 */

const CONSOLE_PATH = '/demo/api/grpc-console';

export class GrpcConsoleApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** Fetch the roster: the live satellite, the contract stanza, the methods. */
  async roster(): Promise<GrpcConsoleRoster> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, CONSOLE_PATH);
      return parseDto(body, status, grpcConsoleRosterFromJson);
    });
  }

  /** Perform one real gRPC round and report its outcome. */
  async run(call: GrpcConsoleCall): Promise<GrpcConsoleRound> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, CONSOLE_PATH, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(grpcConsoleCallToJson(call)),
      });
      return parseDto(body, status, grpcConsoleRoundFromJson);
    });
  }
}
