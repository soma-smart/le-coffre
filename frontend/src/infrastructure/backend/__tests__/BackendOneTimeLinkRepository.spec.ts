import { beforeEach, describe, expect, it, vi } from 'vitest'

const sdk = vi.hoisted(() => ({
  createOneTimeLinkPasswordsPasswordIdOneTimeLinksPost: vi.fn(),
  listOneTimeLinksPasswordsPasswordIdOneTimeLinksGet: vi.fn(),
}))

vi.mock('@/client/sdk.gen', () => sdk)

import { BackendOneTimeLinkRepository } from '@/infrastructure/backend/BackendOneTimeLinkRepository'

describe('BackendOneTimeLinkRepository notification options', () => {
  const repository = new BackendOneTimeLinkRepository()

  beforeEach(() => {
    vi.clearAllMocks()
    sdk.createOneTimeLinkPasswordsPasswordIdOneTimeLinksPost.mockResolvedValue({
      data: { id: 'link-1', token: 'tok', expires_at: '2026-01-02T00:00:00Z' },
      response: { status: 201 },
    })
  })

  it('sends both notification flags in the creation body', async () => {
    await repository.create('pwd-1', {
      lifetimeSeconds: 3600,
      notifyOnRead: true,
      notifyOnExpiry: true,
    })

    expect(sdk.createOneTimeLinkPasswordsPasswordIdOneTimeLinksPost).toHaveBeenCalledWith({
      path: { password_id: 'pwd-1' },
      body: { lifetime_seconds: 3600, notify_on_read: true, notify_on_expiry: true },
    })
  })

  it('defaults both flags to false and the lifetime to null', async () => {
    await repository.create('pwd-1')

    expect(sdk.createOneTimeLinkPasswordsPasswordIdOneTimeLinksPost).toHaveBeenCalledWith({
      path: { password_id: 'pwd-1' },
      body: { lifetime_seconds: null, notify_on_read: false, notify_on_expiry: false },
    })
  })

  it('maps the notification flags of the listing onto the domain link', async () => {
    sdk.listOneTimeLinksPasswordsPasswordIdOneTimeLinksGet.mockResolvedValue({
      data: {
        links: [
          {
            id: 'link-1',
            password_id: 'pwd-1',
            created_by_user_id: 'user-1',
            created_at: '2026-01-01T00:00:00Z',
            expires_at: '2026-01-02T00:00:00Z',
            read_at: null,
            revoked_at: null,
            notify_on_read: true,
            notify_on_expiry: false,
          },
        ],
        total: 1,
        active: 1,
        max_active: 5,
      },
      response: { status: 200 },
    })

    const page = await repository.listForPassword('pwd-1')

    expect(page.links[0].notifyOnRead).toBe(true)
    expect(page.links[0].notifyOnExpiry).toBe(false)
  })
})
