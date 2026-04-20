import { describe, expect, it } from 'vitest'
import { ListPasswordAccessUseCase } from '@/application/password/ListPasswordAccess'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { PasswordNotFoundError } from '@/domain/password/errors'

describe('ListPasswordAccessUseCase', () => {
  it('returns the access entries reflecting the owning + shared groups', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'owner-group' })
    await repo.share('pwd-1', 'shared-group')

    const access = await new ListPasswordAccessUseCase(repo).execute({ passwordId: 'pwd-1' })

    expect(access.resourceId).toBe('pwd-1')
    expect(access.groups.map((g) => g.userId).sort()).toEqual(['owner-group', 'shared-group'])
    const owner = access.groups.find((g) => g.userId === 'owner-group')!
    const shared = access.groups.find((g) => g.userId === 'shared-group')!
    expect(owner.isOwner).toBe(true)
    expect(shared.isOwner).toBe(false)
  })

  it('propagates PasswordNotFoundError for an unknown id', async () => {
    await expect(
      new ListPasswordAccessUseCase(new InMemoryPasswordRepository()).execute({
        passwordId: 'missing',
      }),
    ).rejects.toBeInstanceOf(PasswordNotFoundError)
  })
})
