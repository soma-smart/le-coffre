import type { UserRepository } from '@/application/ports/UserRepository'

export interface DeleteUserCommand {
  userId: string
}

export class DeleteUserUseCase {
  constructor(private readonly repository: UserRepository) {}

  execute(command: DeleteUserCommand): Promise<void> {
    return this.repository.delete(command.userId)
  }
}
