import type { Password } from '@/domain/password/Password'
import type { PasswordRepository } from '@/application/ports/PasswordRepository'

export class ListPasswordsUseCase {
  constructor(private readonly repository: PasswordRepository) {}

  execute(): Promise<Password[]> {
    return this.repository.list()
  }
}
