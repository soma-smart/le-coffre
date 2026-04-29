import type { AuthGateway } from '@/application/ports/AuthGateway'
import {
  SsoClientIdRequiredError,
  SsoClientSecretRequiredError,
  SsoDiscoveryUrlRequiredError,
} from '@/domain/auth/errors'

export interface ConfigureSsoProviderCommand {
  clientId: string
  clientSecret: string
  discoveryUrl: string
}

export class ConfigureSsoProviderUseCase {
  constructor(private readonly gateway: AuthGateway) {}

  async execute(command: ConfigureSsoProviderCommand): Promise<void> {
    if (!command.clientId.trim()) throw new SsoClientIdRequiredError()
    if (!command.clientSecret) throw new SsoClientSecretRequiredError()
    if (!command.discoveryUrl.trim()) throw new SsoDiscoveryUrlRequiredError()
    await this.gateway.configureSsoProvider({
      clientId: command.clientId.trim(),
      clientSecret: command.clientSecret,
      discoveryUrl: command.discoveryUrl.trim(),
    })
  }
}
