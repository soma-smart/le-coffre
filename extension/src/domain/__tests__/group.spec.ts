import { describe, expect, it } from 'vitest'

import { filterGroupsForUser, pickDefaultGroup, sortGroups } from '../group'
import type { Group } from '../group'

function group(overrides: Partial<Group> = {}): Group {
  return {
    id: 'g1',
    name: 'Marketing',
    isPersonal: false,
    userId: null,
    owners: [],
    members: [],
    ...overrides,
  }
}

describe('filterGroupsForUser', () => {
  it('drops groups the user does not belong to', () => {
    // GET /api/groups returns EVERY group on the instance, including other
    // people's personal groups. Skipping this filter would offer the user
    // groups they cannot read, and the entry list would come back empty.
    const groups = [
      group({ id: 'mine', members: ['me'] }),
      group({ id: 'someone-elses', isPersonal: true, userId: 'them', owners: ['them'] }),
    ]

    expect(filterGroupsForUser(groups, 'me').map((g) => g.id)).toEqual(['mine'])
  })

  it('keeps groups the user owns', () => {
    const groups = [group({ id: 'owned', owners: ['me'] })]

    expect(filterGroupsForUser(groups, 'me').map((g) => g.id)).toEqual(['owned'])
  })

  it('returns nothing without a user id', () => {
    expect(filterGroupsForUser([group({ members: ['me'] })], null)).toEqual([])
  })
})

describe('sortGroups', () => {
  it('puts the personal group first', () => {
    const groups = [
      group({ id: 'a', name: 'Alpha' }),
      group({ id: 'p', name: 'Zeta', isPersonal: true }),
    ]

    expect(sortGroups(groups).map((g) => g.id)).toEqual(['p', 'a'])
  })

  it('sorts the rest alphabetically', () => {
    const groups = [group({ id: 'z', name: 'Zeta' }), group({ id: 'a', name: 'Alpha' })]

    expect(sortGroups(groups).map((g) => g.id)).toEqual(['a', 'z'])
  })

  it('does not mutate its input', () => {
    const groups = [group({ id: 'z', name: 'Zeta' }), group({ id: 'a', name: 'Alpha' })]
    sortGroups(groups)

    expect(groups.map((g) => g.id)).toEqual(['z', 'a'])
  })
})

describe('pickDefaultGroup', () => {
  it('prefers the personal group', () => {
    const groups = [group({ id: 'a', name: 'Alpha' }), group({ id: 'p', isPersonal: true })]

    expect(pickDefaultGroup(groups)?.id).toBe('p')
  })

  it('returns null when there are no groups', () => {
    expect(pickDefaultGroup([])).toBeNull()
  })
})
