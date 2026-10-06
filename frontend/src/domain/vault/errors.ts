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

/**
 * The share link cannot be used. Deliberately does not say why: the backend
 * answers the same 404 for unknown, expired and already retrieved links so an
 * anonymous caller cannot probe which exist.
 */
export class ShareLinkUnusableError extends VaultDomainError {
  constructor() {
    super('This share link is invalid, expired or has already been used')
    this.name = 'ShareLinkUnusableError'
  }
}

export class ShareLinkTokenRequiredError extends VaultDomainError {
  constructor() {
    super('This link is incomplete: the part after # is missing')
    this.name = 'ShareLinkTokenRequiredError'
  }
}

/**
 * The sealed share came back but does not open with this link's token. A
 * truncated token never gets this far (its hash matches no link), so this
 * means the data was tampered with between sealing and delivery. The server
 * has already spent the link at this point.
 */
export class ShareLinkCorruptedError extends VaultDomainError {
  constructor() {
    super(
      'The share could not be decrypted: the data received was altered. Alert your administrator',
    )
    this.name = 'ShareLinkCorruptedError'
  }
}

/** WebCrypto is only exposed to secure contexts (HTTPS or localhost). */
export class ShareLinkInsecureContextError extends VaultDomainError {
  constructor() {
    super('Opening a share requires a secure (HTTPS) connection')
    this.name = 'ShareLinkInsecureContextError'
  }
}
