/**
 * Domain models for the api-design topic's workbench (demo block id
 * `api:posts-workbench`) — the client-side shape of the /api/demo/api/
 * workbench endpoints. Field names match the server's camelCase wire
 * contract 1:1. The demo's subject is the REAL posts substrate: the
 * caller assembles a request (method + path template + query / id /
 * body), the server executes it through the same use cases /api/posts
 * resolves, and the outcome reports the request it would send, the
 * status line, the page/post/envelope payload, the pagination headers a
 * list would carry, and the layer stack that served it.
 */

/** The methods the workbench offers — DELETE earns the honest 405. */
export type WorkbenchMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

/** The two path shapes of the posts resource, template-spelled. */
export type WorkbenchTemplate = '/api/posts' | '/api/posts/{postId}';

/** What a method+template combination resolves to on the real route table. */
export type WorkbenchOperation =
  | 'list'
  | 'get'
  | 'create'
  | 'replace'
  | 'method-not-allowed';

/** The post states the substrate knows (mirrors the server's Literal). */
export type PostStatus = 'draft' | 'published';

/** The collection's sort vocabulary (mirrors the server's Literal). */
export type PostSort = 'newest' | 'oldest' | 'title';

/** The collection query surface — one page of a filtered, sorted view. */
export interface WorkbenchQuery {
  page: number;
  limit: number;
  author?: string;
  tag?: string;
  status?: PostStatus;
  sort: PostSort;
}

/** The create/replace body — the client's half of the post contract. */
export interface WorkbenchPostBody {
  title: string;
  body?: string;
  author: string;
  tags?: string[];
  status?: PostStatus;
}

/** One stored post: the entity and the wire representation in one shape. */
export interface PostRecord {
  id: string;
  title: string;
  body: string;
  author: string;
  tags: string[];
  status: PostStatus;
  createdAt: string;
  updatedAt: string;
}

/** One page of the collection; totals counted after filters. */
export interface PostPage {
  items: PostRecord[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

/** The request a round would put on the wire, spelled as data. */
export interface WorkbenchRequestFact {
  method: WorkbenchMethod;
  template: WorkbenchTemplate;
  /** The concrete URL: template instantiated, canonical query string. */
  path: string;
  /** Present only for POST/PUT rounds. */
  body?: Record<string, unknown>;
}

/** The error envelope a failure earns — shape-identical to the real one. */
export interface WorkbenchEnvelope {
  code: string;
  message: string;
  requestId: string;
}

/** The pagination facts a list response carries in its headers. */
export interface WorkbenchPagination {
  total: number;
  page: number;
  limit: number;
  pages: number;
  /** Absent when there is no such neighbor page (null never rides the wire). */
  next?: string;
  prev?: string;
}

/** One pipeline layer that served the round, in call order. */
export interface WorkbenchLayer {
  name: string;
  detail: string;
}

/** One workbench round: the request you would send, spelled as data. */
export interface WorkbenchRound {
  method: WorkbenchMethod;
  template: WorkbenchTemplate;
  postId?: string;
  query?: WorkbenchQuery;
  body?: WorkbenchPostBody;
}

/** Wire shape of POST /api/demo/api/workbench. */
export interface WorkbenchOutcome {
  operation: WorkbenchOperation;
  request: WorkbenchRequestFact;
  status: number;
  statusReason: string;
  kind: 'page' | 'post' | 'envelope';
  /** List rounds only. */
  page?: PostPage;
  /** Get/create/replace rounds only. */
  post?: PostRecord;
  /** Failure rounds only. */
  envelope?: WorkbenchEnvelope;
  /** List rounds only: the headers' view of the page. */
  pagination?: WorkbenchPagination;
  layers: WorkbenchLayer[];
  reasoning: string;
}

/** Wire shape of GET /api/demo/api/workbench: the substrate's live facets. */
export interface WorkbenchRoster {
  authors: string[];
  tags: string[];
  statuses: PostStatus[];
  sorts: PostSort[];
  totalPosts: number;
  reasoning: string;
}
