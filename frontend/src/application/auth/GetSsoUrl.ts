import type { AuthGateway } from '@/application/ports/AuthGateway'

export class GetSsoUrlUseCase {
  constructor(private readonly gateway: AuthGateway) {}

  execute(): Promise<string> {
    return this.gateway.getSsoUrl()
  }
}
