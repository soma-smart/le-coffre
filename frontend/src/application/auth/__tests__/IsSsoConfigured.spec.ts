import { describe, expect, it } from 'vitest'
import { IsSsoConfiguredUseCase } from '@/application/auth/IsSsoConfigured'
import { InMemoryAuthGateway } from '@/infrastructure/in_memory/InMemoryAuthGateway'

describe('IsSsoConfiguredUseCase', () => {
  it('returns false by default', async () => {
    expect(await new IsSsoConfiguredUseCase(new InMemoryAuthGateway()).execute()).toBe(false)
  })

  it('returns true once the gateway has been flagged configured', async () => {
    const gw = new InMemoryAuthGateway().setSsoConfigured(true)
    expect(await new IsSsoConfiguredUseCase(gw).execute()).toBe(true)
  })
})
