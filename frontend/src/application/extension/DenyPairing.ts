import type { ExtensionGateway } from '@/application/ports/ExtensionGateway'

export interface DenyPairingCommand {
  userCode: string
}

export class DenyPairingUseCase {
  constructor(private readonly gateway: ExtensionGateway) {}

  execute(command: DenyPairingCommand): Promise<void> {
    return this.gateway.denyPairing(command.userCode)
  }
}
