import type { SsoCallbackResult } from '@/domain/auth/Auth'
import type { AuthGateway } from '@/application/ports/AuthGateway'
import { SsoCallbackCodeRequiredError } from '@/domain/auth/errors'

export interface HandleSsoCallbackCommand {
  code: string
  state?: string
}

export class HandleSsoCallbackUseCase {
  constructor(private readonly gateway: AuthGateway) {}

  async execute(command: HandleSsoCallbackCommand): Promise<SsoCallbackResult> {
    if (!command.code) throw new SsoCallbackCodeRequiredError()
    return this.gateway.ssoCallback({ code: command.code, state: command.state })
  }
}
