import type { User } from '@/domain/user/User'
import type { UserRepository } from '@/application/ports/UserRepository'

export class ListUsersUseCase {
  constructor(private readonly repository: UserRepository) {}

  execute(): Promise<User[]> {
    return this.repository.list()
  }
}
