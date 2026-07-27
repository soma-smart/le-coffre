import type { OneTimeLinkRepository } from '@/application/ports/OneTimeLinkRepository'

/** Revoke any link, whoever issued it. */
export class RevokeOneTimeLinkAsAdminUseCase {
  constructor(private readonly repository: OneTimeLinkRepository) {}

  async execute(linkId: string): Promise<void> {
    return this.repository.revokeAsAdmin(linkId)
  }
}
