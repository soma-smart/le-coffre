import type { PasswordRepository } from '@/application/ports/PasswordRepository'
import { PasswordGroupRequiredError, ShareExpirationInvalidError } from '@/domain/password/errors'

export interface SharePasswordCommand {
  passwordId: string
  groupId: string
  /** ISO date the share lapses on. Omit or pass null to share permanently. */
  expiresAt?: string | null
}

/**
 * Grants a group access to a password, permanently or until `expiresAt`.
 *
 * UX-level checks: a group id must be supplied, and a deadline must parse and
 * be in the future. The backend enforces that the requesting user owns the
 * password's group (403 → PasswordAccessDeniedError) and caps how far out a
 * deadline may sit (400 → ShareExpirationInvalidError).
 */
export class SharePasswordUseCase {
  constructor(private readonly repository: PasswordRepository) {}

  async execute(command: SharePasswordCommand, now: Date = new Date()): Promise<void> {
    if (!command.groupId) throw new PasswordGroupRequiredError()

    const expiresAt = command.expiresAt ?? null
    if (expiresAt !== null) {
      const deadline = new Date(expiresAt)
      if (Number.isNaN(deadline.getTime())) throw new ShareExpirationInvalidError()
      if (deadline <= now) {
        throw new ShareExpirationInvalidError('The expiry date must be in the future')
      }
    }

    await this.repository.share(command.passwordId, command.groupId, expiresAt)
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
