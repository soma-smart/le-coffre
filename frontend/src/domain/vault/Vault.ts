/**
 * Vault domain types. Pure TypeScript — no Vue, no fetch, no SDK.
 *
 * The vault has one piece of serialisable state (its status +
 * optional last-share timestamp) and one one-shot output from the
 * setup flow (setup id + Shamir shares returned to the admin once).
 */

export type VaultStatus =
  | 'LOCKED'
  | 'UNLOCKED'
  | 'NOT_SETUP'
  | 'PENDING'
  | 'SETUPED'
  | 'PENDING_UNLOCK'

export interface VaultState {
  status: VaultStatus
  /** Timestamp of the most recent share submission, when partially unlocked. */
  lastShareTimestamp: string | null
}

export interface VaultSetup {
  setupId: string
  /** Plain share secrets, returned once by create — the user must store them. */
  shares: string[]
}

export function isVaultLocked(state: VaultState | null): boolean {
  return state?.status === 'LOCKED' || state?.status === 'PENDING_UNLOCK'
}

export function isVaultSetup(state: VaultState | null): boolean {
  return !!state && state.status !== 'NOT_SETUP'
}
