import { describe, expect, it } from 'vitest'
import { DeleteGroupUseCase } from '@/application/group/DeleteGroup'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import { GroupNotFoundError } from '@/domain/group/errors'

describe('DeleteGroupUseCase', () => {
  it('removes the stored group', async () => {
    const repo = new InMemoryGroupRepository().seed({
      id: 'g1',
      name: 'Team',
      isPersonal: false,
      userId: null,
      owners: [],
      members: [],
    })
    await new DeleteGroupUseCase(repo).execute({ groupId: 'g1' })
    expect(await repo.list()).toEqual([])
  })

  it('propagates GroupNotFoundError for unknown id', async () => {
    await expect(
      new DeleteGroupUseCase(new InMemoryGroupRepository()).execute({ groupId: 'missing' }),
    ).rejects.toBeInstanceOf(GroupNotFoundError)
  })
})
