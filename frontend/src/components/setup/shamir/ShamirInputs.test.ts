import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ShamirInputs from './ShamirInputs.vue'

// Mock PrimeVue components to avoid importing/configuring them in the test
const mocks = {
    Card: {
        template: `<div><slot name="content"></slot></div>`
    },
    InputNumber: {
        props: ['modelValue'],
        emits: ['update:modelValue'],
        template: `<input type="number" :value="modelValue"
    @input="$emit('update:modelValue', $event.target.valueAsNumber)" />`,
    },
}

// Helper to mount the component and get the exposed properties
const setupComponent = () => {
    const wrapper = mount(ShamirInputs, {
        global: {
            components: mocks,
        },
    })
    // Access the exposed properties (isValidSSSConfig, state)
    const { isValidSSSConfig, state } = wrapper.vm as unknown as {
        isValidSSSConfig: boolean
        state: { shares: number; threshold: number }
    }
    return { wrapper, isValidSSSConfig, state }
}

describe('ShamirInputs Logic', () => {

    // Test initial state and validation
    it('initial state should be valid and correctly exposed', () => {
        const { isValidSSSConfig, state } = setupComponent()

        expect(state.shares).toBe(5)
        expect(state.threshold).toBe(3)
        expect(isValidSSSConfig).toBe(true) // 5 >= 3
    })

    // Test the isValidSSSConfig computed property
    describe('isValidSSSConfig computed property', () => {
        let state: { shares: number; threshold: number }
        let isValidSSSConfig: boolean

        beforeEach(() => {
            ({ state, isValidSSSConfig } = setupComponent())
        })

        it('should be true when shares >= threshold and within Zod limits', async () => {
            state.shares = 10
            state.threshold = 5
            await nextTick()
            expect(isValidSSSConfig).toBe(true)
        })

        it('should be false when shares < threshold', async () => {
            state.shares = 4
            state.threshold = 5
            await nextTick()
            expect(isValidSSSConfig).toBe(false)
        })

        it('should be false when shares is outside Zod max limit (16)', async () => {
            state.shares = 17
            state.threshold = 5
            await nextTick()
            expect(isValidSSSConfig).toBe(false)
        })

        it('should be false when threshold is outside Zod min limit (2)', async () => {
            state.shares = 5
            state.threshold = 1
            await nextTick()
            expect(isValidSSSConfig).toBe(false)
        })
    })

    // Test the watcher for state.shares
    describe('state.shares watcher', () => {
        let state: { shares: number; threshold: number }

        beforeEach(() => {
            ({ state } = setupComponent())
        })

        it('should update threshold to new shares value if threshold > new shares', async () => {
            state.threshold = 10
            state.shares = 8 // New shares is less than current threshold (10)

            await nextTick() // Wait for watcher to execute

            expect(state.shares).toBe(8)
            expect(state.threshold).toBe(8) // Threshold should be updated to 8
        })

        it('should NOT update threshold if threshold <= new shares', async () => {
            state.threshold = 3
            state.shares = 5 // New shares (5) is greater than current threshold (3)

            await nextTick()

            expect(state.shares).toBe(5)
            expect(state.threshold).toBe(3) // Threshold should remain 3
        })
    })

    // Test the watcher for state.threshold
    describe('state.threshold watcher', () => {
        let state: { shares: number; threshold: number }

        beforeEach(() => {
            ({ state } = setupComponent())
        })

        it('should update shares to new threshold value if new threshold > shares', async () => {
            state.shares = 5
            state.threshold = 8 // New threshold (8) is greater than current shares (5)

            await nextTick() // Wait for watcher to execute

            expect(state.threshold).toBe(8)
            expect(state.shares).toBe(8) // Shares should be updated to 8
        })

        it('should NOT update shares if new threshold <= shares', async () => {
            state.shares = 10
            state.threshold = 6 // New threshold (6) is less than current shares (10)

            await nextTick()

            expect(state.shares).toBe(10) // Shares should remain 10
            expect(state.threshold).toBe(6)
        })
    })

    // Test component interactions (optional, but good for coverage)
    describe('Component Interaction (InputNumber)', () => {
        it('updates state.shares when InputNumber for shares is changed', async () => {
            const { wrapper, state } = setupComponent()
            const sharesInput = wrapper.find('input[input-id="shares"]')

            // Set new value (InputNumber mock emits number via valueAsNumber)
            sharesInput.setValue(12)
            await nextTick()

            expect(state.shares).toBe(12)
            expect((sharesInput.element as HTMLInputElement).value).toBe('12') // Check the mocked input value
        })

        it('updates state.threshold when InputNumber for threshold is changed', async () => {
            const { wrapper, state } = setupComponent()
            const thresholdInput = wrapper.find('input[input-id="threshold"]')

            // Set new value
            thresholdInput.setValue(7)
            await nextTick()

            expect(state.threshold).toBe(7)
            expect((thresholdInput.element as HTMLInputElement).value).toBe('7') // Check the mocked input value
        })

        it('triggers watcher side-effect on input change for shares', async () => {
            const { wrapper, state } = setupComponent()
            // Initial state: shares=5, threshold=3
            state.threshold = 10 // Set threshold higher than initial shares
            await nextTick()

            const sharesInput = wrapper.find('input[input-id="shares"]')

            // Change shares to 8 (shares < threshold: 8 < 10)
            sharesInput.setValue(8)
            await nextTick() // Wait for Input update
            await nextTick() // Wait for watcher

            // Shares is updated, and threshold is corrected by the watcher
            expect(state.shares).toBe(8)
            expect(state.threshold).toBe(8)
        })

        it('triggers watcher side-effect on input change for threshold', async () => {
            const { wrapper, state } = setupComponent()
            // Initial state: shares=5, threshold=3

            const thresholdInput = wrapper.find('input[input-id="threshold"]')

            // Change threshold to 10 (threshold > shares: 10 > 5)
            thresholdInput.setValue(10)
            await nextTick() // Wait for Input update
            await nextTick() // Wait for watcher

            // Threshold is updated, and shares is corrected by the watcher
            expect(state.threshold).toBe(10)
            expect(state.shares).toBe(10)
        })
    })
})