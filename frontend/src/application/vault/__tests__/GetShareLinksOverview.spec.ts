import { describe, expect, it } from 'vitest'
import { GetShareLinksOverviewUseCase } from '@/application/vault/GetShareLinksOverview'
import { VaultDomainError, VaultNotConfiguredError } from '@/domain/vault/errors'
import type { ShareLinksOverview } from '@/domain/vault/ShareLinksOverview'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'

const overview: ShareLinksOverview = {
  setupId: 'setup-1',
  nbShares: 2,
  threshold: 2,
  createdAt: '2026-10-06T09:00:00Z',
  links: [
    {
      shareIndex: 1,
      status: 'ACKNOWLEDGED',
      expiresAt: '2026-10-08T09:00:00Z',
      firstOpenedAt: '2026-10-06T10:00:00Z',
      reopenableUntil: null,
      acknowledgedAt: '2026-10-06T10:05:00Z',
      openCount: 1,
    },
    {
      shareIndex: 2,
      status: 'PENDING',
      expiresAt: '2026-10-08T09:00:00Z',
      firstOpenedAt: null,
      reopenableUntil: null,
      acknowledgedAt: null,
      openCount: 0,
    },
  ],
  counts: { PENDING: 1, OPENED: 0, OPENED_UNCONFIRMED: 0, ACKNOWLEDGED: 1, EXPIRED: 0 },
}

describe('GetShareLinksOverviewUseCase', () => {
  it('returns the overview held by the repository', async () => {
    const repo = new InMemoryVaultRepository().seedShareLinksOverview(overview)

    expect(await new GetShareLinksOverviewUseCase(repo).execute()).toEqual(overview)
  })

  it('rejects with VaultNotConfiguredError when no vault exists', async () => {
    const repo = new InMemoryVaultRepository()

    await expect(new GetShareLinksOverviewUseCase(repo).execute()).rejects.toBeInstanceOf(
      VaultNotConfiguredError,
    )
  })

  it('lets any other repository failure through', async () => {
    const repo = new InMemoryVaultRepository()
      .seedShareLinksOverview(overview)
      .failGetShareLinksOverviewOnce(new VaultDomainError('boom'))

    await expect(new GetShareLinksOverviewUseCase(repo).execute()).rejects.toThrow('boom')
  })
})
