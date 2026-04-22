import { describe, expect, it } from 'vitest'
import {
  PasswordAccessDeniedError,
  PasswordDomainError,
  PasswordGroupRequiredError,
  PasswordNameRequiredError,
  PasswordNotFoundError,
  PasswordValueRequiredError,
} from '@/domain/password/errors'

describe('password domain errors', () => {
  it('every domain error descends from PasswordDomainError and Error', () => {
    const cases: PasswordDomainError[] = [
      new PasswordNotFoundError('pwd-1'),
      new PasswordAccessDeniedError('pwd-1'),
      new PasswordNameRequiredError(),
      new PasswordValueRequiredError(),
      new PasswordGroupRequiredError(),
    ]

    for (const err of cases) {
      expect(err).toBeInstanceOf(PasswordDomainError)
      expect(err).toBeInstanceOf(Error)
    }
  })

  it('preserves contextual fields and sets a distinct name', () => {
    const notFound = new PasswordNotFoundError('pwd-42')
    expect(notFound.passwordId).toBe('pwd-42')
    expect(notFound.name).toBe('PasswordNotFoundError')
    expect(notFound.message).toContain('pwd-42')

    const denied = new PasswordAccessDeniedError('pwd-7')
    expect(denied.passwordId).toBe('pwd-7')
    expect(denied.name).toBe('PasswordAccessDeniedError')
  })
})
