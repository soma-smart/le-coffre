import { describe, expect, it } from 'vitest'
import { LockVaultUseCase } from '@/application/vault/LockVault'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'

describe('LockVaultUseCase', () => {
  it('transitions an UNLOCKED vault to LOCKED', async () => {
    const repo = new InMemoryVaultRepository().seed({
      status: 'UNLOCKED',
      lastShareTimestamp: null,
    })
    await new LockVaultUseCase(repo).execute()
    expect((await repo.getStatus()).status).toBe('LOCKED')
  })
})
