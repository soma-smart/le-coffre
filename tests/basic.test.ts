import { $fetch, isDev, setup } from '@nuxt/test-utils'
import { describe, expect, it } from 'vitest'

describe('frontend', async () => {
  await setup()

  it('renders Setup word on /setup page', async () => {
    expect(await $fetch('/setup')).toMatch('Setup')
  })

  if (isDev()) {
    it('[dev] ensure vite client script is added', async () => {
      expect(await $fetch('/')).toMatch('/_nuxt/@vite/client"')
    })
  }
})
