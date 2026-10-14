import { beforeEach, describe, expect, it, vi } from 'vitest'

const sdk = vi.hoisted(() => ({
  subscribeToOneTimeLinkNotificationsOneTimeLinksLinkIdPut: vi.fn(),
}))

vi.mock('@/client/sdk.gen', () => sdk)

import { BackendOneTimeLinkSubscriptionRepository } from '@/infrastructure/backend/BackendOneTimeLinkSubscriptionRepository'
import { NotificationDomainError } from '@/domain/notification/errors'

describe('BackendOneTimeLinkSubscriptionRepository', () => {
  const repository = new BackendOneTimeLinkSubscriptionRepository()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('puts both flags in snake_case for the link and maps the answer back', async () => {
    sdk.subscribeToOneTimeLinkNotificationsOneTimeLinksLinkIdPut.mockResolvedValue({
      data: { link_id: 'link-1', notify_on_read: true, notify_on_expiry: false },
      response: { status: 200 },
    })

    const result = await repository.subscribeToOneTimeLink('link-1', {
      notifyOnRead: true,
      notifyOnExpiry: false,
    })

    expect(sdk.subscribeToOneTimeLinkNotificationsOneTimeLinksLinkIdPut).toHaveBeenCalledWith({
      path: { link_id: 'link-1' },
      body: { notify_on_read: true, notify_on_expiry: false },
    })
    expect(result).toEqual({ notifyOnRead: true, notifyOnExpiry: false })
  })

  it.each([404, 409])('surfaces the server detail on a %i', async (status) => {
    sdk.subscribeToOneTimeLinkNotificationsOneTimeLinksLinkIdPut.mockResolvedValue({
      error: { detail: `refused ${status}` },
      response: { status },
    })

    const attempt = repository.subscribeToOneTimeLink('link-1', {
      notifyOnRead: true,
      notifyOnExpiry: true,
    })

    await expect(attempt).rejects.toBeInstanceOf(NotificationDomainError)
    await expect(attempt).rejects.toThrow(`refused ${status}`)
  })

  it('falls back to a generic message when there is no detail', async () => {
    sdk.subscribeToOneTimeLinkNotificationsOneTimeLinksLinkIdPut.mockResolvedValue({
      error: {},
      response: { status: 500 },
    })

    await expect(
      repository.subscribeToOneTimeLink('link-1', { notifyOnRead: true, notifyOnExpiry: false }),
    ).rejects.toThrow('One-time link notifications unavailable')
  })
})
