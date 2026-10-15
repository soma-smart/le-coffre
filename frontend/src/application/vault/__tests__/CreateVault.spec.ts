import { describe, expect, it, vi } from 'vitest'
import { CreateVaultUseCase } from '@/application/vault/CreateVault'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import { InMemoryShareLinkCipher } from '@/infrastructure/in_memory/InMemoryShareLinkCipher'
import { ShareLinksUnsupportedError, VaultThresholdInvalidError } from '@/domain/vault/errors'

describe('CreateVaultUseCase', () => {
  it('delegates to the repository and returns one share link per share', async () => {
    const repo = new InMemoryVaultRepository()
      .useClock(() => new Date('2026-10-06T09:00:00Z'))
      .queueSetup('setup-42', ['t1', 't2', 't3'])
    const result = await new CreateVaultUseCase(repo, new InMemoryShareLinkCipher()).execute({
      nbShares: 3,
      threshold: 2,
    })
    expect(result).toEqual({
      setupId: 'setup-42',
      shareLinks: [
        { shareIndex: 1, token: 't1', expiresAt: '2026-10-08T09:00:00.000Z' },
        { shareIndex: 2, token: 't2', expiresAt: '2026-10-08T09:00:00.000Z' },
        { shareIndex: 3, token: 't3', expiresAt: '2026-10-08T09:00:00.000Z' },
      ],
    })
  })

  it('never hands the shares themselves back', async () => {
    const result = await new CreateVaultUseCase(
      new InMemoryVaultRepository(),
      new InMemoryShareLinkCipher(),
    ).execute({
      nbShares: 3,
      threshold: 2,
    })
    expect(result).not.toHaveProperty('shares')
  })

  it('rejects threshold below 2', async () => {
    await expect(
      new CreateVaultUseCase(new InMemoryVaultRepository(), new InMemoryShareLinkCipher()).execute({
        nbShares: 3,
        threshold: 1,
      }),
    ).rejects.toBeInstanceOf(VaultThresholdInvalidError)
  })

  it('rejects threshold greater than the number of shares', async () => {
    await expect(
      new CreateVaultUseCase(new InMemoryVaultRepository(), new InMemoryShareLinkCipher()).execute({
        nbShares: 2,
        threshold: 3,
      }),
    ).rejects.toBeInstanceOf(VaultThresholdInvalidError)
  })

  it('rejects shares above the SSS ceiling', async () => {
    await expect(
      new CreateVaultUseCase(new InMemoryVaultRepository(), new InMemoryShareLinkCipher()).execute({
        nbShares: 17,
        threshold: 5,
      }),
    ).rejects.toBeInstanceOf(VaultThresholdInvalidError)
  })

  it('refuses to set up a vault whose links no custodian could open, before sending anything', async () => {
    const repo = new InMemoryVaultRepository()
    const createVault = vi.spyOn(repo, 'createVault')
    const cipher = new InMemoryShareLinkCipher()
    cipher.supported = false
    const useCase = new CreateVaultUseCase(repo, cipher)

    expect(useCase.canIssueShareLinks()).toBe(false)
    await expect(useCase.execute({ nbShares: 3, threshold: 2 })).rejects.toBeInstanceOf(
      ShareLinksUnsupportedError,
    )
    expect(createVault).not.toHaveBeenCalled()
  })
})
