import { describe, expect, it } from 'vitest'
import { DemoteOwnerToMemberUseCase } from '@/application/group/DemoteOwnerToMember'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import {
  GroupLastOwnerError,
  GroupNotFoundError,
  GroupUserRequiredError,
} from '@/domain/group/errors'

function seed() {
  return new InMemoryGroupRepository().seed({
    id: 'g1',
    name: 'Team',
    isPersonal: false,
    userId: null,
    owners: ['owner-1', 'owner-2'],
    members: ['user-2'],
  })
}

describe('DemoteOwnerToMemberUseCase', () => {
  it('removes the user from the owners list and adds them to members', async () => {
    const repo = seed()
    await new DemoteOwnerToMemberUseCase(repo).execute({ groupId: 'g1', userId: 'owner-2' })
    const group = await repo.get('g1')
    expect(group.owners).not.toContain('owner-2')
    expect(group.members).toContain('owner-2')
  })

  it('does not duplicate an existing membership entry', async () => {
    const repo = new InMemoryGroupRepository().seed({
      id: 'g1',
      name: 'Team',
      isPersonal: false,
      userId: null,
      owners: ['owner-1', 'owner-2'],
      members: ['owner-1'],
    })
    await new DemoteOwnerToMemberUseCase(repo).execute({ groupId: 'g1', userId: 'owner-1' })
    const group = await repo.get('g1')
    expect(group.owners).not.toContain('owner-1')
    expect(group.members.filter((id) => id === 'owner-1')).toHaveLength(1)
  })

  it('rejects demoting the last owner of a group', async () => {
    const repo = new InMemoryGroupRepository().seed({
      id: 'g1',
      name: 'Team',
      isPersonal: false,
      userId: null,
      owners: ['owner-1'],
      members: [],
    })
    await expect(
      new DemoteOwnerToMemberUseCase(repo).execute({ groupId: 'g1', userId: 'owner-1' }),
    ).rejects.toBeInstanceOf(GroupLastOwnerError)
    expect((await repo.get('g1')).owners).toContain('owner-1')
  })

  it('rejects an empty user id', async () => {
    await expect(
      new DemoteOwnerToMemberUseCase(seed()).execute({ groupId: 'g1', userId: '' }),
    ).rejects.toBeInstanceOf(GroupUserRequiredError)
  })

  it('propagates GroupNotFoundError for unknown group', async () => {
    await expect(
      new DemoteOwnerToMemberUseCase(new InMemoryGroupRepository()).execute({
        groupId: 'missing',
        userId: 'u',
      }),
    ).rejects.toBeInstanceOf(GroupNotFoundError)
  })
})
