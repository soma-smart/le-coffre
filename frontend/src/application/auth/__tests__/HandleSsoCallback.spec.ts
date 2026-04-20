import { describe, expect, it } from 'vitest'
import { HandleSsoCallbackUseCase } from '@/application/auth/HandleSsoCallback'
import { InMemoryAuthGateway } from '@/infrastructure/in_memory/InMemoryAuthGateway'
import { SsoCallbackCodeRequiredError } from '@/domain/auth/errors'

describe('HandleSsoCallbackUseCase', () => {
  it('returns the SSO user info the gateway resolves with', async () => {
    const gw = new InMemoryAuthGateway().setSsoCallback({
      user: {
        userId: 'u-1',
        email: 'new@example.com',
        displayName: 'Newly Created',
        isNewUser: true,
      },
    })

    const result = await new HandleSsoCallbackUseCase(gw).execute({ code: 'oauth-code' })

    expect(result.user).toEqual({
      userId: 'u-1',
      email: 'new@example.com',
      displayName: 'Newly Created',
      isNewUser: true,
    })
  })

  it('rejects an empty authorization code', async () => {
    await expect(
      new HandleSsoCallbackUseCase(new InMemoryAuthGateway()).execute({ code: '' }),
    ).rejects.toBeInstanceOf(SsoCallbackCodeRequiredError)
  })
})
