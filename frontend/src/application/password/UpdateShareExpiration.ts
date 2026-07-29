import type { PasswordRepository } from '@/application/ports/PasswordRepository'
import { PasswordGroupRequiredError, ShareExpirationInvalidError } from '@/domain/password/errors'

export interface UpdateShareExpirationCommand {
  passwordId: string
  groupId: string
  /** ISO date the share lapses on; null makes it permanent. */
  expiresAt: string | null
}

/**
 * Retimes an existing share: extend it, shorten it, or lift the deadline.
 *
 * UX-level checks only: a group id, and a deadline that parses. The backend
 * owns the real rules (ownership, the maximum lifetime, and whether the share
 * still exists), and those come back as 403 / 400 / 404.
 *
 * A deadline already in the past is rejected here rather than sent, because the
 * one legitimate reason to set one is a clock the user cannot see. Extending a
 * share that has *already* expired is a different thing and stays allowed: the
 * new date is in the future.
 */
export class UpdateShareExpirationUseCase {
  constructor(private readonly repository: PasswordRepository) {}

  async execute(command: UpdateShareExpirationCommand, now: Date = new Date()): Promise<void> {
    if (!command.groupId) throw new PasswordGroupRequiredError()

    if (command.expiresAt !== null) {
      const deadline = new Date(command.expiresAt)
      if (Number.isNaN(deadline.getTime())) throw new ShareExpirationInvalidError()
      if (deadline <= now) {
        throw new ShareExpirationInvalidError('The expiry date must be in the future')
      }
    }

    await this.repository.updateShareExpiration(
      command.passwordId,
      command.groupId,
      command.expiresAt,
    )
  }
}
