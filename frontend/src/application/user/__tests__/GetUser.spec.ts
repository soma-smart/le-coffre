import { describe, expect, it } from 'vitest'
import { GetUserUseCase } from '@/application/user/GetUser'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import { UserNotFoundError } from '@/domain/user/errors'

describe('GetUserUseCase', () => {
  it('returns a seeded user by id', async () => {
    const repo = new InMemoryUserRepository().seed({
      id: 'user-1',
      username: 'alice',
      email: 'alice@example.com',
      name: 'Alice',
      roles: [],
      personalGroupId: null,
      isSso: false,
    })

    const result = await new GetUserUseCase(repo).execute({ userId: 'user-1' })

    expect(result.name).toBe('Alice')
  })

  it('propagates UserNotFoundError for an unknown id', async () => {
    await expect(
      new GetUserUseCase(new InMemoryUserRepository()).execute({ userId: 'missing' }),
    ).rejects.toBeInstanceOf(UserNotFoundError)
  })
})
