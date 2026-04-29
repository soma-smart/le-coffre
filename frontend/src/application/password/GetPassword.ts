import type { PasswordRepository } from '@/application/ports/PasswordRepository'

export interface GetPasswordCommand {
  passwordId: string
}

/**
 * Retrieves the decrypted secret for a single password. The repository
 * is responsible for enforcing access control (backend does the check
 * server-side; the adapter translates 403 → PasswordAccessDeniedError).
 */
export class GetPasswordUseCase {
  constructor(private readonly repository: PasswordRepository) {}

  execute(command: GetPasswordCommand): Promise<string> {
    return this.repository.getDecryptedValue(command.passwordId)
  }
}
