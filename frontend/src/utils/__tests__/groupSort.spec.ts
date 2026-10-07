import { describe, expect, it } from 'vitest'
import type { Group } from '@/domain/group/Group'
import { sortGroups, sortGroupsByName } from '@/utils/groupSort'

const g = (overrides: Partial<Group>): Group => ({
  id: 'g',
  name: 'Group',
  isPersonal: false,
  userId: null,
  owners: [],
  members: [],
  ...overrides,
})

describe('sortGroupsByName', () => {
  it('sorts alphabetically when no personal pin is provided', () => {
    const out = sortGroupsByName([g({ id: 'b', name: 'Beta' }), g({ id: 'a', name: 'Alpha' })])
    expect(out.map((x) => x.id)).toEqual(['a', 'b'])
  })

  it('pins the personal group id first when provided', () => {
    const out = sortGroupsByName(
      [
        g({ id: 'shared-z', name: 'Zeta' }),
        g({ id: 'personal', name: 'Zzz Personal', isPersonal: true }),
        g({ id: 'shared-a', name: 'Alpha' }),
      ],
      'personal',
    )
    expect(out.map((x) => x.id)).toEqual(['personal', 'shared-a', 'shared-z'])
  })

  it('falls back to isPersonal flag when no personal id is given', () => {
    const out = sortGroupsByName([
      g({ id: 'shared', name: 'Zzz' }),
      g({ id: 'personal', name: 'Aaa', isPersonal: true }),
    ])
    expect(out.map((x) => x.id)).toEqual(['personal', 'shared'])
  })

  it('does not mutate the input array', () => {
    const input = [g({ id: 'b', name: 'Beta' }), g({ id: 'a', name: 'Alpha' })]
    const snapshot = input.map((x) => x.id)
    sortGroupsByName(input)
    expect(input.map((x) => x.id)).toEqual(snapshot)
  })

  it('handles empty input', () => {
    expect(sortGroupsByName([])).toEqual([])
  })
})

describe('sortGroups (alias)', () => {
  it('delegates to sortGroupsByName', () => {
    const groups = [g({ id: 'b', name: 'Beta' }), g({ id: 'a', name: 'Alpha' })]
    expect(sortGroups(groups).map((x) => x.id)).toEqual(['a', 'b'])
  })
})
