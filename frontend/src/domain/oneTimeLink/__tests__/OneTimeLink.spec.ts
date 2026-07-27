import { describe, expect, it } from 'vitest'
import {
  buildOneTimeLinkUrl,
  isActive,
  readTokenFromFragment,
  statusOf,
  type OneTimeLink,
} from '../OneTimeLink'

const NOW = new Date('2026-01-01T12:00:00Z')

function makeLink(overrides: Partial<OneTimeLink> = {}): OneTimeLink {
  return {
    id: 'link-1',
    passwordId: 'password-1',
    createdByUserId: 'user-1',
    createdAt: '2026-01-01T11:00:00Z',
    expiresAt: '2026-01-02T11:00:00Z',
    readAt: null,
    revokedAt: null,
    ...overrides,
  }
}

describe('statusOf', () => {
  it('reports an unread, unexpired link as active', () => {
    expect(statusOf(makeLink(), NOW)).toBe('active')
  })

  it('reports a read link as read', () => {
    expect(statusOf(makeLink({ readAt: '2026-01-01T11:30:00Z' }), NOW)).toBe('read')
  })

  it('reports an expired link as expired', () => {
    expect(statusOf(makeLink({ expiresAt: '2026-01-01T11:00:00Z' }), NOW)).toBe('expired')
  })

  it('prefers revoked over expired, because revocation is a deliberate act', () => {
    const link = makeLink({ revokedAt: '2026-01-01T11:30:00Z', expiresAt: '2026-01-01T11:00:00Z' })
    expect(statusOf(link, NOW)).toBe('revoked')
  })

  it('prefers read over expired, so the audit fact survives the passage of time', () => {
    const link = makeLink({ readAt: '2026-01-01T10:30:00Z', expiresAt: '2026-01-01T11:00:00Z' })
    expect(statusOf(link, NOW)).toBe('read')
  })
})

describe('isActive', () => {
  it('is true only for a link that can still be redeemed', () => {
    expect(isActive(makeLink(), NOW)).toBe(true)
    expect(isActive(makeLink({ readAt: '2026-01-01T11:30:00Z' }), NOW)).toBe(false)
    expect(isActive(makeLink({ revokedAt: '2026-01-01T11:30:00Z' }), NOW)).toBe(false)
  })
})

describe('one-time link URL', () => {
  it('puts the token in the fragment so it is never sent to the server', () => {
    const url = buildOneTimeLinkUrl('https://coffre.example.com', 'abc123')

    expect(url).toBe('https://coffre.example.com/one-time-link#abc123')
    // The token must not appear before the '#', which is the part browsers send.
    expect(url.split('#')[0]).not.toContain('abc123')
  })

  it('round-trips a token that needs escaping', () => {
    const token = 'a+b/c=d'
    const url = buildOneTimeLinkUrl('https://coffre.example.com', token)

    expect(readTokenFromFragment(new URL(url).hash)).toBe(token)
  })

  it('reads a fragment with or without its leading hash', () => {
    expect(readTokenFromFragment('#abc')).toBe('abc')
    expect(readTokenFromFragment('abc')).toBe('abc')
  })
})
