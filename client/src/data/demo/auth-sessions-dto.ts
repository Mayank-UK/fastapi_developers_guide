import type {
  CookieInstruction,
  SessionInspection,
  SessionLoginOutcome,
  SessionLogoutOutcome,
  SessionRosterEntry,
  SessionsPanel,
} from '../../domain/demo/auth-sessions';
import {
  isRecord,
  requiredArray,
  requiredBoolean,
  requiredNumber,
  requiredRecord,
  requiredString,
} from '../content/validate';

/**
 * AuthSessionsDTO — the wire/transport shapes of the cookie lab: the roster
 * payload plus the three action outcomes. The cookie instruction rides as a
 * nested record (its flags are part of the lab's teaching surface).
 */

function cookieFromJson(value: unknown): CookieInstruction {
  if (!isRecord(value)) throw new Error('cookie instruction must be an object');
  const samesite = requiredString(value, 'samesite');
  if (samesite !== 'lax' && samesite !== 'strict' && samesite !== 'none') {
    throw new Error(`unknown samesite: ${samesite}`);
  }
  return {
    name: requiredString(value, 'name'),
    value: requiredString(value, 'value'),
    maxAgeSeconds: requiredNumber(value, 'maxAgeSeconds'),
    path: requiredString(value, 'path'),
    httponly: requiredBoolean(value, 'httponly'),
    samesite,
    secure: requiredBoolean(value, 'secure'),
  };
}

function rosterEntryFromJson(value: unknown): SessionRosterEntry {
  if (!isRecord(value)) throw new Error('session roster entry must be an object');
  return {
    sessionIdPreview: requiredString(value, 'sessionIdPreview'),
    username: requiredString(value, 'username'),
    displayName: requiredString(value, 'displayName'),
    issuedAt: requiredString(value, 'issuedAt'),
    expiresAt: requiredString(value, 'expiresAt'),
  };
}

/** Deserialize + validate the roster payload. */
export function sessionsPanelFromJson(body: unknown): SessionsPanel {
  if (!isRecord(body)) throw new Error('sessions panel must be an object');
  return {
    cookieName: requiredString(body, 'cookieName'),
    cookiePath: requiredString(body, 'cookiePath'),
    maxAgeSeconds: requiredNumber(body, 'maxAgeSeconds'),
    flagsSet: requiredArray(body, 'flagsSet').map((v) => {
      if (typeof v !== 'string') throw new Error('flagsSet items must be strings');
      return v;
    }),
    secureNote: requiredString(body, 'secureNote'),
    sealNote: requiredString(body, 'sealNote'),
    activeSessions: requiredArray(body, 'activeSessions').map(rosterEntryFromJson),
    loginEndpoint: requiredString(body, 'loginEndpoint'),
    meEndpoint: requiredString(body, 'meEndpoint'),
    logoutEndpoint: requiredString(body, 'logoutEndpoint'),
    reasoning: requiredString(body, 'reasoning'),
  };
}

/** Deserialize + validate the login outcome (cookie instruction included). */
export function sessionLoginFromJson(body: unknown): SessionLoginOutcome {
  if (!isRecord(body)) throw new Error('session login outcome must be an object');
  return {
    username: requiredString(body, 'username'),
    displayName: requiredString(body, 'displayName'),
    scopes: requiredArray(body, 'scopes').map((v) => {
      if (typeof v !== 'string') throw new Error('scopes items must be strings');
      return v;
    }),
    cookie: cookieFromJson(requiredRecord(body, 'cookie')),
    cookieValueAnatomy: requiredString(body, 'cookieValueAnatomy'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the /me inspection. */
export function sessionInspectionFromJson(body: unknown): SessionInspection {
  if (!isRecord(body)) throw new Error('session inspection must be an object');
  return {
    sessionIdPreview: requiredString(body, 'sessionIdPreview'),
    username: requiredString(body, 'username'),
    displayName: requiredString(body, 'displayName'),
    scopes: requiredArray(body, 'scopes').map((v) => {
      if (typeof v !== 'string') throw new Error('scopes items must be strings');
      return v;
    }),
    issuedAt: requiredString(body, 'issuedAt'),
    expiresAt: requiredString(body, 'expiresAt'),
    detail: requiredString(body, 'detail'),
  };
}

/** Deserialize + validate the logout outcome. */
export function sessionLogoutFromJson(body: unknown): SessionLogoutOutcome {
  if (!isRecord(body)) throw new Error('session logout outcome must be an object');
  return {
    revoked: requiredBoolean(body, 'revoked'),
    cookie: cookieFromJson(requiredRecord(body, 'cookie')),
    detail: requiredString(body, 'detail'),
  };
}
