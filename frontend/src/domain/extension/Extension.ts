/**
 * Browser-extension pairing, as the presentation ring sees it.
 *
 * Pure TypeScript: no Vue, no SDK. The backend speaks snake_case; the adapter
 * translates at the boundary and everything above this line is camelCase.
 */

/** A pairing request awaiting the user's decision. */
export interface ExtensionPairingDetails {
  /**
   * The code the user must match against the one shown in their extension.
   * This is the whole anti-phishing ceremony: it is what lets someone tell
   * "my extension asked for this" from "some page asked for this".
   */
  userCode: string
  /**
   * Reported by the extension itself, so it is untrusted input. The approval
   * page must label it as such rather than present it as fact.
   */
  deviceName: string
  createdAt: Date
  /**
   * When this *request* stops being approvable, minutes away. Not the lifetime
   * of the credential it would create: the approval page states that one, and
   * showing this in its place understated the grant by a factor of thousands.
   */
  expiresAt: Date
  /** How long the credential itself would last, which is what is consented to. */
  accessLifetimeSeconds: number
  /**
   * The address the pairing was requested from. A foreign one is what gives
   * away a remote attacker who started it.
   */
  createdFromIp: string | null
  /** Already approved or denied. The page must not offer to decide again. */
  isResolved: boolean
}

/** One browser extension connected to the account. */
export interface ConnectedExtension {
  id: string
  deviceName: string
  createdAt: Date
  expiresAt: Date
  lastUsedAt: Date | null
  revokedAt: Date | null
  createdFromIp: string | null
  isActive: boolean
}

/**
 * Sort for the connected-devices list: live entries first, then most recently
 * created. Someone scanning the list is looking for what still has access.
 */
export function sortConnectedExtensions(
  extensions: readonly ConnectedExtension[],
): ConnectedExtension[] {
  return [...extensions].sort((left, right) => {
    if (left.isActive !== right.isActive) return left.isActive ? -1 : 1
    return right.createdAt.getTime() - left.createdAt.getTime()
  })
}
