import { afterEach, describe, expect, it } from 'vitest'
import { getCookie, isAuthenticated } from '@/utils/auth'

const COOKIES_TO_CLEAR = ['logged_in', 'session', 'feature%20flag']

afterEach(() => {
  COOKIES_TO_CLEAR.forEach((name) => {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`
  })
})

describe('isAuthenticated', () => {
  it('returns true when the logged_in cookie is exactly "true"', () => {
    document.cookie = 'logged_in=true; path=/'
    expect(isAuthenticated()).toBe(true)
  })

  it('returns false when the cookie is missing', () => {
    expect(isAuthenticated()).toBe(false)
  })

  it('returns false when the cookie value is anything other than "true"', () => {
    document.cookie = 'logged_in=false; path=/'
    expect(isAuthenticated()).toBe(false)
    document.cookie = 'logged_in=1; path=/'
    expect(isAuthenticated()).toBe(false)
  })
})

describe('getCookie', () => {
  it('returns the value when the cookie is present', () => {
    document.cookie = 'session=abc123; path=/'
    expect(getCookie('session')).toBe('abc123')
  })

  it('returns null for a missing cookie', () => {
    expect(getCookie('absent')).toBeNull()
  })

  it('decodes URL-encoded values', () => {
    document.cookie = `feature%20flag=${encodeURIComponent('on / off')}; path=/`
    expect(getCookie('feature%20flag')).toBe('on / off')
  })
})
