import { describe, expect, it } from 'vitest'
import { ListPasswordsUseCase } from '@/application/password/ListPasswords'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'

describe('ListPasswordsUseCase', () => {
  it('returns an empty list when no passwords are stored', async () => {
    const useCase = new ListPasswordsUseCase(new InMemoryPasswordRepository())
    expect(await useCase.execute()).toEqual([])
  })

  it('returns every stored password', async () => {
    const repo = new InMemoryPasswordRepository().useIdGenerator(sequentialIds(['pwd-1', 'pwd-2']))
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'g1' })
    await repo.create({ name: 'GitHub', password: 'y', groupId: 'g2' })
    const useCase = new ListPasswordsUseCase(repo)

    const result = await useCase.execute()

    expect(result.map((p) => p.name).sort()).toEqual(['GitHub', 'Gmail'])
  })
})

function sequentialIds(ids: string[]): () => string {
  let index = 0
  return () => ids[index++]
}
