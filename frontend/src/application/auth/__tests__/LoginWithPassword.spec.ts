import { describe, expect, it } from 'vitest'
import { LoginWithPasswordUseCase } from '@/application/auth/LoginWithPassword'
import { InMemoryAuthGateway } from '@/infrastructure/in_memory/InMemoryAuthGateway'
import {
  AuthEmailRequiredError,
  AuthPasswordRequiredError,
  InvalidCredentialsError,
} from '@/domain/auth/errors'

describe('LoginWithPasswordUseCase', () => {
  it('succeeds when credentials match the seeded admin', async () => {
    const gw = new InMemoryAuthGateway().seedAdmin('admin@example.com', 'correct')
    await expect(
      new LoginWithPasswordUseCase(gw).execute({
        email: 'admin@example.com',
        password: 'correct',
      }),
    ).resolves.toBeUndefined()
  })

  it('throws InvalidCredentialsError when password is wrong', async () => {
    const gw = new InMemoryAuthGateway().seedAdmin('admin@example.com', 'correct')
    await expect(
      new LoginWithPasswordUseCase(gw).execute({
        email: 'admin@example.com',
        password: 'wrong',
      }),
    ).rejects.toBeInstanceOf(InvalidCredentialsError)
  })

  it('trims the email before submitting', async () => {
    const gw = new InMemoryAuthGateway().seedAdmin('admin@example.com', 'correct')
    await expect(
      new LoginWithPasswordUseCase(gw).execute({
        email: '  admin@example.com  ',
        password: 'correct',
      }),
    ).resolves.toBeUndefined()
  })

  it('rejects a blank email', async () => {
    await expect(
      new LoginWithPasswordUseCase(new InMemoryAuthGateway()).execute({
        email: '  ',
        password: 'x',
      }),
    ).rejects.toBeInstanceOf(AuthEmailRequiredError)
  })

  it('rejects an empty password', async () => {
    await expect(
      new LoginWithPasswordUseCase(new InMemoryAuthGateway()).execute({
        email: 'e',
        password: '',
      }),
    ).rejects.toBeInstanceOf(AuthPasswordRequiredError)
  })
})
