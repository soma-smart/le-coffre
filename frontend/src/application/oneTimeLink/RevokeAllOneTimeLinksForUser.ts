import type { OneTimeLinkRepository } from '@/application/ports/OneTimeLinkRepository'
import { OneTimeLinkUserRequiredError } from '@/domain/oneTimeLink/errors'

/**
 * Cut every live link one user issued. Returns how many were actually cut, so
 * the UI can report a number rather than guess.
 */
export class RevokeAllOneTimeLinksForUserUseCase {
  constructor(private readonly repository: OneTimeLinkRepository) {}

  async execute(userId: string): Promise<number> {
    // Guard against an unselected dropdown reaching the API: without a user id
    // the request would target a path segment that is simply missing.
    if (!userId.trim()) throw new OneTimeLinkUserRequiredError()
    return this.repository.revokeAllForUser(userId)
  }
}
