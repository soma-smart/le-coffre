import type { AuthGateway } from '@/application/ports/AuthGateway'
import {
  AuthDisplayNameRequiredError,
  AuthEmailRequiredError,
  AuthPasswordRequiredError,
} from '@/domain/auth/errors'

export interface RegisterAdminCommand {
  email: string
  password: string
  displayName: string
}

export class RegisterAdminUseCase {
  constructor(private readonly gateway: AuthGateway) {}

  async execute(command: RegisterAdminCommand): Promise<string> {
    if (!command.email.trim()) throw new AuthEmailRequiredError()
    if (!command.password) throw new AuthPasswordRequiredError()
    if (!command.displayName.trim()) throw new AuthDisplayNameRequiredError()
    return this.gateway.registerAdmin({
      email: command.email.trim(),
      password: command.password,
      displayName: command.displayName.trim(),
    })
  }
}
