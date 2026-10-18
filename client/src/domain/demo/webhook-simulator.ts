/**
 * Domain models for the webhooks topic's simulator (demo block id
 * `api:webhook-simulator`) — the client-side shape of the simulator
 * endpoints plus the receipt the live receive endpoint answers. Field
 * names match the server's camelCase wire contract 1:1.
 *
 * The simulation walks a delivery lifecycle: every attempt carries its
 * scheduled-at offset (from the pure backoff engine), its own signing
 * timestamp, and the real HMAC-SHA256 signature computed over exactly
 * that timestamp + body. The verdict is `delivered` or `dead-lettered`
 * — the dead letter rides along when the attempt budget ran out, and
 * the omitted-when-null facts (`deliveredAtOffset`, `deadLetter`,
 * `successOnAttempt`) are optional here because the server serializes
 * them with exclude_none (a null on the wire would be a drift).
 */

/** The three target behaviors the simulator can deliver against. */
export type WebhookScenario = 'immediate-2xx' | 'always-500' | 'flaky-then-success';

/** The event catalog — a closed vocabulary, mirrored from the server Literal. */
export type WebhookEventType = 'post.published' | 'post.updated' | 'comment.created';

/** One target scenario as the roster offers it. */
export interface ScenarioCard {
  id: WebhookScenario;
  label: string;
  description: string;
  /** The attempt this target would finally answer 2xx on (absent: never). */
  successOnAttempt?: number;
}

/** The retry policy facts the simulation runs under — schedule included. */
export interface SimulatorPolicy {
  maxAttempts: number;
  baseDelaySeconds: number;
  backoffFactor: number;
  offsets: readonly number[];
}

/** Wire shape of GET /api/demo/api/webhook-simulator. */
export interface WebhookSimulatorRoster {
  scenarios: readonly ScenarioCard[];
  eventTypes: readonly WebhookEventType[];
  secret: string;
  receiveEndpoint: string;
  policy: SimulatorPolicy;
  reasoning: string;
}

/** One simulation round: register a subscription (scenario) + fire an event. */
export interface WebhookSimulatorRequest {
  eventType: WebhookEventType;
  scenario: WebhookScenario;
  note?: string;
}

/** The subscription the round registered — the receiver's own address. */
export interface SubscriptionFact {
  id: string;
  url: string;
  scenario: WebhookScenario;
}

/** The fired event: identity, type, and the payload body as an object. */
export interface EventFact {
  id: string;
  type: string;
  body: Readonly<Record<string, unknown>>;
}

/** One delivery attempt: when, signed how, answered with what. */
export interface AttemptFact {
  attempt: number;
  offsetSeconds: number;
  timestamp: number;
  signature: string;
  status: number;
  outcome: 'delivered' | 'retry-scheduled' | 'exhausted';
}

/** The dead-letter entry an exhausted attempt budget mints. */
export interface DeadLetterFact {
  eventId: string;
  attempts: number;
  lastStatus: number;
  finalOffsetSeconds: number;
  reason: string;
}

/** A ready-to-fire REAL round at this repo's live receive endpoint. */
export interface SignedDelivery {
  method: 'POST';
  url: string;
  headers: Readonly<Record<string, string>>;
  body: string;
}

/** Wire shape of POST /api/demo/api/webhook-simulator. */
export interface WebhookSimulation {
  subscription: SubscriptionFact;
  event: EventFact;
  secret: string;
  policy: SimulatorPolicy;
  attempts: readonly AttemptFact[];
  verdict: 'delivered' | 'dead-lettered';
  deliveredAtOffset?: number;
  deadLetter?: DeadLetterFact;
  deliverByHand: SignedDelivery;
  reasoning: string;
}

/** Wire shape of the 202 the receive endpoint answers (POST /webhooks/receive). */
export interface WebhookReceipt {
  eventId?: string;
  receivedAt: number;
  ageSeconds: number;
  detail: string;
}
