import { describe, expect, it } from 'vitest'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { PasswordNotFoundError } from '@/domain/password/errors'

describe('InMemoryPasswordRepository', () => {
  it('round-trips a seeded password through list + getDecryptedValue', async () => {
    const repo = new InMemoryPasswordRepository().seed(
      {
        id: 'pwd-1',
        name: 'Gmail',
        folder: 'Mail',
        groupId: 'group-personal',
        createdAt: '2024-01-01T00:00:00Z',
        lastUpdatedAt: '2024-01-02T00:00:00Z',
        canRead: true,
        canWrite: true,
        login: 'alice@example.com',
        url: 'https://mail.google.com',
        accessibleGroupIds: ['group-personal'],
      },
      'super-secret',
    )

    const passwords = await repo.list()
    expect(passwords).toHaveLength(1)
    expect(passwords[0].name).toBe('Gmail')
    expect(await repo.getDecryptedValue('pwd-1')).toBe('super-secret')
  })

  it('create() uses the injected id generator', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-42')

    const id = await repo.create({
      name: 'GitHub',
      password: 'secret',
      groupId: 'group-team',
    })

    expect(id).toBe('pwd-42')
    const [stored] = await repo.list()
    expect(stored).toMatchObject({ id: 'pwd-42', name: 'GitHub', groupId: 'group-team' })
  })

  it('throws PasswordNotFoundError for unknown ids on read/update/delete', async () => {
    const repo = new InMemoryPasswordRepository()

    await expect(repo.getDecryptedValue('missing')).rejects.toBeInstanceOf(PasswordNotFoundError)
    await expect(repo.update({ id: 'missing', name: 'x' })).rejects.toBeInstanceOf(
      PasswordNotFoundError,
    )
    await expect(repo.delete('missing')).rejects.toBeInstanceOf(PasswordNotFoundError)
  })
})
