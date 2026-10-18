import type {
  AttemptFact,
  DeadLetterFact,
  ScenarioCard,
  SignedDelivery,
  SimulatorPolicy,
  WebhookEventType,
  WebhookReceipt,
  WebhookScenario,
  WebhookSimulation,
  WebhookSimulatorRoster,
} from '../../domain/demo/webhook-simulator';
import {
  isRecord,
  optionalNumber,
  optionalRecord,
  optionalString,
  requiredArray,
  requiredNumber,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * WebhookSimulatorDTO — the wire/transport shapes of the webhook
 * simulator. Mirrors the domain models 1:1 (the interface is the seam
 * where wire and domain may diverge); the `fromJson` builders construct
 * ONLY the listed fields (whitelist) and throw on any shape violation,
 * which parseDto upgrades to an InvalidResponseException.
 *
 * The server serializes optional facts with exclude_none, so absent
 * keys (a broken receiver's `successOnAttempt`, a delivered round's
 * `deadLetter`) are undefined here — a literal null on the wire is a
 * drift and fails validation loudly.
 */

export type WebhookSimulatorRosterDto = WebhookSimulatorRoster;
export type WebhookSimulationDto = WebhookSimulation;
export type WebhookReceiptDto = WebhookReceipt;

const SCENARIOS: readonly WebhookScenario[] = [
  'immediate-2xx',
  'always-500',
  'flaky-then-success',
];
const EVENT_TYPES: readonly WebhookEventType[] = [
  'post.published',
  'post.updated',
  'comment.created',
];
const OUTCOMES: readonly AttemptFact['outcome'][] = [
  'delivered',
  'retry-scheduled',
  'exhausted',
];

function oneOf<T extends string>(value: unknown, allowed: readonly T[], what: string): T {
  if (typeof value === 'string' && (allowed as readonly string[]).includes(value)) {
    return value as T;
  }
  throw new Error(`expected one of [${allowed.join(', ')}] at "${what}"`);
}

function scenarioCardFromJson(body: unknown): ScenarioCard {
  if (!isRecord(body)) throw new Error('scenario card must be an object');
  const successOnAttempt = optionalNumber(body, 'successOnAttempt');
  return {
    id: oneOf(body.id, SCENARIOS, 'scenarios.id'),
    label: requiredString(body, 'label'),
    description: requiredString(body, 'description'),
    ...(successOnAttempt === undefined ? {} : { successOnAttempt }),
  };
}

function policyFromJson(source: Record<string, unknown>, key: string): SimulatorPolicy {
  const policy = requiredRecord(source, key);
  return {
    maxAttempts: requiredNumber(policy, 'maxAttempts'),
    baseDelaySeconds: requiredNumber(policy, 'baseDelaySeconds'),
    backoffFactor: requiredNumber(policy, 'backoffFactor'),
    offsets: requiredArray(policy, 'offsets').map((offset) => {
      if (typeof offset !== 'number' || !Number.isFinite(offset)) {
        throw new Error('expected number at "offsets[]"');
      }
      return offset;
    }),
  };
}

/** Deserialize + validate the roster. */
export function webhookSimulatorRosterFromJson(body: unknown): WebhookSimulatorRosterDto {
  if (!isRecord(body)) throw new Error('webhook roster must be an object');
  const eventTypes = requiredArray(body, 'eventTypes').map((type) =>
    oneOf(type, EVENT_TYPES, 'eventTypes[]'),
  );
  return {
    scenarios: requiredArray(body, 'scenarios').map(scenarioCardFromJson),
    eventTypes,
    secret: requiredString(body, 'secret'),
    receiveEndpoint: requiredString(body, 'receiveEndpoint'),
    policy: policyFromJson(body, 'policy'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

function attemptFromJson(body: unknown): AttemptFact {
  if (!isRecord(body)) throw new Error('attempt must be an object');
  return {
    attempt: requiredNumber(body, 'attempt'),
    offsetSeconds: requiredNumber(body, 'offsetSeconds'),
    timestamp: requiredNumber(body, 'timestamp'),
    signature: requiredString(body, 'signature'),
    status: requiredNumber(body, 'status'),
    outcome: oneOf(body.outcome, OUTCOMES, 'attempts.outcome'),
  };
}

function deadLetterFromJson(body: unknown): DeadLetterFact {
  if (!isRecord(body)) throw new Error('dead letter must be an object');
  return {
    eventId: requiredString(body, 'eventId'),
    attempts: requiredNumber(body, 'attempts'),
    lastStatus: requiredNumber(body, 'lastStatus'),
    finalOffsetSeconds: requiredNumber(body, 'finalOffsetSeconds'),
    reason: requiredString(body, 'reason'),
  };
}

function stringRecordFromJson(source: Record<string, unknown>, key: string): Record<string, string> {
  const raw = requiredRecord(source, key);
  const headers: Record<string, string> = {};
  for (const [name, value] of Object.entries(raw)) {
    if (typeof value !== 'string') {
      throw new Error(`expected string at "${key}.${name}"`);
    }
    headers[name] = value;
  }
  return headers;
}

function signedDeliveryFromJson(source: Record<string, unknown>): SignedDelivery {
  return {
    method: 'POST',
    url: requiredString(source, 'url'),
    headers: stringRecordFromJson(source, 'headers'),
    body: requiredString(source, 'body'),
  };
}

/** Deserialize + validate one simulation. */
export function webhookSimulationFromJson(body: unknown): WebhookSimulationDto {
  if (!isRecord(body)) throw new Error('webhook simulation must be an object');
  const subscriptionRaw = requiredRecord(body, 'subscription');
  const eventRaw = requiredRecord(body, 'event');
  const verdict = oneOf(body.verdict, ['delivered', 'dead-lettered'] as const, 'verdict');
  const deadLetterRaw = optionalRecord(body, 'deadLetter');
  const deliveredAtOffset = optionalNumber(body, 'deliveredAtOffset');
  return {
    subscription: {
      id: requiredString(subscriptionRaw, 'id'),
      url: requiredString(subscriptionRaw, 'url'),
      scenario: oneOf(subscriptionRaw.scenario, SCENARIOS, 'subscription.scenario'),
    },
    event: {
      id: requiredString(eventRaw, 'id'),
      type: requiredString(eventRaw, 'type'),
      body: requiredRecord(eventRaw, 'body'),
    },
    secret: requiredString(body, 'secret'),
    policy: policyFromJson(body, 'policy'),
    attempts: requiredArray(body, 'attempts').map(attemptFromJson),
    verdict,
    ...(deliveredAtOffset === undefined ? {} : { deliveredAtOffset }),
    ...(deadLetterRaw === undefined ? {} : { deadLetter: deadLetterFromJson(deadLetterRaw) }),
    deliverByHand: signedDeliveryFromJson(requiredRecord(body, 'deliverByHand')),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the receive endpoint's 202 receipt. */
export function webhookReceiptFromJson(body: unknown): WebhookReceiptDto {
  if (!isRecord(body)) throw new Error('webhook receipt must be an object');
  const eventId = optionalString(body, 'eventId');
  return {
    ...(eventId === undefined ? {} : { eventId }),
    receivedAt: requiredNumber(body, 'receivedAt'),
    ageSeconds: requiredNumber(body, 'ageSeconds'),
    detail: requiredString(body, 'detail'),
  };
}
