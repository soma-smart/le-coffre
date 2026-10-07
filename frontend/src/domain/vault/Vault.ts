import type { IssuedShareLink } from './ShareLink'

/**
 * Vault domain types. Pure TypeScript — no Vue, no fetch, no SDK.
 *
 * The vault has one piece of serialisable state (its status +
 * optional last-share timestamp) and one one-shot output from the
 * setup flow (setup id + one share link per Shamir share).
 */

export type VaultStatus =
  'LOCKED' | 'UNLOCKED' | 'NOT_SETUP' | 'PENDING' | 'SETUPED' | 'PENDING_UNLOCK'

export interface VaultState {
  status: VaultStatus
  /** Timestamp of the most recent share submission, when partially unlocked. */
  lastShareTimestamp: string | null
}

export interface VaultSetup {
  setupId: string
  /**
   * One link per share, returned once by create. The shares
   * themselves never reach the admin's screen: each custodian opens their own.
   */
  shareLinks: IssuedShareLink[]
}

export function isVaultLocked(state: VaultState | null): boolean {
  return state?.status === 'LOCKED' || state?.status === 'PENDING_UNLOCK'
}

export function isVaultSetup(state: VaultState | null): boolean {
  return !!state && state.status !== 'NOT_SETUP'
}
