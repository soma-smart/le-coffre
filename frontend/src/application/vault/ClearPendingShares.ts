import type { VaultRepository } from '@/application/ports/VaultRepository'

export class ClearPendingSharesUseCase {
  constructor(private readonly repository: VaultRepository) {}

  execute(): Promise<void> {
    return this.repository.clearPendingShares()
  }
}
