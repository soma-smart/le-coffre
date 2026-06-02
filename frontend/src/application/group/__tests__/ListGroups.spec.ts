import { describe, expect, it } from 'vitest'
import { ListGroupsUseCase } from '@/application/group/ListGroups'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'

function seed() {
  return new InMemoryGroupRepository()
    .seed({
      id: 'g1',
      name: 'Personal',
      isPersonal: true,
      userId: 'u1',
      owners: ['u1'],
      members: [],
    })
    .seed({
      id: 'g2',
      name: 'Team',
      isPersonal: false,
      userId: null,
      owners: ['u1'],
      members: ['u2'],
    })
}

describe('ListGroupsUseCase', () => {
  it('returns every group by default (includePersonal = true)', async () => {
    const result = await new ListGroupsUseCase(seed()).execute()
    expect(result.map((g) => g.id).sort()).toEqual(['g1', 'g2'])
  })

  it('filters out personal groups when includePersonal=false', async () => {
    const result = await new ListGroupsUseCase(seed()).execute({ includePersonal: false })
    expect(result.map((g) => g.id)).toEqual(['g2'])
  })
})
