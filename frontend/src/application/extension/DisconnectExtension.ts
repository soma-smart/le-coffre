import type { ExtensionGateway } from '@/application/ports/ExtensionGateway'

export interface DisconnectExtensionCommand {
  extensionId: string
}

export class DisconnectExtensionUseCase {
  constructor(private readonly gateway: ExtensionGateway) {}

  execute(command: DisconnectExtensionCommand): Promise<void> {
    return this.gateway.disconnectExtension(command.extensionId)
  }
}
