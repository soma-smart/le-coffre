import { describe, expect, it } from 'vitest'
import {
  CsrfDomainError,
  CsrfTokenEmptyError,
  CsrfTokenUnavailableError,
} from '@/domain/csrf/errors'

describe('csrf errors', () => {
  it('CsrfTokenUnavailableError descends from CsrfDomainError and Error', () => {
    const err = new CsrfTokenUnavailableError('detail')
    expect(err).toBeInstanceOf(CsrfTokenUnavailableError)
    expect(err).toBeInstanceOf(CsrfDomainError)
    expect(err).toBeInstanceOf(Error)
    expect(err.name).toBe('CsrfTokenUnavailableError')
    expect(err.message).toBe('detail')
  })

  it('CsrfTokenUnavailableError defaults to a generic message', () => {
    expect(new CsrfTokenUnavailableError().message).toBe('Failed to fetch CSRF token')
  })

  it('CsrfTokenEmptyError carries a stable message', () => {
    const err = new CsrfTokenEmptyError()
    expect(err).toBeInstanceOf(CsrfDomainError)
    expect(err.name).toBe('CsrfTokenEmptyError')
    expect(err.message).toBe('Empty response from CSRF token endpoint')
  })
})
