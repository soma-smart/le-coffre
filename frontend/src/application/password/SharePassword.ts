import type { PasswordRepository } from '@/application/ports/PasswordRepository'
import { PasswordGroupRequiredError } from '@/domain/password/errors'

export interface SharePasswordCommand {
  passwordId: string
  groupId: string
}

/**
 * Grants a group access to a password. UX-level check: a group id must
 * be supplied. The backend enforces that the requesting user owns the
 * password's group; that failure comes back as 403 →
 * PasswordAccessDeniedError.
 */
export class SharePasswordUseCase {
  constructor(private readonly repository: PasswordRepository) {}

  async execute(command: SharePasswordCommand): Promise<void> {
    if (!command.groupId) throw new PasswordGroupRequiredError()
    await this.repository.share(command.passwordId, command.groupId)
  }
}

/**
 * Revokes a group's access to a password. Same UX-level check; the
 * backend enforces authorisation.
 */
export class UnsharePasswordUseCase {
  constructor(private readonly repository: PasswordRepository) {}

  async execute(command: SharePasswordCommand): Promise<void> {
    if (!command.groupId) throw new PasswordGroupRequiredError()
    await this.repository.unshare(command.passwordId, command.groupId)
  }
}
