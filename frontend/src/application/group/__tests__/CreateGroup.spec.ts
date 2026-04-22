import { describe, expect, it } from 'vitest'
import { CreateGroupUseCase } from '@/application/group/CreateGroup'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import { GroupNameRequiredError } from '@/domain/group/errors'

describe('CreateGroupUseCase', () => {
  it('creates a group and returns its id', async () => {
    const repo = new InMemoryGroupRepository().useIdGenerator(() => 'group-42')
    const id = await new CreateGroupUseCase(repo).execute({ name: 'Team' })
    expect(id).toBe('group-42')
    expect((await repo.get('group-42')).name).toBe('Team')
  })

  it('trims whitespace around the name', async () => {
    const repo = new InMemoryGroupRepository().useIdGenerator(() => 'g1')
    await new CreateGroupUseCase(repo).execute({ name: '   Team   ' })
    expect((await repo.get('g1')).name).toBe('Team')
  })

  it('rejects a blank name', async () => {
    await expect(
      new CreateGroupUseCase(new InMemoryGroupRepository()).execute({ name: '  ' }),
    ).rejects.toBeInstanceOf(GroupNameRequiredError)
  })
})
