import type { ExtensionGateway } from '@/application/ports/ExtensionGateway'
import type { ConnectedExtension } from '@/domain/extension/Extension'
import { sortConnectedExtensions } from '@/domain/extension/Extension'

export class ListConnectedExtensionsUseCase {
  constructor(private readonly gateway: ExtensionGateway) {}

  async execute(): Promise<ConnectedExtension[]> {
    return sortConnectedExtensions(await this.gateway.listConnectedExtensions())
  }
}
