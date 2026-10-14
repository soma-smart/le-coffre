import type { ExtensionGateway } from '@/application/ports/ExtensionGateway'

export interface ApprovePairingCommand {
  userCode: string
}

export class ApprovePairingUseCase {
  constructor(private readonly gateway: ExtensionGateway) {}

  execute(command: ApprovePairingCommand): Promise<void> {
    return this.gateway.approvePairing(command.userCode)
  }
}
