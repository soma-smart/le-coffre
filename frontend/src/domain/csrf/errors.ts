/**
 * CSRF domain errors. Use cases throw these; the presentation layer
 * catches them and maps to user-facing messages. Every error descends
 * from CsrfDomainError so a single catch block can funnel them.
 */

export class CsrfDomainError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'CsrfDomainError'
  }
}

/**
 * The CSRF endpoint responded with a transport-level error
 * (network failure, non-2xx HTTP code, malformed response envelope).
 */
export class CsrfTokenUnavailableError extends CsrfDomainError {
  constructor(message = 'Failed to fetch CSRF token') {
    super(message)
    this.name = 'CsrfTokenUnavailableError'
  }
}

/**
 * The CSRF endpoint succeeded but the response body had no token.
 * Distinct from `Unavailable` because it suggests a server-side
 * misconfiguration rather than a network issue.
 */
export class CsrfTokenEmptyError extends CsrfDomainError {
  constructor() {
    super('Empty response from CSRF token endpoint')
    this.name = 'CsrfTokenEmptyError'
  }
}
