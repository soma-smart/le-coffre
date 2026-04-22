import type { UserRepository } from '@/application/ports/UserRepository'
import {
  UserEmailRequiredError,
  UserNameRequiredError,
  UserUsernameRequiredError,
} from '@/domain/user/errors'

export interface UpdateUserCommand {
  id: string
  username: string
  email: string
  name: string
}

export class UpdateUserUseCase {
  constructor(private readonly repository: UserRepository) {}

  async execute(command: UpdateUserCommand): Promise<void> {
    if (!command.username.trim()) throw new UserUsernameRequiredError()
    if (!command.email.trim()) throw new UserEmailRequiredError()
    if (!command.name.trim()) throw new UserNameRequiredError()

    await this.repository.update({
      id: command.id,
      username: command.username.trim(),
      email: command.email.trim(),
      name: command.name.trim(),
    })
  }
}
