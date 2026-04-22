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
}
