import { describe, expect, it } from 'vitest'
import { FetchCsrfTokenUseCase } from '@/application/csrf/FetchCsrfToken'
import { InMemoryCsrfGateway } from '@/infrastructure/in_memory/InMemoryCsrfGateway'

describe('FetchCsrfTokenUseCase', () => {
  it('returns the token produced by the gateway', async () => {
    const gateway = new InMemoryCsrfGateway().seed('abc-123')
    const useCase = new FetchCsrfTokenUseCase(gateway)

    expect(await useCase.execute()).toBe('abc-123')
  })

  it('propagates gateway errors unchanged', async () => {
    const gateway = new InMemoryCsrfGateway().failWith(new Error('boom'))
    const useCase = new FetchCsrfTokenUseCase(gateway)

    await expect(useCase.execute()).rejects.toThrow('boom')
  })
})
