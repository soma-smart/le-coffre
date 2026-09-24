import { describe, expect, it } from 'vitest'
import { SearchUsersUseCase } from '@/application/user/SearchUsers'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'

describe('SearchUsersUseCase', () => {
  it('returns users matching the query by name, username or id', async () => {
    const repo = new InMemoryUserRepository()
      .seed({
        id: 'u1',
        username: 'jdoe',
        email: 'jdoe@example.com',
        name: 'Jane Doe',
        roles: [],
        personalGroupId: null,
        isSso: false,
      })
      .seed({
        id: 'u2',
        username: 'bob',
        email: 'bob@example.com',
        name: 'Bob',
        roles: [],
        personalGroupId: null,
        isSso: false,
      })

    const results = await new SearchUsersUseCase(repo).execute({ query: 'jdo' })

    expect(results.map((u) => u.id)).toEqual(['u1'])
  })

  it('returns an empty list when nothing matches', async () => {
    const repo = new InMemoryUserRepository()

    const results = await new SearchUsersUseCase(repo).execute({ query: 'nobody' })

    expect(results).toEqual([])
  })
})
