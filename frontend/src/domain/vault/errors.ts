export class VaultDomainError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'VaultDomainError'
  }
}

export class VaultSharesRequiredError extends VaultDomainError {
  constructor() {
    super('At least one share is required to unlock the vault')
    this.name = 'VaultSharesRequiredError'
  }
}

export class VaultThresholdInvalidError extends VaultDomainError {
  constructor() {
    super('Threshold must be between 2 and the total number of shares')
    this.name = 'VaultThresholdInvalidError'
  }
}

export class VaultSetupIdRequiredError extends VaultDomainError {
  constructor() {
    super('A setup id is required to validate the vault setup')
    this.name = 'VaultSetupIdRequiredError'
  }
}
