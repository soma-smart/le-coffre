import {
  clearPendingSharesVaultUnlockClearDelete,
  createVaultVaultSetupPost,
  getVaultStatusVaultStatusGet,
  lockVaultVaultLockPost,
  unlockVaultVaultUnlockPost,
  validateVaultSetupVaultValidateSetupPost,
} from '@/client/sdk.gen'
import type { CreateVaultInput, VaultRepository } from '@/application/ports/VaultRepository'
import type { VaultSetup, VaultState } from '@/domain/vault/Vault'
import { VaultDomainError } from '@/domain/vault/errors'

/**
 * Backend adapter for VaultRepository. Wraps every /vault/* SDK
 * function and maps snake_case DTOs into the domain shape. Errors
 * bubble up as VaultDomainError with the backend detail string; the
 * UI lives through state changes (LOCKED → PENDING_UNLOCK →
 * UNLOCKED) rather than specific error types.
 */
export class BackendVaultRepository implements VaultRepository {
  async getStatus(): Promise<VaultState> {
    const response = await getVaultStatusVaultStatusGet()
    this.throwIfError(response.error)
    if (!response.data) {
      return { status: 'NOT_SETUP', lastShareTimestamp: null }
    }
    return {
      status: response.data.status,
      lastShareTimestamp: response.data.last_share_timestamp ?? null,
    }
  }

  async createVault(input: CreateVaultInput): Promise<VaultSetup> {
    const response = await createVaultVaultSetupPost({
      body: { nb_shares: input.nbShares, threshold: input.threshold },
    })
    this.throwIfError(response.error)
    if (!response.data) throw new VaultDomainError('Empty response from create vault')
    return {
      setupId: response.data.setup_id,
      shares: response.data.shares.map((s) => s.secret),
    }
  }

  async validateSetup(setupId: string): Promise<void> {
    const response = await validateVaultSetupVaultValidateSetupPost({
      body: { setup_id: setupId },
    })
    this.throwIfError(response.error)
  }

  async unlock(shares: string[]): Promise<void> {
    const response = await unlockVaultVaultUnlockPost({ body: { shares } })
    this.throwIfError(response.error)
  }

  async lock(): Promise<void> {
    const response = await lockVaultVaultLockPost()
    this.throwIfError(response.error)
  }

  async clearPendingShares(): Promise<void> {
    const response = await clearPendingSharesVaultUnlockClearDelete()
    this.throwIfError(response.error)
  }

  private throwIfError(error: unknown): void {
    if (!error) return
    throw new VaultDomainError(extractDetail(error) ?? 'Vault operation failed')
  }
}

function extractDetail(error: unknown): string | null {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return null
}
