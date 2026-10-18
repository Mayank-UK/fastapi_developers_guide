import { describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { WorkbenchDemo } from './workbench_demo';
import { demoRegistry } from '../demo-registry';
import { container, ContainerTokens } from '../../../core/container';
import { createAppConfig } from '../../../core/config/app-config';
import { failed, success, type Result } from '../../../core/result';
import { ServerFailure } from '../../../core/error-handling/failures';
import type { GetFilesWorkbenchDemoUseCase } from '../../../domain/demo/get-files-workbench-demo-usecase';
import type {
  DownloadRound,
  FilesWorkbenchPanel,
  ImageVariantsRow,
  StreamChunkArrival,
  StreamOutcome,
  StoredFileRow,
  TraversalRow,
  UploadOutcome,
} from '../../../domain/demo/files-workbench';

/**
 * WorkbenchDemo spec — fixture-driven (happy + failure): the panel renders
 * the real policy and honesty notes; the sample-file upload surfaces the
 * stored row with BOTH names and the sniff verdict, and a 422 rejection
 * renders as the typed rejection it is; the range download shows 206 +
 * Content-Range + the slice preview; the traversal verdict and the stream
 * summary render from their typed outcomes; a failed panel degrades to
 * the shared error panel with recovery.
 */

const storedFile: StoredFileRow = {
  fileId: 'f-0a1b2c3d',
  displayName: '拍chapter.txt',
  sanitizedName: 'chapter.txt',
  declaredType: 'text/plain',
  sniffedType: 'text/plain',
  sizeBytes: 13,
  storedAt: '2026-10-17T12:00:00+00:00',
};

const panel: FilesWorkbenchPanel = {
  policy: {
    maxUploadBytes: 2 * 1024 * 1024,
    readChunkBytes: 65536,
    spoolThresholdBytes: 1024 * 1024,
    thumbnailMaxEdge: 96,
  },
  storedFiles: [storedFile],
  endpoints: [
    { path: '/api/demo/files/upload', method: 'POST', teaches: 'multipart upload' },
  ],
  honestyNotes: ['the store is IN MEMORY and demo-scoped: a restart loses it'],
  reasoning: 'Uploads are streams validated while they are read.',
};

const uploadOutcome: UploadOutcome = {
  file: { ...storedFile, displayName: 'chapter26.txt', sanitizedName: 'chapter26.txt' },
  sniff: {
    declaredType: 'text/plain',
    sniffedType: 'text/plain',
    agrees: true,
    note: 'declared type matches the magic bytes',
  },
  detail: 'stored as f-0a1b2c3d',
};

const rangeDownload: DownloadRound = {
  status: 206,
  bytes: new TextEncoder().encode('the guide, chapter 2'),
  contentType: 'text/plain',
  contentDisposition: 'attachment; filename="chapter26.txt"',
  contentRange: 'bytes 0-18/46',
  acceptRanges: 'bytes',
  preview: 'the guide, chapter 2',
};

const imageOutcome: ImageVariantsRow = {
  file: storedFile,
  sniff: uploadOutcome.sniff,
  width: 8,
  height: 8,
  decodedFormat: 'PNG',
  thumbnailDataUrl: 'data:image/png;base64,AAA',
  grayscaleDataUrl: 'data:image/png;base64,BBB',
  thumbnailBytes: 74,
  grayscaleBytes: 61,
  detail: 'decoded 8×8 PNG from the pixels',
};

const traversalRow: TraversalRow = {
  submittedName: '../../etc/passwd',
  sanitizedName: 'etcpasswd',
  accepted: false,
  storageKey: 'f-<server-minted hex — never derived from the name>',
  naiveJoinTarget: '/srv/uploads/../../etc/passwd',
  containmentHolds: false,
  verdict: 'REJECTED — the raw name escapes a naive join',
};

const streamOutcome: StreamOutcome = {
  plan: { chunkCount: 3, chunkBytes: 128, paceMs: 0 },
  arrivals: [
    { index: 1, of: 3, bytes: 128, elapsedMs: 3, text: '…' },
    { index: 2, of: 3, bytes: 128, elapsedMs: 5, text: '…' },
    { index: 3, of: 3, bytes: 128, elapsedMs: 7, text: '…' },
  ],
  totalBytes: 387,
  elapsedMs: 7,
  throughputBps: 55285,
  aborted: false,
};

type Stubs = {
  panel?: () => Promise<Result<FilesWorkbenchPanel>>;
  upload?: (file: File) => Promise<Result<UploadOutcome>>;
  download?: (fileId: string, mode: 'inline' | 'attachment', bytes?: string) => Promise<Result<DownloadRound>>;
  processImage?: (file: File) => Promise<Result<ImageVariantsRow>>;
  testTraversal?: (name: string) => Promise<Result<TraversalRow>>;
  stream?: (
    plan: { chunkCount: number; chunkBytes: number; paceMs: number },
    onArrival: (arrival: StreamChunkArrival) => void,
  ) => Promise<Result<StreamOutcome>>;
};

function stubUseCase(stubs: Stubs): void {
  container.initialize(createAppConfig());
  container.register(ContainerTokens.GetFilesWorkbenchDemoUseCase, {
    panel: stubs.panel ?? (async () => success(panel)),
    stored: async () => success({ count: panel.storedFiles.length, files: panel.storedFiles }),
    upload: stubs.upload ?? (async () => success(uploadOutcome)),
    download:
      stubs.download ??
      (async () => success(rangeDownload)),
    processImage: stubs.processImage ?? (async () => success(imageOutcome)),
    testTraversal: stubs.testTraversal ?? (async () => success(traversalRow)),
    stream:
      stubs.stream ??
      (async (_plan, onArrival) => {
        for (const arrival of streamOutcome.arrivals) onArrival(arrival);
        return success(streamOutcome);
      }),
  } as unknown as GetFilesWorkbenchDemoUseCase);
}

describe('WorkbenchDemo', () => {
  it('is bound in the demo registry under its demo-block id', () => {
    expect(demoRegistry['files:workbench']).toBeDefined();
  });

  it('renders the policy, honesty notes, and the stored inventory', async () => {
    stubUseCase({});
    render(<WorkbenchDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('files-workbench-policy')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('files-workbench-policy')).toHaveTextContent('cap 2 MiB');
    expect(screen.getByTestId('files-workbench-policy')).toHaveTextContent('IN MEMORY');
    expect(screen.getByTestId('files-workbench-stored')).toHaveTextContent('f-0a1b2c3d');
    expect(screen.getByTestId('files-workbench-stored')).toHaveTextContent('拍chapter.txt');
  });

  it('uploads the sample text file and surfaces both names and the sniff', async () => {
    stubUseCase({});
    render(<WorkbenchDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('files-workbench-stored')).toBeInTheDocument(),
    );

    screen.getByRole('button', { name: 'use sample text file' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('files-workbench-upload-outcome')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('files-workbench-upload-outcome')).toHaveTextContent(
      'stored f-0a1b2c3d',
    );
    expect(screen.getByTestId('files-workbench-upload-outcome')).toHaveTextContent(
      'sniff text/plain (agrees)',
    );
  });

  it('renders a rejected upload as the typed 422 rejection it is', async () => {
    stubUseCase({
      upload: async () =>
        failed(
          new ServerFailure(
            'upload rejected — body exceeds the 2097152-byte cap (at least 2097153 bytes)',
            { code: 'validation_failed', status: 422, requestId: 'req-f1' },
          ),
        ),
    });
    render(<WorkbenchDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('files-workbench-stored')).toBeInTheDocument(),
    );

    screen.getByRole('button', { name: 'use sample text file' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('files-workbench-upload-rejected')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('files-workbench-upload-rejected')).toHaveTextContent(
      'exceeds the 2097152-byte cap',
    );
  });

  it('shows the 206 range round with Content-Range and the slice preview', async () => {
    stubUseCase({});
    render(<WorkbenchDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('files-workbench-stored')).toBeInTheDocument(),
    );

    screen.getByRole('button', { name: 'range 0-23' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('files-workbench-download')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('files-workbench-download')).toHaveTextContent('206');
    expect(screen.getByTestId('files-workbench-download')).toHaveTextContent(
      'bytes 0-18/46',
    );
    expect(screen.getByTestId('files-workbench-download')).toHaveTextContent(
      'first bytes: the guide, chapter 2',
    );
  });

  it('processes the sample image and renders the derived variants', async () => {
    stubUseCase({});
    render(<WorkbenchDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('files-workbench-stored')).toBeInTheDocument(),
    );

    screen.getByRole('button', { name: 'process sample image' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('files-workbench-image-outcome')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('files-workbench-image-outcome')).toHaveTextContent(
      'decoded 8×8 PNG',
    );
    expect(screen.getByTestId('files-workbench-image-outcome')).toHaveTextContent('74B');
  });

  it('runs the traversal defense and the stream with live arrivals', async () => {
    stubUseCase({});
    render(<WorkbenchDemo />);
    await waitFor(() =>
      expect(screen.getByTestId('files-workbench-stored')).toBeInTheDocument(),
    );

    screen.getByRole('button', { name: 'run through the defense' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('files-workbench-traversal-outcome')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('files-workbench-traversal-outcome')).toHaveTextContent(
      'etcpasswd',
    );

    screen.getByRole('button', { name: 'start stream' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('files-workbench-stream-summary')).toBeInTheDocument(),
    );
    expect(screen.getAllByTestId('files-workbench-arrival')).toHaveLength(3);
    expect(screen.getByTestId('files-workbench-stream-summary')).toHaveTextContent(
      'simulated pacing',
    );
  });

  it('degrades to the shared error panel on a Failed panel, with recovery', async () => {
    let calls = 0;
    stubUseCase({
      panel: async () => {
        calls += 1;
        return calls === 1
          ? failed(
              new ServerFailure('Could not reach the server.', {
                code: 'unknown_error',
                status: 0,
                requestId: 'req-f2',
              }),
            )
          : success(panel);
      },
    });
    render(<WorkbenchDemo />);
    await waitFor(() => expect(screen.getByTestId('error-panel')).toBeInTheDocument());
    screen.getByRole('button', { name: 'Try again' }).click();
    await waitFor(() =>
      expect(screen.getByTestId('files-workbench-policy')).toBeInTheDocument(),
    );
  });
});
