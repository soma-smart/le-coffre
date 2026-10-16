import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import GroupHistoryModal from '@/components/modals/GroupHistoryModal.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import type { Group, GroupEvent } from '@/domain/group/Group'
import i18n from '@/i18n'

const t = i18n.global.t.bind(i18n.global)

const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

const DialogStub = defineComponent({
  props: ['visible'],
  setup(_, { slots }) {
    return () => h('div', { class: 'dialog-stub' }, [slots.default?.()])
  },
})

const group: Group = {
  id: 'group-1',
  name: 'Platform',
  isPersonal: false,
  userId: null,
  owners: ['user-1'],
  members: ['user-2'],
}

function makeEvent(overrides: Partial<GroupEvent>): GroupEvent {
  return {
    eventId: 'e1',
    eventType: 'UserRemovedFromGroupEvent',
    occurredOn: new Date().toISOString(),
    actorUserId: 'user-1',
    actorEmail: 'actor@example.com',
    eventData: { userId: 'user-2', userEmail: 'user2@example.com' },
    ...overrides,
  }
}

async function mountModal(repo: InMemoryGroupRepository) {
  const { pinia, container } = createTestContext({ groupRepository: repo })
  const wrapper = mount(GroupHistoryModal, {
    props: { visible: true, group },
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
      stubs: { Dialog: DialogStub },
    },
  })
  await flushPromises()
  return wrapper
}

describe('GroupHistoryModal self-leave labelling', () => {
  it('tags a self-removal as a voluntary departure, not a removal', async () => {
    const repo = new InMemoryGroupRepository().seed(group)
    repo.addEvent(group.id, makeEvent({ actorUserId: 'user-2', eventData: { userId: 'user-2' } }))

    const wrapper = await mountModal(repo)

    expect(wrapper.text()).toContain(t('components.groupHistoryModal.leftGroupEventType'))
    expect(wrapper.text()).not.toContain(t('common.eventTypes.UserRemovedFromGroupEvent'))
  })

  it('tags an owner-initiated removal as a removal, not a departure', async () => {
    const repo = new InMemoryGroupRepository().seed(group)
    repo.addEvent(group.id, makeEvent({ actorUserId: 'user-1', eventData: { userId: 'user-2' } }))

    const wrapper = await mountModal(repo)

    expect(wrapper.text()).toContain(t('common.eventTypes.UserRemovedFromGroupEvent'))
    expect(wrapper.text()).not.toContain(t('components.groupHistoryModal.leftGroupEventType'))
  })

  it('offers the self-leave filter as its own entry, distinct from plain removal', async () => {
    const repo = new InMemoryGroupRepository().seed(group)
    repo.addEvent(
      group.id,
      makeEvent({ eventId: 'e-left', actorUserId: 'user-2', eventData: { userId: 'user-2' } }),
    )
    repo.addEvent(
      group.id,
      makeEvent({ eventId: 'e-removed', actorUserId: 'user-1', eventData: { userId: 'user-2' } }),
    )

    const wrapper = await mountModal(repo)

    const multiSelect = wrapper.findComponent({ name: 'MultiSelect' })
    const options = multiSelect.props('options') as { label: string; value: string }[]

    expect(options).toEqual(
      expect.arrayContaining([
        {
          label: t('components.groupHistoryModal.leftGroupEventType'),
          value: 'UserLeftGroupEvent',
        },
        {
          label: t('common.eventTypes.UserRemovedFromGroupEvent'),
          value: 'UserRemovedFromGroupEvent',
        },
      ]),
    )
  })

  it('selecting the self-leave filter entry only displays self-leave rows', async () => {
    const repo = new InMemoryGroupRepository().seed(group)
    repo.addEvent(
      group.id,
      makeEvent({ eventId: 'e-left', actorUserId: 'user-2', eventData: { userId: 'user-2' } }),
    )
    repo.addEvent(
      group.id,
      makeEvent({ eventId: 'e-removed', actorUserId: 'user-1', eventData: { userId: 'user-2' } }),
    )

    const wrapper = await mountModal(repo)

    const multiSelect = wrapper.findComponent({ name: 'MultiSelect' })
    await multiSelect.vm.$emit('update:modelValue', ['UserLeftGroupEvent'])
    await multiSelect.vm.$emit('change')
    await flushPromises()

    expect(wrapper.text()).toContain(t('components.groupHistoryModal.leftGroupEventType'))
    expect(wrapper.text()).not.toContain(t('common.eventTypes.UserRemovedFromGroupEvent'))
  })
})
