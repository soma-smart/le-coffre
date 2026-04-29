import { describe, expect, it } from 'vitest'
import { ValidateVaultSetupUseCase } from '@/application/vault/ValidateVaultSetup'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import { VaultSetupIdRequiredError } from '@/domain/vault/errors'

describe('ValidateVaultSetupUseCase', () => {
  it('moves the vault to SETUPED', async () => {
    const repo = new InMemoryVaultRepository()
    await repo.createVault({ nbShares: 2, threshold: 2 })
    await new ValidateVaultSetupUseCase(repo).execute({ setupId: 'setup-test' })
    expect((await repo.getStatus()).status).toBe('SETUPED')
  })

  it('rejects an empty setup id', async () => {
    await expect(
      new ValidateVaultSetupUseCase(new InMemoryVaultRepository()).execute({ setupId: '' }),
    ).rejects.toBeInstanceOf(VaultSetupIdRequiredError)
  })
})
