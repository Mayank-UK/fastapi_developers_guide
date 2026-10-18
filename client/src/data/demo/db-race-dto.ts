import { type RaceDemo, type RaceRunCard, type RaceSlot } from '../../domain/demo/db-race';
import {
  isRecord,
  requiredArray,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * DbRaceDTO — the wire/transport shapes of the race lab: both runs'
 * timelines, final comment slots, and evidence-computed verdicts.
 */

export type DbRaceDto = RaceDemo;

function slotFromJson(body: unknown): RaceSlot {
  if (!isRecord(body)) throw new Error('race slot must be an object');
  return {
    author: requiredString(body, 'author'),
    body: requiredString(body, 'body'),
  };
}

function timelineLine(value: unknown, index: number): string {
  if (typeof value !== 'string') {
    throw new Error(`expected timeline line at ${index}`);
  }
  return value;
}

function runFromJson(body: unknown): RaceRunCard {
  if (!isRecord(body)) throw new Error('race run must be an object');
  return {
    mode: requiredString(body, 'mode'),
    timeline: requiredArray(body, 'timeline').map(timelineLine),
    finalSlots: requiredArray(body, 'finalSlots').map(slotFromJson),
    verdict: requiredString(body, 'verdict'),
  };
}

/** Deserialize + validate the race payload (both runs side by side). */
export function dbRaceFromJson(body: unknown): DbRaceDto {
  if (!isRecord(body)) throw new Error('race demo must be an object');
  return {
    postId: requiredNumber(body, 'postId'),
    postTitle: requiredString(body, 'postTitle'),
    baselineComments: requiredNumber(body, 'baselineComments'),
    unlocked: runFromJson(body.unlocked),
    locked: runFromJson(body.locked),
    reasoning: requiredString(body, 'reasoning'),
  };
}
