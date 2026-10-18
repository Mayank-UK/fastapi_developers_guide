import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type {
  OutboxConsumeOutcome,
  OutboxPanel,
  OutboxWriteOutcome,
  RelayOutcome,
} from '../../domain/demo/msg-outbox';
import {
  outboxConsumeFromJson,
  outboxPanelFromJson,
  outboxWriteFromJson,
  relayFromJson,
} from './msg-outbox-dto';

/**
 * MsgOutboxApi — the transport for the outbox lab's four endpoints. All
 * ride the shared guarded JSON pipeline: the roster is a GET, every
 * action is a POST with the small body its button sends.
 */

const PANEL_PATH = '/demo/msg/outbox';
const POSTS_PATH = '/demo/msg/outbox/posts';
const RELAY_PATH = '/demo/msg/outbox/relay';
const CONSUME_PATH = '/demo/msg/outbox/consume';

export class MsgOutboxApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/msg/outbox — the roster panel's facts. */
  async panel(): Promise<OutboxPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PANEL_PATH);
      return parseDto(body, status, outboxPanelFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/msg/outbox/posts — the one-transaction write. */
  async create(title: string, body: string): Promise<OutboxWriteOutcome> {
    return guardedApiCall(async () => {
      const { body: parsed, status } = await guardedSendJson(this.config, POSTS_PATH, {
        method: 'POST',
        body: JSON.stringify({ title, body }),
      });
      return parseDto(parsed, status, outboxWriteFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/msg/outbox/relay — one cycle; the crash window optional. */
  async relay(crashBeforeMark: boolean): Promise<RelayOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, RELAY_PATH, {
        method: 'POST',
        body: JSON.stringify({ crashBeforeMark }),
      });
      return parseDto(body, status, relayFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/msg/outbox/consume — the dedupe-proof walk. */
  async consume(): Promise<OutboxConsumeOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, CONSUME_PATH, {
        method: 'POST',
      });
      return parseDto(body, status, outboxConsumeFromJson);
    });
  }
}
