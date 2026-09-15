import type { ExtensionGateway } from '@/application/ports/ExtensionGateway'
import type { ConnectedExtension, ExtensionPairingDetails } from '@/domain/extension/Extension'
import { ExtensionPairingUnavailableError } from '@/domain/extension/errors'

/**
 * Test-only fake for ExtensionGateway.
 *
 * Models the states the approval page has to render, including the ones that
 * are easy to forget: a pairing that no longer exists, and one that has already
 * been resolved.
 */
export class InMemoryExtensionGateway implements ExtensionGateway {
  private pairings = new Map<string, ExtensionPairingDetails>()
  private extensions: ConnectedExtension[] = []
  private nextError: Error | null = null

  /** Records what was approved and denied, so tests can assert on the effect. */
  readonly approved: string[] = []
  readonly denied: string[] = []
  readonly disconnected: string[] = []

  seedPairing(pairing: ExtensionPairingDetails): this {
    this.pairings.set(pairing.userCode, pairing)
    return this
  }

  seedExtensions(extensions: ConnectedExtension[]): this {
    this.extensions = [...extensions]
    return this
  }

  failWith(error: Error): this {
    this.nextError = error
    return this
  }

  private throwIfFailing(): void {
    if (this.nextError) {
      const error = this.nextError
      this.nextError = null
      throw error
    }
  }

  async getPairing(userCode: string): Promise<ExtensionPairingDetails> {
    this.throwIfFailing()
    const pairing = this.pairings.get(userCode)
    if (!pairing) throw new ExtensionPairingUnavailableError()
    return pairing
  }

  async approvePairing(userCode: string): Promise<void> {
    this.throwIfFailing()
    this.approved.push(userCode)
  }

  async denyPairing(userCode: string): Promise<void> {
    this.throwIfFailing()
    this.denied.push(userCode)
  }

  async listConnectedExtensions(): Promise<ConnectedExtension[]> {
    this.throwIfFailing()
    return [...this.extensions]
  }

  async disconnectExtension(extensionId: string): Promise<void> {
    this.throwIfFailing()
    this.disconnected.push(extensionId)
    this.extensions = this.extensions.map((extension) =>
      extension.id === extensionId
        ? { ...extension, isActive: false, revokedAt: new Date() }
        : extension,
    )
  }

  async disconnectAllExtensions(): Promise<number> {
    this.throwIfFailing()
    const active = this.extensions.filter((extension) => extension.isActive).length
    this.extensions = this.extensions.map((extension) => ({
      ...extension,
      isActive: false,
      revokedAt: extension.revokedAt ?? new Date(),
    }))
    return active
  }
}
