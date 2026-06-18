// src/application/password/CreatePasswordsFromKeepassUseCase.ts

import type { PasswordRepository } from '@/application/ports/PasswordRepository'
import { PasswordGroupRequiredError, PasswordValueRequiredError } from '@/domain/password/errors'

export interface CreatePasswordsFromKeepassCommand {
  file: File
  password: string
  groupId: string
}

export class CreatePasswordsFromKeepassUseCase {
  constructor(private readonly repository: PasswordRepository) {}

  async execute(command: CreatePasswordsFromKeepassCommand): Promise<string[]> {
    if (!command.file) throw new Error('KeePass file is required')
    if (!command.password) throw new PasswordValueRequiredError()
    if (!command.groupId) throw new PasswordGroupRequiredError()

    return this.repository.importFromKeepass({
      file: command.file,
      password: command.password,
      groupId: command.groupId,
    })
  }
}
