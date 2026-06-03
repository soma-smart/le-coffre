import type { UserRepository } from '@/application/ports/UserRepository'
import { UserPasswordMustBeDifferentError, UserPasswordRequiredError } from '@/domain/user/errors'

export interface UpdateUserPasswordCommand {
  oldPassword: string
  newPassword: string
}

/**
 * Changes the current user's password. UX-level checks: both fields
 * required, new must differ from old. Server verifies the old password
 * hash — that failure surfaces as a UserDomainError with the backend
 * detail string.
 */
export class UpdateUserPasswordUseCase {
  constructor(private readonly repository: UserRepository) {}

  async execute(command: UpdateUserPasswordCommand): Promise<void> {
    if (!command.oldPassword || !command.newPassword) {
      throw new UserPasswordRequiredError()
    }
    if (command.oldPassword === command.newPassword) {
      throw new UserPasswordMustBeDifferentError()
    }

    await this.repository.updatePassword({
      oldPassword: command.oldPassword,
      newPassword: command.newPassword,
    })
  }
}
