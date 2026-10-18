import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, guardedSendJson, parseDto } from '../../core/error-handling/guards';
import type {
  ConsumeMode,
  ConsumeOutcome,
  PendingListOutcome,
  ProduceOutcome,
  ReclaimOutcome,
  StreamPanel,
} from '../../domain/demo/msg-stream';
import {
  consumeFromJson,
  pendingListFromJson,
  produceFromJson,
  reclaimFromJson,
  streamPanelFromJson,
} from './msg-stream-dto';

/**
 * MsgStreamApi — the transport for the stream lab's five endpoints. All
 * ride the shared guarded JSON pipeline: the roster is a GET, every
 * action is a POST with the small body its button sends.
 */

const PANEL_PATH = '/demo/msg/stream';
const PRODUCE_PATH = '/demo/msg/stream/produce';
const CONSUME_PATH = '/demo/msg/stream/consume';
const PENDING_PATH = '/demo/msg/stream/pending';
const RECLAIM_PATH = '/demo/msg/stream/reclaim';

export class MsgStreamApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/msg/stream — the roster panel's facts. */
  async panel(): Promise<StreamPanel> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PANEL_PATH);
      return parseDto(body, status, streamPanelFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/msg/stream/produce — XADD one note. */
  async produce(note: string): Promise<ProduceOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, PRODUCE_PATH, {
        method: 'POST',
        body: JSON.stringify({ note }),
      });
      return parseDto(body, status, produceFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/msg/stream/consume — read as one persona. */
  async consume(mode: ConsumeMode): Promise<ConsumeOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, CONSUME_PATH, {
        method: 'POST',
        body: JSON.stringify({ mode, count: 5 }),
      });
      return parseDto(body, status, consumeFromJson);
    });
  }

  /** GET {apiBaseUrl}/demo/msg/stream/pending — the PEL, honestly listed. */
  async pending(): Promise<PendingListOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, PENDING_PATH);
      return parseDto(body, status, pendingListFromJson);
    });
  }

  /** POST {apiBaseUrl}/demo/msg/stream/reclaim — XAUTOCLAIM stale entries. */
  async reclaim(minIdleMs: number): Promise<ReclaimOutcome> {
    return guardedApiCall(async () => {
      const { body, status } = await guardedSendJson(this.config, RECLAIM_PATH, {
        method: 'POST',
        body: JSON.stringify({ minIdleMs }),
      });
      return parseDto(body, status, reclaimFromJson);
    });
  }
}
