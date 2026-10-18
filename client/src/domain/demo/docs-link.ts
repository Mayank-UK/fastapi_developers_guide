/**
 * Domain models for the api-documentation topic's hub (demo block id
 * `api:docs-link`) — the client-side shape of GET /api/demo/api/docs-link.
 * Field names match the server's camelCase wire contract 1:1. The payload
 * is the running app's OWN generated documentation, read from the same
 * OpenAPI document /docs and /redoc render: where the contract lives and
 * renders, the info identity, path/operation/schema counts, the tag
 * areas with their methods, the posts resource's generated operations,
 * and one showcase slice — the POST /api/posts operation exactly as
 * generated, $ref names included.
 */

/** Where the contract lives and renders (absent when a mount is disabled). */
export interface DocsLocations {
  swaggerUi?: string;
  redoc?: string;
  openapiJson?: string;
}

/** One documentation area (an OpenAPI tag) with its live shape. */
export interface DocsArea {
  tag: string;
  paths: number;
  operations: number;
  methods: string[];
}

/** One generated operation of the posts resource, as the schema has it. */
export interface DocsOperation {
  method: string;
  path: string;
  operationId: string;
  summary: string;
  description: string;
  responses: string[];
}

/** The POST /api/posts operation, sliced straight from the schema. */
export interface DocsShowcase {
  method: string;
  path: string;
  summary: string;
  description: string;
  operationId: string;
  tags: string[];
  requestSchema?: string;
  successStatus?: string;
  successSchema?: string;
  validationSchema?: string;
}

/** Wire shape of GET /api/demo/api/docs-link. */
export interface DocsHub {
  infoTitle: string;
  infoVersion: string;
  openapiVersion: string;
  docs: DocsLocations;
  pathCount: number;
  operationCount: number;
  areaCount: number;
  areas: DocsArea[];
  schemaCount: number;
  schemaNames: string[];
  postsOperations: DocsOperation[];
  showcase?: DocsShowcase;
  reasoning: string;
}
