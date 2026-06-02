import { describe, expect, it } from 'vitest'
import { ConfigureSsoProviderUseCase } from '@/application/auth/ConfigureSsoProvider'
import { InMemoryAuthGateway } from '@/infrastructure/in_memory/InMemoryAuthGateway'
import {
  SsoClientIdRequiredError,
  SsoClientSecretRequiredError,
  SsoDiscoveryUrlRequiredError,
} from '@/domain/auth/errors'

function validCommand(overrides: Record<string, string> = {}) {
  return {
    clientId: 'client-id',
    clientSecret: 'client-secret',
    discoveryUrl: 'https://idp.example/.well-known/openid-configuration',
    ...overrides,
  }
}

describe('ConfigureSsoProviderUseCase', () => {
  it('flips the gateway into the configured state on success', async () => {
    const gw = new InMemoryAuthGateway()
    expect(await gw.isSsoConfigured()).toBe(false)
    await new ConfigureSsoProviderUseCase(gw).execute(validCommand())
    expect(await gw.isSsoConfigured()).toBe(true)
  })

  it.each<[string, Record<string, string>, unknown]>([
    ['blank client id', { clientId: '  ' }, SsoClientIdRequiredError],
    ['empty client secret', { clientSecret: '' }, SsoClientSecretRequiredError],
    ['blank discovery url', { discoveryUrl: '  ' }, SsoDiscoveryUrlRequiredError],
  ])('rejects %s', async (_label, override, ErrorType) => {
    await expect(
      new ConfigureSsoProviderUseCase(new InMemoryAuthGateway()).execute(validCommand(override)),
    ).rejects.toBeInstanceOf(ErrorType as new () => Error)
  })
})
