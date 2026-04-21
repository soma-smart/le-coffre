import { describe, expect, it } from 'vitest'
import { UpdatePasswordUseCase } from '@/application/password/UpdatePassword'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import {
  PasswordNameRequiredError,
  PasswordNotFoundError,
  PasswordUrlInvalidError,
} from '@/domain/password/errors'

describe('UpdatePasswordUseCase', () => {
  it('updates name, secret and folder together', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Old', password: 'x', groupId: 'g' })

    await new UpdatePasswordUseCase(repo).execute({
      id: 'pwd-1',
      name: 'New',
      password: 'new-secret',
      folder: 'Work',
    })

    const [stored] = await repo.list()
    expect(stored.name).toBe('New')
    expect(stored.folder).toBe('Work')
    expect(await repo.getDecryptedValue('pwd-1')).toBe('new-secret')
  })

  it('keeps the existing secret when no password is supplied', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Old', password: 'original', groupId: 'g' })

    await new UpdatePasswordUseCase(repo).execute({ id: 'pwd-1', name: 'Renamed' })

    expect(await repo.getDecryptedValue('pwd-1')).toBe('original')
  })

  it('trims and rejects a blank name', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Old', password: 'x', groupId: 'g' })

    await expect(
      new UpdatePasswordUseCase(repo).execute({ id: 'pwd-1', name: '   ' }),
    ).rejects.toBeInstanceOf(PasswordNameRequiredError)
  })

  it('propagates PasswordNotFoundError for an unknown id', async () => {
    await expect(
      new UpdatePasswordUseCase(new InMemoryPasswordRepository()).execute({
        id: 'missing',
        name: 'X',
      }),
    ).rejects.toBeInstanceOf(PasswordNotFoundError)
  })

  it('rejects a url that does not start with http(s)://', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')
    await repo.create({ name: 'Old', password: 'x', groupId: 'g' })

    await expect(
      new UpdatePasswordUseCase(repo).execute({ id: 'pwd-1', name: 'Old', url: 'ftp://x' }),
    ).rejects.toBeInstanceOf(PasswordUrlInvalidError)
  })
})
