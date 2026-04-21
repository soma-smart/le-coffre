import { describe, expect, it } from 'vitest'
import {
  accessibleGroupIdsFor,
  isPasswordStale,
  isValidPasswordUrl,
  matchesPasswordQuery,
  PASSWORD_STALE_AFTER_DAYS,
  type Password,
} from '@/domain/password/Password'

function makePassword(overrides: Partial<Password> = {}): Password {
  return {
    id: 'p1',
    name: 'GitHub',
    folder: 'Work',
    groupId: 'g1',
    createdAt: '2026-01-01T00:00:00Z',
    lastUpdatedAt: '2026-01-01T00:00:00Z',
    canRead: true,
    canWrite: true,
    login: 'alice@example.com',
    url: 'https://github.com',
    accessibleGroupIds: [],
    ...overrides,
  }
}

describe('matchesPasswordQuery', () => {
  it('matches everything when the query is empty or whitespace', () => {
    const password = makePassword()
    expect(matchesPasswordQuery(password, '')).toBe(true)
    expect(matchesPasswordQuery(password, '   ')).toBe(true)
  })

  it('is case-insensitive across every searchable field', () => {
    const password = makePassword()
    expect(matchesPasswordQuery(password, 'GITHUB')).toBe(true)
    expect(matchesPasswordQuery(password, 'work')).toBe(true)
    expect(matchesPasswordQuery(password, 'ALICE@')).toBe(true)
    expect(matchesPasswordQuery(password, 'GITHUB.com')).toBe(true)
  })

  it('matches the group name when provided', () => {
    const password = makePassword()
    expect(matchesPasswordQuery(password, 'engineering', 'Engineering Team')).toBe(true)
  })

  it('returns false when the query is nowhere to be found', () => {
    const password = makePassword()
    expect(matchesPasswordQuery(password, 'netflix')).toBe(false)
  })

  it('handles passwords with null login and url', () => {
    const password = makePassword({ login: null, url: null })
    expect(matchesPasswordQuery(password, 'github')).toBe(true) // name still matches
    expect(matchesPasswordQuery(password, 'alice')).toBe(false)
  })
})

describe('isValidPasswordUrl', () => {
  it('accepts empty / null / undefined (URL is optional)', () => {
    expect(isValidPasswordUrl(null)).toBe(true)
    expect(isValidPasswordUrl(undefined)).toBe(true)
    expect(isValidPasswordUrl('')).toBe(true)
  })

  it('accepts http:// and https:// regardless of case', () => {
    expect(isValidPasswordUrl('http://x')).toBe(true)
    expect(isValidPasswordUrl('https://x')).toBe(true)
    expect(isValidPasswordUrl('HTTPS://X')).toBe(true)
  })

  it('rejects other schemes and scheme-less strings', () => {
    expect(isValidPasswordUrl('ftp://example.com')).toBe(false)
    expect(isValidPasswordUrl('example.com')).toBe(false)
    expect(isValidPasswordUrl('javascript:alert(1)')).toBe(false)
  })
})

describe('isPasswordStale', () => {
  const now = new Date('2026-04-21T00:00:00Z')

  const withLastUpdated = (daysAgo: number): Password =>
    makePassword({
      lastUpdatedAt: new Date(now.getTime() - daysAgo * 24 * 60 * 60 * 1000).toISOString(),
    })

  it('returns false for a fresh password', () => {
    expect(isPasswordStale(withLastUpdated(1), now)).toBe(false)
  })

  it('returns false exactly at the threshold boundary', () => {
    expect(isPasswordStale(withLastUpdated(PASSWORD_STALE_AFTER_DAYS), now)).toBe(false)
  })

  it('returns true once past the threshold', () => {
    expect(isPasswordStale(withLastUpdated(PASSWORD_STALE_AFTER_DAYS + 1), now)).toBe(true)
  })
})

describe('accessibleGroupIdsFor', () => {
  it('returns the explicit list when at least one group is shared', () => {
    const password = makePassword({ groupId: 'g1', accessibleGroupIds: ['g1', 'g2'] })
    expect(accessibleGroupIdsFor(password)).toEqual(['g1', 'g2'])
  })

  it('falls back to the owning group when no groups are shared', () => {
    const password = makePassword({ groupId: 'g1', accessibleGroupIds: [] })
    expect(accessibleGroupIdsFor(password)).toEqual(['g1'])
  })
})
