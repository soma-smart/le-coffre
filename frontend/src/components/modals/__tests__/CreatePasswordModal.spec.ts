import { describe, expect, it, beforeEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import CreatePasswordModal from '@/components/modals/CreatePasswordModal.vue'
import { buildContainer, type Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { useGroupsStore } from '@/stores/groups'

// Pass-through stub so Dialog doesn't teleport to document.body, which
// would make findAll() miss the form. The component body still renders.
const DialogStub = defineComponent({
  props: ['visible'],
  setup(_, { slots }) {
    return () => h('div', { class: 'dialog-stub' }, [slots.default?.(), slots.footer?.()])
  },
})

function mountModal(container: Container) {
  return mount(CreatePasswordModal, {
    props: { visible: true, editPassword: null, defaultGroupId: 'group-personal' },
    global: {
      provide: { [CONTAINER_KEY as symbol]: container },
      stubs: { Dialog: DialogStub },
    },
  })
}

describe('CreatePasswordModal', () => {
  let repo: InMemoryPasswordRepository
  let container: Container

  beforeEach(() => {
    setActivePinia(createPinia())
    repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-new')
    container = buildContainer({ passwordRepository: repo })
    // Seed the groups store so `groupsForPasswordCreation` resolves a default.
    const groupsStore = useGroupsStore()
    groupsStore.groups = [
      {
        id: 'group-personal',
        name: 'Personal',
        is_personal: true,
        user_id: 'user-1',
        owners: ['user-1'],
        members: [],
      },
    ]
  })

  it('creates a password through the use case when the form is submitted', async () => {
    const wrapper = mountModal(container)

    // Fill the form via the InputText components' v-model inputs.
    const inputs = wrapper.findAll('input')
    expect(inputs.length).toBeGreaterThanOrEqual(3)
    await inputs[0].setValue('Gmail') // name
    await inputs[1].setValue('super-secret') // password

    // Find the submit button (labelled "Create") inside the footer.
    const buttons = wrapper.findAll('button')
    const submit = buttons.find((b) => b.text().includes('Create'))
    expect(submit, 'expected a Create button').toBeTruthy()

    await submit!.trigger('click')
    await flushPromises()

    const stored = await repo.list()
    expect(stored).toHaveLength(1)
    expect(stored[0]).toMatchObject({ id: 'pwd-new', name: 'Gmail', groupId: 'group-personal' })
  })
})
