import type { User } from '@/domain/user/User'
import type { UserRepository } from '@/application/ports/UserRepository'

export interface GetUserCommand {
  userId: string
}

export class GetUserUseCase {
  constructor(private readonly repository: UserRepository) {}

  execute(command: GetUserCommand): Promise<User> {
    return this.repository.get(command.userId)
  }
}
