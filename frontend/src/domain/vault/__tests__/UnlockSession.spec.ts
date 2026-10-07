import { describe, expect, it } from 'vitest'
import {
  generateUnlockSessionId,
  isValidUnlockSessionId,
  readUnlockSessionIdFromFragment,
  unlockSessionFragment,
} from '@/domain/vault/UnlockSession'

describe('generateUnlockSessionId', () => {
  it('generates ids the backend accepts', () => {
    const id = generateUnlockSessionId()
    expect(id).toMatch(/^[0-9A-Z]{16}$/)
    expect(isValidUnlockSessionId(id)).toBe(true)
  })

  it('generates a different id each time', () => {
    const ids = new Set(Array.from({ length: 50 }, generateUnlockSessionId))
    expect(ids.size).toBe(50)
  })
})

describe('isValidUnlockSessionId', () => {
  it.each(['ZOJRGBIZK4XQ7M2P', 'a'.repeat(64), 'abc_DEF-123_ghi-4'])('accepts %s', (value) => {
    expect(isValidUnlockSessionId(value)).toBe(true)
  })

  it.each([
    '',
    'ZOJRGBIZ',
    'a'.repeat(65),
    'ZOJRGBIZK4XQ7M2P!',
    null,
    undefined,
    ['ZOJRGBIZK4XQ7M2P'],
  ])('rejects %s', (value) => {
    expect(isValidUnlockSessionId(value)).toBe(false)
  })
})

describe('unlock session fragment', () => {
  it('round-trips a session id through the URL fragment', () => {
    expect(unlockSessionFragment('ZOJRGBIZK4XQ7M2P')).toBe('#id=ZOJRGBIZK4XQ7M2P')
    expect(readUnlockSessionIdFromFragment('#id=ZOJRGBIZK4XQ7M2P')).toBe('ZOJRGBIZK4XQ7M2P')
  })

  it.each(['', '#', '#id=', '#id=short', '#other=ZOJRGBIZK4XQ7M2P', 'ZOJRGBIZK4XQ7M2P'])(
    'finds no session id in %j',
    (fragment) => {
      expect(readUnlockSessionIdFromFragment(fragment)).toBeNull()
    },
  )
})
