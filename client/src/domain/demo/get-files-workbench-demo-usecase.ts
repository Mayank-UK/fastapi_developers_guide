import type { Result } from '../../core/result';
import type { FilesWorkbenchRepository } from './files-workbench-repository';
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
 * GetFilesWorkbenchDemoUseCase — the files workbench's use case: the panel
 * and its follow-on rounds over the real endpoints. Every method is a thin
 * delegation today (the demo's logic is the server's); the use case exists
 * for the same reason every other demo's does — the view depends on one
 * named capability, not on an HTTP client, and future client-side shaping
 * (sample-file construction, stream bookkeeping) has an obvious home.
 */
export class GetFilesWorkbenchDemoUseCase {
  private readonly repository: FilesWorkbenchRepository;

  constructor(repository: FilesWorkbenchRepository) {
    this.repository = repository;
  }

  /** The panel: policy, stored inventory, endpoint tour, honesty notes. */
  panel(): Promise<Result<FilesWorkbenchPanel>> {
    return this.repository.panel();
  }

  /** The store's inventory. */
  stored(): Promise<Result<StoredFilesInventory>> {
    return this.repository.stored();
  }

  /** One multipart upload (cap + sniff enforced server-side). */
  upload(file: File): Promise<Result<UploadOutcome>> {
    return this.repository.upload(file);
  }

  /** The Pillow round: thumbnail + grayscale variants as data URLs. */
  processImage(file: File): Promise<Result<ImageVariantsRow>> {
    return this.repository.processImage(file);
  }

  /** One raw download round, optionally one range window (e.g. '0-99'). */
  download(
    fileId: string,
    mode: DownloadMode,
    bytesWindow?: string,
  ): Promise<Result<DownloadRound>> {
    return this.repository.download(fileId, mode, bytesWindow);
  }

  /** One hostile name through the naming defense. */
  testTraversal(name: string): Promise<Result<TraversalRow>> {
    return this.repository.testTraversal(name);
  }

  /** The paced stream, arrivals surfaced live as they land. */
  stream(
    plan: { chunkCount: number; chunkBytes: number; paceMs: number },
    onArrival: (arrival: StreamChunkArrival) => void,
    signal?: AbortSignal,
  ): Promise<Result<StreamOutcome>> {
    return this.repository.stream(plan, onArrival, signal);
  }
}
