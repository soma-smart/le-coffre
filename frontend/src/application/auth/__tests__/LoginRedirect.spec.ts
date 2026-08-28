import { describe, expect, it } from 'vitest'

import { ConsumeLoginRedirectUseCase } from '@/application/auth/ConsumeLoginRedirect'
import { RememberLoginRedirectUseCase } from '@/application/auth/RememberLoginRedirect'
import { InMemoryLoginRedirectGateway } from '@/infrastructure/in_memory/InMemoryLoginRedirectGateway'

// Regression tier for the SSO round trip: the password flow keeps ?redirect=
// in the URL, but SSO leaves the app for the identity provider, so the
// destination has to survive in the handoff and come back exactly once.
describe('login redirect handoff', () => {
  function build() {
    const gateway = new InMemoryLoginRedirectGateway()
    return {
      gateway,
      remember: new RememberLoginRedirectUseCase(gateway),
      consume: new ConsumeLoginRedirectUseCase(gateway),
    }
  }

  it('should carry an in-app path across the round trip, exactly once', () => {
    const { remember, consume } = build()

    remember.execute({ path: '/extension/connect' })

    expect(consume.execute()).toBe('/extension/connect')
    expect(consume.execute()).toBeNull()
  })

  it('should return null when nothing was stashed', () => {
    const { consume } = build()

    expect(consume.execute()).toBeNull()
  })

  it.each(['https://evil.example', '//evil.example', 'javascript://x', 'ftp://evil'])(
    'should refuse to remember %s',
    (path) => {
      // A login redirect is the classic open-redirect vehicle: everything that
      // is not an in-app path is dropped, not sanitised.
      const { remember, consume } = build()

      remember.execute({ path })

      expect(consume.execute()).toBeNull()
    },
  )

  it('should ignore an empty or missing redirect', () => {
    const { remember, consume } = build()

    remember.execute({ path: undefined })
    remember.execute({ path: '   ' })

    expect(consume.execute()).toBeNull()
  })

  it('should re-validate on the way out, since session storage is origin-writable', () => {
    const { gateway, consume } = build()
    gateway.seed('https://evil.example/phish')

    expect(consume.execute()).toBeNull()
  })
})
