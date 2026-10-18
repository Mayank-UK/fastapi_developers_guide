import type {
  FilesEndpointRow,
  FilesPolicy,
  FilesWorkbenchPanel,
  ImageVariantsRow,
  SniffRow,
  StoredFileRow,
  StoredFilesInventory,
  TraversalRow,
  UploadOutcome,
} from '../../domain/demo/files-workbench';
import {
  isRecord,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredString,
} from '../content/validate';

/**
 * FilesWorkbenchDTO — the wire/transport shapes of the workbench's JSON
 * endpoints (panel, stored, upload, images, traversal). The two RAW rounds
 * (binary download, ndjson stream) are not DTOs — the API layer shapes
 * them from status + headers + bytes, because a binary body has no JSON
 * to validate (the security lab's raw-round precedent, applied to files).
 */

function policyFromJson(source: Record<string, unknown>): FilesPolicy {
  return {
    maxUploadBytes: requiredNumber(source, 'maxUploadBytes'),
    readChunkBytes: requiredNumber(source, 'readChunkBytes'),
    spoolThresholdBytes: requiredNumber(source, 'spoolThresholdBytes'),
    thumbnailMaxEdge: requiredNumber(source, 'thumbnailMaxEdge'),
  };
}

function storedFileFromJson(value: unknown): StoredFileRow {
  if (!isRecord(value)) throw new Error('stored file row must be an object');
  return {
    fileId: requiredString(value, 'fileId'),
    displayName: requiredString(value, 'displayName'),
    sanitizedName: requiredString(value, 'sanitizedName'),
    declaredType: requiredString(value, 'declaredType'),
    sniffedType: requiredString(value, 'sniffedType'),
    sizeBytes: requiredNumber(value, 'sizeBytes'),
    storedAt: requiredString(value, 'storedAt'),
  };
}

function endpointFromJson(value: unknown): FilesEndpointRow {
  if (!isRecord(value)) throw new Error('endpoint row must be an object');
  return {
    path: requiredString(value, 'path'),
    method: requiredString(value, 'method'),
    teaches: requiredString(value, 'teaches'),
  };
}

function sniffFromJson(value: unknown): SniffRow {
  if (!isRecord(value)) throw new Error('sniff row must be an object');
  return {
    declaredType: requiredString(value, 'declaredType'),
    sniffedType: requiredString(value, 'sniffedType'),
    agrees: requiredBoolean(value, 'agrees'),
    note: requiredString(value, 'note'),
  };
}

/** Deserialize + validate the workbench panel. */
export function filesWorkbenchPanelFromJson(body: unknown): FilesWorkbenchPanel {
  if (!isRecord(body)) throw new Error('files workbench panel must be an object');
  const policy = body['policy'];
  if (!isRecord(policy)) throw new Error('policy must be an object');
  const honestyNotes = requiredArray(body, 'honestyNotes').map((note) => {
    if (typeof note !== 'string') throw new Error('honesty notes must be strings');
    return note;
  });
  return {
    policy: policyFromJson(policy),
    storedFiles: requiredArray(body, 'storedFiles').map(storedFileFromJson),
    endpoints: requiredArray(body, 'endpoints').map(endpointFromJson),
    honestyNotes,
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the stored inventory. */
export function storedFilesFromJson(body: unknown): StoredFilesInventory {
  if (!isRecord(body)) throw new Error('stored inventory must be an object');
  return {
    count: requiredNumber(body, 'count'),
    files: requiredArray(body, 'files').map(storedFileFromJson),
  };
}

/** Deserialize + validate one accepted upload. */
export function uploadOutcomeFromJson(body: unknown): UploadOutcome {
  if (!isRecord(body)) throw new Error('upload outcome must be an object');
  return {
    file: storedFileFromJson(body['file']),
    sniff: sniffFromJson(body['sniff']),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the Pillow round. */
export function imageVariantsFromJson(body: unknown): ImageVariantsRow {
  if (!isRecord(body)) throw new Error('image variants must be an object');
  return {
    file: storedFileFromJson(body['file']),
    sniff: sniffFromJson(body['sniff']),
    width: requiredNumber(body, 'width'),
    height: requiredNumber(body, 'height'),
    decodedFormat: requiredString(body, 'decodedFormat'),
    thumbnailDataUrl: requiredString(body, 'thumbnailDataUrl'),
    grayscaleDataUrl: requiredString(body, 'grayscaleDataUrl'),
    thumbnailBytes: requiredNumber(body, 'thumbnailBytes'),
    grayscaleBytes: requiredNumber(body, 'grayscaleBytes'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate one traversal verdict. */
export function traversalRowFromJson(body: unknown): TraversalRow {
  if (!isRecord(body)) throw new Error('traversal row must be an object');
  const sanitizedName = body['sanitizedName'];
  if (sanitizedName !== null && typeof sanitizedName !== 'string') {
    throw new Error('sanitizedName must be a string or null');
  }
  return {
    submittedName: requiredString(body, 'submittedName'),
    sanitizedName,
    accepted: requiredBoolean(body, 'accepted'),
    storageKey: requiredString(body, 'storageKey'),
    naiveJoinTarget: requiredString(body, 'naiveJoinTarget'),
    containmentHolds: requiredBoolean(body, 'containmentHolds'),
    verdict: requiredString(body, 'verdict'),
  };
}
