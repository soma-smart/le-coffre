import { describe, expect, it } from 'vitest'
import { UpdateUserPasswordUseCase } from '@/application/user/UpdateUserPassword'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import {
  IncorrectOldPasswordError,
  UserPasswordMustBeDifferentError,
  UserPasswordRequiredError,
} from '@/domain/user/errors'

function repoWithCurrent() {
  const repo = new InMemoryUserRepository()
  repo.setCurrent({
    id: 'u1',
    username: 'alice',
    email: 'alice@example.com',
    name: 'Alice',
    roles: [],
    personalGroupId: null,
    isSso: false,
  })
  repo.setPassword('u1', 'old-password')
  return repo
}

describe('UpdateUserPasswordUseCase', () => {
  it('updates the stored password when inputs are valid', async () => {
    const repo = repoWithCurrent()
    const useCase = new UpdateUserPasswordUseCase(repo)

    await useCase.execute({ oldPassword: 'old-password', newPassword: 'new-password' })

    // After rotation, re-using the OLD password should fail with the typed
    // IncorrectOldPasswordError, and re-using the NEW one as the "old" side
    // should succeed.
    await expect(
      useCase.execute({ oldPassword: 'old-password', newPassword: 'newer' }),
    ).rejects.toBeInstanceOf(IncorrectOldPasswordError)
    await expect(
      useCase.execute({ oldPassword: 'new-password', newPassword: 'newer' }),
    ).resolves.toBeUndefined()
  })

  it('rejects empty fields', async () => {
    const useCase = new UpdateUserPasswordUseCase(repoWithCurrent())
    await expect(useCase.execute({ oldPassword: '', newPassword: 'x' })).rejects.toBeInstanceOf(
      UserPasswordRequiredError,
    )
    await expect(useCase.execute({ oldPassword: 'x', newPassword: '' })).rejects.toBeInstanceOf(
      UserPasswordRequiredError,
    )
  })

  it('rejects reusing the same password', async () => {
    await expect(
      new UpdateUserPasswordUseCase(repoWithCurrent()).execute({
        oldPassword: 'same',
        newPassword: 'same',
      }),
    ).rejects.toBeInstanceOf(UserPasswordMustBeDifferentError)
  })
})
