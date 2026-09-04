import type { ExtensionGateway } from '@/application/ports/ExtensionGateway'
import type { ExtensionPairingDetails } from '@/domain/extension/Extension'

export interface GetPairingCommand {
  userCode: string
}

export class GetPairingUseCase {
  constructor(private readonly gateway: ExtensionGateway) {}

  execute(command: GetPairingCommand): Promise<ExtensionPairingDetails> {
    return this.gateway.getPairing(command.userCode)
  }
}
