import { beforeEach, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import PasswordHistoryModal from '@/components/modals/PasswordHistoryModal.vue'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import type { Password } from '@/domain/password/Password'
import { createTestContext } from '@/test/componentTestHelpers'

const DialogStub = defineComponent({
  props: ['visible'],
  setup(_, { slots }) {
    return () => h('div', { class: 'dialog-stub' }, [slots.default?.(), slots.footer?.()])
  },
})

const samplePassword: Password = {
  id: 'pwd-1',
  name: 'Gmail',
  folder: 'Mail',
  groupId: 'g',
  createdAt: '2024-01-01T00:00:00Z',
  lastUpdatedAt: '2024-02-01T00:00:00Z',
  canRead: true,
  canWrite: true,
  login: null,
  url: null,
  accessibleGroupIds: ['g'],
}

describe('PasswordHistoryModal', () => {
  let repo: InMemoryPasswordRepository
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    repo = new InMemoryPasswordRepository().seed(samplePassword)
    // The modal's default date range is "last 30 days" — seed events
    // relative to `now` so they fall inside that window.
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    const twoDaysAgo = new Date()
    twoDaysAgo.setDate(twoDaysAgo.getDate() - 2)
    repo.addEvent('pwd-1', {
      eventId: 'e1',
      eventType: 'PasswordCreatedEvent',
      occurredOn: twoDaysAgo.toISOString(),
      actorUserId: 'u',
      actorEmail: 'alice@example.com',
      eventData: { folder: 'Mail' },
    })
    repo.addEvent('pwd-1', {
      eventId: 'e2',
      eventType: 'PasswordUpdatedEvent',
      occurredOn: yesterday.toISOString(),
      actorUserId: 'u',
      actorEmail: 'alice@example.com',
      eventData: { has_name_changed: true },
    })
    ;({ pinia, container } = createTestContext({ passwordRepository: repo }))
  })

  it('renders events fetched through ListPasswordEventsUseCase', async () => {
    const wrapper = mount(PasswordHistoryModal, {
      props: { visible: true, password: samplePassword },
      global: {
        plugins: [pinia],
        provide: { [CONTAINER_KEY as symbol]: container },
        stubs: { Dialog: DialogStub },
      },
    })
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('alice@example.com')
    expect(text).toContain('Created')
    expect(text).toContain('Updated')
  })
})
