import { describe, expect, it } from 'vitest'
import { ListUsersUseCase } from '@/application/user/ListUsers'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'

describe('ListUsersUseCase', () => {
  it('returns every seeded user', async () => {
    const repo = new InMemoryUserRepository()
      .seed({
        id: 'u1',
        username: 'alice',
        email: 'alice@example.com',
        name: 'Alice',
        roles: [],
        personalGroupId: null,
        isSso: false,
      })
      .seed({
        id: 'u2',
        username: 'bob',
        email: 'bob@example.com',
        name: 'Bob',
        roles: ['admin'],
        personalGroupId: null,
        isSso: false,
      })

    const users = await new ListUsersUseCase(repo).execute()

    expect(users.map((u) => u.username).sort()).toEqual(['alice', 'bob'])
  })
})
