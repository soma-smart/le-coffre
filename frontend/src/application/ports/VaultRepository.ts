import type { SealedShare } from '@/domain/vault/ShareLink'
import type { ShareLinksOverview } from '@/domain/vault/ShareLinksOverview'
import type { VaultSetup, VaultState } from '@/domain/vault/Vault'

export interface CreateVaultInput {
  nbShares: number
  threshold: number
}

export interface VaultRepository {
  /**
   * With an unlock session id, a locked vault reports PENDING_UNLOCK when
   * that session already holds shares. Without one, it is simply LOCKED.
   */
  getStatus(unlockSessionId?: string): Promise<VaultState>
  createVault(input: CreateVaultInput): Promise<VaultSetup>
  validateSetup(setupId: string): Promise<void>
  unlock(unlockSessionId: string, shares: string[]): Promise<void>
  lock(): Promise<void>
  /** Anonymous. Reopenable for a short while after the first opening, until acknowledged. */
  retrieveSealedShare(lookupHash: string): Promise<SealedShare>
  /** Anonymous. Deletes the link for good; only a key derived from the token is accepted. */
  acknowledgeShare(lookupHash: string, ackKey: string): Promise<void>
  /**
   * Administrators only. Where each link of the current setup stands; throws
   * VaultNotConfiguredError when no vault exists yet.
   */
  getShareLinksOverview(): Promise<ShareLinksOverview>
}
