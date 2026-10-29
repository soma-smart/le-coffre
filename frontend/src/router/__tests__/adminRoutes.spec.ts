import { describe, expect, it } from 'vitest'
import router from '@/router/index'

describe('admin routes', () => {
  it('reserves the share links tracking page to administrators', () => {
    // The guard is deny-by-default for anonymous visitors, but only
    // `requiresAdmin` keeps a signed-in non-admin out of the custodians' status.
    const route = router.getRoutes().find((entry) => entry.name === 'AdminShareLinks')

    expect(route).toBeDefined()
    expect(route?.path).toBe('/admin/share-links')
    expect(route?.meta.requiresAdmin).toBe(true)
    expect(route?.meta.public).toBeUndefined()
  })
})
