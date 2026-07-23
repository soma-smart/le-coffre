import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import OneTimeLinkModal from '@/components/modals/OneTimeLinkModal.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryOneTimeLinkRepository } from '@/infrastructure/in_memory/InMemoryOneTimeLinkRepository'
import type { Password } from '@/domain/password/Password'
import type { OneTimeLink } from '@/domain/oneTimeLink/OneTimeLink'

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

function mountModal(repo: InMemoryOneTimeLinkRepository) {
  const { pinia, container } = createTestContext({ oneTimeLinkRepository: repo })
  return mount(OneTimeLinkModal, {
    props: { visible: false, password },
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
      stubs: { Dialog: DialogStub, ConfirmationModal: ConfirmationStub },
    },
  })
}

async function openModal(repo: InMemoryOneTimeLinkRepository) {
  const wrapper = mountModal(repo)
  // The list only loads when the dialog opens, mirroring production.
  await wrapper.setProps({ visible: true })
  await flushPromises()
  return wrapper
}

describe('OneTimeLinkModal', () => {
  it('shows when each link was created, not only its expiry', async () => {
    const repo = new InMemoryOneTimeLinkRepository().seed(makeLink())

    const wrapper = await openModal(repo)

    expect(wrapper.find('[data-testid="created-label"]').text()).toMatch(
      /created .*(hour|minute|second)/,
    )
  })

  it('revokes only after confirmation, never on the click alone', async () => {
    const repo = new InMemoryOneTimeLinkRepository().seed(makeLink({ id: 'live' }))
    const revokeSpy = vi.spyOn(repo, 'revoke')

    const wrapper = await openModal(repo)
    const revokeButton = wrapper.findAll('button').find((b) => b.text().includes('Revoke'))
    await revokeButton!.trigger('click')

    // The click opens the prompt; the use case has not run yet.
    expect(revokeSpy).not.toHaveBeenCalled()

    await wrapper.find('[data-testid="confirm-yes"]').trigger('click')
    await flushPromises()
    expect(revokeSpy).toHaveBeenCalledWith('live')
  })
})
