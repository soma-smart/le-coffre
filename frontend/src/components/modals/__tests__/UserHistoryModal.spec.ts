import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import UserHistoryModal from '@/components/modals/UserHistoryModal.vue'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import type { User, UserPasswordEvent } from '@/domain/user/User'
import { createTestContext } from '@/test/componentTestHelpers'
import i18n from '@/i18n'

const t = i18n.global.t.bind(i18n.global)

const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

const DialogStub = defineComponent({
  props: ['visible'],
  setup(_, { slots }) {
    return () => h('div', { class: 'dialog-stub' }, [slots.default?.(), slots.footer?.()])
  },
})

const sampleUser: User = {
  id: 'user-1',
  username: 'alice',
  email: 'alice@example.com',
  name: 'Alice',
  roles: [],
  personalGroupId: 'personal-user-1',
  isSso: false,
}

function makeEvent(overrides: Partial<UserPasswordEvent>): UserPasswordEvent {
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  return {
    eventId: 'e1',
    eventType: 'PasswordCreatedEvent',
    occurredOn: yesterday.toISOString(),
    passwordId: 'pwd-1',
    actorUserId: 'user-1',
    eventData: {},
    ...overrides,
  }
}

describe('UserHistoryModal', () => {
  let repo: InMemoryUserRepository
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    toastAdd.mockClear()
    repo = new InMemoryUserRepository()
    repo.seed(sampleUser)
    ;({ pinia, container } = createTestContext({ userRepository: repo }))
  })

  const mountModal = () =>
    mount(UserHistoryModal, {
      props: { visible: true, user: sampleUser },
      global: {
        plugins: [pinia],
        provide: { [CONTAINER_KEY as symbol]: container },
        stubs: { Dialog: DialogStub },
      },
    })

  it('renders a share expiration change rather than dumping raw JSON', async () => {
    repo.seedPasswordEvents('user-1', [
      makeEvent({
        eventType: 'PasswordShareExpirationUpdatedEvent',
        eventData: { sharedWithGroupId: 'abcdef12-3456', expiresAt: '2026-09-01T10:00:00Z' },
      }),
    ])

    const wrapper = mountModal()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain(t('common.passwordEvents.accessDurationChanged'))
    expect(text).toContain(t('common.passwordEvents.nowExpiresLabel').trim())
    expect(text).not.toContain('sharedWithGroupId')
  })

  it('says a share was made permanent when the deadline is lifted', async () => {
    repo.seedPasswordEvents('user-1', [
      makeEvent({
        eventType: 'PasswordShareExpirationUpdatedEvent',
        eventData: { sharedWithGroupId: 'abcdef12-3456', expiresAt: null },
      }),
    ])

    const wrapper = mountModal()
    await flushPromises()

    expect(wrapper.text()).toContain(t('common.passwordEvents.nowPermanentLabel').trim())
  })

  it('shows the deadline of a time-limited share', async () => {
    repo.seedPasswordEvents('user-1', [
      makeEvent({
        eventType: 'PasswordSharedEvent',
        eventData: { sharedWithGroupName: 'Contractors', expiresAt: '2026-09-01T10:00:00Z' },
      }),
    ])

    const wrapper = mountModal()
    await flushPromises()

    expect(wrapper.text()).toContain('Contractors')
    expect(wrapper.text()).toContain(t('common.passwordEvents.untilLabel').trim())
  })

  it('labels one-time-link events, which the local severity copy used to miss', async () => {
    // This modal carried its own copy of the domain's severity table and had
    // fallen behind by a whole feature. It now calls the domain directly.
    repo.seedPasswordEvents('user-1', [
      makeEvent({ eventType: 'OneTimeLinkReadEvent', eventData: {} }),
    ])

    const wrapper = mountModal()
    await flushPromises()

    expect(wrapper.text()).toContain(t('common.eventTypes.OneTimeLinkReadEvent'))
  })

  it('shows translated labels in the event-type filter, keyed by the raw event type', async () => {
    repo.seedPasswordEvents('user-1', [
      makeEvent({ eventType: 'PasswordCreatedEvent' }),
      makeEvent({ eventId: 'e2', eventType: 'PasswordUpdatedEvent' }),
    ])

    const wrapper = mountModal()
    await flushPromises()

    const multiSelect = wrapper.findComponent({ name: 'MultiSelect' })
    const options = multiSelect.props('options') as { label: string; value: string }[]

    expect(options).toEqual(
      expect.arrayContaining([
        { label: t('common.eventTypes.PasswordCreatedEvent'), value: 'PasswordCreatedEvent' },
        { label: t('common.eventTypes.PasswordUpdatedEvent'), value: 'PasswordUpdatedEvent' },
      ]),
    )
  })

  it('queries by the raw event type when a translated filter option is selected', async () => {
    repo.seedPasswordEvents('user-1', [makeEvent({ eventType: 'PasswordCreatedEvent' })])
    const listEventsSpy = vi.spyOn(repo, 'listPasswordEvents')

    const wrapper = mountModal()
    await flushPromises()
    listEventsSpy.mockClear()

    const multiSelect = wrapper.findComponent({ name: 'MultiSelect' })
    await multiSelect.vm.$emit('update:modelValue', ['PasswordCreatedEvent'])
    await multiSelect.vm.$emit('change')
    await flushPromises()

    expect(listEventsSpy).toHaveBeenCalledWith(
      'user-1',
      expect.objectContaining({ eventTypes: ['PasswordCreatedEvent'] }),
    )
  })
})
