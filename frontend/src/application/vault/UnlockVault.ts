import type { VaultRepository } from '@/application/ports/VaultRepository'
import { VaultSharesRequiredError } from '@/domain/vault/errors'

export interface UnlockVaultCommand {
  shares: string[]
}

/**
 * Submits Shamir shares to the backend. UX guard: at least one share
 * must be provided, each must be non-blank. The server verifies the
 * cryptographic threshold — partial submissions keep the vault in
 * PENDING_UNLOCK until enough shares accumulate.
 */
export class UnlockVaultUseCase {
  constructor(private readonly repository: VaultRepository) {}

  async execute(command: UnlockVaultCommand): Promise<void> {
    const trimmed = command.shares.map((s) => s.trim()).filter(Boolean)
    if (trimmed.length === 0) throw new VaultSharesRequiredError()
    await this.repository.unlock(trimmed)
  }
}
