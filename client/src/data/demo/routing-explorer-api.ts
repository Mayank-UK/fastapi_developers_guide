import type { AppConfig } from '../../core/config/app-config';
import { guardedApiCall, guardedGetJson, parseDto } from '../../core/error-handling/guards';
import {
  routingExplorerDtoFromJson,
  type RoutingExplorerDto,
} from './routing-explorer-dto';
import type { RoutingExplorerRequest } from '../../domain/demo/routing-explorer';

/**
 * RoutingExplorerApi — the transport for GET /api/demo/routing/explorer,
 * in the same style as the other data/demo adapters: the simulated request
 * line travels as the endpoint's two query parameters (method, path), each
 * encoded so an embedded ? in the path survives as data rather than
 * splitting the URL. The shared guarded fetch pipeline maps every
 * transport failure (network down / non-JSON / non-2xx envelope) to typed
 * AppExceptions, then the JSON payload is validated into a DTO.
 */

const DEMO_PATH = '/demo/routing/explorer';

export class RoutingExplorerApi {
  private readonly config: AppConfig;

  constructor(config: AppConfig) {
    this.config = config;
  }

  /** GET {apiBaseUrl}/demo/routing/explorer — resolve the simulated request. */
  async resolve(request: RoutingExplorerRequest): Promise<RoutingExplorerDto> {
    const query = `?method=${encodeURIComponent(request.method)}&path=${encodeURIComponent(request.path)}`;
    return guardedApiCall(async () => {
      const { body, status } = await guardedGetJson(this.config, `${DEMO_PATH}${query}`);
      return parseDto(body, status, routingExplorerDtoFromJson);
    });
  }
}
