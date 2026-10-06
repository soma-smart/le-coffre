import { describe, expect, it } from 'vitest'
import { UnlockVaultUseCase } from '@/application/vault/UnlockVault'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import { VaultSharesRequiredError, VaultUnlockSessionInvalidError } from '@/domain/vault/errors'

const SESSION = 'SESSIONAAAAAAAAA'
const OTHER_SESSION = 'SESSIONBBBBBBBBB'

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
    await new UnlockVaultUseCase(repo).execute({ unlockSessionId: SESSION, shares: ['a', 'b'] })
    expect((await repo.getStatus()).status).toBe('UNLOCKED')
  })

  it('keeps the session PENDING_UNLOCK when only some shares are submitted', async () => {
    const repo = await seededRepo()
    await new UnlockVaultUseCase(repo).execute({ unlockSessionId: SESSION, shares: ['only-one'] })
    expect((await repo.getStatus(SESSION)).status).toBe('PENDING_UNLOCK')
    expect((await repo.getStatus(OTHER_SESSION)).status).toBe('LOCKED')
    expect((await repo.getStatus()).status).toBe('LOCKED')
  })

  it('does not pool shares across sessions', async () => {
    const repo = await seededRepo()
    const useCase = new UnlockVaultUseCase(repo)
    await useCase.execute({ unlockSessionId: SESSION, shares: ['a'] })
    await useCase.execute({ unlockSessionId: OTHER_SESSION, shares: ['b'] })
    expect((await repo.getStatus()).status).toBe('LOCKED')
  })

  it('rejects an empty / whitespace-only share list', async () => {
    const repo = await seededRepo()
    const useCase = new UnlockVaultUseCase(repo)
    await expect(useCase.execute({ unlockSessionId: SESSION, shares: [] })).rejects.toBeInstanceOf(
      VaultSharesRequiredError,
    )
    await expect(
      useCase.execute({ unlockSessionId: SESSION, shares: ['   ', ''] }),
    ).rejects.toBeInstanceOf(VaultSharesRequiredError)
  })

  it('rejects a malformed unlock session id', async () => {
    const repo = await seededRepo()
    await expect(
      new UnlockVaultUseCase(repo).execute({ unlockSessionId: 'short', shares: ['a'] }),
    ).rejects.toBeInstanceOf(VaultUnlockSessionInvalidError)
  })

  it('trims whitespace before submitting shares', async () => {
    const repo = await seededRepo()
    await new UnlockVaultUseCase(repo).execute({
      unlockSessionId: SESSION,
      shares: ['  a  ', '\tb\n'],
    })
    expect((await repo.getStatus()).status).toBe('UNLOCKED')
  })
})
