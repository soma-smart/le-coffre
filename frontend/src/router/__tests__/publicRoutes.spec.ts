import { describe, expect, it } from 'vitest'
import router from '@/router/index'

describe('public routes', () => {
  it('marks the one-time link page as public', () => {
    // The global beforeEach guard is deny-by-default: every route other than
    // Login requires a session. Recipients of a one-time link have none, so
    // dropping this meta flag would silently bounce them to /login and the
    // feature would stop working end to end.
    const route = router.getRoutes().find((entry) => entry.name === 'OneTimeLink')

    expect(route).toBeDefined()
    expect(route?.meta.public).toBe(true)
    expect(route?.meta.skipSetupCheck).toBe(true)
  })

  it('keeps the extension approval page behind the session', () => {
    // It was public while the pairing code rode the URL fragment and had to be
    // stashed before sign-in. The code is typed on the page now, so nothing
    // needs to happen before authentication, and going through the guard is
    // what primes the CSRF token that Approve and Refuse need.
    const route = router.getRoutes().find((entry) => entry.name === 'ExtensionConnect')

    expect(route).toBeDefined()
    expect(route?.meta.public).toBeUndefined()
  })

  it('keeps every other route non-public', () => {
    // Deliberately an exact list. Adding a route here means someone reviewed
    // why it may be reached without a session.
    const publicRoutes = router
      .getRoutes()
      .filter((entry) => entry.meta.public)
      .map((entry) => entry.name)

    expect(publicRoutes.sort()).toEqual(['OneTimeLink'])
  })
})
