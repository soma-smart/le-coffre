import type { VaultRepository } from '@/application/ports/VaultRepository'
import { isValidUnlockSessionId } from '@/domain/vault/UnlockSession'
import { VaultSharesRequiredError, VaultUnlockSessionInvalidError } from '@/domain/vault/errors'

export interface UnlockVaultCommand {
  unlockSessionId: string
  shares: string[]
}

/**
 * Submits Shamir shares to an unlock session on the backend. UX guard: at
 * least one share must be provided, each must be non-blank. The server
 * verifies the cryptographic threshold — partial submissions keep the
 * session in PENDING_UNLOCK until enough shares accumulate in it.
 */
export class UnlockVaultUseCase {
  constructor(private readonly repository: VaultRepository) {}

  async execute(command: UnlockVaultCommand): Promise<void> {
    if (!isValidUnlockSessionId(command.unlockSessionId)) throw new VaultUnlockSessionInvalidError()
    const trimmed = command.shares.map((s) => s.trim()).filter(Boolean)
    if (trimmed.length === 0) throw new VaultSharesRequiredError()
    await this.repository.unlock(command.unlockSessionId, trimmed)
  }
}
