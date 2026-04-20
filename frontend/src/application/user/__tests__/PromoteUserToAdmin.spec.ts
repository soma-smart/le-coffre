import { describe, expect, it } from 'vitest'
import { PromoteUserToAdminUseCase } from '@/application/user/PromoteUserToAdmin'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import { ADMIN_ROLE } from '@/domain/user/User'
import { UserNotFoundError } from '@/domain/user/errors'

describe('PromoteUserToAdminUseCase', () => {
  it('adds the admin role when missing', async () => {
    const repo = new InMemoryUserRepository().seed({
      id: 'u1',
      username: 'alice',
      email: 'alice@example.com',
      name: 'Alice',
      roles: [],
      personalGroupId: null,
      isSso: false,
    })

    await new PromoteUserToAdminUseCase(repo).execute({ userId: 'u1' })

    expect((await repo.get('u1')).roles).toContain(ADMIN_ROLE)
  })

  it('is idempotent — no duplicate admin role', async () => {
    const repo = new InMemoryUserRepository().seed({
      id: 'u1',
      username: 'alice',
      email: 'alice@example.com',
      name: 'Alice',
      roles: [ADMIN_ROLE],
      personalGroupId: null,
      isSso: false,
    })

    await new PromoteUserToAdminUseCase(repo).execute({ userId: 'u1' })

    const roles = (await repo.get('u1')).roles
    expect(roles.filter((r) => r === ADMIN_ROLE)).toHaveLength(1)
  })

  it('propagates UserNotFoundError for unknown id', async () => {
    await expect(
      new PromoteUserToAdminUseCase(new InMemoryUserRepository()).execute({ userId: 'missing' }),
    ).rejects.toBeInstanceOf(UserNotFoundError)
  })
})
