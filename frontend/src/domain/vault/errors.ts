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
 * The share link cannot be used, for good. Deliberately does not say why: the
 * backend answers the same 404 for unknown, expired and closed links (closed
 * by the custodian's confirmation, or by its reopen window running out), so an
 * anonymous caller cannot probe which exist. Retrying will not help.
 */
export class ShareLinkUnusableError extends VaultDomainError {
  constructor() {
    super('This share link is invalid, expired or has already been used')
    this.name = 'ShareLinkUnusableError'
  }
}

/**
 * The server refused to close the link: the acknowledgement did not come from
 * its token. A real custodian's browser never sends that; the link stays open.
 */
export class ShareLinkAckRejectedError extends VaultDomainError {
  constructor() {
    super('This link could not be closed: the confirmation does not match it')
    this.name = 'ShareLinkAckRejectedError'
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
 * means the data, or the setup id or share index it was sealed with, was
 * altered between sealing and delivery. The server has delivered the link,
 * which starts its reopen window but does not close it: the custodian can
 * retry until the window ends, and the next opening comes back as a reopening.
 */
export class ShareLinkCorruptedError extends VaultDomainError {
  constructor() {
    super(
      'The share could not be decrypted: the data received was altered. Alert your administrator',
    )
    this.name = 'ShareLinkCorruptedError'
  }
}

/**
 * The setup refuses to issue share links nobody could open: custodians open
 * them with WebCrypto at this same origin, which plain HTTP does not expose.
 * Issued anyway, the links would expire unopened and take the master key
 * with them.
 */
export class ShareLinksUnsupportedError extends VaultDomainError {
  constructor() {
    super(
      'Share links can only be opened over HTTPS: serve Le Coffre over HTTPS before setting up the vault',
    )
    this.name = 'ShareLinksUnsupportedError'
  }
}

/** WebCrypto is only exposed to secure contexts (HTTPS or localhost). */
export class ShareLinkInsecureContextError extends VaultDomainError {
  constructor() {
    super('Opening a share requires a secure (HTTPS) connection')
    this.name = 'ShareLinkInsecureContextError'
  }
}
