export class OneTimeLinkDomainError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'OneTimeLinkDomainError'
  }
}

/**
 * The link cannot be redeemed. Deliberately does not say why: the backend
 * answers the same 404 for unknown, expired, already-read and revoked tokens so
 * that an anonymous caller cannot probe which tokens exist. Mirroring that here
 * keeps the UI from inventing a distinction the API does not make.
 */
export class OneTimeLinkUnusableError extends OneTimeLinkDomainError {
  constructor() {
    super('This link is invalid or has already been used')
    this.name = 'OneTimeLinkUnusableError'
  }
}

export class OneTimeLinkVaultLockedError extends OneTimeLinkDomainError {
  constructor() {
    super('The vault is locked, so the secret cannot be revealed right now')
    this.name = 'OneTimeLinkVaultLockedError'
  }
}

export class OneTimeLinkTokenRequiredError extends OneTimeLinkDomainError {
  constructor() {
    super('A link token is required')
    this.name = 'OneTimeLinkTokenRequiredError'
  }
}

export class OneTimeLinkNotOwnerError extends OneTimeLinkDomainError {
  constructor() {
    super('Only an owner of this password can manage its one-time links')
    this.name = 'OneTimeLinkNotOwnerError'
  }
}

/**
 * The password already has as many redeemable links as the server allows.
 * Carries the backend's wording, which names the actual limit.
 */
export class TooManyActiveOneTimeLinksError extends OneTimeLinkDomainError {
  constructor(detail?: string | null) {
    super(detail || 'This password already has too many active links. Revoke one first.')
    this.name = 'TooManyActiveOneTimeLinksError'
  }
}

/** Guards the bulk revoke against an unselected dropdown reaching the API. */
export class OneTimeLinkUserRequiredError extends OneTimeLinkDomainError {
  constructor() {
    super('Select a user before revoking their links')
    this.name = 'OneTimeLinkUserRequiredError'
  }
}
