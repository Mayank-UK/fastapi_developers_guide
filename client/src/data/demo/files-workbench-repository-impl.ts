import { safeRepositoryCall } from '../../core/error-handling/guards';
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
} from '../../domain/demo/files-workbench';
import type { FilesWorkbenchRepository } from '../../domain/demo/files-workbench-repository';
import type { FilesWorkbenchApi } from './files-workbench-api';

/**
 * FilesWorkbenchRepositoryImpl — adapts the workbench API to the domain
 * port. Expected failures resolve as Failed Results; the raw rounds
 * (binary download, live stream) arrive as the typed outcomes the API
 * shaped, never as thrown bodies.
 */
export class FilesWorkbenchRepositoryImpl implements FilesWorkbenchRepository {
  private readonly api: FilesWorkbenchApi;

  constructor(api: FilesWorkbenchApi) {
    this.api = api;
  }

  panel(): Promise<Result<FilesWorkbenchPanel>> {
    return safeRepositoryCall(() => this.api.panel());
  }

  stored(): Promise<Result<StoredFilesInventory>> {
    return safeRepositoryCall(() => this.api.stored());
  }

  upload(file: File): Promise<Result<UploadOutcome>> {
    return safeRepositoryCall(() => this.api.upload(file));
  }

  processImage(file: File): Promise<Result<ImageVariantsRow>> {
    return safeRepositoryCall(() => this.api.processImage(file));
  }

  download(
    fileId: string,
    mode: DownloadMode,
    bytesWindow?: string,
  ): Promise<Result<DownloadRound>> {
    return safeRepositoryCall(() => this.api.download(fileId, mode, bytesWindow));
  }

  testTraversal(name: string): Promise<Result<TraversalRow>> {
    return safeRepositoryCall(() => this.api.testTraversal(name));
  }

  stream(
    plan: { chunkCount: number; chunkBytes: number; paceMs: number },
    onArrival: (arrival: StreamChunkArrival) => void,
    signal?: AbortSignal,
  ): Promise<Result<StreamOutcome>> {
    return safeRepositoryCall(() => this.api.stream(plan, onArrival, signal));
  }
}
