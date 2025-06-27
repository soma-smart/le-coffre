import { $fetch, setup } from '@nuxt/test-utils'
import { describe, expect, it, vi, beforeAll } from 'vitest'
import { requireAuth } from '~/server/utils/requireAuth'

// Setup Nuxt test environment before running any tests
beforeAll(async () => {
  await setup()
})

describe('calling folders api', () => {
  it('should fail when not connected', async () => {
    try {
      await $fetch('/api/folders', { method: 'POST' })
      throw new Error('Should have thrown') // in case the request does not throw
    }
    catch (error: any) {
      expect(error.statusCode || error.response?.status).toBe(401)
      expect(error.message).toMatch(/unauthorized/i)
    }
  })

  it('should fail when no folder name is provided', async () => {
    vi.mocked(requireAuth).mockReturnValue({} as any)

    try {
      await $fetch('/api/folders', {
        method: 'POST',
        headers: {
          Authorization: 'Bearer test-token',
        },
      })
    }
    catch (error: any) {
      expect(error.statusCode || error.response?.status).toBe(400)
      expect(error.message).toMatch(/folder name is required/i)
    }
  })
})
