import type { OneTimeLinkRepository } from '@/application/ports/OneTimeLinkRepository'
import type { CreatedOneTimeLink } from '@/domain/oneTimeLink/OneTimeLink'

export interface CreateOneTimeLinkCommand {
  passwordId: string
  lifetimeSeconds?: number
  /** Email the creator when the link is opened. Off unless asked for. */
  notifyOnRead?: boolean
  /** Email the creator if the link expires without being opened. Off unless asked for. */
  notifyOnExpiry?: boolean
}

export class CreateOneTimeLinkUseCase {
  constructor(private readonly repository: OneTimeLinkRepository) {}

  async execute(command: CreateOneTimeLinkCommand): Promise<CreatedOneTimeLink> {
    return this.repository.create(command.passwordId, {
      lifetimeSeconds: command.lifetimeSeconds,
      notifyOnRead: command.notifyOnRead ?? false,
      notifyOnExpiry: command.notifyOnExpiry ?? false,
    })
  }
}
