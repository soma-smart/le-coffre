import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import InputNumber from 'primevue/inputnumber'
import ShamirInputs from './ShamirInputs.vue'

const setupComponent = () => {
  const wrapper = mount(ShamirInputs)
  const vm = wrapper.vm as unknown as {
    isValidSSSConfig: boolean
    state: { shares: number; threshold: number }
  }
  return { wrapper, vm }
}

describe('ShamirInputs Logic', () => {
  it('initial state should be valid and correctly exposed', () => {
    const { vm } = setupComponent()

    expect(vm.state.shares).toBe(5)
    expect(vm.state.threshold).toBe(3)
    expect(vm.isValidSSSConfig).toBe(true)
  })

  describe('isValidSSSConfig computed property', () => {
    it('should be true when shares >= threshold and within Zod limits', async () => {
      const { vm } = setupComponent()
      vm.state.shares = 10
      vm.state.threshold = 5
      await nextTick()
      expect(vm.isValidSSSConfig).toBe(true)
    })

    // Note: shares < threshold is an impossible state in this component —
    // watchers always maintain the invariant threshold <= shares.
    // Invalid states can only be caused by out-of-range Zod values.

    it('should be false when shares is outside Zod max limit (16)', async () => {
      const { vm } = setupComponent()
      vm.state.shares = 17
      vm.state.threshold = 5
      await nextTick()
      expect(vm.isValidSSSConfig).toBe(false)
    })

    it('should be false when threshold is outside Zod min limit (2)', async () => {
      const { vm } = setupComponent()
      vm.state.shares = 5
      vm.state.threshold = 1
      await nextTick()
      expect(vm.isValidSSSConfig).toBe(false)
    })
  })

  describe('state.shares watcher', () => {
    it('should update threshold to new shares value if threshold > new shares', async () => {
      const { vm } = setupComponent()
      // Initial: shares=5, threshold=3 — reduce shares below threshold
      vm.state.shares = 2
      await nextTick()
      expect(vm.state.shares).toBe(2)
      expect(vm.state.threshold).toBe(2)
    })

    it('should NOT update threshold if threshold <= new shares', async () => {
      const { vm } = setupComponent()
      vm.state.shares = 5
      await nextTick()
      expect(vm.state.shares).toBe(5)
      expect(vm.state.threshold).toBe(3)
    })
  })

  describe('state.threshold watcher', () => {
    it('should update shares to new threshold value if new threshold > shares', async () => {
      const { vm } = setupComponent()
      // Initial: shares=5, threshold=3 — raise threshold above shares
      vm.state.threshold = 8
      await nextTick()
      expect(vm.state.threshold).toBe(8)
      expect(vm.state.shares).toBe(8)
    })

    it('should NOT update shares if new threshold <= shares', async () => {
      const { vm } = setupComponent()
      vm.state.threshold = 4
      await nextTick()
      expect(vm.state.shares).toBe(5)
      expect(vm.state.threshold).toBe(4)
    })
  })

  describe('Component Interaction (InputNumber v-model)', () => {
    it('updates state.shares when InputNumber emits a new value', async () => {
      const { wrapper, vm } = setupComponent()
      const inputs = wrapper.findAllComponents(InputNumber)
      await inputs[0].vm.$emit('update:modelValue', 12)
      await nextTick()
      expect(vm.state.shares).toBe(12)
    })

    it('updates state.threshold when InputNumber emits a new value', async () => {
      const { wrapper, vm } = setupComponent()
      const inputs = wrapper.findAllComponents(InputNumber)
      await inputs[1].vm.$emit('update:modelValue', 7)
      await nextTick()
      expect(vm.state.threshold).toBe(7)
    })

    it('triggers threshold watcher when threshold InputNumber raises above shares', async () => {
      const { wrapper, vm } = setupComponent()
      const inputs = wrapper.findAllComponents(InputNumber)
      await inputs[1].vm.$emit('update:modelValue', 10)
      await nextTick()
      expect(vm.state.threshold).toBe(10)
      expect(vm.state.shares).toBe(10)
    })

    it('triggers shares watcher when shares InputNumber drops below threshold', async () => {
      const { vm } = setupComponent()
      // Set threshold=8 first and let watcher sync shares to 8
      vm.state.threshold = 8
      await nextTick()
      expect(vm.state.shares).toBe(8)
      // Now lower shares below threshold via watcher
      vm.state.shares = 5
      await nextTick()
      expect(vm.state.shares).toBe(5)
      expect(vm.state.threshold).toBe(5)
    })
  })
})
