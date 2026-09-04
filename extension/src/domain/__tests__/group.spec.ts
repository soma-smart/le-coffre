import { describe, expect, it } from 'vitest'

import { pickDefaultGroup, sortGroups } from '../group'
import type { Group } from '../group'

function group(overrides: Partial<Group> = {}): Group {
  return {
    id: 'g1',
    name: 'Marketing',
    isPersonal: false,
    isOwner: false,
    ...overrides,
  }
}

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
