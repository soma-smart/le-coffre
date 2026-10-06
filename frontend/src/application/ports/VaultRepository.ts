import type { SealedShare } from '@/domain/vault/ShareLink'
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
  /** Anonymous and single use: the server wipes the sealed share once handed out. */
  retrieveSealedShare(lookupHash: string): Promise<SealedShare>
}
