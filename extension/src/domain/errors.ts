/**
 * Every failure the UI can face, expressed in the product's terms rather than
 * HTTP's.
 *
 * This union is what keeps the popup at six screens instead of twenty: each
 * view renders a single `<StatusPanel :error>` and switches on `kind`, instead
 * of growing a bespoke branch per status code. Mapping from HTTP happens once,
 * in `api/http.ts`.
 */
export type AppError =
  /** No vault URL stored yet, first run. */
  | { kind: 'NOT_CONFIGURED' }
  /** Host permission missing or revoked. Recoverable, needs a user gesture. */
  | { kind: 'PERMISSION_MISSING'; origin: string }
  /** DNS/TCP/TLS failure, or a fetch made without host permission. */
  | { kind: 'NETWORK_UNREACHABLE' }
  /** Something answered, but it does not look like Le Coffre. */
  | { kind: 'NOT_A_VAULT' }
  /** It is Le Coffre, but too old to know about extension pairing. */
  | { kind: 'VAULT_TOO_OLD'; detail: string }
  /** 503 with code `vault_locked`, an admin must unlock it. */
  | { kind: 'VAULT_LOCKED' }
  /** 503 with code `starting`, migrations in progress, retry shortly. */
  | { kind: 'SERVER_STARTING' }
  /** 401, the token is gone for good; re-pairing is the only way back. */
  | { kind: 'AUTH_LOST'; reason: 'expired' | 'revoked' }
  /** 429. `retryAfterSeconds` comes from the Retry-After header. */
  | { kind: 'RATE_LIMITED'; retryAfterSeconds: number }
  /** 403, should be unreachable for a read-only client; log it loudly. */
  | { kind: 'FORBIDDEN' }
  /** 404, the entry vanished or access was revoked since the list was cached. */
  | { kind: 'NOT_FOUND' }
  | { kind: 'SERVER_ERROR'; status: number }
  /** The response parsed as JSON but not as the shape we expect. */
  | { kind: 'PROTOCOL_MISMATCH'; detail: string }

/** A handler result. Handlers never throw across the message boundary. */
export type Result<T> = { ok: true; data: T } | { ok: false; error: AppError }

export const ok = <T>(data: T): Result<T> => ({ ok: true, data })
export const err = <T = never>(error: AppError): Result<T> => ({ ok: false, error })
