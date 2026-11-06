import { beforeEach, describe, expect, it, vi } from 'vitest'

const sdk = vi.hoisted(() => ({
  createOneTimeLinkPasswordsPasswordIdOneTimeLinksPost: vi.fn(),
}))

vi.mock('@/client/sdk.gen', () => sdk)

import { BackendOneTimeLinkRepository } from '@/infrastructure/backend/BackendOneTimeLinkRepository'

describe('BackendOneTimeLinkRepository creation', () => {
  const repository = new BackendOneTimeLinkRepository()

  beforeEach(() => {
    vi.clearAllMocks()
    sdk.createOneTimeLinkPasswordsPasswordIdOneTimeLinksPost.mockResolvedValue({
      data: { id: 'link-1', token: 'tok', expires_at: '2026-01-02T00:00:00Z' },
      response: { status: 201 },
    })
  })

  it('sends only the lifetime in the creation body, notifications live elsewhere', async () => {
    await repository.create('pwd-1', 3600)

    expect(sdk.createOneTimeLinkPasswordsPasswordIdOneTimeLinksPost).toHaveBeenCalledWith({
      path: { password_id: 'pwd-1' },
      body: { lifetime_seconds: 3600 },
    })
  })

  it('defaults the lifetime to null', async () => {
    await repository.create('pwd-1')

    expect(sdk.createOneTimeLinkPasswordsPasswordIdOneTimeLinksPost).toHaveBeenCalledWith({
      path: { password_id: 'pwd-1' },
      body: { lifetime_seconds: null },
    })
  })
})
