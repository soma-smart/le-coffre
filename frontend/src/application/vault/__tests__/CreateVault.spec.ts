import { describe, expect, it } from 'vitest'
import { CreateVaultUseCase } from '@/application/vault/CreateVault'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import { VaultThresholdInvalidError } from '@/domain/vault/errors'

describe('CreateVaultUseCase', () => {
  it('delegates to the repository and returns the setup payload', async () => {
    const repo = new InMemoryVaultRepository().queueSetup('setup-42', ['s1', 's2', 's3'])
    const result = await new CreateVaultUseCase(repo).execute({ nbShares: 3, threshold: 2 })
    expect(result).toEqual({ setupId: 'setup-42', shares: ['s1', 's2', 's3'] })
  })

  it('rejects threshold below 2', async () => {
    await expect(
      new CreateVaultUseCase(new InMemoryVaultRepository()).execute({ nbShares: 3, threshold: 1 }),
    ).rejects.toBeInstanceOf(VaultThresholdInvalidError)
  })

  it('rejects threshold greater than the number of shares', async () => {
    await expect(
      new CreateVaultUseCase(new InMemoryVaultRepository()).execute({ nbShares: 2, threshold: 3 }),
    ).rejects.toBeInstanceOf(VaultThresholdInvalidError)
  })

  it('rejects shares above the SSS ceiling', async () => {
    await expect(
      new CreateVaultUseCase(new InMemoryVaultRepository()).execute({
        nbShares: 17,
        threshold: 5,
      }),
    ).rejects.toBeInstanceOf(VaultThresholdInvalidError)
  })
})
