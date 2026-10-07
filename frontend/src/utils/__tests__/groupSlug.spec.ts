import { describe, expect, it } from 'vitest'
import type { Group } from '@/domain/group/Group'
import { findGroupIdBySlug, slugifyGroupName } from '@/utils/groupSlug'

const g = (overrides: Partial<Group>): Group => ({
  id: 'g',
  name: 'Group',
  isPersonal: false,
  userId: null,
  owners: [],
  members: [],
  ...overrides,
})

describe('slugifyGroupName', () => {
  it('returns the name verbatim (slug = name today)', () => {
    expect(slugifyGroupName('Engineering')).toBe('Engineering')
    expect(slugifyGroupName('Special chars / spaces')).toBe('Special chars / spaces')
  })
})

describe('findGroupIdBySlug', () => {
  const groups = [
    g({ id: 'eng', name: 'Engineering' }),
    g({ id: 'special', name: 'Special chars / spaces' }),
  ]

  it('returns null for null / undefined / empty slug', () => {
    expect(findGroupIdBySlug(groups, null)).toBeNull()
    expect(findGroupIdBySlug(groups, undefined)).toBeNull()
    expect(findGroupIdBySlug(groups, '')).toBeNull()
  })

  it('matches a plain name', () => {
    expect(findGroupIdBySlug(groups, 'Engineering')).toBe('eng')
  })

  it('matches a URL-encoded slug back to the decoded name', () => {
    const encoded = encodeURIComponent('Special chars / spaces')
    expect(findGroupIdBySlug(groups, encoded)).toBe('special')
  })

  it('falls back to comparing the raw slug against an encoded name', () => {
    // Pre-encoded group names should still match if the slug is the same
    // pre-encoded form (i.e. caller passed the literal encoded string).
    expect(
      findGroupIdBySlug(
        [g({ id: 'pre', name: 'Special chars / spaces' })],
        encodeURIComponent('Special chars / spaces'),
      ),
    ).toBe('pre')
  })

  it('returns null when no group matches', () => {
    expect(findGroupIdBySlug(groups, 'Nonexistent')).toBeNull()
  })

  it('survives a malformed slug that decodeURIComponent rejects', () => {
    // '%E0%A4%A' is incomplete; decodeURIComponent throws URIError. The util
    // catches that and falls back to the raw slug — so the search just won't
    // find anything, but it must not propagate the URIError.
    expect(findGroupIdBySlug(groups, '%E0%A4%A')).toBeNull()
  })
})
