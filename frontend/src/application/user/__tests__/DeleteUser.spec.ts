import { describe, expect, it } from 'vitest'
import { DeleteUserUseCase } from '@/application/user/DeleteUser'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import { UserNotFoundError } from '@/domain/user/errors'

describe('DeleteUserUseCase', () => {
  it('removes the stored user', async () => {
    const repo = new InMemoryUserRepository().seed({
      id: 'u1',
      username: 'alice',
      email: 'alice@example.com',
      name: 'Alice',
      roles: [],
      personalGroupId: null,
      isSso: false,
    })

    await new DeleteUserUseCase(repo).execute({ userId: 'u1' })

    expect(await repo.list()).toEqual([])
  })

  it('propagates UserNotFoundError for unknown id', async () => {
    await expect(
      new DeleteUserUseCase(new InMemoryUserRepository()).execute({ userId: 'missing' }),
    ).rejects.toBeInstanceOf(UserNotFoundError)
  })
})
