import type { AuthGateway } from '@/application/ports/AuthGateway'

export class IsSsoConfiguredUseCase {
  constructor(private readonly gateway: AuthGateway) {}

  execute(): Promise<boolean> {
    return this.gateway.isSsoConfigured()
  }
}
