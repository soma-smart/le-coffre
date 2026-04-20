import { describe, expect, it } from 'vitest'
import { AddMemberToGroupUseCase } from '@/application/group/AddMemberToGroup'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import { GroupNotFoundError, GroupUserRequiredError } from '@/domain/group/errors'

function seed() {
  return new InMemoryGroupRepository().seed({
    id: 'g1',
    name: 'Team',
    isPersonal: false,
    userId: null,
    owners: ['owner-1'],
    members: [],
  })
}

describe('AddMemberToGroupUseCase', () => {
  it('adds the user to the members list', async () => {
    const repo = seed()
    await new AddMemberToGroupUseCase(repo).execute({ groupId: 'g1', userId: 'user-2' })
    expect((await repo.get('g1')).members).toContain('user-2')
  })

  it('is idempotent — no duplicate member entry', async () => {
    const repo = seed()
    const useCase = new AddMemberToGroupUseCase(repo)
    await useCase.execute({ groupId: 'g1', userId: 'user-2' })
    await useCase.execute({ groupId: 'g1', userId: 'user-2' })
    const members = (await repo.get('g1')).members
    expect(members.filter((id) => id === 'user-2')).toHaveLength(1)
  })

  it('rejects an empty user id', async () => {
    await expect(
      new AddMemberToGroupUseCase(seed()).execute({ groupId: 'g1', userId: '' }),
    ).rejects.toBeInstanceOf(GroupUserRequiredError)
  })

  it('propagates GroupNotFoundError for unknown group', async () => {
    await expect(
      new AddMemberToGroupUseCase(new InMemoryGroupRepository()).execute({
        groupId: 'missing',
        userId: 'u',
      }),
    ).rejects.toBeInstanceOf(GroupNotFoundError)
  })
})
