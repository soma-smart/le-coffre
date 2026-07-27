import type { OneTimeLinkRepository } from '@/application/ports/OneTimeLinkRepository'

export class RevokeOneTimeLinkUseCase {
  constructor(private readonly repository: OneTimeLinkRepository) {}

  async execute(linkId: string): Promise<void> {
    return this.repository.revoke(linkId)
  }
}
