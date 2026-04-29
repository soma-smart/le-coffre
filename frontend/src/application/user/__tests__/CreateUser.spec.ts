import { describe, expect, it } from 'vitest'
import { CreateUserUseCase } from '@/application/user/CreateUser'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import {
  UserEmailRequiredError,
  UserNameRequiredError,
  UserPasswordRequiredError,
  UserUsernameRequiredError,
} from '@/domain/user/errors'

describe('CreateUserUseCase', () => {
  it('creates a user through the repository and returns its id', async () => {
    const repo = new InMemoryUserRepository().useIdGenerator(() => 'user-42')

    const id = await new CreateUserUseCase(repo).execute({
      username: 'alice',
      email: 'alice@example.com',
      name: 'Alice',
      password: 'secret',
    })

    expect(id).toBe('user-42')
    const stored = await repo.get('user-42')
    expect(stored).toMatchObject({ username: 'alice', email: 'alice@example.com', name: 'Alice' })
  })

  it('trims whitespace around username, email and name', async () => {
    const repo = new InMemoryUserRepository().useIdGenerator(() => 'u1')

    await new CreateUserUseCase(repo).execute({
      username: '  alice  ',
      email: '  alice@example.com  ',
      name: '  Alice  ',
      password: 'secret',
    })

    const stored = await repo.get('u1')
    expect(stored).toMatchObject({
      username: 'alice',
      email: 'alice@example.com',
      name: 'Alice',
    })
  })

  it.each<[string, Record<string, string>, unknown]>([
    ['empty username', { username: '' }, UserUsernameRequiredError],
    ['empty email', { email: '' }, UserEmailRequiredError],
    ['empty name', { name: '' }, UserNameRequiredError],
    ['empty password', { password: '' }, UserPasswordRequiredError],
  ])('rejects %s', async (_label, override, ErrorType) => {
    const useCase = new CreateUserUseCase(new InMemoryUserRepository())
    await expect(
      useCase.execute({
        username: 'alice',
        email: 'alice@example.com',
        name: 'Alice',
        password: 'secret',
        ...override,
      }),
    ).rejects.toBeInstanceOf(ErrorType as new () => Error)
  })
})
