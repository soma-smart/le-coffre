import type { VaultSetup } from '@/domain/vault/Vault'
import type { VaultRepository } from '@/application/ports/VaultRepository'
import { VaultThresholdInvalidError } from '@/domain/vault/errors'

export interface CreateVaultCommand {
  nbShares: number
  threshold: number
}

/**
 * Kicks off the Shamir-backed vault setup. UX-level guardrails:
 * threshold must be at least 2 and at most nbShares. The server
 * enforces the full cryptographic constraints.
 */
export class CreateVaultUseCase {
  constructor(private readonly repository: VaultRepository) {}

  async execute(command: CreateVaultCommand): Promise<VaultSetup> {
    if (command.threshold < 2 || command.threshold > command.nbShares) {
      throw new VaultThresholdInvalidError()
    }
    return this.repository.createVault({
      nbShares: command.nbShares,
      threshold: command.threshold,
    })
  }
}
