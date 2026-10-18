/**
 * Domain models for the sql-schema topic's UUID lab (demo block id
 * `db:uuid`) — the client-side shape of GET /api/demo/db/uuid. Field
 * names match the server's camelCase wire contract 1:1.
 *
 * The payload is a live comparison: three freshly minted sample runs
 * (uuid4, uuid7, sequence) each with its ordering proof (sortRanks —
 * the rank of each generated value in lexicographic sort order), one
 * real UUIDv7 dissected into its five RFC 9562 fields, and the three
 * strategies' trade-off cards. All of it is minted server-side at
 * request time; the client only renders the facts.
 */

export type RunKind = 'uuid4' | 'uuid7' | 'sequence';

/** One strategy's freshly minted sample, with its ordering proof. */
export interface SampleRun {
  kind: RunKind;
  values: string[];
  /** For each generated value (in order), its rank in sorted order. */
  sortRanks: number[];
  sortable: boolean;
}

/** One labeled slice of a UUIDv7's hex, as the layout reads left → right. */
export interface UuidSegment {
  label: string;
  hexValue: string;
  bits: number;
  meaning: string;
}

/** One real UUIDv7, disassembled: segments + the timestamp read back. */
export interface Uuid7Layout {
  value: string;
  unixMs: number;
  generatedAtIso: string;
  segments: UuidSegment[];
}

/** One id strategy's trade-offs, as the lab compares them. */
export interface UuidStrategy {
  id: string;
  name: string;
  sortableAsText: boolean;
  indexLocality: string;
  /** Random bits per id (uuid4: 122, uuid7: 74); 0 for the sequence. */
  randomBits?: number;
  coordination: string;
  leaksTiming: boolean;
}

/** The whole lab payload: runs, layout, strategies, reasoning. */
export interface UuidLab {
  sampleCount: number;
  runs: SampleRun[];
  sharedPrefixHex: string;
  layout: Uuid7Layout;
  strategies: UuidStrategy[];
  reasoning: string;
}
