import {
  type DocsArea,
  type DocsHub,
  type DocsLocations,
  type DocsOperation,
  type DocsShowcase,
} from '../../domain/demo/docs-link';
import {
  isRecord,
  optionalString,
  requiredArray,
  requiredNumber,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * DocsLinkDTO — the wire/transport shapes of the api-documentation hub.
 * Mirrors the domain models 1:1 (the interface is the seam where wire and
 * domain may diverge); the `fromJson` builders construct ONLY the listed
 * fields (whitelist) and throw on any shape violation, which parseDto
 * upgrades to an InvalidResponseException. Optional wire fields (a
 * disabled docs mount, a $ref the sliced operation does not carry) stay
 * undefined when the server omitted them — the null-as-invalid rule
 * everywhere in this client.
 */

export type DocsHubDto = DocsHub;

function stringList(source: Record<string, unknown>, key: string): string[] {
  return requiredArray(source, key).map((value) => {
    if (typeof value !== 'string' || value === '') {
      throw new Error(`expected a non-empty string in "${key}"`);
    }
    return value;
  });
}

function docsLocationsFromJson(body: Record<string, unknown>): DocsLocations {
  const swaggerUi = optionalString(body, 'swaggerUi');
  const redoc = optionalString(body, 'redoc');
  const openapiJson = optionalString(body, 'openapiJson');
  return {
    ...(swaggerUi === undefined ? {} : { swaggerUi }),
    ...(redoc === undefined ? {} : { redoc }),
    ...(openapiJson === undefined ? {} : { openapiJson }),
  };
}

function docsAreaFromJson(body: unknown): DocsArea {
  if (!isRecord(body)) throw new Error('docs area must be an object');
  return {
    tag: requiredString(body, 'tag'),
    paths: requiredNumber(body, 'paths'),
    operations: requiredNumber(body, 'operations'),
    methods: stringList(body, 'methods'),
  };
}

function docsOperationFromJson(body: unknown): DocsOperation {
  if (!isRecord(body)) throw new Error('docs operation must be an object');
  return {
    method: requiredString(body, 'method'),
    path: requiredString(body, 'path'),
    operationId: requiredString(body, 'operationId'),
    summary: requiredString(body, 'summary'),
    description: requiredString(body, 'description'),
    responses: stringList(body, 'responses'),
  };
}

function docsShowcaseFromJson(body: unknown): DocsShowcase {
  if (!isRecord(body)) throw new Error('docs showcase must be an object');
  const requestSchema = optionalString(body, 'requestSchema');
  const successStatus = optionalString(body, 'successStatus');
  const successSchema = optionalString(body, 'successSchema');
  const validationSchema = optionalString(body, 'validationSchema');
  return {
    method: requiredString(body, 'method'),
    path: requiredString(body, 'path'),
    summary: requiredString(body, 'summary'),
    description: requiredString(body, 'description'),
    operationId: requiredString(body, 'operationId'),
    tags: stringList(body, 'tags'),
    ...(requestSchema === undefined ? {} : { requestSchema }),
    ...(successStatus === undefined ? {} : { successStatus }),
    ...(successSchema === undefined ? {} : { successSchema }),
    ...(validationSchema === undefined ? {} : { validationSchema }),
  };
}

/** Deserialize + validate the hub payload. */
export function docsHubFromJson(body: unknown): DocsHubDto {
  if (!isRecord(body)) throw new Error('docs hub must be an object');
  const showcase = body.showcase;
  return {
    infoTitle: requiredString(body, 'infoTitle'),
    infoVersion: requiredString(body, 'infoVersion'),
    openapiVersion: requiredString(body, 'openapiVersion'),
    docs: docsLocationsFromJson(requiredRecord(body, 'docs')),
    pathCount: requiredNumber(body, 'pathCount'),
    operationCount: requiredNumber(body, 'operationCount'),
    areaCount: requiredNumber(body, 'areaCount'),
    areas: requiredArray(body, 'areas').map(docsAreaFromJson),
    schemaCount: requiredNumber(body, 'schemaCount'),
    schemaNames: stringList(body, 'schemaNames'),
    postsOperations: requiredArray(body, 'postsOperations').map(docsOperationFromJson),
    ...(showcase === undefined ? {} : { showcase: docsShowcaseFromJson(showcase) }),
    reasoning: requiredString(body, 'reasoning'),
  };
}
