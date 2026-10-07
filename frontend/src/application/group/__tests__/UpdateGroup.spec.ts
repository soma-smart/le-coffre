import { describe, expect, it } from 'vitest'
import { UpdateGroupUseCase } from '@/application/group/UpdateGroup'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import { GroupNameRequiredError, GroupNotFoundError } from '@/domain/group/errors'

function seed() {
  return new InMemoryGroupRepository().seed({
    id: 'g1',
    name: 'Old',
    isPersonal: false,
    userId: null,
    owners: [],
    members: [],
  })
}

describe('UpdateGroupUseCase', () => {
  it('updates the name (trimmed)', async () => {
    const repo = seed()
    await new UpdateGroupUseCase(repo).execute({ groupId: 'g1', name: '  New  ' })
    expect((await repo.get('g1')).name).toBe('New')
  })

  it('rejects a blank name', async () => {
    await expect(
      new UpdateGroupUseCase(seed()).execute({ groupId: 'g1', name: '  ' }),
    ).rejects.toBeInstanceOf(GroupNameRequiredError)
  })

  it('propagates GroupNotFoundError for unknown id', async () => {
    await expect(
      new UpdateGroupUseCase(new InMemoryGroupRepository()).execute({
        groupId: 'missing',
        name: 'x',
      }),
    ).rejects.toBeInstanceOf(GroupNotFoundError)
  })
})
