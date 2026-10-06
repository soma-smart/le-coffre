import {
  clearPendingSharesVaultUnlockClearDelete,
  createVaultVaultSetupPost,
  getVaultStatusVaultStatusGet,
  lockVaultVaultLockPost,
  retrieveShareLinkVaultShareLinksRetrievePost,
  unlockVaultVaultUnlockPost,
  validateVaultSetupVaultValidateSetupPost,
} from '@/client/sdk.gen'
import type { CreateVaultInput, VaultRepository } from '@/application/ports/VaultRepository'
import type { SealedShare } from '@/domain/vault/ShareLink'
import type { VaultSetup, VaultState } from '@/domain/vault/Vault'
import { ShareLinkUnusableError, VaultDomainError } from '@/domain/vault/errors'

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
    // An empty body on a 200 response is a server bug, not "vault not
    // configured" — coercing to NOT_SETUP would redirect a configured
    // admin into the bootstrap wizard.
    if (!response.data) {
      throw new VaultDomainError('Empty response from /vault/status')
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
      shareLinks: response.data.share_links.map((link) => ({
        shareIndex: link.share_index,
        token: link.token,
        expiresAt: link.expires_at,
      })),
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

  async retrieveSealedShare(lookupHash: string): Promise<SealedShare> {
    const response = await retrieveShareLinkVaultShareLinksRetrievePost({
      body: { lookup_hash: lookupHash },
    })
    if (response.error) {
      // 404 covers unknown, expired and already retrieved alike; the backend
      // keeps them indistinguishable on purpose. 400 is a hash that no link
      // could have produced, which to the custodian is the same dead link.
      const status = response.response?.status
      if (status === 404 || status === 400) throw new ShareLinkUnusableError()
      this.throwIfError(response.error)
    }
    if (!response.data) throw new ShareLinkUnusableError()
    return { shareIndex: response.data.share_index, sealedShare: response.data.sealed_share }
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
