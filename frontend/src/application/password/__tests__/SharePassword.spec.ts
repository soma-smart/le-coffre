import { describe, expect, it } from 'vitest'
import { SharePasswordUseCase, UnsharePasswordUseCase } from '@/application/password/SharePassword'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { PasswordGroupRequiredError, PasswordNotFoundError } from '@/domain/password/errors'

describe('SharePasswordUseCase', () => {
  it('adds the target group to the accessible group ids', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'group-personal' })

    await new SharePasswordUseCase(repo).execute({
      passwordId: 'pwd-1',
      groupId: 'group-team',
    })

    const [stored] = await repo.list()
    expect(stored.accessibleGroupIds).toEqual(
      expect.arrayContaining(['group-personal', 'group-team']),
    )
  })

  it('rejects an empty group id', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'g' })

    await expect(
      new SharePasswordUseCase(repo).execute({ passwordId: 'pwd-1', groupId: '' }),
    ).rejects.toBeInstanceOf(PasswordGroupRequiredError)
  })

  it('propagates PasswordNotFoundError when the password does not exist', async () => {
    await expect(
      new SharePasswordUseCase(new InMemoryPasswordRepository()).execute({
        passwordId: 'missing',
        groupId: 'g',
      }),
    ).rejects.toBeInstanceOf(PasswordNotFoundError)
  })
})

describe('UnsharePasswordUseCase', () => {
  it('removes the target group from the accessible group ids', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'owner' })
    await repo.share('pwd-1', 'extra')

    await new UnsharePasswordUseCase(repo).execute({
      passwordId: 'pwd-1',
      groupId: 'extra',
    })

    const [stored] = await repo.list()
    expect(stored.accessibleGroupIds).not.toContain('extra')
  })

  it('rejects an empty group id', async () => {
    await expect(
      new UnsharePasswordUseCase(new InMemoryPasswordRepository()).execute({
        passwordId: 'pwd-1',
        groupId: '',
      }),
    ).rejects.toBeInstanceOf(PasswordGroupRequiredError)
  })
})
