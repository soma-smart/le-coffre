import type { OneTimeLinkRepository } from '@/application/ports/OneTimeLinkRepository'
import type { AuditedOneTimeLinkPage } from '@/domain/oneTimeLink/OneTimeLink'

/** The links the signed-in user issued, wherever they point. */
export class ListMyOneTimeLinksUseCase {
  constructor(private readonly repository: OneTimeLinkRepository) {}

  async execute(includeInactive = false): Promise<AuditedOneTimeLinkPage> {
    return this.repository.listMine(includeInactive)
  }
}
