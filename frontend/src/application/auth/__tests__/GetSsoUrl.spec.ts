import { describe, expect, it } from 'vitest'
import { GetSsoUrlUseCase } from '@/application/auth/GetSsoUrl'
import { InMemoryAuthGateway } from '@/infrastructure/in_memory/InMemoryAuthGateway'

describe('GetSsoUrlUseCase', () => {
  it('returns the URL the gateway was seeded with', async () => {
    const gw = new InMemoryAuthGateway().setSsoUrl('https://sso.test/authorize')
    expect(await new GetSsoUrlUseCase(gw).execute()).toBe('https://sso.test/authorize')
  })
})
