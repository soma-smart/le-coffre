import { describe, expect, it } from 'vitest'
import { UpdateShareExpirationUseCase } from '@/application/password/UpdateShareExpiration'
import {
  PasswordGroupRequiredError,
  ShareExpirationInvalidError,
  ShareNotFoundError,
} from '@/domain/password/errors'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'

const NOW = new Date('2026-07-27T12:00:00Z')

async function repoWithSharedPassword(expiresAt: string | null = '2026-07-27T13:00:00Z') {
  const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
  await repo.create({ name: 'Gmail', password: 'x', groupId: 'owner' })
  await repo.share('pwd-1', 'group-team', expiresAt)
  return repo
}

async function expiryOf(repo: InMemoryPasswordRepository, groupId: string) {
  const access = await repo.listAccess('pwd-1')
  return access.groups.find((group) => group.groupId === groupId)?.expiresAt
}

describe('UpdateShareExpirationUseCase', () => {
  it('extends a share to a later date', async () => {
    const repo = await repoWithSharedPassword()

    await new UpdateShareExpirationUseCase(repo).execute(
      { passwordId: 'pwd-1', groupId: 'group-team', expiresAt: '2026-08-27T12:00:00Z' },
      NOW,
    )

    expect(await expiryOf(repo, 'group-team')).toBe('2026-08-27T12:00:00Z')
  })

  it('lifts the deadline entirely when given null', async () => {
    const repo = await repoWithSharedPassword()

    await new UpdateShareExpirationUseCase(repo).execute(
      { passwordId: 'pwd-1', groupId: 'group-team', expiresAt: null },
      NOW,
    )

    expect(await expiryOf(repo, 'group-team')).toBeNull()
  })

  it('puts a deadline on a share that had none', async () => {
    const repo = await repoWithSharedPassword(null)

    await new UpdateShareExpirationUseCase(repo).execute(
      { passwordId: 'pwd-1', groupId: 'group-team', expiresAt: '2026-08-27T12:00:00Z' },
      NOW,
    )

    expect(await expiryOf(repo, 'group-team')).toBe('2026-08-27T12:00:00Z')
  })

  it('revives a share that already lapsed, since the new date is in the future', async () => {
    const repo = await repoWithSharedPassword('2026-07-27T11:00:00Z')

    await new UpdateShareExpirationUseCase(repo).execute(
      { passwordId: 'pwd-1', groupId: 'group-team', expiresAt: '2026-08-27T12:00:00Z' },
      NOW,
    )

    expect(await expiryOf(repo, 'group-team')).toBe('2026-08-27T12:00:00Z')
  })

  it('rejects a deadline that has already passed', async () => {
    const repo = await repoWithSharedPassword()

    await expect(
      new UpdateShareExpirationUseCase(repo).execute(
        { passwordId: 'pwd-1', groupId: 'group-team', expiresAt: '2026-07-27T11:00:00Z' },
        NOW,
      ),
    ).rejects.toBeInstanceOf(ShareExpirationInvalidError)
  })

  it('rejects an empty group id', async () => {
    const repo = await repoWithSharedPassword()

    await expect(
      new UpdateShareExpirationUseCase(repo).execute(
        { passwordId: 'pwd-1', groupId: '', expiresAt: null },
        NOW,
      ),
    ).rejects.toBeInstanceOf(PasswordGroupRequiredError)
  })

  it('propagates ShareNotFoundError when the group holds no share', async () => {
    const repo = await repoWithSharedPassword()

    await expect(
      new UpdateShareExpirationUseCase(repo).execute(
        { passwordId: 'pwd-1', groupId: 'stranger', expiresAt: null },
        NOW,
      ),
    ).rejects.toBeInstanceOf(ShareNotFoundError)
  })
})
