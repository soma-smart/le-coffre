import { describe, expect, it } from 'vitest'
import { GetPasswordUseCase } from '@/application/password/GetPassword'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { PasswordNotFoundError } from '@/domain/password/errors'

describe('GetPasswordUseCase', () => {
  it('returns the decrypted value for a known password', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Gmail', password: 'super-secret', groupId: 'g' })

    const result = await new GetPasswordUseCase(repo).execute({ passwordId: 'pwd-1' })

    expect(result).toBe('super-secret')
  })

  it('propagates PasswordNotFoundError for an unknown id', async () => {
    const useCase = new GetPasswordUseCase(new InMemoryPasswordRepository())

    await expect(useCase.execute({ passwordId: 'missing' })).rejects.toBeInstanceOf(
      PasswordNotFoundError,
    )
  })
})
