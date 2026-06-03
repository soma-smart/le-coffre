import type { UserRepository } from '@/application/ports/UserRepository'

export interface PromoteUserToAdminCommand {
  userId: string
}

export class PromoteUserToAdminUseCase {
  constructor(private readonly repository: UserRepository) {}

  execute(command: PromoteUserToAdminCommand): Promise<void> {
    return this.repository.promoteToAdmin(command.userId)
  }
}
