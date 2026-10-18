import type { Result } from '../../core/result';
import type {
  DownloadMode,
  DownloadRound,
  FilesWorkbenchPanel,
  ImageVariantsRow,
  StoredFilesInventory,
  StreamChunkArrival,
  StreamOutcome,
  TraversalRow,
  UploadOutcome,
} from './files-workbench';

/**
 * FilesWorkbenchRepository — the domain-facing port for the files topic's
 * workbench. Demo components depend on this interface only; the HTTP
 * adapter lives in data/demo and is wired at the composition root.
 *
 * `upload` and `processImage` take a real browser `File` (the demo builds
 * sample Files client-side for the in-app browser, or receives one from
 * the real picker). `download` and `stream` are the raw rounds — binary
 * and streaming responses have no JSON body to validate, so the API layer
 * shapes them itself (the security lab's 429 precedent) and hands back
 * typed outcomes. `stream` reports arrivals live as they land, so the
 * panel can render the cadence while the stream is still flowing.
 */
export interface FilesWorkbenchRepository {
  /** The panel: real policy, stored inventory, endpoint tour, honesty notes. */
  panel(): Promise<Result<FilesWorkbenchPanel>>;
  /** The store's inventory: every row with both names and the sniff verdict. */
  stored(): Promise<Result<StoredFilesInventory>>;
  /** One multipart upload: streamed cap + sniff server-side; outcome or 422. */
  upload(file: File): Promise<Result<UploadOutcome>>;
  /** The Pillow round: decode + thumbnail + grayscale variants as data URLs. */
  processImage(file: File): Promise<Result<ImageVariantsRow>>;
  /** One raw download round — full or ranged by `bytesWindow` (e.g. '0-99'). */
  download(
    fileId: string,
    mode: DownloadMode,
    bytesWindow?: string,
  ): Promise<Result<DownloadRound>>;
  /** One hostile name through the naming defense: sanitize + containment. */
  testTraversal(name: string): Promise<Result<TraversalRow>>;
  /** The paced stream: every arrival surfaced live, throughput measured. */
  stream(
    plan: { chunkCount: number; chunkBytes: number; paceMs: number },
    onArrival: (arrival: StreamChunkArrival) => void,
    signal?: AbortSignal,
  ): Promise<Result<StreamOutcome>>;
}
