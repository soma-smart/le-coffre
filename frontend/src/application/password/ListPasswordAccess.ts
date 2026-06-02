import type { PasswordAccess } from '@/domain/password/Password'
import type { PasswordRepository } from '@/application/ports/PasswordRepository'

export interface ListPasswordAccessCommand {
  passwordId: string
}

export class ListPasswordAccessUseCase {
  constructor(private readonly repository: PasswordRepository) {}

  execute(command: ListPasswordAccessCommand): Promise<PasswordAccess> {
    return this.repository.listAccess(command.passwordId)
  }
}
