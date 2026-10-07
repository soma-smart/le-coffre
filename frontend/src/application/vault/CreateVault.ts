import type { VaultSetup } from '@/domain/vault/Vault'
import type { VaultRepository } from '@/application/ports/VaultRepository'
import type { ShareLinkCipher } from '@/application/ports/ShareLinkCipher'
import { isValidShamirConfig } from '@/domain/vault/ShamirConfig'
import { ShareLinksUnsupportedError, VaultThresholdInvalidError } from '@/domain/vault/errors'

export interface CreateVaultCommand {
  nbShares: number
  threshold: number
}

/**
 * Kicks off the Shamir-backed vault setup. UX-level guardrails match the
 * full SSS invariants from domain/vault/ShamirConfig.ts; the server still
 * enforces the authoritative cryptographic constraints.
 */
export class CreateVaultUseCase {
  constructor(
    private readonly repository: VaultRepository,
    private readonly shareLinkCipher: ShareLinkCipher,
  ) {}

  /**
   * Whether this origin can hand shares out by link. Checked before anything
   * is sent: a vault set up with links its custodians cannot open is lost.
   */
  canIssueShareLinks(): boolean {
    return this.shareLinkCipher.isSupported()
  }

  async execute(command: CreateVaultCommand): Promise<VaultSetup> {
    if (!this.canIssueShareLinks()) throw new ShareLinksUnsupportedError()
    if (!isValidShamirConfig({ shares: command.nbShares, threshold: command.threshold })) {
      throw new VaultThresholdInvalidError()
    }
    return this.repository.createVault({
      nbShares: command.nbShares,
      threshold: command.threshold,
    })
  }
}
