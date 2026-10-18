import { useCallback, useEffect, useRef, useState } from 'react';
import { container } from '../../../core/container';
import type { Failure } from '../../../core/error-handling/failures';
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
import { ErrorPanel } from '../../components/error-panel';

/**
 * WorkbenchDemo — the files topic's lab (demo block id `files:workbench`).
 * The upload panel IS the lesson: sample files are built client-side (the
 * in-app browser has no file picker) beside a real picker for real
 * browsers; every round answers from the live endpoints — upload with its
 * sniff verdict and BOTH names, downloads with explicit Content-Disposition
 * (inline vs attachment) and a 206 range slice, the Pillow variants, the
 * traversal defense, and the paced stream with per-chunk timing and
 * measured throughput (pacing simulated server-side, labeled).
 */

type PanelStatus =
  | { state: 'loading' }
  | { state: 'failed'; failure: Failure }
  | { state: 'ready'; data: FilesWorkbenchPanel };

const SAMPLE_TEXT = 'the guide, chapter 26 — bytes over the wire, chunk by chunk';
const SAMPLE_PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFklEQVR4nGOwqdgHRycqbOCIYWhJAACbpF3BqJ6P3wAAAABJRU5ErkJggg==';

const buttonClass =
  'w-fit rounded-md border border-outline px-sm py-xxs text-caption hover:border-primary hover:text-primary disabled:opacity-50';
const fieldClass =
  'rounded-md border border-outline bg-surface-tint px-sm py-xxs font-mono text-caption text-on-surface';

function sampleTextFile(): File {
  return new File([SAMPLE_TEXT], 'chapter26.txt', { type: 'text/plain' });
}

function sampleImageFile(): File {
  const binary = atob(SAMPLE_PNG_BASE64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return new File([bytes], 'sample-columns.png', { type: 'image/png' });
}

function failureText(failure: Failure): string {
  return `${failure.code}: ${failure.message}`;
}

export function WorkbenchDemo() {
  const useCase = container.getFilesWorkbenchDemoUseCase;
  const [panel, setPanel] = useState<PanelStatus>({ state: 'loading' });
  const [stored, setStored] = useState<StoredFileRow[]>([]);
  const [uploadOutcome, setUploadOutcome] = useState<UploadOutcome | null>(null);
  const [uploadFailure, setUploadFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [download, setDownload] = useState<DownloadRound | null>(null);
  const [downloadLabel, setDownloadLabel] = useState('');
  const [image, setImage] = useState<ImageVariantsRow | null>(null);
  const [imageFailure, setImageFailure] = useState<string | null>(null);
  const [traversalName, setTraversalName] = useState('../../etc/passwd');
  const [traversal, setTraversal] = useState<TraversalRow | null>(null);
  const [streamChunks, setStreamChunks] = useState('6');
  const [streamPace, setStreamPace] = useState('300');
  const [arrivals, setArrivals] = useState<StreamChunkArrival[]>([]);
  const [streamOutcome, setStreamOutcome] = useState<StreamOutcome | null>(null);
  const streamAbort = useRef<AbortController | null>(null);

  const refreshStored = useCallback(() => {
    void useCase.stored().then((result) => {
      if (result.ok) setStored(result.value.files);
    });
  }, [useCase]);

  const refreshPanel = useCallback(() => {
    void useCase.panel().then((result) => {
      if (result.ok) {
        setPanel({ state: 'ready', data: result.value });
        setStored(result.value.storedFiles);
      } else {
        setPanel({ state: 'failed', failure: result.failure });
      }
    });
  }, [useCase]);

  useEffect(() => {
    refreshPanel();
  }, [refreshPanel]);

  function upload(file: File): void {
    setBusy('upload');
    setUploadFailure(null);
    void useCase.upload(file).then((result) => {
      if (result.ok) {
        setUploadOutcome(result.value);
        refreshStored();
      } else {
        setUploadOutcome(null);
        setUploadFailure(failureText(result.failure));
      }
      setBusy(null);
    });
  }

  function processImage(file: File): void {
    setBusy('image');
    setImageFailure(null);
    void useCase.processImage(file).then((result) => {
      if (result.ok) {
        setImage(result.value);
        refreshStored();
      } else {
        setImage(null);
        setImageFailure(failureText(result.failure));
      }
      setBusy(null);
    });
  }

  function runDownload(fileId: string, mode: 'inline' | 'attachment', bytesWindow?: string): void {
    setBusy(`download:${fileId}`);
    void useCase.download(fileId, mode, bytesWindow).then((result) => {
      if (result.ok) {
        setDownload(result.value);
        setDownloadLabel(
          bytesWindow
            ? `${fileId} · range ${bytesWindow}`
            : `${fileId} · ${mode}`,
        );
      } else {
        setDownload(null);
        setDownloadLabel(failureText(result.failure));
      }
      setBusy(null);
    });
  }

  function runTraversal(): void {
    setBusy('traversal');
    void useCase.testTraversal(traversalName).then((result) => {
      // A traversal test always answers 200; a failure here is transport.
      setTraversal(result.ok ? result.value : null);
      setBusy(null);
    });
  }

  function startStream(): void {
    const chunkCount = Math.min(64, Math.max(1, Number(streamChunks) || 6));
    const paceMs = Math.min(1000, Math.max(0, Number(streamPace) || 0));
    setArrivals([]);
    setStreamOutcome(null);
    streamAbort.current = new AbortController();
    setBusy('stream');
    void useCase
      .stream(
        { chunkCount, chunkBytes: 128, paceMs },
        (arrival) => setArrivals((current) => [...current, arrival]),
        streamAbort.current.signal,
      )
      .then((result) => {
        if (result.ok) setStreamOutcome(result.value);
        setBusy(null);
      });
  }

  function stopStream(): void {
    streamAbort.current?.abort();
  }

  if (panel.state === 'loading') {
    return (
      <p data-testid="files-workbench-loading" className="text-body-sm text-on-surface-variant">
        opening the files workbench…
      </p>
    );
  }

  if (panel.state === 'failed') {
    return <ErrorPanel subject="the files workbench" failure={panel.failure} onRetry={refreshPanel} />;
  }

  const { policy } = panel.data;

  return (
    <div className="flex flex-col gap-md">
      <section data-testid="files-workbench-policy" className="flex flex-col gap-xxs">
        <p className="font-mono text-caption text-on-surface">
          cap {(policy.maxUploadBytes / 1024 / 1024).toFixed(0)} MiB · read chunks{' '}
          {policy.readChunkBytes / 1024} KiB · spool to disk past{' '}
          {(policy.spoolThresholdBytes / 1024 / 1024).toFixed(0)} MiB · thumbnail box{' '}
          {policy.thumbnailMaxEdge}px
        </p>
        {panel.data.honestyNotes.map((note) => (
          <p key={note} className="text-caption text-on-surface-variant">
            · {note}
          </p>
        ))}
      </section>

      <section data-testid="files-workbench-upload" className="flex flex-col gap-xs">
        <div className="flex flex-wrap gap-xs">
          <button
            type="button"
            className={buttonClass}
            disabled={busy === 'upload'}
            onClick={() => upload(sampleTextFile())}
          >
            use sample text file
          </button>
          <button
            type="button"
            className={buttonClass}
            disabled={busy === 'upload'}
            onClick={() => upload(sampleImageFile())}
          >
            use sample image file
          </button>
          <label className={`${buttonClass} cursor-pointer`}>
            pick a real file
            <input
              type="file"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) upload(file);
                event.target.value = '';
              }}
            />
          </label>
        </div>
        {uploadOutcome && (
          <p data-testid="files-workbench-upload-outcome" className="font-mono text-caption text-primary">
            stored {uploadOutcome.file.fileId} · display{' '}
            {uploadOutcome.file.displayName} · sanitized{' '}
            {uploadOutcome.file.sanitizedName} · sniff{' '}
            {uploadOutcome.sniff.sniffedType} ({uploadOutcome.sniff.agrees ? 'agrees' : 'DISAGREES'})
            {' · '}
            {uploadOutcome.file.sizeBytes}B
          </p>
        )}
        {uploadFailure && (
          <p data-testid="files-workbench-upload-rejected" className="font-mono text-caption text-error">
            rejected — {uploadFailure}
          </p>
        )}
      </section>

      <section data-testid="files-workbench-stored" className="flex flex-col gap-xs">
        <p className="text-caption text-on-surface-variant">
          stored inventory ({stored.length}) — the id is server-minted; your name travels as data
        </p>
        {stored.slice(-4).reverse().map((file) => (
          <div key={file.fileId} className="flex flex-col gap-xxs">
            <p className="font-mono text-caption text-on-surface">
              {file.fileId} · {file.displayName} → {file.sanitizedName} · {file.sizeBytes}B
            </p>
            <div className="flex flex-wrap gap-xxs">
              <button
                type="button"
                className={buttonClass}
                disabled={busy === `download:${file.fileId}`}
                onClick={() => runDownload(file.fileId, 'attachment')}
              >
                download attachment
              </button>
              <button
                type="button"
                className={buttonClass}
                disabled={busy === `download:${file.fileId}`}
                onClick={() => runDownload(file.fileId, 'inline')}
              >
                download inline
              </button>
              <button
                type="button"
                className={buttonClass}
                disabled={busy === `download:${file.fileId}`}
                onClick={() => runDownload(file.fileId, 'attachment', '0-23')}
              >
                range 0-23
              </button>
            </div>
          </div>
        ))}
        {download && (
          <div data-testid="files-workbench-download" className="flex flex-col gap-xxs">
            <p className="font-mono text-caption text-primary">
              {downloadLabel}: {download.status} · {download.contentDisposition}
              {download.contentRange ? ` · ${download.contentRange}` : ''}
            </p>
            <p className="font-mono text-caption text-on-surface-variant">
              first bytes: {download.preview}
            </p>
          </div>
        )}
        {!download && downloadLabel && (
          <p className="font-mono text-caption text-error">{downloadLabel}</p>
        )}
      </section>

      <section data-testid="files-workbench-image" className="flex flex-col gap-xs">
        <div className="flex flex-wrap gap-xs">
          <button
            type="button"
            className={buttonClass}
            disabled={busy === 'image'}
            onClick={() => processImage(sampleImageFile())}
          >
            process sample image
          </button>
          <label className={`${buttonClass} cursor-pointer`}>
            pick a real image
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) processImage(file);
                event.target.value = '';
              }}
            />
          </label>
        </div>
        {image && (
          <div data-testid="files-workbench-image-outcome" className="flex flex-col gap-xxs">
            <p className="font-mono text-caption text-primary">
              decoded {image.width}×{image.height} {image.decodedFormat} · thumbnail{' '}
              {image.thumbnailBytes}B · grayscale {image.grayscaleBytes}B
            </p>
            <div className="flex flex-wrap items-center gap-sm">
              <img src={image.thumbnailDataUrl} alt="derived thumbnail" className="h-16 w-16" />
              <img src={image.grayscaleDataUrl} alt="derived grayscale variant" className="h-16" />
            </div>
          </div>
        )}
        {imageFailure && (
          <p className="font-mono text-caption text-error">{imageFailure}</p>
        )}
      </section>

      <section data-testid="files-workbench-traversal" className="flex flex-col gap-xs">
        <div className="flex flex-wrap items-center gap-xs">
          <input
            className={`${fieldClass} w-64`}
            value={traversalName}
            onChange={(event) => setTraversalName(event.target.value)}
            aria-label="traversal test name"
          />
          <button
            type="button"
            className={buttonClass}
            disabled={busy === 'traversal'}
            onClick={runTraversal}
          >
            run through the defense
          </button>
        </div>
        {traversal && (
          <div data-testid="files-workbench-traversal-outcome" className="flex flex-col gap-xxs">
            <p className="font-mono text-caption text-primary">
              {traversal.submittedName} → {traversal.sanitizedName ?? '(nothing survives)'} ·
              accepted: {String(traversal.accepted)} · containment:{' '}
              {String(traversal.containmentHolds)}
            </p>
            <p className="text-caption text-on-surface-variant">{traversal.verdict}</p>
            <p className="font-mono text-caption text-on-surface-variant">
              storage key: {traversal.storageKey}
            </p>
          </div>
        )}
      </section>

      <section data-testid="files-workbench-stream" className="flex flex-col gap-xs">
        <div className="flex flex-wrap items-center gap-xs">
          <label className="text-caption text-on-surface-variant" htmlFor="stream-chunks">
            chunks
          </label>
          <input
            id="stream-chunks"
            className={`${fieldClass} w-16`}
            value={streamChunks}
            onChange={(event) => setStreamChunks(event.target.value)}
          />
          <label className="text-caption text-on-surface-variant" htmlFor="stream-pace">
            pace ms
          </label>
          <input
            id="stream-pace"
            className={`${fieldClass} w-20`}
            value={streamPace}
            onChange={(event) => setStreamPace(event.target.value)}
          />
          <button
            type="button"
            className={buttonClass}
            disabled={busy === 'stream'}
            onClick={startStream}
          >
            start stream
          </button>
          <button
            type="button"
            className={buttonClass}
            disabled={busy !== 'stream'}
            onClick={stopStream}
          >
            stop
          </button>
        </div>
        {arrivals.slice(-6).map((arrival) => (
          <p key={arrival.index} data-testid="files-workbench-arrival" className="font-mono text-caption text-primary">
            chunk {arrival.index}/{arrival.of} · {arrival.bytes}B · t+{arrival.elapsedMs}ms
          </p>
        ))}
        {streamOutcome && (
          <p data-testid="files-workbench-stream-summary" className="font-mono text-caption text-on-surface">
            {streamOutcome.arrivals.length} chunks · {streamOutcome.totalBytes}B in{' '}
            {streamOutcome.elapsedMs}ms · {streamOutcome.throughputBps} B/s (simulated pacing)
          </p>
        )}
      </section>

      <p data-testid="files-workbench-reasoning" className="text-body-sm text-on-surface-variant">
        {panel.data.reasoning}
      </p>
    </div>
  );
}

export default WorkbenchDemo;
