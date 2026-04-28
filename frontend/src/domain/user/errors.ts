/**
 * Domain errors for the user bounded context. Use cases throw these;
 * the presentation layer catches them and maps them to user-visible
 * messages.
 */

export class UserDomainError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'UserDomainError'
  }
}

export class UserNotFoundError extends UserDomainError {
  constructor(public readonly userId: string) {
    super(`User ${userId} not found`)
    this.name = 'UserNotFoundError'
  }
}

export class UserNameRequiredError extends UserDomainError {
  constructor() {
    super('Name is required')
    this.name = 'UserNameRequiredError'
  }
}

export class UserUsernameRequiredError extends UserDomainError {
  constructor() {
    super('Username is required')
    this.name = 'UserUsernameRequiredError'
  }
}

export class UserEmailRequiredError extends UserDomainError {
  constructor() {
    super('Email is required')
    this.name = 'UserEmailRequiredError'
  }
}

export class UserPasswordRequiredError extends UserDomainError {
  constructor() {
    super('Password is required')
    this.name = 'UserPasswordRequiredError'
  }
}

export class UserPasswordMustBeDifferentError extends UserDomainError {
  constructor() {
    super('New password must be different from the current password')
    this.name = 'UserPasswordMustBeDifferentError'
  }
}

/**
 * The user submitted a wrong "current password" when trying to change
 * their password. Distinct from generic auth failures because it surfaces
 * inline on the change-password form, not via the global 401 handler.
 */
export class IncorrectOldPasswordError extends UserDomainError {
  constructor() {
    super('Current password is incorrect')
    this.name = 'IncorrectOldPasswordError'
  }
}
