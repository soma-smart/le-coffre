import type { OneTimeLinkRepository } from '@/application/ports/OneTimeLinkRepository'
import type { RevealedSecret } from '@/domain/oneTimeLink/OneTimeLink'
import { OneTimeLinkTokenRequiredError } from '@/domain/oneTimeLink/errors'

export class ConsumeOneTimeLinkUseCase {
  constructor(private readonly repository: OneTimeLinkRepository) {}

  async execute(token: string): Promise<RevealedSecret> {
    if (!token.trim()) throw new OneTimeLinkTokenRequiredError()
    return this.repository.consume(token)
  }
}
