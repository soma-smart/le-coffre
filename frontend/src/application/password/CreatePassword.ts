import type { PasswordRepository } from '@/application/ports/PasswordRepository'
import {
  PasswordGroupRequiredError,
  PasswordNameRequiredError,
  PasswordValueRequiredError,
} from '@/domain/password/errors'

export interface CreatePasswordCommand {
  name: string
  password: string
  groupId: string
  folder?: string | null
  login?: string | null
  url?: string | null
}

/**
 * Creates a password. Performs UX-level validation only (the backend is
 * still the authoritative guard): non-blank name, non-empty secret, a
 * group id. Backend-side rules (permission to write in the group,
 * server-side encryption, audit events) stay on the server.
 */
export class CreatePasswordUseCase {
  constructor(private readonly repository: PasswordRepository) {}

  async execute(command: CreatePasswordCommand): Promise<string> {
    if (!command.name.trim()) throw new PasswordNameRequiredError()
    if (!command.password) throw new PasswordValueRequiredError()
    if (!command.groupId) throw new PasswordGroupRequiredError()

    return this.repository.create({
      name: command.name.trim(),
      password: command.password,
      groupId: command.groupId,
      folder: command.folder ?? null,
      login: command.login ?? null,
      url: command.url ?? null,
    })
  }
}
