import { describe, expect, it, vi } from 'vitest'
import { RefreshAccessTokenUseCase } from '@/application/auth/RefreshAccessToken'
import { InMemoryAuthGateway } from '@/infrastructure/in_memory/InMemoryAuthGateway'

describe('RefreshAccessTokenUseCase', () => {
  it('delegates to the gateway', async () => {
    const gw = new InMemoryAuthGateway()
    const spy = vi.spyOn(gw, 'refreshAccessToken')
    await new RefreshAccessTokenUseCase(gw).execute()
    expect(spy).toHaveBeenCalledOnce()
  })
})
