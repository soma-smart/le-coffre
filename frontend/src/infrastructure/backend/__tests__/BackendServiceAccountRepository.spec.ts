import { afterEach, describe, expect, it, vi } from 'vitest'
import { client } from '@/client/client.gen'
import { BackendServiceAccountRepository } from '@/infrastructure/backend/BackendServiceAccountRepository'

const { list } = vi.hoisted(() => ({ list: vi.fn() }))
vi.mock('@/client/sdk.gen', () => ({
  createServiceAccountIamServiceAccountsPost: vi.fn(),
  listServiceAccountsIamServiceAccountsGet: list,
  revokeServiceAccountIamServiceAccountsServiceAccountIdDelete: vi.fn(),
  rotateServiceAccountTokenIamServiceAccountsServiceAccountIdRotatePost: vi.fn(),
}))

function summary(overrides: Record<string, unknown> = {}) {
  return {
    id: 'account-1',
    group_id: 'group-1',
    name: 'nightly-backup',
    created_by_principal_id: 'user-1',
    created_by_user_name: 'Ada Owner',
    created_at: '2026-01-01T12:00:00Z',
    revoked_at: null,
    last_rotated_at: null,
    last_used_at: null,
    ...overrides,
  }
}

describe('BackendServiceAccountRepository', () => {
  const repository = new BackendServiceAccountRepository()
  const baseUrl = client.getConfig().baseUrl

  afterEach(() => {
    client.setConfig({ baseUrl })
  })

  it('maps the last use and the last renewal of each account', async () => {
    list.mockResolvedValue({
      data: {
        items: [
          summary({
            last_used_at: '2026-03-01T12:00:00Z',
            last_rotated_at: '2026-02-01T12:00:00Z',
          }),
          summary({ id: 'account-2' }),
        ],
        active: 2,
        max_active: 10,
      },
      response: { status: 200 },
    })

    const page = await repository.listForGroup('group-1')

    expect(page.accounts.map((a) => [a.lastUsedAt, a.lastRotatedAt])).toEqual([
      ['2026-03-01T12:00:00Z', '2026-02-01T12:00:00Z'],
      [null, null],
    ])
  })

  it('gives the full address of the API this app calls', () => {
    client.setConfig({ baseUrl: '/api' })

    expect(repository.apiUrl()).toBe(`${window.location.origin}/api`)
  })

  it('keeps an API configured on another host', () => {
    client.setConfig({ baseUrl: 'https://vault-api.example.com/api' })

    expect(repository.apiUrl()).toBe('https://vault-api.example.com/api')
  })

  it('ends without a slash when the API answers at the root of its host', () => {
    // The URL of a bare host ends with "/": the commands would then call "//iam/…".
    client.setConfig({ baseUrl: 'https://vault-api.example.com' })

    expect(repository.apiUrl()).toBe('https://vault-api.example.com')
  })
})
