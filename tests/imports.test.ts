import { describe, expect, it } from 'vitest'

describe('import vue components', () => {
  it('normal imports as expected', async () => {
    const { default: MenuTop } = await import('../components/Menu/Top.vue')
    expect(MenuTop).toBeDefined()
  })
})
