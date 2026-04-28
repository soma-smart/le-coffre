import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import ConfirmationModal from '@/components/modals/ConfirmationModal.vue'

// Pass-through stub so Dialog's default teleport doesn't move the body to
// document.body, which would make findAll() / template assertions miss it.
const DialogStub = defineComponent({
  props: ['visible'],
  emits: ['update:visible'],
  setup(_, { slots }) {
    return () => h('div', { 'data-testid': 'dialog-stub' }, [slots.default?.(), slots.footer?.()])
  },
})

describe('ConfirmationModal', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('clears the countdown interval when the component unmounts mid-countdown', async () => {
    const clearSpy = vi.spyOn(globalThis, 'clearInterval')

    const wrapper = mount(ConfirmationModal, {
      props: {
        visible: false,
        title: 'Confirm',
        question: 'Are you sure?',
        description: 'This will delete the row.',
        countdownSeconds: 5,
      },
      global: { stubs: { Dialog: DialogStub } },
    })

    // Open the modal — the watcher fires, schedules an interval after nextTick.
    await wrapper.setProps({ visible: true })
    await wrapper.vm.$nextTick()
    clearSpy.mockClear() // ignore any stopCountdown(s) called during open

    wrapper.unmount()
    expect(clearSpy).toHaveBeenCalled()
  })

  it('renders the description slot when provided, ignoring the description prop', () => {
    const wrapper = mount(ConfirmationModal, {
      props: {
        visible: true,
        title: 'Confirm',
        question: 'Are you sure?',
        description: 'fallback text that should not render',
      },
      slots: {
        description: '<span data-testid="custom-desc">Custom <b>rich</b> description</span>',
      },
      global: { stubs: { Dialog: DialogStub } },
    })

    expect(wrapper.find('[data-testid="custom-desc"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('fallback text that should not render')
  })

  it('falls back to splitting the description prop on newlines when no slot is provided', () => {
    const wrapper = mount(ConfirmationModal, {
      props: {
        visible: true,
        title: 'Confirm',
        question: 'Are you sure?',
        description: 'Line 1\nLine 2\nLine 3',
      },
      global: { stubs: { Dialog: DialogStub } },
    })

    const paragraphs = wrapper.findAll('p').filter((p) => /Line/.test(p.text()))
    expect(paragraphs.map((p) => p.text())).toEqual(['Line 1', 'Line 2', 'Line 3'])
  })
})
