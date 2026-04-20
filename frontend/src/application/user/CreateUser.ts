import type { UserRepository } from '@/application/ports/UserRepository'
import {
  UserEmailRequiredError,
  UserNameRequiredError,
  UserPasswordRequiredError,
  UserUsernameRequiredError,
} from '@/domain/user/errors'

export interface CreateUserCommand {
  username: string
  email: string
  name: string
  password: string
}

/**
 * Admin-only use case. Performs UX-level validation; server-side
 * authorisation (current user must be admin, unique email/username)
 * stays backend-side.
 */
export class CreateUserUseCase {
  constructor(private readonly repository: UserRepository) {}

  async execute(command: CreateUserCommand): Promise<string> {
    if (!command.username.trim()) throw new UserUsernameRequiredError()
    if (!command.email.trim()) throw new UserEmailRequiredError()
    if (!command.name.trim()) throw new UserNameRequiredError()
    if (!command.password) throw new UserPasswordRequiredError()

    return this.repository.create({
      username: command.username.trim(),
      email: command.email.trim(),
      name: command.name.trim(),
      password: command.password,
    })
  }
}
