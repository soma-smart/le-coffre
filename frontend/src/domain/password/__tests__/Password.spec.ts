import { describe, expect, it } from 'vitest'
import { matchesPasswordQuery, type Password } from '@/domain/password/Password'

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
