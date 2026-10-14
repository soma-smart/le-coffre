import { describe, expect, it } from 'vitest'

import { accessibleGroupIdsFor, matchesEntryQuery, visibleEntriesForGroup } from '../entry'
import type { Entry } from '../entry'

const NOW = new Date('2026-08-27T12:00:00Z')

function entry(overrides: Partial<Entry> = {}): Entry {
  return {
    id: 'e1',
    name: 'Production database',
    folder: 'infra',
    login: 'dba',
    url: 'https://db.example.com',
    groupId: 'owning-group',
    accessibleGroupIds: [],
    canRead: true,
    canWrite: true,
    accessExpiresAt: null,
    ...overrides,
  }
}

describe('accessibleGroupIdsFor', () => {
  it('falls back to the owning group when the entry is not shared', () => {
    // The trap. An unshared entry carries no accessible_group_ids, so filtering
    // on that alone would hide it entirely.
    expect(accessibleGroupIdsFor(entry({ accessibleGroupIds: [] }))).toEqual(['owning-group'])
  })

  it('uses the shared list when the entry is shared', () => {
    const shared = entry({ accessibleGroupIds: ['a', 'b'] })

    expect(accessibleGroupIdsFor(shared)).toEqual(['a', 'b'])
  })
})

describe('visibleEntriesForGroup', () => {
  it('keeps an entry shared INTO the selected group', () => {
    // The bug this whole function exists to prevent: filtering on groupId alone
    // makes every shared entry vanish from the extension while the web app
    // still shows it.
    const shared = entry({ groupId: 'other-group', accessibleGroupIds: ['other-group', 'mine'] })

    const result = visibleEntriesForGroup([shared], 'mine', NOW)

    expect(result.entries).toHaveLength(1)
  })

  it('keeps an unshared entry owned by the selected group', () => {
    const owned = entry({ groupId: 'mine', accessibleGroupIds: [] })

    expect(visibleEntriesForGroup([owned], 'mine', NOW).entries).toHaveLength(1)
  })

  it('drops entries belonging to another group', () => {
    const elsewhere = entry({ groupId: 'other', accessibleGroupIds: [] })

    expect(visibleEntriesForGroup([elsewhere], 'mine', NOW).entries).toEqual([])
  })

  it('drops entries the caller cannot read and counts them', () => {
    // An admin's listing carries can_read=false rows. A copy-only client can do
    // nothing with them, and showing them would produce buttons that always fail.
    const unreadable = entry({ groupId: 'mine', canRead: false })

    const result = visibleEntriesForGroup([unreadable], 'mine', NOW)

    expect(result.entries).toEqual([])
    expect(result.hiddenCount).toBe(1)
  })

  it('drops a share that has already lapsed', () => {
    const lapsed = entry({ groupId: 'mine', accessExpiresAt: '2026-08-27T11:00:00Z' })

    expect(visibleEntriesForGroup([lapsed], 'mine', NOW).entries).toEqual([])
  })

  it('keeps a share that has not lapsed yet', () => {
    const live = entry({ groupId: 'mine', accessExpiresAt: '2026-08-27T13:00:00Z' })

    expect(visibleEntriesForGroup([live], 'mine', NOW).entries).toHaveLength(1)
  })

  it('reports nothing hidden when everything is visible', () => {
    expect(visibleEntriesForGroup([entry({ groupId: 'mine' })], 'mine', NOW).hiddenCount).toBe(0)
  })

  it('sorts by name', () => {
    const entries = [
      entry({ id: 'b', name: 'Zebra', groupId: 'mine' }),
      entry({ id: 'a', name: 'Alpha', groupId: 'mine' }),
    ]

    expect(visibleEntriesForGroup(entries, 'mine', NOW).entries.map((e) => e.id)).toEqual([
      'a',
      'b',
    ])
  })
})

describe('matchesEntryQuery', () => {
  it('matches everything when the query is blank', () => {
    expect(matchesEntryQuery(entry(), '   ')).toBe(true)
  })

  it.each([
    ['name', 'production'],
    ['folder', 'infra'],
    ['login', 'dba'],
    ['url', 'db.example.com'],
  ])('matches on %s', (_field, needle) => {
    expect(matchesEntryQuery(entry(), needle)).toBe(true)
  })

  it('is case insensitive', () => {
    expect(matchesEntryQuery(entry(), 'PRODUCTION')).toBe(true)
  })

  it('does not match an unrelated needle', () => {
    expect(matchesEntryQuery(entry(), 'unrelated')).toBe(false)
  })

  it('tolerates null login and url', () => {
    expect(matchesEntryQuery(entry({ login: null, url: null }), 'dba')).toBe(false)
  })
})
