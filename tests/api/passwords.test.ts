import { $fetch, setup } from '@nuxt/test-utils'
import { describe, expect, it } from 'vitest'

describe('calling passwords api', async () => {
  await setup()

  it('returns a generated password when calling generating', async () => {
    const result = await $fetch('/api/passwords/generate')

    expect(typeof result).toBe('string')
    expect((result as string).length).not.toBe(0)
  })

  it('returns a password of length 20 when calling default generating', async () => {
    const result = await $fetch('/api/passwords/generate')

    expect((result as string).length).toBe(20)
  })

  it.each([
    5, 20, 50,
  ])('returns a password of given length when calling generating with length', async (size) => {
    const result = await $fetch('/api/passwords/generate', { params: { size } })

    expect((result as string).length).toBe(size)
  })
})
