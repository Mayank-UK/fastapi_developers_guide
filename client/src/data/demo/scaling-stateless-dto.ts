import type {
  PlacementRow,
  ReplicaStepRow,
  ScalingFactRow,
  StatelessPanel,
} from '../../domain/demo/scaling-stateless';
import { isRecord, requiredArray, requiredNumber, requiredString } from '../content/validate';

/**
 * ScalingStatelessDTO — the wire/transport shape of the statelessness
 * panel. Every field is always present on this payload; validation
 * happens at the boundary so a drifted wire fails HERE, not in a view.
 */

function factRowFromJson(value: unknown): ScalingFactRow {
  if (!isRecord(value)) throw new Error('scaling fact row must be an object');
  return {
    id: requiredString(value, 'id'),
    label: requiredString(value, 'label'),
    value: requiredString(value, 'value'),
  };
}

function replicaStepFromJson(value: unknown): ReplicaStepRow {
  if (!isRecord(value)) throw new Error('replica step row must be an object');
  return {
    step: requiredNumber(value, 'step'),
    side: requiredString(value, 'side'),
    label: requiredString(value, 'label'),
    detail: requiredString(value, 'detail'),
    observed: requiredString(value, 'observed'),
  };
}

function placementRowFromJson(value: unknown): PlacementRow {
  if (!isRecord(value)) throw new Error('placement row must be an object');
  return {
    id: requiredString(value, 'id'),
    state: requiredString(value, 'state'),
    holder: requiredString(value, 'holder'),
    placement: requiredString(value, 'placement'),
    where: requiredString(value, 'where'),
    restart: requiredString(value, 'restart'),
    evidence: requiredString(value, 'evidence'),
  };
}

/** Deserialize + validate the statelessness panel (process, round, verdicts, inventory). */
export function statelessPanelFromJson(body: unknown): StatelessPanel {
  if (!isRecord(body)) throw new Error('stateless panel must be an object');
  return {
    process: requiredArray(body, 'process').map(factRowFromJson),
    replicaRound: requiredArray(body, 'replicaRound').map(replicaStepFromJson),
    verdicts: requiredArray(body, 'verdicts').map(factRowFromJson),
    inventory: requiredArray(body, 'inventory').map(placementRowFromJson),
    honestyNote: requiredString(body, 'honestyNote'),
  };
}
