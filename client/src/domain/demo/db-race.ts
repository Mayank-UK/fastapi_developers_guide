/**
 * Domain models for the databases-sql topic's race lab (demo block id
 * `db:race`) — the client-side shape of GET /api/demo/db/race. Field
 * names match the server's camelCase wire contract 1:1.
 *
 * Two deterministic choreographies over the same post's comment count:
 * `unlocked` (both transactions read the same count, both write the
 * same slot — the lost update) and `locked` (SELECT … FOR UPDATE
 * serializes them; both slots really assigned). Verdicts are computed
 * from the final evidence, not asserted.
 */

/** One comment a race run left behind. */
export interface RaceSlot {
  author: string;
  body: string;
}

/** One run: choreography timeline, final comments, verdict. */
export interface RaceRunCard {
  mode: string;
  timeline: string[];
  finalSlots: RaceSlot[];
  verdict: string;
}

/** The whole race payload: both runs side by side. */
export interface RaceDemo {
  postId: number;
  postTitle: string;
  baselineComments: number;
  unlocked: RaceRunCard;
  locked: RaceRunCard;
  reasoning: string;
}
