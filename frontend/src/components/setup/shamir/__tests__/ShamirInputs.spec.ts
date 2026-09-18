import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ShamirInputs from '../ShamirInputs.vue'

describe('ShamirInputs', () => {
  it('renders the whole-sentence translation with the numbers interpolated', () => {
    const wrapper = mount(ShamirInputs)

    // Defaults: shares=5, threshold=3, so 2 parts are losable (plural).
    // Asserted per-paragraph (not the whole wrapper's .text()) so a missing
    // separator between the two sentences can't hide inside one big string.
    expect(wrapper.get('[data-testid="need-parts"]').text()).toBe(
      'You will need 3 parts out of 5 to reconstruct the key.',
    )
    expect(wrapper.get('[data-testid="can-lose"]').text()).toBe('You can lose 2 parts.')
  })

  it('uses the singular form when exactly one part is losable', async () => {
    const wrapper = mount(ShamirInputs)
    const vm = wrapper.vm as unknown as { state: { shares: number; threshold: number } }
    vm.state.shares = 4
    vm.state.threshold = 3
    await wrapper.vm.$nextTick()

    expect(wrapper.get('[data-testid="can-lose"]').text()).toBe('You can lose 1 part.')
  })
})
