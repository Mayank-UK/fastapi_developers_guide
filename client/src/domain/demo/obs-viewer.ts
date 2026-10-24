/**
 * Domain models for the observability topic's structured-log viewer (demo
 * block id `obs:viewer`) — the client-side shape of GET /api/demo/obs/viewer.
 * Field names match the server's camelCase wire contract 1:1.
 *
 * The panel is one live read of the server's REAL logging pipeline: the
 * active structlog processor chain (introspected from the process's own
 * configuration, in execution order), the configured log level with its
 * real source, and the recent-events ring — every event the process really
 * logged, most-recent-last, each carrying the level, the event name, the
 * correlation request id (empty when the event carries none), and the
 * remaining key/value pairs as rendered field rows.
 */

/** One key/value pair of a structured event, rendered for display. */
export interface EventField {
  name: string;
  value: string;
}

/** One real event from the server's recent-events ring. */
export interface CapturedEvent {
  sequence: number;
  level: string;
  event: string;
  requestId: string;
  timestamp: string;
  fields: EventField[];
}

/** One processor of the ACTIVE chain, in execution order. */
export interface PipelineStage {
  orderIndex: number;
  processor: string;
  role: string;
}

/** Wire shape of GET /api/demo/obs/viewer — the viewer's contract. */
export interface LogViewerPanel {
  configuredLevel: string;
  levelSource: string;
  ringCapacity: number;
  pipeline: PipelineStage[];
  events: CapturedEvent[];
  panelRequestId: string;
  pipelineNote: string;
  honestyNote: string;
}
