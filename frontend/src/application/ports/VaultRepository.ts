import type { SealedShare } from '@/domain/vault/ShareLink'
import type { VaultSetup, VaultState } from '@/domain/vault/Vault'

export interface CreateVaultInput {
  nbShares: number
  threshold: number
}

export interface VaultRepository {
  getStatus(): Promise<VaultState>
  createVault(input: CreateVaultInput): Promise<VaultSetup>
  validateSetup(setupId: string): Promise<void>
  unlock(shares: string[]): Promise<void>
  lock(): Promise<void>
  clearPendingShares(): Promise<void>
  /** Anonymous. Reopenable for a short while after the first opening, until acknowledged. */
  retrieveSealedShare(lookupHash: string): Promise<SealedShare>
  /** Anonymous. Deletes the link for good; only a key derived from the token is accepted. */
  acknowledgeShare(lookupHash: string, ackKey: string): Promise<void>
}
