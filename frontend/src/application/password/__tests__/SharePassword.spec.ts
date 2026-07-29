import { describe, expect, it } from 'vitest'
import { SharePasswordUseCase, UnsharePasswordUseCase } from '@/application/password/SharePassword'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import {
  PasswordGroupRequiredError,
  PasswordNotFoundError,
  ShareExpirationInvalidError,
} from '@/domain/password/errors'

const NOW = new Date('2026-07-27T12:00:00Z')

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

  it('records the deadline on a time-limited share', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'owner' })

    await new SharePasswordUseCase(repo).execute(
      { passwordId: 'pwd-1', groupId: 'group-team', expiresAt: '2026-07-28T12:00:00Z' },
      NOW,
    )

    const access = await repo.listAccess('pwd-1')
    const shared = access.groups.find((group) => group.groupId === 'group-team')
    expect(shared?.expiresAt).toBe('2026-07-28T12:00:00Z')
  })

  it('shares permanently when no deadline is given', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'owner' })

    await new SharePasswordUseCase(repo).execute(
      { passwordId: 'pwd-1', groupId: 'group-team' },
      NOW,
    )

    const access = await repo.listAccess('pwd-1')
    expect(access.groups.find((group) => group.groupId === 'group-team')?.expiresAt).toBeNull()
  })

  it('rejects a deadline that has already passed', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'owner' })

    await expect(
      new SharePasswordUseCase(repo).execute(
        { passwordId: 'pwd-1', groupId: 'group-team', expiresAt: '2026-07-27T11:00:00Z' },
        NOW,
      ),
    ).rejects.toBeInstanceOf(ShareExpirationInvalidError)
  })

  it('rejects a deadline that is not a date', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'owner' })

    await expect(
      new SharePasswordUseCase(repo).execute(
        { passwordId: 'pwd-1', groupId: 'group-team', expiresAt: 'not-a-date' },
        NOW,
      ),
    ).rejects.toBeInstanceOf(ShareExpirationInvalidError)
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
