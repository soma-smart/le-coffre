import type { ExtensionGateway } from '@/application/ports/ExtensionGateway'

export class DisconnectAllExtensionsUseCase {
  constructor(private readonly gateway: ExtensionGateway) {}

  execute(): Promise<number> {
    return this.gateway.disconnectAllExtensions()
  }
}
