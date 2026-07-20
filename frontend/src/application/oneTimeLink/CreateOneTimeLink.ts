import type { OneTimeLinkRepository } from '@/application/ports/OneTimeLinkRepository'
import type { CreatedOneTimeLink } from '@/domain/oneTimeLink/OneTimeLink'

export interface CreateOneTimeLinkCommand {
  passwordId: string
  lifetimeSeconds?: number
}

export class CreateOneTimeLinkUseCase {
  constructor(private readonly repository: OneTimeLinkRepository) {}

  async execute(command: CreateOneTimeLinkCommand): Promise<CreatedOneTimeLink> {
    return this.repository.create(command.passwordId, command.lifetimeSeconds)
  }
}
