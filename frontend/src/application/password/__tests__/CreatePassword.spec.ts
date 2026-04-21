import { describe, expect, it } from 'vitest'
import { CreatePasswordUseCase } from '@/application/password/CreatePassword'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import {
  PasswordGroupRequiredError,
  PasswordNameRequiredError,
  PasswordUrlInvalidError,
  PasswordValueRequiredError,
} from '@/domain/password/errors'

describe('CreatePasswordUseCase', () => {
  it('persists the password and returns its id', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-42')
    const useCase = new CreatePasswordUseCase(repo)

    const id = await useCase.execute({
      name: 'Gmail',
      password: 'secret',
      groupId: 'group-personal',
    })

    expect(id).toBe('pwd-42')
    const [stored] = await repo.list()
    expect(stored).toMatchObject({
      id: 'pwd-42',
      name: 'Gmail',
      groupId: 'group-personal',
      accessibleGroupIds: ['group-personal'],
    })
    expect(await repo.getDecryptedValue('pwd-42')).toBe('secret')
  })

  it('trims whitespace around the name', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-1')

    await new CreatePasswordUseCase(repo).execute({
      name: '   Gmail   ',
      password: 'secret',
      groupId: 'g',
    })

    const [stored] = await repo.list()
    expect(stored.name).toBe('Gmail')
  })

  it('rejects a blank name', async () => {
    const useCase = new CreatePasswordUseCase(new InMemoryPasswordRepository())
    await expect(
      useCase.execute({ name: '   ', password: 'x', groupId: 'g' }),
    ).rejects.toBeInstanceOf(PasswordNameRequiredError)
  })

  it('rejects an empty secret', async () => {
    const useCase = new CreatePasswordUseCase(new InMemoryPasswordRepository())
    await expect(
      useCase.execute({ name: 'Gmail', password: '', groupId: 'g' }),
    ).rejects.toBeInstanceOf(PasswordValueRequiredError)
  })

  it('rejects a missing group id', async () => {
    const useCase = new CreatePasswordUseCase(new InMemoryPasswordRepository())
    await expect(
      useCase.execute({ name: 'Gmail', password: 'x', groupId: '' }),
    ).rejects.toBeInstanceOf(PasswordGroupRequiredError)
  })

  it('rejects a url that does not start with http(s)://', async () => {
    const useCase = new CreatePasswordUseCase(new InMemoryPasswordRepository())
    await expect(
      useCase.execute({ name: 'Gmail', password: 'x', groupId: 'g', url: 'ftp://x' }),
    ).rejects.toBeInstanceOf(PasswordUrlInvalidError)
  })

  it('accepts an https url', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-url')
    const useCase = new CreatePasswordUseCase(repo)

    await useCase.execute({
      name: 'Gmail',
      password: 'x',
      groupId: 'g',
      url: 'https://mail.google.com',
    })

    const [stored] = await repo.list()
    expect(stored.url).toBe('https://mail.google.com')
  })
})
