import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type { SliceRunDto, TestingRunnerDto } from './testing-runner-dto';
import { sliceRunDtoFromJson, testingRunnerDtoFromJson } from './testing-runner-dto';

/**
 * TestingRunnerApi — the transport for the runner's two endpoints: the
 * roster (an honest 2xx GET) and the run (a bodyless POST whose answer
 * is a real subprocess pytest round — multi-second by design, which the
 * panel shows as a pending row while it waits). Both ride the shared
 * guarded JSON pipeline; the slice id is URL-encoded so the roster
 * vocabulary is the only thing that ever reaches the path.
 */

const PANEL_PATH = '/demo/testing';

export class TestingRunnerApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/testing — the roster panel. */
  async roster(): Promise<TestingRunnerDto> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PANEL_PATH, { method: 'GET' });
      return parseDto(body, status, testingRunnerDtoFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/testing/run/{sliceId} — execute one slice for real. */
  async run(sliceId: string): Promise<SliceRunDto> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(
        this.config,
        `${PANEL_PATH}/run/${encodeURIComponent(sliceId)}`,
        { method: 'POST' },
      );
      return parseDto(body, status, sliceRunDtoFromJson);
    });
  }
}
