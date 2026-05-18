import { describe, expect, it } from 'vitest'
import { UpdateUserUseCase } from '@/application/user/UpdateUser'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import {
  UserEmailRequiredError,
  UserNameRequiredError,
  UserNotFoundError,
  UserUsernameRequiredError,
} from '@/domain/user/errors'

function seedAlice() {
  return new InMemoryUserRepository().seed({
    id: 'u1',
    username: 'alice',
    email: 'alice@example.com',
    name: 'Alice',
    roles: [],
    personalGroupId: null,
    isSso: false,
  })
}

describe('UpdateUserUseCase', () => {
  it('updates all mutable fields', async () => {
    const repo = seedAlice()

    await new UpdateUserUseCase(repo).execute({
      id: 'u1',
      username: 'alice2',
      email: 'alice2@example.com',
      name: 'Alice Two',
    })

    const stored = await repo.get('u1')
    expect(stored).toMatchObject({
      username: 'alice2',
      email: 'alice2@example.com',
      name: 'Alice Two',
    })
  })

  it('rejects blank fields', async () => {
    const useCase = new UpdateUserUseCase(seedAlice())
    await expect(
      useCase.execute({ id: 'u1', username: ' ', email: 'e', name: 'n' }),
    ).rejects.toBeInstanceOf(UserUsernameRequiredError)
    await expect(
      useCase.execute({ id: 'u1', username: 'u', email: ' ', name: 'n' }),
    ).rejects.toBeInstanceOf(UserEmailRequiredError)
    await expect(
      useCase.execute({ id: 'u1', username: 'u', email: 'e', name: ' ' }),
    ).rejects.toBeInstanceOf(UserNameRequiredError)
  })

  it('propagates UserNotFoundError for unknown id', async () => {
    await expect(
      new UpdateUserUseCase(new InMemoryUserRepository()).execute({
        id: 'missing',
        username: 'u',
        email: 'e',
        name: 'n',
      }),
    ).rejects.toBeInstanceOf(UserNotFoundError)
  })
})
