export class VaultDomainError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'VaultDomainError'
  }
}

/**
 * Raised when a crypto operation is attempted while the vault is locked
 * (the backend returns 503). The global HTTP interceptor already surfaces the
 * unlock modal + a "Vault Locked" toast, so callers that catch this should
 * NOT show their own duplicate error toast.
 */
export class VaultLockedError extends VaultDomainError {
  constructor() {
    super('The vault is locked')
    this.name = 'VaultLockedError'
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
