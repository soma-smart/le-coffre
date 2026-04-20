export class AuthDomainError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'AuthDomainError'
  }
}

export class InvalidCredentialsError extends AuthDomainError {
  constructor() {
    super('Invalid email or password')
    this.name = 'InvalidCredentialsError'
  }
}

export class AuthEmailRequiredError extends AuthDomainError {
  constructor() {
    super('Email is required')
    this.name = 'AuthEmailRequiredError'
  }
}

export class AuthPasswordRequiredError extends AuthDomainError {
  constructor() {
    super('Password is required')
    this.name = 'AuthPasswordRequiredError'
  }
}

export class AuthDisplayNameRequiredError extends AuthDomainError {
  constructor() {
    super('Display name is required')
    this.name = 'AuthDisplayNameRequiredError'
  }
}

export class SsoClientIdRequiredError extends AuthDomainError {
  constructor() {
    super('Client ID is required')
    this.name = 'SsoClientIdRequiredError'
  }
}

export class SsoClientSecretRequiredError extends AuthDomainError {
  constructor() {
    super('Client secret is required')
    this.name = 'SsoClientSecretRequiredError'
  }
}

export class SsoDiscoveryUrlRequiredError extends AuthDomainError {
  constructor() {
    super('Discovery URL is required')
    this.name = 'SsoDiscoveryUrlRequiredError'
  }
}

export class SsoCallbackCodeRequiredError extends AuthDomainError {
  constructor() {
    super('Authorization code is required to complete SSO login')
    this.name = 'SsoCallbackCodeRequiredError'
  }
}
