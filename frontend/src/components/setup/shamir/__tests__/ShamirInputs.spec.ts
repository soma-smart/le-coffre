import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import i18n from '@/i18n'
import ShamirInputs from '../ShamirInputs.vue'

describe('ShamirInputs', () => {
  it('renders the whole-sentence translation with the numbers interpolated', () => {
    const wrapper = mount(ShamirInputs)

    // Defaults: shares=5, threshold=3, so 2 parts are losable (plural).
    // Expected string is resolved through the real i18n instance rather than
    // hardcoded, so this proves the component passes the right params into
    // the right slots without coupling the test to current wording or to
    // the default locale staying 'en'.
    expect(wrapper.get('[data-testid="shamir-summary"]').text()).toBe(
      i18n.global.t(
        'components.setup.shamirInputs.needAndCanLose',
        { threshold: 3, shares: 5, count: 2 },
        2,
      ),
    )
  })

  it('uses the singular form when exactly one part is losable', async () => {
    const wrapper = mount(ShamirInputs)
    const vm = wrapper.vm as unknown as { state: { shares: number; threshold: number } }
    vm.state.shares = 4
    vm.state.threshold = 3
    await wrapper.vm.$nextTick()

    expect(wrapper.get('[data-testid="shamir-summary"]').text()).toBe(
      i18n.global.t(
        'components.setup.shamirInputs.needAndCanLose',
        { threshold: 3, shares: 4, count: 1 },
        1,
      ),
    )
  })
})
