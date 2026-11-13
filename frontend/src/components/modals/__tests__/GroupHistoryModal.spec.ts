import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import GroupHistoryModal from '@/components/modals/GroupHistoryModal.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import type { Group, GroupEvent } from '@/domain/group/Group'
import { createTestContext } from '@/test/componentTestHelpers'
import i18n from '@/i18n'

const t = i18n.global.t.bind(i18n.global)

vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))

const DialogStub = defineComponent({
  props: ['visible'],
  setup(_, { slots }) {
    return () => h('div', { class: 'dialog-stub' }, [slots.default?.()])
  },
})

const group: Group = {
  id: 'group-1',
  name: 'Platform',
  isPersonal: true,
  userId: 'user-1',
  owners: ['user-1'],
  members: [],
}

function serviceAccountEvent(eventType: string, eventId: string): GroupEvent {
  return {
    eventId,
    eventType,
    occurredOn: new Date(Date.now() - 60_000).toISOString(),
    actorPrincipalId: 'user-1',
    actor: { kind: 'user', displayName: 'Ada Owner' },
    eventData: {
      actorPrincipalId: 'user-1',
      serviceAccountId: 'account-1',
      serviceAccountName: 'nightly-deploy',
      groupId: 'group-1',
    },
  }
}

function mountWith(events: GroupEvent[]) {
  const repo = new InMemoryGroupRepository().seed(group)
  events.forEach((event) => repo.addEvent(group.id, event))
  const { pinia, container } = createTestContext({ groupRepository: repo })
  return mount(GroupHistoryModal, {
    props: { visible: true, group },
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
      stubs: { Dialog: DialogStub },
    },
  })
}

describe('GroupHistoryModal', () => {
  it('tells the lifecycle of a service account by its name, with its author', async () => {
    const wrapper = mountWith([
      serviceAccountEvent('ServiceAccountCreatedEvent', 'e1'),
      serviceAccountEvent('ServiceAccountTokenRotatedEvent', 'e2'),
      serviceAccountEvent('ServiceAccountRevokedEvent', 'e3'),
    ])
    await flushPromises()

    const text = wrapper.text()
    for (const key of [
      'serviceAccountCreated',
      'serviceAccountTokenRotated',
      'serviceAccountRevoked',
    ]) {
      expect(text).toContain(
        t(`components.groupHistoryModal.${key}`, { name: 'nightly-deploy' }).replace(/\s+/g, ' '),
      )
    }
    expect(text).toContain(t('common.eventTypes.ServiceAccountCreatedEvent'))
    expect(text).toContain('Ada Owner')
    // Rendered as sentences, never as the raw payload.
    expect(text).not.toContain('serviceAccountId')
  })
})
