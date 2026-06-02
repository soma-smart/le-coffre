import type { AuthGateway } from '@/application/ports/AuthGateway'
import { AuthEmailRequiredError, AuthPasswordRequiredError } from '@/domain/auth/errors'

export interface LoginWithPasswordCommand {
  email: string
  password: string
}

export class LoginWithPasswordUseCase {
  constructor(private readonly gateway: AuthGateway) {}

  async execute(command: LoginWithPasswordCommand): Promise<void> {
    if (!command.email.trim()) throw new AuthEmailRequiredError()
    if (!command.password) throw new AuthPasswordRequiredError()
    await this.gateway.login({ email: command.email.trim(), password: command.password })
  }
}
