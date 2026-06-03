import { describe, expect, it } from 'vitest'
import { GetCurrentUserUseCase } from '@/application/user/GetCurrentUser'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import type { User } from '@/domain/user/User'

const sampleUser: User = {
  id: 'user-1',
  username: 'alice',
  email: 'alice@example.com',
  name: 'Alice',
  roles: ['admin'],
  personalGroupId: 'group-1',
  isSso: false,
}

describe('GetCurrentUserUseCase', () => {
  it('returns the current user seeded on the repository', async () => {
    const repo = new InMemoryUserRepository().setCurrent(sampleUser)
    expect(await new GetCurrentUserUseCase(repo).execute()).toEqual(sampleUser)
  })

  it('returns null when no current user is set', async () => {
    const repo = new InMemoryUserRepository()
    expect(await new GetCurrentUserUseCase(repo).execute()).toBeNull()
  })
})
