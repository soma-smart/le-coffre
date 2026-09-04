import type { ConnectedExtension, ExtensionPairingDetails } from '@/domain/extension/Extension'

/**
 * Contract the infrastructure must satisfy for browser-extension pairing.
 *
 * Methods express what the screens actually ask, not the endpoint shapes. Note
 * what is absent: nothing here can mint or read a token. The credential is
 * issued to the extension by the exchange call, which the SPA never makes.
 */
export interface ExtensionGateway {
  /** Load a pairing so the user can decide on it. */
  getPairing(userCode: string): Promise<ExtensionPairingDetails>

  approvePairing(userCode: string): Promise<void>

  denyPairing(userCode: string): Promise<void>

  listConnectedExtensions(): Promise<ConnectedExtension[]>

  disconnectExtension(extensionId: string): Promise<void>

  /** Returns how many were still active. */
  disconnectAllExtensions(): Promise<number>
}
