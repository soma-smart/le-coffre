import { describe, expect, it } from 'vitest'
import { DeletePasswordUseCase } from '@/application/password/DeletePassword'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { PasswordNotFoundError } from '@/domain/password/errors'

describe('DeletePasswordUseCase', () => {
  it('removes a stored password', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'g' })

    await new DeletePasswordUseCase(repo).execute({ passwordId: 'pwd-1' })

    expect(await repo.list()).toEqual([])
  })

  it('propagates PasswordNotFoundError when the password does not exist', async () => {
    await expect(
      new DeletePasswordUseCase(new InMemoryPasswordRepository()).execute({
        passwordId: 'missing',
      }),
    ).rejects.toBeInstanceOf(PasswordNotFoundError)
  })
})
