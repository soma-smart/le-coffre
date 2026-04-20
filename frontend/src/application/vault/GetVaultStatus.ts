import type { VaultState } from '@/domain/vault/Vault'
import type { VaultRepository } from '@/application/ports/VaultRepository'

export class GetVaultStatusUseCase {
  constructor(private readonly repository: VaultRepository) {}

  execute(): Promise<VaultState> {
    return this.repository.getStatus()
  }
}
