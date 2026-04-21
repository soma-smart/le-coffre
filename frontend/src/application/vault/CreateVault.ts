import type { VaultSetup } from '@/domain/vault/Vault'
import type { VaultRepository } from '@/application/ports/VaultRepository'
import { isValidShamirConfig } from '@/domain/vault/ShamirConfig'
import { VaultThresholdInvalidError } from '@/domain/vault/errors'

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
  constructor(private readonly repository: VaultRepository) {}

  async execute(command: CreateVaultCommand): Promise<VaultSetup> {
    if (!isValidShamirConfig({ shares: command.nbShares, threshold: command.threshold })) {
      throw new VaultThresholdInvalidError()
    }
    return this.repository.createVault({
      nbShares: command.nbShares,
      threshold: command.threshold,
    })
  }
}
