import type { OneTimeLinkRepository } from '@/application/ports/OneTimeLinkRepository'
import type { AuditedOneTimeLinkPage } from '@/domain/oneTimeLink/OneTimeLink'

/** Every link in the vault, for an administrator. */
export class ListAllOneTimeLinksUseCase {
  constructor(private readonly repository: OneTimeLinkRepository) {}

  async execute(includeInactive = false): Promise<AuditedOneTimeLinkPage> {
    return this.repository.listAll(includeInactive)
  }
}
