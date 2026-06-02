import type { PasswordRepository } from '@/application/ports/PasswordRepository'
import { isValidPasswordUrl } from '@/domain/password/Password'
import { PasswordNameRequiredError, PasswordUrlInvalidError } from '@/domain/password/errors'

export interface UpdatePasswordCommand {
  id: string
  name: string
  password?: string | null
  folder?: string | null
  login?: string | null
  url?: string | null
}

/**
 * Partial update. Only `name` is required; every other field is
 * optional. Passing `null` for the secret means "leave the current
 * value unchanged" (how the edit form works in the UI).
 */
export class UpdatePasswordUseCase {
  constructor(private readonly repository: PasswordRepository) {}

  async execute(command: UpdatePasswordCommand): Promise<void> {
    if (!command.name.trim()) throw new PasswordNameRequiredError()
    if (!isValidPasswordUrl(command.url)) throw new PasswordUrlInvalidError()

    await this.repository.update({
      id: command.id,
      name: command.name.trim(),
      password: command.password ?? null,
      folder: command.folder ?? null,
      login: command.login ?? null,
      url: command.url ?? null,
    })
  }
}
