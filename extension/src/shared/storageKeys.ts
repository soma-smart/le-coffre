/**
 * Where each piece of state lives, and why.
 *
 * `local` persists to disk and survives a browser restart. `session` is
 * memory-backed, cleared when the browser closes, and unreachable from content
 * scripts.
 */

/** Survives a restart. Configuration, plus the bearer token. */
export const LOCAL_KEYS = {
  vaultUrl: 'vaultUrl',
  /** The exact granted string, so contains() and remove() use the same value. */
  apiMatchPattern: 'apiMatchPattern',
  selectedGroupId: 'selectedGroupId',
  deviceName: 'deviceName',
  settings: 'settings',
  /**
   * The bearer credential.
   *
   * In `local` deliberately. `session` would clear it on every browser restart,
   * meaning the user re-pairs daily, and it buys nothing in confidentiality:
   * anyone who can read storage.local can equally attach a debugger to this
   * extension. What actually protects this token is its scope (read-only,
   * never admin), its 30-day expiry, and being revocable from the web app.
   */
  token: 'token',
  tokenExpiresAt: 'tokenExpiresAt',
} as const

/** Dies with the browser session. Never anything that must outlive it. */
export const SESSION_KEYS = {
  /**
   * Cached entry metadata. In `session` rather than `local` because `login` and
   * `url` together enumerate which sites the user has accounts on, and that
   * list has no business being on disk.
   */
  entriesCache: 'entriesCache',
  lastActivityAt: 'lastActivityAt',
  /** The in-flight pairing: its code, verifier and deadline. */
  pairing: 'pairing',
} as const

/** Alarm names. MV3 kills the worker on idle, so setTimeout is not an option. */
export const ALARMS = {
  autoLock: 'auto-lock',
  pairingPoll: 'pairing-poll',
} as const
