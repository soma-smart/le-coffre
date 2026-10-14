import type { ExtensionGateway } from '@/application/ports/ExtensionGateway'
import type { ExtensionPairingDetails } from '@/domain/extension/Extension'
import { InvalidPairingUserCodeError } from '@/domain/extension/errors'
import { normalizePairingUserCode } from '@/domain/extension/pairingUserCode'

export interface GetPairingCommand {
  /** As typed by the user: any case, dash optional. */
  userCode: string
}

export class GetPairingUseCase {
  constructor(private readonly gateway: ExtensionGateway) {}

  async execute(command: GetPairingCommand): Promise<ExtensionPairingDetails> {
    const userCode = normalizePairingUserCode(command.userCode)
    // Refused here so a typo never becomes a request: the pairing routes are
    // rate-limited per IP, and a malformed code can only ever be a 400.
    if (!userCode) throw new InvalidPairingUserCodeError()
    return this.gateway.getPairing(userCode)
  }
}
