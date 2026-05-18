import { describe, expect, it } from 'vitest'
import { RegisterAdminUseCase } from '@/application/auth/RegisterAdmin'
import { InMemoryAuthGateway } from '@/infrastructure/in_memory/InMemoryAuthGateway'
import {
  AuthDisplayNameRequiredError,
  AuthEmailRequiredError,
  AuthPasswordRequiredError,
} from '@/domain/auth/errors'

describe('RegisterAdminUseCase', () => {
  it('creates the admin account and returns a non-empty id', async () => {
    const gw = new InMemoryAuthGateway()
    const id = await new RegisterAdminUseCase(gw).execute({
      email: 'admin@example.com',
      password: 'secret',
      displayName: 'Admin',
    })
    expect(id).toMatch(/^admin-/)
  })

  it('trims email + displayName before submission', async () => {
    const gw = new InMemoryAuthGateway()
    await new RegisterAdminUseCase(gw).execute({
      email: '  admin@example.com  ',
      password: 'secret',
      displayName: '  Admin  ',
    })
    // The stored admin credentials can be exercised by a subsequent login.
    const { LoginWithPasswordUseCase } = await import('@/application/auth/LoginWithPassword')
    await expect(
      new LoginWithPasswordUseCase(gw).execute({
        email: 'admin@example.com',
        password: 'secret',
      }),
    ).resolves.toBeUndefined()
  })

  it.each<[string, Record<string, string>, unknown]>([
    ['blank email', { email: '  ' }, AuthEmailRequiredError],
    ['empty password', { password: '' }, AuthPasswordRequiredError],
    ['blank display name', { displayName: '  ' }, AuthDisplayNameRequiredError],
  ])('rejects %s', async (_label, override, ErrorType) => {
    await expect(
      new RegisterAdminUseCase(new InMemoryAuthGateway()).execute({
        email: 'admin@example.com',
        password: 'secret',
        displayName: 'Admin',
        ...override,
      }),
    ).rejects.toBeInstanceOf(ErrorType as new () => Error)
  })
})
