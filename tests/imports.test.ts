import { describe, expect, test } from 'vitest'

describe('import vue components', () => {
  test('normal imports as expected', async () => {
    const { default: MenuTop } = await import('../components/Menu/Top.vue')
    expect(MenuTop).toBeDefined()
  })
})