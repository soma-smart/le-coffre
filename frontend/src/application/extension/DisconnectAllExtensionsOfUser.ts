import type { ExtensionGateway } from '@/application/ports/ExtensionGateway'
import { ExtensionUserRequiredError } from '@/domain/extension/errors'

/**
 * Administrator only: cut every browser extension of another account.
 *
 * For an account disabled in the identity provider but still in the vault, or
 * a device its owner can no longer reach. Returns how many were still active,
 * so the screen can report a number rather than guess.
 */
export class DisconnectAllExtensionsOfUserUseCase {
  constructor(private readonly gateway: ExtensionGateway) {}

  async execute(input: { userId: string }): Promise<number> {
    if (!input.userId.trim()) throw new ExtensionUserRequiredError()
    return this.gateway.disconnectAllExtensionsOfUser(input.userId)
  }
}
