import { describe, expect, it } from 'vitest'
import { ClearPendingSharesUseCase } from '@/application/vault/ClearPendingShares'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'

describe('ClearPendingSharesUseCase', () => {
  it('drops any pending shares and returns the vault to LOCKED', async () => {
    const repo = new InMemoryVaultRepository().seed({
      status: 'PENDING_UNLOCK',
      lastShareTimestamp: '2024-06-01T00:00:00Z',
    })
    await new ClearPendingSharesUseCase(repo).execute()
    const state = await repo.getStatus()
    expect(state.status).toBe('LOCKED')
    expect(state.lastShareTimestamp).toBeNull()
  })
})
