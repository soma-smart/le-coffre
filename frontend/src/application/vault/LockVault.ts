import type { VaultRepository } from '@/application/ports/VaultRepository'

export class LockVaultUseCase {
  constructor(private readonly repository: VaultRepository) {}

  execute(): Promise<void> {
    return this.repository.lock()
  }
}
