import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { ArenaRound, ArenaRoster, ArenaVerdict } from '../../domain/demo/validation-arena';
import { arenaRosterFromJson, arenaVerdictFromJson } from './validation-arena-dto';

/**
 * ValidationArenaApi — the transport for the validation arena: GET
 * /api/demo/validation/arena/roster and POST /api/demo/validation/arena,
 * through the shared guarded fetch pipelines. The round body is serialized
 * with an explicit JSON content-type — and a body the server's own request
 * model refuses (a bogus model key, a non-object candidates value) comes
 * back as the 422 envelope, which the guards surface as a typed server
 * failure for the error panel to teach.
 */

const ROSTER_PATH = '/demo/validation/arena/roster';
const ARENA_PATH = '/demo/validation/arena';

export class ValidationArenaApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** Fetch the roster: the real models, their fields, their rules. */
  async roster(): Promise<ArenaRoster> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, ROSTER_PATH);
      return parseDto(body, status, arenaRosterFromJson);
    });
  }

  /** Submit one round: the chosen model judges the candidate values. */
  async run(round: ArenaRound): Promise<ArenaVerdict> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, ARENA_PATH, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(round),
      });
      return parseDto(body, status, arenaVerdictFromJson);
    });
  }
}
