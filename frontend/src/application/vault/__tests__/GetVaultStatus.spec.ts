import { describe, expect, it } from 'vitest'
import { GetVaultStatusUseCase } from '@/application/vault/GetVaultStatus'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'

describe('GetVaultStatusUseCase', () => {
  it('defaults to NOT_SETUP on a fresh repository', async () => {
    const result = await new GetVaultStatusUseCase(new InMemoryVaultRepository()).execute()
    expect(result.status).toBe('NOT_SETUP')
    expect(result.lastShareTimestamp).toBeNull()
  })

  it('returns whatever status the repository has been seeded with', async () => {
    const repo = new InMemoryVaultRepository().seed({
      status: 'PENDING_UNLOCK',
      lastShareTimestamp: '2024-06-01T00:00:00Z',
    })
    const result = await new GetVaultStatusUseCase(repo).execute()
    expect(result.status).toBe('PENDING_UNLOCK')
    expect(result.lastShareTimestamp).toBe('2024-06-01T00:00:00Z')
  })
})
