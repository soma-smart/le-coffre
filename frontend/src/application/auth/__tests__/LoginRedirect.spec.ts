import { describe, expect, it } from 'vitest'

import { ConsumeLoginRedirectUseCase } from '@/application/auth/ConsumeLoginRedirect'
import { ForgetLoginRedirectUseCase } from '@/application/auth/ForgetLoginRedirect'
import { RememberLoginRedirectUseCase } from '@/application/auth/RememberLoginRedirect'
import { ResolveLoginRedirectUseCase } from '@/application/auth/ResolveLoginRedirect'
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
      resolve: new ResolveLoginRedirectUseCase(gateway),
      forget: new ForgetLoginRedirectUseCase(gateway),
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

  it.each([
    ['/\\evil.com', 'a backslash, which the URL parser reads as a slash'],
    ['/\t/evil.com', 'a tab, which the URL parser strips before parsing'],
    ['/\n/evil.com', 'a newline, stripped the same way'],
    ['/ evil.com', 'whitespace inside the path'],
    ['/\u0000evil.com', 'a control character'],
  ])('should refuse %j: %s', (path) => {
    // Regression. The old rule only looked for "//" and "://", and vue-router
    // hands the path to history.pushState: the browser turned these into
    // "//evil.com", pushState refused the cross-origin result, and the router
    // fell back to location.assign. A login link could leave the site.
    const { remember, consume } = build()

    remember.execute({ path })

    expect(consume.execute()).toBeNull()
  })

  it('should keep /%5Cevil.com, whose encoded backslash stays a path segment', () => {
    // The percent-encoded form is what a browser keeps as-is, so it lands on
    // /%5Cevil.com of this origin. Rejecting it would only cost a legitimate
    // (if odd) path; accepting it is consistent with the origin rule above.
    const { remember, consume } = build()

    remember.execute({ path: '/%5Cevil.com' })

    expect(consume.execute()).toBe('/%5Cevil.com')
  })

  it('should ignore a repeated ?redirect=, which the router reads as an array', () => {
    // Regression. The SSO button cast the query value to a string and called
    // .trim() on it, so "?redirect=/a&redirect=/b" threw inside the handler
    // and the button died with a generic toast.
    const { remember, consume } = build()

    expect(() => remember.execute({ path: ['/a', '/b'] })).not.toThrow()
    expect(consume.execute()).toBeNull()
  })

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

  describe('password login', () => {
    // The password flow keeps ?redirect= in the URL, so its destination is the
    // query value, held to the same rule as the stash. The login form used to
    // push the query straight to the router.
    it('should resolve a safe in-app path from the query', () => {
      const { resolve } = build()

      expect(resolve.execute({ requested: ' /groups ' })).toBe('/groups')
    })

    it.each([
      'https://evil.example',
      '//evil.example',
      '/\\evil.com',
      '/\t/evil.com',
      ['/a', '/b'],
    ])('should refuse %j from the query', (requested) => {
      const { resolve } = build()

      expect(resolve.execute({ requested })).toBeNull()
    })

    it('should drop an SSO stash the user abandoned for a password login', () => {
      // Otherwise it would wait for the next SSO login in this tab, possibly
      // by someone else on a shared machine.
      const { gateway, resolve, consume } = build()
      gateway.seed('/extension/connect')

      resolve.execute({ requested: undefined })

      expect(consume.execute()).toBeNull()
    })
  })

  it('should let a failed SSO callback drop the stash', () => {
    const { gateway, forget, consume } = build()
    gateway.seed('/extension/connect')

    forget.execute()

    expect(consume.execute()).toBeNull()
  })
})
