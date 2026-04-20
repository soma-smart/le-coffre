import { describe, expect, it } from 'vitest'
import { PromoteMemberToOwnerUseCase } from '@/application/group/PromoteMemberToOwner'
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

describe('PromoteMemberToOwnerUseCase', () => {
  it('adds the user to the owners list', async () => {
    const repo = seed()
    await new PromoteMemberToOwnerUseCase(repo).execute({ groupId: 'g1', userId: 'user-2' })
    expect((await repo.get('g1')).owners).toContain('user-2')
  })

  it('is idempotent — no duplicate owner entry', async () => {
    const repo = seed()
    const useCase = new PromoteMemberToOwnerUseCase(repo)
    await useCase.execute({ groupId: 'g1', userId: 'owner-1' })
    expect((await repo.get('g1')).owners.filter((id) => id === 'owner-1')).toHaveLength(1)
  })

  it('rejects an empty user id', async () => {
    await expect(
      new PromoteMemberToOwnerUseCase(seed()).execute({ groupId: 'g1', userId: '' }),
    ).rejects.toBeInstanceOf(GroupUserRequiredError)
  })

  it('propagates GroupNotFoundError for unknown group', async () => {
    await expect(
      new PromoteMemberToOwnerUseCase(new InMemoryGroupRepository()).execute({
        groupId: 'missing',
        userId: 'u',
      }),
    ).rejects.toBeInstanceOf(GroupNotFoundError)
  })
})
