/**
 * Extension domain errors. Use cases throw these; the presentation layer
 * catches them and maps to a toast. Every error descends from
 * ExtensionDomainError so a single catch block can funnel them.
 */

export class ExtensionDomainError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ExtensionDomainError'
  }
}

/**
 * The pairing is unknown, expired, already resolved or already redeemed.
 *
 * One error for all of them on purpose: the backend deliberately returns a
 * single indistinguishable message, so the UI has nothing finer to say and
 * must not invent it.
 */
export class ExtensionPairingUnavailableError extends ExtensionDomainError {
  constructor(detail?: string) {
    super(detail ?? 'This pairing request is invalid or has expired')
    this.name = 'ExtensionPairingUnavailableError'
  }
}

/** The account already holds the maximum number of connected extensions. */
export class TooManyConnectedExtensionsError extends ExtensionDomainError {
  constructor(detail?: string) {
    super(detail ?? 'You have reached the maximum number of connected extensions')
    this.name = 'TooManyConnectedExtensionsError'
  }
}

export class ConnectedExtensionNotFoundError extends ExtensionDomainError {
  constructor(detail?: string) {
    super(detail ?? 'This connected extension no longer exists')
    this.name = 'ConnectedExtensionNotFoundError'
  }
}
