import { beforeEach, describe, expect, it, vi } from 'vitest'
import { VaultDomainError, VaultNotConfiguredError } from '@/domain/vault/errors'

const { getShareLinksOverview } = vi.hoisted(() => ({ getShareLinksOverview: vi.fn() }))
vi.mock('@/client/sdk.gen', () => ({
  getShareLinksOverviewVaultShareLinksGet: getShareLinksOverview,
}))

import { BackendVaultRepository } from '@/infrastructure/backend/BackendVaultRepository'

describe('BackendVaultRepository.getShareLinksOverview', () => {
  beforeEach(() => getShareLinksOverview.mockReset())

  it('maps the snake_case payload to the domain shape', async () => {
    getShareLinksOverview.mockResolvedValue({
      data: {
        setup_id: 'setup-1',
        nb_shares: 2,
        threshold: 2,
        created_at: '2026-10-06T09:00:00',
        links: [
          {
            share_index: 1,
            status: 'OPENED_UNCONFIRMED',
            expires_at: '2026-10-08T09:00:00',
            first_opened_at: '2026-10-06T10:00:00',
            reopenable_until: null,
            acknowledged_at: null,
            open_count: 2,
          },
        ],
        counts: { pending: 0, opened: 0, opened_unconfirmed: 1, acknowledged: 0, expired: 1 },
      },
    })

    const overview = await new BackendVaultRepository().getShareLinksOverview()

    expect(overview.setupId).toBe('setup-1')
    expect(overview.links[0]).toEqual({
      shareIndex: 1,
      status: 'OPENED_UNCONFIRMED',
      expiresAt: '2026-10-08T09:00:00',
      firstOpenedAt: '2026-10-06T10:00:00',
      reopenableUntil: null,
      acknowledgedAt: null,
      openCount: 2,
    })
    expect(overview.counts).toEqual({
      PENDING: 0,
      OPENED: 0,
      OPENED_UNCONFIRMED: 1,
      ACKNOWLEDGED: 0,
      EXPIRED: 1,
    })
  })

  it('maps a 404 to VaultNotConfiguredError', async () => {
    getShareLinksOverview.mockResolvedValue({
      error: { detail: 'Vault has not been setup yet' },
      response: { status: 404 },
    })

    await expect(new BackendVaultRepository().getShareLinksOverview()).rejects.toBeInstanceOf(
      VaultNotConfiguredError,
    )
  })

  it('surfaces the backend detail on any other error', async () => {
    getShareLinksOverview.mockResolvedValue({
      error: { detail: 'Only administrators can view the share links' },
      response: { status: 403 },
    })

    await expect(new BackendVaultRepository().getShareLinksOverview()).rejects.toThrow(
      new VaultDomainError('Only administrators can view the share links'),
    )
  })
})
