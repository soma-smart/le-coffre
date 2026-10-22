import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import OneTimeLinkModal from '@/components/modals/OneTimeLinkModal.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryOneTimeLinkRepository } from '@/infrastructure/in_memory/InMemoryOneTimeLinkRepository'
import { InMemoryOneTimeLinkSubscriptionRepository } from '@/infrastructure/in_memory/InMemoryOneTimeLinkSubscriptionRepository'
import type { Password } from '@/domain/password/Password'
import type { OneTimeLink } from '@/domain/oneTimeLink/OneTimeLink'
import i18n from '@/i18n'

const t = i18n.global.t.bind(i18n.global)

const HOUR = 3_600_000

const password: Password = {
  id: 'pwd-1',
  name: 'Prod DB',
  folder: 'Work',
  groupId: 'g',
  createdAt: '2026-01-01T00:00:00Z',
  lastUpdatedAt: '2026-01-01T00:00:00Z',
  canRead: true,
  canWrite: true,
  login: null,
  url: null,
  accessibleGroupIds: ['g'],
  accessExpiresAt: null,
}

function makeLink(overrides: Partial<OneTimeLink> = {}): OneTimeLink {
  const now = Date.now()
  return {
    id: 'link-1',
    passwordId: 'pwd-1',
    createdByUserId: 'user-1',
    createdAt: new Date(now - HOUR).toISOString(),
    expiresAt: new Date(now + HOUR).toISOString(),
    readAt: null,
    revokedAt: null,
    ...overrides,
  }
}

// Pass-through so PrimeVue's Dialog teleport does not move content out of the wrapper.
const DialogStub = defineComponent({
  props: ['visible'],
  setup(_, { slots }) {
    return () => h('div', { 'data-testid': 'dialog' }, [slots.default?.()])
  },
})

const ConfirmationStub = defineComponent({
  props: { visible: Boolean },
  emits: ['update:visible', 'confirm'],
  setup(props, { emit }) {
    return () =>
      props.visible
        ? h('button', { 'data-testid': 'confirm-yes', onClick: () => emit('confirm') }, 'yes')
        : null
  },
})

function mountModal(
  repo: InMemoryOneTimeLinkRepository,
  subscriptions = new InMemoryOneTimeLinkSubscriptionRepository(),
) {
  const { pinia, container } = createTestContext({
    oneTimeLinkRepository: repo,
    oneTimeLinkSubscriptionRepository: subscriptions,
  })
  return mount(OneTimeLinkModal, {
    props: { visible: false, password },
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
      stubs: { Dialog: DialogStub, ConfirmationModal: ConfirmationStub },
    },
  })
}

async function openModal(
  repo: InMemoryOneTimeLinkRepository,
  subscriptions?: InMemoryOneTimeLinkSubscriptionRepository,
) {
  const wrapper = mountModal(repo, subscriptions)
  // The list only loads when the dialog opens, mirroring production.
  await wrapper.setProps({ visible: true })
  await flushPromises()
  return wrapper
}

describe('OneTimeLinkModal', () => {
  it('shows when each link was created, not only its expiry', async () => {
    const repo = new InMemoryOneTimeLinkRepository().seed(makeLink())

    const wrapper = await openModal(repo)

    const createdPrefix = t('components.oneTimeLinkModal.createdLabel', { relative: '' }).trim()
    expect(wrapper.find('[data-testid="created-label"]').text()).toMatch(
      new RegExp(`${createdPrefix} .*(hour|minute|second)`),
    )
  })

  it('revokes only after confirmation, never on the click alone', async () => {
    const repo = new InMemoryOneTimeLinkRepository().seed(makeLink({ id: 'live' }))
    const revokeSpy = vi.spyOn(repo, 'revoke')

    const wrapper = await openModal(repo)
    const revokeLabel = t('components.oneTimeLinkModal.revokeButton')
    const revokeButton = wrapper.findAll('button').find((b) => b.text().includes(revokeLabel))
    await revokeButton!.trigger('click')

    // The click opens the prompt; the use case has not run yet.
    expect(revokeSpy).not.toHaveBeenCalled()

    await wrapper.find('[data-testid="confirm-yes"]').trigger('click')
    await flushPromises()
    expect(revokeSpy).toHaveBeenCalledWith('live')
  })

  describe('notification options', () => {
    const readBox = (wrapper: ReturnType<typeof mountModal>) =>
      wrapper.find<HTMLInputElement>('#otl-notify-on-read')
    const expiryBox = (wrapper: ReturnType<typeof mountModal>) =>
      wrapper.find<HTMLInputElement>('#otl-notify-on-expiry')
    const generate = async (wrapper: ReturnType<typeof mountModal>) => {
      await wrapper.find('[data-testid="generate-link"]').trigger('click')
      await flushPromises()
    }

    const openWithSubscriptions = async () => {
      const repo = new InMemoryOneTimeLinkRepository().useIdGenerator(() => 'link-1')
      const subscriptions = new InMemoryOneTimeLinkSubscriptionRepository()
      const wrapper = await openModal(repo, subscriptions)
      return { repo, subscriptions, wrapper }
    }

    it('offers both options, unchecked by default, with their labels', async () => {
      const wrapper = await openModal(new InMemoryOneTimeLinkRepository())

      expect(readBox(wrapper).exists()).toBe(true)
      expect(expiryBox(wrapper).exists()).toBe(true)
      expect(readBox(wrapper).element.checked).toBe(false)
      expect(expiryBox(wrapper).element.checked).toBe(false)
      expect(wrapper.text()).toContain(t('components.oneTimeLinkModal.notifyOnReadLabel'))
      expect(wrapper.text()).toContain(t('components.oneTimeLinkModal.notifyOnExpiryLabel'))
    })

    it('creates a link that notifies nobody when left untouched', async () => {
      const { repo, subscriptions, wrapper } = await openWithSubscriptions()
      const createSpy = vi.spyOn(repo, 'create')
      const subscribeSpy = vi.spyOn(subscriptions, 'subscribeToOneTimeLink')

      await generate(wrapper)

      expect(createSpy).toHaveBeenCalledWith('pwd-1', 86400)
      expect(subscribeSpy).not.toHaveBeenCalled()
      expect(wrapper.find('[data-testid="generated-url"]').exists()).toBe(true)
    })

    it('subscribes the created link to the chosen notification', async () => {
      const { subscriptions, wrapper } = await openWithSubscriptions()
      const subscribeSpy = vi.spyOn(subscriptions, 'subscribeToOneTimeLink')

      await readBox(wrapper).setValue(true)
      await generate(wrapper)

      expect(subscribeSpy).toHaveBeenCalledTimes(1)
      expect(subscribeSpy).toHaveBeenLastCalledWith('link-1', {
        notifyOnRead: true,
        notifyOnExpiry: false,
      })
    })

    it('subscribes to both notifications when both are checked', async () => {
      const { subscriptions, wrapper } = await openWithSubscriptions()
      const subscribeSpy = vi.spyOn(subscriptions, 'subscribeToOneTimeLink')

      await readBox(wrapper).setValue(true)
      await expiryBox(wrapper).setValue(true)
      await generate(wrapper)

      expect(subscribeSpy).toHaveBeenLastCalledWith('link-1', {
        notifyOnRead: true,
        notifyOnExpiry: true,
      })
      expect(wrapper.find('[data-testid="notifications-failed"]').exists()).toBe(false)
    })

    it('keeps the link and warns when the notifications could not be set up', async () => {
      const { subscriptions, wrapper } = await openWithSubscriptions()
      subscriptions.failSubscribeOnce(new Error('boom'))

      await expiryBox(wrapper).setValue(true)
      await generate(wrapper)

      expect(wrapper.find('[data-testid="generated-url"]').exists()).toBe(true)
      expect(wrapper.find('code').text()).toContain('/')
      expect(wrapper.find('[data-testid="notifications-failed"]').text()).toContain(
        t('components.oneTimeLinkModal.notificationsFailed'),
      )
    })

    it('resets both choices when the dialog is closed', async () => {
      const wrapper = await openModal(new InMemoryOneTimeLinkRepository())
      await readBox(wrapper).setValue(true)
      await expiryBox(wrapper).setValue(true)
      expect(readBox(wrapper).element.checked).toBe(true)

      await wrapper.setProps({ visible: false })
      await wrapper.setProps({ visible: true })
      await flushPromises()

      expect(readBox(wrapper).element.checked).toBe(false)
      expect(expiryBox(wrapper).element.checked).toBe(false)
    })
  })
})
