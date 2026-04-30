import { describe, expect, it } from 'vitest'
import { decideAdminGuard } from '@/router/index'

describe('decideAdminGuard', () => {
  it('allows the navigation when the user is admin and the fetch succeeded', () => {
    expect(decideAdminGuard({ error: null, isAdmin: true, hasFromRoute: true })).toEqual({
      kind: 'allow',
    })
    expect(decideAdminGuard({ error: null, isAdmin: true, hasFromRoute: false })).toEqual({
      kind: 'allow',
    })
  })

  it('redirects to Home when the user is genuinely not admin', () => {
    expect(decideAdminGuard({ error: null, isAdmin: false, hasFromRoute: true })).toEqual({
      kind: 'redirectHome',
    })
  })

  it('blocks (stays put) on transient backend failure when there is a from-route', () => {
    // Critical regression — silent demotion to Home on a 5xx used to mask the
    // real failure. With a `from` route the user keeps their current page.
    expect(decideAdminGuard({ error: 'backend down', isAdmin: false, hasFromRoute: true })).toEqual(
      { kind: 'block' },
    )
  })

  it('redirects to Home on backend failure when there is no from-route (initial nav)', () => {
    // Block (`return false`) is meaningless when the navigation is the very
    // first one — the user lands on a blank page. Falling through to Home is
    // the safest default for that edge case.
    expect(
      decideAdminGuard({ error: 'backend down', isAdmin: false, hasFromRoute: false }),
    ).toEqual({ kind: 'redirectHome' })
  })

  it('error path takes precedence over isAdmin (we cannot trust the verdict)', () => {
    // Even if the cached `isAdmin` is true, an error from the just-attempted
    // refresh means we cannot vouch for it — keep the user where they were.
    expect(decideAdminGuard({ error: 'blip', isAdmin: true, hasFromRoute: true })).toEqual({
      kind: 'block',
    })
  })
})
