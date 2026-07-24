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

  it('keeps every other route non-public', () => {
    const publicRoutes = router
      .getRoutes()
      .filter((entry) => entry.meta.public)
      .map((entry) => entry.name)

    expect(publicRoutes).toEqual(['OneTimeLink'])
  })
})
