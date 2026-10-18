/**
 * Domain models for the request-response topic's methods playground — the
 * client-side shape of the /api/demo/reqres/notes resource. Field names
 * match the server's camelCase wire contract 1:1. The payload is the
 * request→response contract per method made inspectable: notes arrive as
 * the FILTERED public view (the server also stores a revision counter the
 * response model deliberately drops — no client ever sees it), and every
 * completed exchange reports the status line the wire actually carried,
 * plus the Location header on 201s.
 */

export interface NoteView {
  id: number;
  title: string;
  body: string;
  tags: string[];
  createdAt: string;
}

export interface NotesListing {
  count: number;
  notes: NoteView[];
  /** One paragraph explaining the filtered listing, server-authored. */
  reasoning: string;
}

/** The full representation a client sends on POST/PUT. */
export interface NoteDraft {
  title: string;
  body: string;
  tags: string[];
}

/**
 * One completed request→response exchange, as the playground reports it:
 * what was asked (method + path) and what the wire answered (status, the
 * Location header on 201s, the body when one rode along).
 */
export interface MethodsExchange {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  path: string;
  status: number;
  /** 201 only: the Location header naming the created resource. */
  location?: string;
  /** 200 on GET-one/PUT and 201 on POST: the filtered note body. */
  note?: NoteView;
  /** 200 on GET-list: the whole collection, already filtered. */
  listing?: NotesListing;
}
