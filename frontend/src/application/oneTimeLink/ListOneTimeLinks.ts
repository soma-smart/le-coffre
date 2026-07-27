import type { OneTimeLinkRepository } from '@/application/ports/OneTimeLinkRepository'
import type { OneTimeLinkPage } from '@/domain/oneTimeLink/OneTimeLink'

export class ListOneTimeLinksUseCase {
  constructor(private readonly repository: OneTimeLinkRepository) {}

  async execute(passwordId: string, includeInactive = false): Promise<OneTimeLinkPage> {
    return this.repository.listForPassword(passwordId, includeInactive)
  }
}
