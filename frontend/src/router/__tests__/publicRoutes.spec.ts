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

  it('marks the extension approval page as public', () => {
    // Public so the page can render before authentication and stash the pairing
    // code from the URL fragment itself. Going through the guard instead would
    // redirect with `redirect=to.fullPath`, writing the code into the SPA
    // host's access log. skipSetupCheck for the same reason as the one-time
    // link: pairing involves no crypto and must work while the vault is locked.
    //
    // Being public grants nothing. The page shows only what a pairing code
    // already identifies, and both approve and deny are cookie-authenticated
    // and CSRF-protected on the backend.
    const route = router.getRoutes().find((entry) => entry.name === 'ExtensionConnect')

    expect(route).toBeDefined()
    expect(route?.meta.public).toBe(true)
    expect(route?.meta.skipSetupCheck).toBe(true)
  })

  it('keeps every other route non-public', () => {
    // Deliberately an exact list. Adding a route here means someone reviewed
    // why it may be reached without a session.
    const publicRoutes = router
      .getRoutes()
      .filter((entry) => entry.meta.public)
      .map((entry) => entry.name)

    expect(publicRoutes.sort()).toEqual(['ExtensionConnect', 'OneTimeLink'])
  })
})
