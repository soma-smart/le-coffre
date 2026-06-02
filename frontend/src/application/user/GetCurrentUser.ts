import type { User } from '@/domain/user/User'
import type { UserRepository } from '@/application/ports/UserRepository'

/**
 * Resolves the currently authenticated user, or null when no session
 * is established (the backend returns 401 in that case, which the
 * adapter translates to null so the router can route to /login).
 */
export class GetCurrentUserUseCase {
  constructor(private readonly repository: UserRepository) {}

  execute(): Promise<User | null> {
    return this.repository.getCurrent()
  }
}
