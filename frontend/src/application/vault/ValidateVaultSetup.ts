import type { VaultRepository } from '@/application/ports/VaultRepository'
import { VaultSetupIdRequiredError } from '@/domain/vault/errors'

export interface ValidateVaultSetupCommand {
  setupId: string
}

export class ValidateVaultSetupUseCase {
  constructor(private readonly repository: VaultRepository) {}

  async execute(command: ValidateVaultSetupCommand): Promise<void> {
    if (!command.setupId) throw new VaultSetupIdRequiredError()
    await this.repository.validateSetup(command.setupId)
  }
}
