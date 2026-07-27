import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import ShareDurationPicker from '@/components/shared/ShareDurationPicker.vue'

const NOW = new Date('2026-07-27T12:00:00Z')

/** Minimal stand-in for PrimeVue's Select: a native select over the options. */
const SelectStub = defineComponent({
  props: { modelValue: { type: null, default: null }, options: { type: Array, default: () => [] } },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () =>
      h(
        'select',
        {
          onChange: (event: Event) =>
            emit('update:modelValue', Number((event.target as HTMLSelectElement).value)),
        },
        (props.options as Array<{ label: string; value: number }>).map((option) =>
          h(
            'option',
            { value: option.value, selected: option.value === props.modelValue },
            option.label,
          ),
        ),
      )
  },
})

/** Stands in for PrimeVue's DatePicker; exposes a button that picks a fixed date. */
const DatePickerStub = defineComponent({
  props: { modelValue: { type: Date, default: null } },
  emits: ['update:modelValue'],
  setup(_, { emit }) {
    return () =>
      h('button', {
        onClick: () => emit('update:modelValue', new Date('2026-12-25T09:30:00Z')),
      })
  },
})

function mountPicker(initial: string | null = null) {
  const model = ref<string | null>(initial)
  const wrapper = mount(ShareDurationPicker, {
    props: {
      modelValue: model.value,
      now: NOW,
      'onUpdate:modelValue': (value: string | null) => {
        model.value = value
        wrapper.setProps({ modelValue: value })
      },
    },
    global: { stubs: { Select: SelectStub, DatePicker: DatePickerStub } },
  })
  return { wrapper, model }
}

async function choosePreset(wrapper: ReturnType<typeof mountPicker>['wrapper'], value: number) {
  const select = wrapper.get('[data-testid="share-duration-select"]')
  ;(select.element as HTMLSelectElement).value = String(value)
  await select.trigger('change')
}

describe('ShareDurationPicker', () => {
  it('starts on Permanent and emits no deadline', () => {
    const { model, wrapper } = mountPicker()

    expect(model.value).toBeNull()
    expect(wrapper.text()).toContain('Access lasts until it is revoked')
  })

  it('turns a preset into an absolute deadline measured from now', async () => {
    const { wrapper, model } = mountPicker()

    await choosePreset(wrapper, 3600)

    expect(model.value).toBe('2026-07-27T13:00:00.000Z')
  })

  it('stays on the chosen preset instead of flipping to Custom', async () => {
    // The emitted value bounces back through the parent's v-model. If the
    // sync-back mistakes that echo for an external change, the dropdown jumps
    // to "Custom…" and the calendar opens under the user's selection.
    const { wrapper } = mountPicker()

    await choosePreset(wrapper, 3600)
    await flushPromises()

    const select = wrapper.get('[data-testid="share-duration-select"]').element as HTMLSelectElement
    expect(select.value).toBe('3600')
    expect(wrapper.find('[data-testid="share-duration-custom"]').exists()).toBe(false)
  })

  it('supports the long presets', async () => {
    const { wrapper, model } = mountPicker()

    await choosePreset(wrapper, 7776000)

    expect(model.value).toBe('2026-10-25T12:00:00.000Z')
  })

  it('follows a switch from one preset to another', async () => {
    const { wrapper, model } = mountPicker()
    await choosePreset(wrapper, 3600)
    await flushPromises()

    await choosePreset(wrapper, 604800)
    await flushPromises()

    expect(model.value).toBe('2026-08-03T12:00:00.000Z')
    const select = wrapper.get('[data-testid="share-duration-select"]').element as HTMLSelectElement
    expect(select.value).toBe('604800')
  })

  it('returns to Permanent when the parent clears the model after a share', async () => {
    const { wrapper } = mountPicker()
    await choosePreset(wrapper, 86400)
    await flushPromises()

    await wrapper.setProps({ modelValue: null })
    await flushPromises()

    const select = wrapper.get('[data-testid="share-duration-select"]').element as HTMLSelectElement
    expect(select.value).toBe('0')
  })

  it('goes back to no deadline when Permanent is re-selected', async () => {
    const { wrapper, model } = mountPicker()
    await choosePreset(wrapper, 3600)

    await choosePreset(wrapper, 0)

    expect(model.value).toBeNull()
  })

  it('reveals the calendar for a custom date and emits what it returns', async () => {
    const { wrapper, model } = mountPicker()

    await choosePreset(wrapper, -1)
    expect(wrapper.find('[data-testid="share-duration-custom"]').exists()).toBe(true)

    await wrapper.get('[data-testid="share-duration-custom"]').trigger('click')

    expect(model.value).toBe('2026-12-25T09:30:00.000Z')
  })

  it('opens on the deadline of an existing share rather than resetting it', () => {
    const { wrapper, model } = mountPicker('2026-09-01T08:00:00Z')

    expect(model.value).toBe('2026-09-01T08:00:00Z')
    expect(wrapper.find('[data-testid="share-duration-custom"]').exists()).toBe(true)
  })

  it('hides the calendar again when the parent clears the model', async () => {
    const { wrapper } = mountPicker('2026-09-01T08:00:00Z')

    await wrapper.setProps({ modelValue: null })

    expect(wrapper.find('[data-testid="share-duration-custom"]').exists()).toBe(false)
  })
})
