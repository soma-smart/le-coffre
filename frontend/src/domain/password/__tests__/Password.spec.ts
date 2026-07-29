import { describe, expect, it } from 'vitest'
import {
  accessibleGroupIdsFor,
  eventSeverity,
  humanizeEventType,
  isPasswordStale,
  isValidPasswordUrl,
  matchesPasswordQuery,
  PASSWORD_STALE_AFTER_DAYS,
  type Password,
  severityForShareStatus,
  shareStatusOf,
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
    accessExpiresAt: null,
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

describe('humanizeEventType', () => {
  it.each([
    ['PasswordCreatedEvent', 'Password Created'],
    ['PasswordDeletedEvent', 'Password Deleted'],
    ['PasswordUpdatedEvent', 'Password Updated'],
    ['PasswordSharedEvent', 'Password Shared'],
    ['PasswordUnsharedEvent', 'Password Unshared'],
    ['PasswordAccessedEvent', 'Password Accessed'],
    ['OneTimeLinkCreatedEvent', 'One Time Link Created'],
    ['OneTimeLinkReadEvent', 'One Time Link Read'],
  ])('humanizes %s to "%s"', (input, expected) => {
    expect(humanizeEventType(input)).toBe(expected)
  })
})

describe('eventSeverity', () => {
  it('maps each known event type to its severity', () => {
    expect(eventSeverity('PasswordCreatedEvent')).toBe('success')
    expect(eventSeverity('PasswordDeletedEvent')).toBe('danger')
    expect(eventSeverity('PasswordUpdatedEvent')).toBe('warn')
    expect(eventSeverity('PasswordSharedEvent')).toBe('info')
    expect(eventSeverity('PasswordUnsharedEvent')).toBe('info')
    expect(eventSeverity('PasswordAccessedEvent')).toBe('secondary')
    expect(eventSeverity('OneTimeLinkCreatedEvent')).toBe('info')
    // The moment a secret left the vault to someone with no account: it must
    // stand out in the log rather than blend into the neutral fallback.
    expect(eventSeverity('OneTimeLinkReadEvent')).toBe('warn')
  })

  it('falls back to "secondary" for unknown event types', () => {
    expect(eventSeverity('PasswordMysteriouslyTeleportedEvent')).toBe('secondary')
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

describe('shareStatusOf', () => {
  const now = new Date('2026-07-27T12:00:00Z')

  it('reports a share with no deadline as permanent', () => {
    expect(shareStatusOf(null, now)).toBe('permanent')
  })

  it('reports a share still in the future as active', () => {
    expect(shareStatusOf('2026-07-27T13:00:00Z', now)).toBe('active')
  })

  it('reports a share past its deadline as expired', () => {
    expect(shareStatusOf('2026-07-27T11:59:59Z', now)).toBe('expired')
  })

  it('treats the exact deadline as expired, matching the backend', () => {
    expect(shareStatusOf('2026-07-27T12:00:00Z', now)).toBe('expired')
  })

  it('reports an unreadable deadline as expired, never as active', () => {
    // Comparing an Invalid Date yields false, which would silently claim the
    // share is live. Never assert a deadline we cannot read.
    expect(shareStatusOf('not-a-date', now)).toBe('expired')
    expect(shareStatusOf('2026-13-45T99:99:99Z', now)).toBe('expired')
  })

  it('still reports a share with no deadline as permanent', () => {
    // Guard against an over-eager fix that lumps null in with unparseable.
    expect(shareStatusOf(null, now)).toBe('permanent')
    expect(shareStatusOf('', now)).toBe('permanent')
  })
})

describe('severityForShareStatus', () => {
  it('escalates from permanent through active to expired', () => {
    expect(severityForShareStatus('permanent')).toBe('info')
    expect(severityForShareStatus('active')).toBe('warn')
    expect(severityForShareStatus('expired')).toBe('danger')
  })
})
