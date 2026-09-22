export class ServiceAccountDomainError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ServiceAccountDomainError'
  }
}

export class ServiceAccountNotOwnerError extends ServiceAccountDomainError {
  constructor() {
    super('Only an owner of this group can manage its service accounts')
    this.name = 'ServiceAccountNotOwnerError'
  }
}

/**
 * The group already has as many usable accounts as the server allows.
 * Carries the backend's wording, which names the actual count and limit.
 */
export class TooManyActiveServiceAccountsError extends ServiceAccountDomainError {
  constructor(detail?: string | null) {
    super(
      detail ||
        'This group already has too many active service accounts. Revoke one before creating another.',
    )
    this.name = 'TooManyActiveServiceAccountsError'
  }
}

/**
 * Rotation and revocation both refuse an account that is already revoked.
 * Reached when the list on screen has gone stale behind another session.
 */
export class ServiceAccountAlreadyRevokedError extends ServiceAccountDomainError {
  constructor(detail?: string | null) {
    super(detail || 'This service account has already been revoked')
    this.name = 'ServiceAccountAlreadyRevokedError'
  }
}

export class ServiceAccountNotFoundError extends ServiceAccountDomainError {
  constructor() {
    super('This service account no longer exists')
    this.name = 'ServiceAccountNotFoundError'
  }
}

/** Mirrors the server's own name rule so a bad name never costs a round trip. */
export class InvalidServiceAccountNameError extends ServiceAccountDomainError {
  constructor(message: string) {
    super(message)
    this.name = 'InvalidServiceAccountNameError'
  }
}

/** Guards a modal opened without a group against reaching the API. */
export class ServiceAccountGroupRequiredError extends ServiceAccountDomainError {
  constructor() {
    super('A group is required to manage service accounts')
    this.name = 'ServiceAccountGroupRequiredError'
  }
}
