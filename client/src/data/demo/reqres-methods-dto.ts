import type { NoteView, NotesListing } from '../../domain/demo/reqres-methods';
import { isRecord, requiredArray, requiredNumber, requiredString } from '../content/validate';

/**
 * ReqresMethodsDTO — the wire/transport shapes of the notes playground.
 * Mirrors the domain models 1:1 (the interface is the seam where wire and
 * domain may diverge); the `fromJson` builders construct ONLY the listed
 * fields (whitelist) and throw on any shape violation, which parseDto
 * upgrades to an InvalidResponseException. The filtered public view is
 * the client's whole truth: `revision` never appears here because the
 * server's response model drops it before serialization.
 */

export type NoteDto = NoteView;
export type NotesListingDto = NotesListing;

/** Deserialize + validate one filtered note (GET-one / POST / PUT body). */
export function noteFromJson(body: unknown): NoteDto {
  if (!isRecord(body)) throw new Error('note must be an object');
  return {
    id: requiredNumber(body, 'id'),
    title: requiredString(body, 'title'),
    body: requiredString(body, 'body'),
    tags: requiredArray(body, 'tags').map(nonEmptyString),
    createdAt: requiredString(body, 'createdAt'),
  };
}

/** Deserialize + validate the GET-list payload. */
export function notesListingFromJson(body: unknown): NotesListingDto {
  if (!isRecord(body)) throw new Error('notes listing must be an object');
  return {
    count: requiredNumber(body, 'count'),
    notes: requiredArray(body, 'notes').map(noteFromJson),
    reasoning: requiredString(body, 'reasoning'),
  };
}

function nonEmptyString(value: unknown): string {
  if (typeof value !== 'string' || value === '') {
    throw new Error('tag lists must be non-empty strings');
  }
  return value;
}
