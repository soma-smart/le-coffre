import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import CreatePasswordModal from '@/components/modals/CreatePasswordModal.vue'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { useGroupsStore } from '@/stores/groups'
import { createTestContext } from '@/test/componentTestHelpers'

// Pass-through stub so Dialog doesn't teleport to document.body, which
// would make findAll() miss the form. The body still renders in place.
const DialogStub = defineComponent({
  props: ['visible'],
  setup(_, { slots }) {
    return () => h('div', { class: 'dialog-stub' }, [slots.default?.(), slots.footer?.()])
  },
})

const personalGroup = {
  id: 'group-personal',
  name: 'Personal',
  is_personal: true,
  user_id: 'user-1',
  owners: ['user-1'],
  members: [],
}

describe('CreatePasswordModal', () => {
  let repo: InMemoryPasswordRepository
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    repo = new InMemoryPasswordRepository().useIdGenerator(() => 'pwd-new')
    ;({ pinia, container } = createTestContext({ passwordRepository: repo }))

    // Seed BOTH `groups` and `userPersonalGroup` — the modal's
    // `groupsForPasswordCreation` computed reads the filtered refs, not
    // the raw `groups` array, so seeding just `groups` isn't enough to
    // make resolveDefaultGroupId() return a non-empty id.
    const groupsStore = useGroupsStore()
    groupsStore.groups = [personalGroup]
    groupsStore.userPersonalGroup = personalGroup
    // Stub the async fetcher — without this, the modal's onMounted +
    // watch(visible) fire fetchAllGroups(true) against the SDK,
    // clobbering the seed on failure.
    groupsStore.fetchAllGroups = vi.fn(async () => {})
  })

  it('creates a password through the use case when the form is submitted', async () => {
    const wrapper = mount(CreatePasswordModal, {
      props: { visible: true, editPassword: null, defaultGroupId: 'group-personal' },
      global: {
        plugins: [pinia],
        provide: { [CONTAINER_KEY as symbol]: container },
        stubs: { Dialog: DialogStub },
      },
    })
    // Let onMounted + watch(visible) callbacks settle before filling the form.
    await flushPromises()

    // Target by id — `findAll('input')` returns the Select's hidden
    // input + AutoComplete's input in among our InputText fields, so
    // positional access is fragile.
    await wrapper.find('input#password-name').setValue('Gmail')
    await wrapper.find('input#password-value').setValue('super-secret')

    const submit = wrapper.findAll('button').find((b) => b.text().trim() === 'Create')
    expect(submit, 'expected a Create button in the footer').toBeTruthy()

    await submit!.trigger('click')
    await flushPromises()

    const stored = await repo.list()
    expect(stored).toHaveLength(1)
    expect(stored[0]).toMatchObject({ id: 'pwd-new', name: 'Gmail', groupId: 'group-personal' })
  })
})
