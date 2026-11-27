import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import GroupHistoryModal from '@/components/modals/GroupHistoryModal.vue'
import ServiceAccountsModal from '@/components/modals/ServiceAccountsModal.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryServiceAccountRepository } from '@/infrastructure/in_memory/InMemoryServiceAccountRepository'
import type { Group } from '@/domain/group/Group'
import type { ServiceAccount, ServiceAccountPage } from '@/domain/serviceAccount/ServiceAccount'
import {
  ServiceAccountAlreadyRevokedError,
  ServiceAccountNotFoundError,
} from '@/domain/serviceAccount/errors'
import { formatAbsoluteTime } from '@/utils/relativeTime'

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
    lastUsedAt: null,
    lastRotatedAt: null,
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

  it('says the creator was deleted when the server no longer knows the user it names', async () => {
    const repo = new InMemoryServiceAccountRepository().seed(
      makeAccount({ createdByUserId: 'gone-user', createdByUserName: null }),
    )
    const wrapper = await openModal(repo)

    expect(wrapper.find('[data-testid="creator-label"]').text()).toBe('· by a deleted user')
  })

  it('says an account was never used', async () => {
    const wrapper = await openModal(new InMemoryServiceAccountRepository().seed(makeAccount()))

    expect(wrapper.find('[data-testid="usage-label"]').text()).toBe('· never used')
  })

  it('tells when an account was last used, with the exact time on hover', async () => {
    const lastUsedAt = new Date(Date.now() - 3 * 3_600_000).toISOString()
    const repo = new InMemoryServiceAccountRepository().seed(makeAccount({ lastUsedAt }))
    const wrapper = await openModal(repo)
    const label = wrapper.find('[data-testid="usage-label"]')

    expect(label.text()).toBe('· used 3 hours ago')
    expect(label.attributes('title')).toBe(formatAbsoluteTime(lastUsedAt))
  })

  it('never tells a use in the future, when the browser clock lags behind the server', async () => {
    const lastUsedAt = new Date(Date.now() + 4_000).toISOString()
    const repo = new InMemoryServiceAccountRepository().seed(makeAccount({ lastUsedAt }))
    const wrapper = await openModal(repo)

    expect(wrapper.find('[data-testid="usage-label"]').text()).toBe('· used 0 seconds ago')
  })

  it('says the new token was never used once renewed, until it is', async () => {
    const lastUsedAt = new Date(Date.now() - 3 * 3_600_000).toISOString()
    const repo = new InMemoryServiceAccountRepository().seed(makeAccount({ lastUsedAt }))
    const wrapper = await openModal(repo)

    await wrapper.find('[data-testid="rotate-account"]').trigger('click')
    await wrapper.find('[data-testid="confirm-yes"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="usage-label"]').text()).toBe('· new token never used')
  })

  it('never shows the token in its connection guide, even right after showing it once', async () => {
    const repo = new InMemoryServiceAccountRepository().useTokenGenerator(() => 'lc_sa_s3cr3t')
    const wrapper = await openModal(repo)
    await createAccount(wrapper)

    await wrapper.find('[data-testid="connection-guide-toggle"]').trigger('click')

    const guide = wrapper.find('[data-testid="connection-guide"]')
    expect(guide.find('[data-testid="command-whoami"]').text()).toContain('$LECOFFRE_TOKEN')
    expect(guide.html()).not.toContain('lc_sa_s3cr3t')
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

    expect(wrapper.text()).toContain(
      'Only the owners of this group can manage its service accounts.',
    )
    expect(wrapper.find('[data-testid="create-account"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="rotate-account"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="revoke-account"]').exists()).toBe(false)
    expect(wrapper.emitted('notOwner')).toBeTruthy()
  })

  it('translates a cap reached behind its back, reloads the list, and says it once', async () => {
    const repo = new InMemoryServiceAccountRepository()
      .withMaxActive(2)
      .seed(makeAccount({ id: 'a1' }))
    const wrapper = await openModal(repo)
    const toastAdd = vi.spyOn(wrapper.vm.$toast, 'add')
    // Another owner fills the last slot while this dialog is open.
    repo.seed(makeAccount({ id: 'a2', name: 'other-session' }))

    await createAccount(wrapper, 'one-too-many')

    expect(toastAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'error',
        detail: expect.stringContaining(
          'This group has reached its maximum of active service accounts.',
        ),
      }),
    )
    expect(wrapper.text()).not.toContain('maximum 2')
    expect(wrapper.find('[data-testid="active-accounts"]').text()).toBe('2/2 active')
    // The banner says it on screen; an error message on top would say it twice.
    expect(wrapper.find('[data-testid="cap-reached"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="error-message"]').exists()).toBe(false)
  })

  it('does not reload over and over when the group is gone', async () => {
    const repo = new InMemoryServiceAccountRepository()
    const list = vi.spyOn(repo, 'listForGroup').mockRejectedValue(new ServiceAccountNotFoundError())
    const wrapper = await openModal(repo)
    await flushPromises()

    expect(list).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('This group no longer exists.')
  })

  it('names both causes when a rotation is refused as a conflict, and reloads', async () => {
    const repo = new InMemoryServiceAccountRepository().seed(makeAccount())
    const wrapper = await openModal(repo)
    vi.spyOn(repo, 'rotate').mockRejectedValueOnce(
      new ServiceAccountAlreadyRevokedError('holds several tokens'),
    )
    const list = vi.spyOn(repo, 'listForGroup')

    await wrapper.find('[data-testid="rotate-account"]').trigger('click')
    await wrapper.find('[data-testid="confirm-yes"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain(
      'the account was revoked in the meantime, or it holds several tokens',
    )
    expect(list).toHaveBeenCalledTimes(1)
  })

  it('opens the group history, where the lifecycle of its accounts is audited', async () => {
    const wrapper = await openModal(new InMemoryServiceAccountRepository().seed(makeAccount()))
    expect(wrapper.findComponent(GroupHistoryModal).exists()).toBe(false)

    await wrapper.find('[data-testid="group-history"]').trigger('click')
    await flushPromises()

    const history = wrapper.findComponent(GroupHistoryModal)
    expect(history.exists()).toBe(true)
    expect(history.props('group')).toEqual(group)
  })

  it('ignores a list response that arrives after the dialog moved on to another group', async () => {
    const otherGroup: Group = { ...group, id: 'group-2', name: 'Data' }
    const repo = new InMemoryServiceAccountRepository()
      .seed(makeAccount({ id: 'a1', groupId: 'group-1', name: 'platform-bot' }))
      .seed(makeAccount({ id: 'a2', groupId: 'group-2', name: 'data-bot' }))
    // Hold back the first group's response until the second group's has landed.
    let releaseFirst!: () => void
    const listForGroup = repo.listForGroup.bind(repo)
    vi.spyOn(repo, 'listForGroup').mockImplementationOnce(
      (groupId) =>
        new Promise<ServiceAccountPage>((resolve) => {
          releaseFirst = () => resolve(listForGroup(groupId))
        }),
    )
    const wrapper = await openModal(repo)

    await wrapper.setProps({ visible: false })
    await wrapper.setProps({ group: otherGroup, visible: true })
    await flushPromises()
    releaseFirst()
    await flushPromises()

    const names = wrapper.findAll('[data-testid="account-name"]').map((name) => name.text())
    expect(names).toEqual(['data-bot'])
  })
})
