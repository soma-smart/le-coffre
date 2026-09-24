import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import ServiceAccountsModal from '@/components/modals/ServiceAccountsModal.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryServiceAccountRepository } from '@/infrastructure/in_memory/InMemoryServiceAccountRepository'
import type { Group } from '@/domain/group/Group'
import type { ServiceAccount } from '@/domain/serviceAccount/ServiceAccount'

const group: Group = {
  id: 'group-1',
  name: 'Platform',
  isPersonal: false,
  userId: null,
  owners: ['user-1'],
  members: ['user-1'],
}

function makeAccount(overrides: Partial<ServiceAccount> = {}): ServiceAccount {
  return {
    id: 'account-1',
    groupId: 'group-1',
    name: 'nightly-backup',
    createdByUserId: 'user-1',
    createdByUserName: 'Ada Owner',
    createdAt: new Date(Date.now() - 3_600_000).toISOString(),
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

// Renders nothing while hidden, so that only the open confirmation of the two
// the modal mounts ever answers to `confirm-yes`.
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

function mountModal(repo: InMemoryServiceAccountRepository) {
  const { pinia, container } = createTestContext({ serviceAccountRepository: repo })
  return mount(ServiceAccountsModal, {
    props: { visible: false, group },
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
      stubs: { Dialog: DialogStub, ConfirmationModal: ConfirmationStub },
    },
  })
}

async function openModal(repo: InMemoryServiceAccountRepository) {
  const wrapper = mountModal(repo)
  // The list only loads when the dialog opens, mirroring production.
  await wrapper.setProps({ visible: true })
  await flushPromises()
  return wrapper
}

async function createAccount(wrapper: ReturnType<typeof mountModal>, name = 'nightly-backup') {
  await wrapper.find('[data-testid="new-account-name"]').setValue(name)
  await wrapper.find('[data-testid="create-account"]').trigger('click')
  await flushPromises()
}

describe('ServiceAccountsModal', () => {
  it('shows the token once after creation', async () => {
    const wrapper = await openModal(new InMemoryServiceAccountRepository())

    await createAccount(wrapper)

    const revealed = wrapper.find('[data-testid="revealed-token"]')
    expect(revealed.exists()).toBe(true)
    expect(revealed.text()).toContain('token-1')
    expect(revealed.text()).toContain('nightly-backup')
    // The create form gives way to the reveal, so the two are never both on screen.
    expect(wrapper.find('[data-testid="create-account"]').exists()).toBe(false)
  })

  it('never puts the token in the list', async () => {
    const wrapper = await openModal(new InMemoryServiceAccountRepository())
    await createAccount(wrapper)

    await wrapper.find('[data-testid="dismiss-token"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="revealed-token"]').exists()).toBe(false)
    expect(wrapper.html()).not.toContain('token-1')
    expect(wrapper.find('[data-testid="account-name"]').text()).toBe('nightly-backup')
  })

  it('wipes the token when the dialog closes, so reopening cannot recover it', async () => {
    const wrapper = await openModal(new InMemoryServiceAccountRepository())
    await createAccount(wrapper)
    expect(wrapper.html()).toContain('token-1')

    await wrapper.setProps({ visible: false })
    await wrapper.setProps({ visible: true })
    await flushPromises()

    expect(wrapper.find('[data-testid="revealed-token"]').exists()).toBe(false)
    expect(wrapper.html()).not.toContain('token-1')
  })

  it('renders the creator and the creation date', async () => {
    const repo = new InMemoryServiceAccountRepository().seed(makeAccount())
    const wrapper = await openModal(repo)

    expect(wrapper.find('[data-testid="created-label"]').text()).toContain('created')
    expect(wrapper.find('[data-testid="creator-label"]').text()).toContain('Ada Owner')
  })

  it('falls back to plain wording when the creation event is missing', async () => {
    const repo = new InMemoryServiceAccountRepository().seed(
      makeAccount({ createdAt: null, createdByUserId: null, createdByUserName: null }),
    )
    const wrapper = await openModal(repo)

    expect(wrapper.find('[data-testid="created-label"]').text()).toBe('creation date unknown')
    expect(wrapper.find('[data-testid="creator-label"]').text()).toContain('unknown')
    expect(wrapper.html()).not.toContain('Invalid Date')
  })

  it('reports how much of the cap is used', async () => {
    const repo = new InMemoryServiceAccountRepository()
      .withMaxActive(3)
      .seed(makeAccount({ id: 'a1' }))
      .seed(makeAccount({ id: 'a2' }))
    const wrapper = await openModal(repo)

    expect(wrapper.find('[data-testid="active-accounts"]').text()).toBe('2/3 active')
  })

  it('refuses creation at the cap before sending anything', async () => {
    const repo = new InMemoryServiceAccountRepository()
      .withMaxActive(2)
      .seed(makeAccount({ id: 'a1' }))
      .seed(makeAccount({ id: 'a2' }))
    const wrapper = await openModal(repo)

    expect(wrapper.find('[data-testid="cap-reached"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="create-account"]').attributes('disabled')).toBeDefined()
  })

  it('will not create an account with a blank name', async () => {
    const wrapper = await openModal(new InMemoryServiceAccountRepository())

    await wrapper.find('[data-testid="new-account-name"]').setValue('   ')

    expect(wrapper.find('[data-testid="create-account"]').attributes('disabled')).toBeDefined()
  })

  it('only rotates once the consequences have been confirmed', async () => {
    const repo = new InMemoryServiceAccountRepository().seed(makeAccount())
    const wrapper = await openModal(repo)

    await wrapper.find('[data-testid="rotate-account"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="revealed-token"]').exists()).toBe(false)

    await wrapper.find('[data-testid="confirm-yes"]').trigger('click')
    await flushPromises()

    const revealed = wrapper.find('[data-testid="revealed-token"]')
    expect(revealed.exists()).toBe(true)
    expect(revealed.text()).toContain('New token for')
    expect(revealed.text()).toContain('nightly-backup')
  })

  it('keeps the account and its history through a rotation', async () => {
    const repo = new InMemoryServiceAccountRepository().seed(makeAccount())
    const wrapper = await openModal(repo)
    const createdBefore = wrapper.find('[data-testid="created-label"]').text()

    await wrapper.find('[data-testid="rotate-account"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="confirm-yes"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="dismiss-token"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="account-name"]').text()).toBe('nightly-backup')
    expect(wrapper.find('[data-testid="created-label"]').text()).toBe(createdBefore)
  })

  it('only revokes once confirmed, and then hides the account behind the history toggle', async () => {
    const repo = new InMemoryServiceAccountRepository().seed(makeAccount())
    const wrapper = await openModal(repo)

    await wrapper.find('[data-testid="revoke-account"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="account-name"]').exists()).toBe(true)

    await wrapper.find('[data-testid="confirm-yes"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="account-name"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="active-accounts"]').text()).toBe('0/3 active')

    // The testid lands on ToggleSwitch's root; its checkbox is the control.
    await wrapper.find('[data-testid="history-toggle"] input').setValue(true)
    await flushPromises()

    expect(wrapper.find('[data-testid="account-name"]').text()).toBe('nightly-backup')
    expect(wrapper.find('[data-testid="revoked-label"]').text()).toContain('revoked')
    // A revoked account offers no actions.
    expect(wrapper.find('[data-testid="rotate-account"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="revoke-account"]').exists()).toBe(false)
  })

  it('offers no history toggle while nothing has been revoked', async () => {
    const repo = new InMemoryServiceAccountRepository().seed(makeAccount())
    const wrapper = await openModal(repo)

    expect(wrapper.find('[data-testid="history-toggle"]').exists()).toBe(false)
  })

  it('withdraws every action and says why when the caller turns out not to be an owner', async () => {
    const repo = new InMemoryServiceAccountRepository().seed(makeAccount()).denyGroup('group-1')
    const wrapper = await openModal(repo)

    expect(wrapper.text()).toContain('Only an owner of this group can manage its service accounts')
    expect(wrapper.find('[data-testid="create-account"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="rotate-account"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="revoke-account"]').exists()).toBe(false)
    expect(wrapper.emitted('notOwner')).toBeTruthy()
  })
})
