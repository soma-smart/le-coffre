import { describe, expect, it, vi } from 'vitest'
import { LogoutUseCase } from '@/application/auth/Logout'
import { InMemoryAuthGateway } from '@/infrastructure/in_memory/InMemoryAuthGateway'

describe('LogoutUseCase', () => {
  it('delegates to the gateway', async () => {
    const gw = new InMemoryAuthGateway()
    const spy = vi.spyOn(gw, 'logout')
    await new LogoutUseCase(gw).execute()
    expect(spy).toHaveBeenCalledOnce()
  })
})
