/**
 * Password domain errors. Use cases throw these; the presentation layer
 * catches them and maps to user-facing messages. Every error descends
 * from PasswordDomainError so a single catch block can funnel them.
 */

export class PasswordDomainError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'PasswordDomainError'
  }
}

export class PasswordNotFoundError extends PasswordDomainError {
  constructor(public readonly passwordId: string) {
    super(`Password ${passwordId} not found`)
    this.name = 'PasswordNotFoundError'
  }
}

export class PasswordAccessDeniedError extends PasswordDomainError {
  constructor(public readonly passwordId: string) {
    super(`Access denied for password ${passwordId}`)
    this.name = 'PasswordAccessDeniedError'
  }
}

export class PasswordNameRequiredError extends PasswordDomainError {
  constructor() {
    super('Password name is required')
    this.name = 'PasswordNameRequiredError'
  }
}

export class PasswordValueRequiredError extends PasswordDomainError {
  constructor() {
    super('Password value is required')
    this.name = 'PasswordValueRequiredError'
  }
}

export class PasswordGroupRequiredError extends PasswordDomainError {
  constructor() {
    super('A group id is required to create a password')
    this.name = 'PasswordGroupRequiredError'
  }
}
