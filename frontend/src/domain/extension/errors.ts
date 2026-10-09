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

/** What was typed is not a pairing code, so nothing was asked of the backend. */
export class InvalidPairingUserCodeError extends ExtensionDomainError {
  constructor() {
    super(
      'Enter the code exactly as your extension shows it: four characters, a dash, four characters',
    )
    this.name = 'InvalidPairingUserCodeError'
  }
}

/**
 * The decision was refused for want of a valid CSRF token (403).
 *
 * The token lives in memory and is primed by the router; losing it means the
 * page's session state is stale, and the only repair is a reload. Distinct
 * from "invalid or expired" because that wording sends the user back to their
 * extension to start over, which would not help.
 */
export class ExtensionSessionLostError extends ExtensionDomainError {
  constructor() {
    super('Your session could not be verified. Reload the page and try again.')
    this.name = 'ExtensionSessionLostError'
  }
}

/** The backend failed (5xx). The pairing may still be there, so: try again. */
export class ExtensionServerError extends ExtensionDomainError {
  constructor() {
    super('The server could not handle the request. Please try again.')
    this.name = 'ExtensionServerError'
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

export class ExtensionUserRequiredError extends ExtensionDomainError {
  constructor() {
    super('Select a user before disconnecting their extensions')
    this.name = 'ExtensionUserRequiredError'
  }
}
