import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { WorkbenchOutcome, WorkbenchRoster, WorkbenchRound } from '../../domain/demo/posts-workbench';
import { workbenchOutcomeFromJson, workbenchRosterFromJson } from './posts-workbench-dto';

/**
 * PostsWorkbenchApi — the transport for the api-design workbench: GET
 * /api/demo/api/workbench (the substrate's live facets) and POST
 * /api/demo/api/workbench (one traced round), through the shared guarded
 * fetch pipelines. The round body is serialized with an explicit JSON
 * content-type — and a combination the server's request model refuses
 * (an item template without a postId, a body on GET) comes back as the
 * 422 envelope, which the guards surface as a typed server failure for
 * the error panel to teach.
 */

const WORKBENCH_PATH = '/demo/api/workbench';

export class PostsWorkbenchApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** Fetch the roster: the live facets of the real posts substrate. */
  async roster(): Promise<WorkbenchRoster> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, WORKBENCH_PATH);
      return parseDto(body, status, workbenchRosterFromJson);
    });
  }

  /** Run one round through the real posts pipeline. */
  async run(round: WorkbenchRound): Promise<WorkbenchOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, WORKBENCH_PATH, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(round),
      });
      return parseDto(body, status, workbenchOutcomeFromJson);
    });
  }
}
