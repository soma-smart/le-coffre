import type { PasswordRepository } from '@/application/ports/PasswordRepository'

export interface DeletePasswordCommand {
  passwordId: string
}

export class DeletePasswordUseCase {
  constructor(private readonly repository: PasswordRepository) {}

  execute(command: DeletePasswordCommand): Promise<void> {
    return this.repository.delete(command.passwordId)
  }
}
