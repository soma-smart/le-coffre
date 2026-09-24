import type { User } from '@/domain/user/User'
import type { UserRepository } from '@/application/ports/UserRepository'

export interface SearchUsersCommand {
  query: string
}

export class SearchUsersUseCase {
  constructor(private readonly repository: UserRepository) {}

  execute(command: SearchUsersCommand): Promise<User[]> {
    return this.repository.search(command.query)
  }
}
