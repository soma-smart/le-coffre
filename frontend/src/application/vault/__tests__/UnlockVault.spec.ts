import { describe, expect, it } from 'vitest'
import { UnlockVaultUseCase } from '@/application/vault/UnlockVault'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import { VaultSharesRequiredError } from '@/domain/vault/errors'

async function seededRepo() {
  const repo = new InMemoryVaultRepository()
  await repo.createVault({ nbShares: 3, threshold: 2 })
  await repo.validateSetup('setup-test')
  await repo.lock()
  return repo
}

describe('UnlockVaultUseCase', () => {
  it('unlocks the vault once the threshold is reached', async () => {
    const repo = await seededRepo()
    await new UnlockVaultUseCase(repo).execute({ shares: ['a', 'b'] })
    expect((await repo.getStatus()).status).toBe('UNLOCKED')
  })

  it('keeps the vault PENDING_UNLOCK when only some shares are submitted', async () => {
    const repo = await seededRepo()
    await new UnlockVaultUseCase(repo).execute({ shares: ['only-one'] })
    expect((await repo.getStatus()).status).toBe('PENDING_UNLOCK')
  })

  it('rejects an empty / whitespace-only share list', async () => {
    const repo = await seededRepo()
    const useCase = new UnlockVaultUseCase(repo)
    await expect(useCase.execute({ shares: [] })).rejects.toBeInstanceOf(VaultSharesRequiredError)
    await expect(useCase.execute({ shares: ['   ', ''] })).rejects.toBeInstanceOf(
      VaultSharesRequiredError,
    )
  })

  it('trims whitespace before submitting shares', async () => {
    const repo = await seededRepo()
    await new UnlockVaultUseCase(repo).execute({ shares: ['  a  ', '\tb\n'] })
    expect((await repo.getStatus()).status).toBe('UNLOCKED')
  })
})
