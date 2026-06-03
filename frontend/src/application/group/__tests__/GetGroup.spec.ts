import { describe, expect, it } from 'vitest'
import { GetGroupUseCase } from '@/application/group/GetGroup'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import { GroupNotFoundError } from '@/domain/group/errors'

describe('GetGroupUseCase', () => {
  it('returns the seeded group', async () => {
    const repo = new InMemoryGroupRepository().seed({
      id: 'g1',
      name: 'Team',
      isPersonal: false,
      userId: null,
      owners: [],
      members: [],
    })
    expect((await new GetGroupUseCase(repo).execute({ groupId: 'g1' })).name).toBe('Team')
  })

  it('propagates GroupNotFoundError for unknown id', async () => {
    await expect(
      new GetGroupUseCase(new InMemoryGroupRepository()).execute({ groupId: 'missing' }),
    ).rejects.toBeInstanceOf(GroupNotFoundError)
  })
})
