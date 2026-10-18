/**
 * Domain models for the files topic's workbench (demo block id
 * `files:workbench`) — the client-side shape of the /api/demo/files*
 * endpoints. Field names match the server's camelCase wire contract 1:1.
 *
 * Two shapes here are deliberately NOT JSON: a download round (binary
 * bytes plus the headers that made them meaningful — Content-Disposition,
 * Content-Range, status) and a live stream round (chunks surfaced as they
 * arrive, each with its own timing, plus the throughput the client
 * measured). Both ride typed raw paths in the API layer, following the
 * raw-round precedent the security lab set for non-JSON responses.
 */

/** The workbench's real policy: the bounds uploads and variants live under. */
export interface FilesPolicy {
  maxUploadBytes: number;
  readChunkBytes: number;
  spoolThresholdBytes: number;
  thumbnailMaxEdge: number;
}

/** One stored file's metadata — the display name beside its sanitized residue. */
export interface StoredFileRow {
  fileId: string;
  displayName: string;
  sanitizedName: string;
  declaredType: string;
  sniffedType: string;
  sizeBytes: number;
  storedAt: string;
}

/** One workbench endpoint on the tour: path, method, what it teaches. */
export interface FilesEndpointRow {
  path: string;
  method: string;
  teaches: string;
}

/** Wire shape of GET /api/demo/files — the workbench panel's contract. */
export interface FilesWorkbenchPanel {
  policy: FilesPolicy;
  storedFiles: StoredFileRow[];
  endpoints: FilesEndpointRow[];
  honestyNotes: string[];
  reasoning: string;
}

/** Wire shape of GET /api/demo/files/stored — the store's inventory. */
export interface StoredFilesInventory {
  count: number;
  files: StoredFileRow[];
}

/** The verdict that admitted a body: the claim beside the magic bytes. */
export interface SniffRow {
  declaredType: string;
  sniffedType: string;
  agrees: boolean;
  note: string;
}

/** Wire shape of one accepted upload: the stored row + the sniff verdict. */
export interface UploadOutcome {
  file: StoredFileRow;
  sniff: SniffRow;
  detail: string;
}

/** Wire shape of the Pillow round: decoded facts + variants as data URLs. */
export interface ImageVariantsRow {
  file: StoredFileRow;
  sniff: SniffRow;
  width: number;
  height: number;
  decodedFormat: string;
  thumbnailDataUrl: string;
  grayscaleDataUrl: string;
  thumbnailBytes: number;
  grayscaleBytes: number;
  detail: string;
}

/** One hostile name's trip through the naming defense, verdicts on display. */
export interface TraversalRow {
  submittedName: string;
  sanitizedName: string | null;
  accepted: boolean;
  storageKey: string;
  naiveJoinTarget: string;
  containmentHolds: boolean;
  verdict: string;
}

/** One stream round's plan, as the server stated it in x-* headers. */
export interface StreamPlan {
  chunkCount: number;
  chunkBytes: number;
  paceMs: number;
}

/** The disposition mode a download may be served in. */
export type DownloadMode = 'inline' | 'attachment';

/** One RAW download round: the bytes plus the headers that gave them meaning. */
export interface DownloadRound {
  status: number;
  /** 200 full body, or the exact slice a 206 answered. */
  bytes: Uint8Array;
  contentType: string;
  contentDisposition: string;
  contentRange: string | null;
  acceptRanges: string | null;
  /** The first bytes, rendered printable — the slice proof the panel shows. */
  preview: string;
}

/** One chunk as it ARRIVED: identity, size, and the client's own timing. */
export interface StreamChunkArrival {
  index: number;
  of: number;
  bytes: number;
  elapsedMs: number;
  /** The line's text, printable — each arrival is shown as it lands. */
  text: string;
}

/** A finished stream round: the plan, every arrival, measured totals. */
export interface StreamOutcome {
  plan: StreamPlan;
  arrivals: StreamChunkArrival[];
  totalBytes: number;
  elapsedMs: number;
  /** Bytes per second, computed from the measured totals. */
  throughputBps: number;
  aborted: boolean;
}
