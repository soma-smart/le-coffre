import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import PasswordHistoryModal from '@/components/modals/PasswordHistoryModal.vue'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import type { Password } from '@/domain/password/Password'
import { VaultLockedError } from '@/domain/vault/errors'
import { createTestContext } from '@/test/componentTestHelpers'

// Whether a load failure surfaces a toast is the behaviour under test for the
// vault-locked case, so we capture toast.add() through a module mock.
const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

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
    toastAdd.mockClear()
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
      eventData: { hasNameChanged: true },
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

  it('clears the rendered events when the modal closes', async () => {
    const wrapper = mount(PasswordHistoryModal, {
      props: { visible: true, password: samplePassword },
      global: {
        plugins: [pinia],
        provide: { [CONTAINER_KEY as symbol]: container },
        stubs: { Dialog: DialogStub },
      },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('alice@example.com')

    await wrapper.setProps({ visible: false })
    await flushPromises()

    // Closing drops the rows so the next open never flashes stale history.
    expect(wrapper.text()).not.toContain('alice@example.com')
  })

  it('suppresses the duplicate toast when the vault is locked (503 → VaultLockedError)', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      repo.listEvents = async () => {
        throw new VaultLockedError()
      }
      mount(PasswordHistoryModal, {
        props: { visible: true, password: samplePassword },
        global: {
          plugins: [pinia],
          provide: { [CONTAINER_KEY as symbol]: container },
          stubs: { Dialog: DialogStub },
        },
      })
      await flushPromises()

      // The global interceptor owns the vault-locked UX; the modal stays quiet.
      expect(toastAdd).not.toHaveBeenCalled()
    } finally {
      consoleError.mockRestore()
    }
  })

  it('shows a load-failed toast on a non-vault error', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      repo.listEvents = async () => {
        throw new Error('network down')
      }
      mount(PasswordHistoryModal, {
        props: { visible: true, password: samplePassword },
        global: {
          plugins: [pinia],
          provide: { [CONTAINER_KEY as symbol]: container },
          stubs: { Dialog: DialogStub },
        },
      })
      await flushPromises()

      expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error' }))
    } finally {
      consoleError.mockRestore()
    }
  })

  it('renders one-time link events in words rather than as raw JSON', async () => {
    // Any event type without its own branch falls through to
    // JSON.stringify(eventData), which leaks the wire format into the UI.
    const anHourAgo = new Date()
    anHourAgo.setHours(anHourAgo.getHours() - 1)
    repo.addEvent('pwd-1', {
      eventId: 'e3',
      eventType: 'OneTimeLinkCreatedEvent',
      occurredOn: anHourAgo.toISOString(),
      actorUserId: 'u',
      actorEmail: 'alice@example.com',
      eventData: { linkId: 'l1', expiresAt: '2030-01-01T12:00:00Z' },
    })
    repo.addEvent('pwd-1', {
      eventId: 'e4',
      eventType: 'OneTimeLinkReadEvent',
      occurredOn: anHourAgo.toISOString(),
      actorUserId: 'u',
      actorEmail: 'alice@example.com',
      eventData: { linkId: 'l1', actor: 'anonymous' },
    })

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
    expect(text).toContain('One-time link created')
    // The actor column names the issuer, so the row has to say the reader was
    // anonymous or it reads as if that user opened it themselves.
    expect(text).toContain('anonymous recipient')
    expect(text).not.toContain('linkId')
    expect(text).not.toContain('{"')
  })
})
