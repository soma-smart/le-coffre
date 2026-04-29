import { describe, expect, it } from 'vitest'
import {
  filterGroupsForUser,
  filterOwnedGroupsForUser,
  isUserMemberOf,
  isUserOwnerOf,
  pickDefaultGroupForUser,
  type Group,
} from '@/domain/group/Group'

function makeGroup(overrides: Partial<Group> = {}): Group {
  return {
    id: 'g1',
    name: 'Engineering',
    isPersonal: false,
    userId: null,
    owners: [],
    members: [],
    ...overrides,
  }
}

describe('isUserOwnerOf / isUserMemberOf', () => {
  it('returns false for a null userId', () => {
    const group = makeGroup({ owners: ['u1'], members: ['u2'] })
    expect(isUserOwnerOf(group, null)).toBe(false)
    expect(isUserMemberOf(group, null)).toBe(false)
  })

  it('matches exact ids in the owners / members lists', () => {
    const group = makeGroup({ owners: ['u1'], members: ['u2'] })
    expect(isUserOwnerOf(group, 'u1')).toBe(true)
    expect(isUserOwnerOf(group, 'u2')).toBe(false)
    expect(isUserMemberOf(group, 'u1')).toBe(false)
    expect(isUserMemberOf(group, 'u2')).toBe(true)
  })
})

describe('filterGroupsForUser', () => {
  const groups = [
    makeGroup({ id: 'g1', owners: ['u1'] }),
    makeGroup({ id: 'g2', members: ['u1'] }),
    makeGroup({ id: 'g3', owners: ['u2'], members: ['u3'] }),
  ]

  it('returns an empty array for a null user id', () => {
    expect(filterGroupsForUser(groups, null)).toEqual([])
  })

  it('includes groups where the user is owner or member', () => {
    expect(filterGroupsForUser(groups, 'u1').map((g) => g.id)).toEqual(['g1', 'g2'])
  })

  it('returns empty when the user is in no group', () => {
    expect(filterGroupsForUser(groups, 'nobody')).toEqual([])
  })
})

describe('filterOwnedGroupsForUser', () => {
  const groups = [makeGroup({ id: 'g1', owners: ['u1'] }), makeGroup({ id: 'g2', members: ['u1'] })]

  it('returns an empty array for a null user id', () => {
    expect(filterOwnedGroupsForUser(groups, null)).toEqual([])
  })

  it('only keeps groups where the user is an owner', () => {
    expect(filterOwnedGroupsForUser(groups, 'u1').map((g) => g.id)).toEqual(['g1'])
  })
})

describe('pickDefaultGroupForUser', () => {
  const sortByName = (groups: Group[]): Group[] =>
    [...groups].sort((a, b) => a.name.localeCompare(b.name))

  it('returns null for an empty list', () => {
    expect(pickDefaultGroupForUser([], 'p1')).toBeNull()
    expect(pickDefaultGroupForUser([], null)).toBeNull()
  })

  it('prefers the personal group when it is in the list', () => {
    const personal = makeGroup({ id: 'p1', name: 'My Stuff', isPersonal: true })
    const shared = makeGroup({ id: 'g1', name: 'A Team' })
    expect(pickDefaultGroupForUser([shared, personal], 'p1', sortByName)).toBe(personal)
  })

  it('falls back to the first sorted group when personal id is missing from the list', () => {
    const groups = [
      makeGroup({ id: 'g2', name: 'Zebra Team' }),
      makeGroup({ id: 'g1', name: 'Alpha Team' }),
    ]
    expect(pickDefaultGroupForUser(groups, 'dangling', sortByName)?.id).toBe('g1')
  })

  it('returns the first sorted group when no personal id is provided', () => {
    const groups = [makeGroup({ id: 'g2', name: 'Zebra' }), makeGroup({ id: 'g1', name: 'Alpha' })]
    expect(pickDefaultGroupForUser(groups, null, sortByName)?.id).toBe('g1')
  })

  it('uses the identity comparator by default (first element wins)', () => {
    const groups = [makeGroup({ id: 'g2' }), makeGroup({ id: 'g1' })]
    expect(pickDefaultGroupForUser(groups, null)?.id).toBe('g2')
  })
})
