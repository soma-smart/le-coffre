import { describe, expect, it } from 'vitest'
import { RemoveMemberFromGroupUseCase } from '@/application/group/RemoveMemberFromGroup'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import { GroupNotFoundError, GroupUserRequiredError } from '@/domain/group/errors'

function seed() {
  return new InMemoryGroupRepository().seed({
    id: 'g1',
    name: 'Team',
    isPersonal: false,
    userId: null,
    owners: ['owner-1'],
    members: ['owner-1', 'user-2'],
  })
}

describe('RemoveMemberFromGroupUseCase', () => {
  it('removes the user from members (and owners if present)', async () => {
    const repo = seed()
    await new RemoveMemberFromGroupUseCase(repo).execute({
      groupId: 'g1',
      userId: 'owner-1',
    })
    const group = await repo.get('g1')
    expect(group.members).not.toContain('owner-1')
    expect(group.owners).not.toContain('owner-1')
  })

  it('rejects an empty user id', async () => {
    await expect(
      new RemoveMemberFromGroupUseCase(seed()).execute({ groupId: 'g1', userId: '' }),
    ).rejects.toBeInstanceOf(GroupUserRequiredError)
  })

  it('propagates GroupNotFoundError for unknown group', async () => {
    await expect(
      new RemoveMemberFromGroupUseCase(new InMemoryGroupRepository()).execute({
        groupId: 'missing',
        userId: 'u',
      }),
    ).rejects.toBeInstanceOf(GroupNotFoundError)
  })
})
