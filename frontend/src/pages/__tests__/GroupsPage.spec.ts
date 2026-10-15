import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import GroupsPage from '@/pages/GroupsPage.vue'
import ConfirmationModal from '@/components/modals/ConfirmationModal.vue'
import GroupDetailsModal from '@/components/modals/GroupDetailsModal.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import type { Group } from '@/domain/group/Group'
import type { User } from '@/domain/user/User'

const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue', async (importOriginal) => {
  const actual = await importOriginal<typeof import('primevue')>()
  return { ...actual, useToast: () => ({ add: toastAdd }) }
})

const USER_ID = 'user-1'
const PERSONAL_GROUP_ID = 'group-personal'

const currentUser: User = {
  id: USER_ID,
  username: 'ada',
  email: 'ada@example.com',
  name: 'Ada Owner',
  roles: [],
  personalGroupId: PERSONAL_GROUP_ID,
  isSso: false,
}

const personalGroup: Group = {
  id: PERSONAL_GROUP_ID,
  name: "Ada's Personal Group",
  isPersonal: true,
  userId: USER_ID,
  owners: [USER_ID],
  members: [USER_ID],
}

function sharedGroup(overrides: Partial<Group> = {}): Group {
  return {
    id: 'group-owned',
    name: 'Platform',
    isPersonal: false,
    userId: null,
    owners: [USER_ID],
    members: [USER_ID],
    ...overrides,
  }
}

async function mountPage(
  groups: Group[],
  user: User = currentUser,
  groupRepository: InMemoryGroupRepository = new InMemoryGroupRepository(),
) {
  groups.forEach((group) => groupRepository.seed(group))
  const userRepository = new InMemoryUserRepository().setCurrent(user)

  const { pinia, container } = createTestContext({ groupRepository, userRepository })
  const wrapper = mount(GroupsPage, {
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
      stubs: { MainLayout: { template: '<div><slot /></div>' } },
    },
  })
  await flushPromises()
  return wrapper
}

describe('GroupsPage personal group card', () => {
  it('shows exactly one personal card, with a single-person icon', async () => {
    const wrapper = await mountPage([personalGroup, sharedGroup()])

    expect(wrapper.findAll('.pi-user')).toHaveLength(1)
    expect(wrapper.text()).toContain("Ada's Personal Group")
    expect(wrapper.text()).toContain('Personal Group')
  })

  it('places the personal card before the shared groups', async () => {
    const wrapper = await mountPage([personalGroup, sharedGroup()])

    const html = wrapper.html()
    expect(html.indexOf("Ada's Personal Group")).toBeLessThan(html.indexOf('Platform'))
  })

  it('offers no edit, delete or members action on the personal card', async () => {
    const wrapper = await mountPage([personalGroup])

    expect(wrapper.text()).not.toContain('View Members')
    expect(wrapper.find('.pi-pencil').exists()).toBe(false)
    expect(wrapper.find('.pi-times').exists()).toBe(false)
  })

  it('offers service accounts on the personal card', async () => {
    const wrapper = await mountPage([personalGroup])

    expect(wrapper.find('[data-testid="service-accounts-button"]').exists()).toBe(true)
  })

  it('shows no empty state when the personal card is the only group', async () => {
    const wrapper = await mountPage([personalGroup])

    expect(wrapper.text()).not.toContain('No groups found')
    expect(wrapper.text()).not.toContain('No groups match')
  })

  it('hides the personal card when it does not match the search', async () => {
    const wrapper = await mountPage([personalGroup, sharedGroup()])

    await wrapper.find('input').setValue('Platform')
    await flushPromises()

    expect(wrapper.text()).not.toContain("Ada's Personal Group")
    expect(wrapper.text()).toContain('Platform')
  })

  it('renders no personal card when the user has no personal group', async () => {
    const wrapper = await mountPage([sharedGroup()], { ...currentUser, personalGroupId: null })

    expect(wrapper.findAll('.pi-user')).toHaveLength(0)
  })
})

describe('GroupsPage service accounts button', () => {
  it('appears on a group the user owns', async () => {
    const wrapper = await mountPage([sharedGroup()])

    expect(wrapper.find('[data-testid="service-accounts-button"]').exists()).toBe(true)
  })

  it('is withheld on a group the user merely belongs to', async () => {
    const wrapper = await mountPage([
      sharedGroup({ id: 'group-member', name: 'Billing', owners: ['someone-else'] }),
    ])

    expect(wrapper.text()).toContain('Billing')
    expect(wrapper.text()).toContain('View Members')
    expect(wrapper.find('[data-testid="service-accounts-button"]').exists()).toBe(false)
  })

  it('is withheld from an administrator who does not own the group', async () => {
    // A service account's token can read the group's passwords, so admin status
    // alone must not grant it — only ownership does, unlike edit/delete.
    const wrapper = await mountPage(
      [sharedGroup({ id: 'g1', name: 'Platform', owners: ['someone-else'] })],
      { ...currentUser, roles: ['admin'] },
    )

    expect(wrapper.find('[data-testid="service-accounts-button"]').exists()).toBe(false)
  })

  it('still appears for an administrator who does own the group', async () => {
    const wrapper = await mountPage([sharedGroup({ id: 'g1', name: 'Platform' })], {
      ...currentUser,
      roles: ['admin'],
    })

    expect(wrapper.find('[data-testid="service-accounts-button"]').exists()).toBe(true)
  })
})

class FailingRemoveMemberGroupRepository extends InMemoryGroupRepository {
  async removeMember(): Promise<void> {
    // Mirrors the shape of a real client-built domain error: untranslated,
    // carrying the raw UUID — exactly what must never reach the toast.
    throw new Error(`Group ${PERSONAL_GROUP_ID} not found`)
  }
}

function findConfirmationModal(wrapper: Awaited<ReturnType<typeof mountPage>>, title: string) {
  return wrapper.findAllComponents(ConfirmationModal).find((c) => c.props('title') === title)
}

describe('GroupsPage leave group', () => {
  beforeEach(() => {
    toastAdd.mockClear()
  })

  it('disables the leave button for a sole owner with other members, with a reason', async () => {
    const wrapper = await mountPage([
      sharedGroup({ owners: [USER_ID], members: ['member-1', 'member-2'] }),
    ])

    const button = wrapper.find('.pi-sign-out').element.closest('button')
    expect(button?.disabled).toBe(true)
    expect(wrapper.find('[aria-describedby="leave-blocked-reason-group-owned"]').exists()).toBe(
      true,
    )
    expect(wrapper.text()).toContain('Promote another member to owner, then demote yourself')
  })

  it('disables the leave button for an owner who is not the sole owner', async () => {
    const wrapper = await mountPage([sharedGroup({ owners: [USER_ID, 'owner-2'], members: ['member-1'] })])

    const button = wrapper.find('.pi-sign-out').element.closest('button')
    expect(button?.disabled).toBe(true)
  })

  it('routes a sole member straight to the delete modal instead of a leave modal', async () => {
    const wrapper = await mountPage([sharedGroup({ owners: [USER_ID], members: [] })])

    const button = wrapper.find('.pi-sign-out').element.closest('button')
    expect(button?.disabled).toBe(false)

    await wrapper.find('.pi-sign-out').trigger('click')

    const leaveModal = findConfirmationModal(wrapper, 'Leave group')
    expect(leaveModal?.props('visible')).toBe(false)

    const deleteModal = findConfirmationModal(wrapper, 'Delete group')
    expect(deleteModal?.props('visible')).toBe(true)
    expect(deleteModal?.props('description')).toContain('only member')
    // Regression: this used to prefix the generic delete description, which
    // claims "all members will lose access" — contradicting the sole-member
    // line right above it.
    expect(deleteModal?.props('description')).not.toContain('members will lose access')
    expect(deleteModal?.props('countdownSeconds')).toBe(6)
  })

  it('opens the leave modal, not the delete one, for a member who is not alone', async () => {
    const wrapper = await mountPage([sharedGroup({ owners: ['owner-2'], members: [USER_ID] })])

    await wrapper.find('.pi-sign-out').trigger('click')

    const leaveModal = findConfirmationModal(wrapper, 'Leave group')
    expect(leaveModal?.props('visible')).toBe(true)

    const deleteModal = findConfirmationModal(wrapper, 'Delete group')
    expect(deleteModal?.props('visible')).toBe(false)
  })

  it('applies the same sole-member routing to a leaveGroup emitted by the modal', async () => {
    // GroupDetailsModal's own "Leave" button always emits `leaveGroup` with
    // its live `props.group` (covered by GroupDetailsModal.spec.ts) — this
    // confirms GroupsPage's `@leave-group="openLeaveGroupDialog"` wiring
    // applies the identical sole-member routing as the card icon's click,
    // regardless of which of the two entry points triggered it.
    const group = sharedGroup({ owners: [USER_ID], members: [] })
    const wrapper = await mountPage([group])

    wrapper.findComponent(GroupDetailsModal).vm.$emit('leaveGroup', group)
    await flushPromises()

    const leaveModal = findConfirmationModal(wrapper, 'Leave group')
    expect(leaveModal?.props('visible')).toBe(false)

    const deleteModal = findConfirmationModal(wrapper, 'Delete group')
    expect(deleteModal?.props('visible')).toBe(true)
  })

  it('refreshes the groups list after a successful leave', async () => {
    const group = sharedGroup({ owners: ['owner-2'], members: [USER_ID] })
    const wrapper = await mountPage([group])

    await wrapper.find('.pi-sign-out').trigger('click')
    const modal = findConfirmationModal(wrapper, 'Leave group')
    modal!.vm.$emit('confirm')
    await flushPromises()

    // The store refreshed from the repository, where the user is no longer
    // a member — so the leave action for this group is gone too.
    expect(wrapper.find('.pi-sign-out').exists()).toBe(false)
    expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'success' }))
  })

  it('shows a translated error toast and refreshes, without leaking the raw error message', async () => {
    const group = sharedGroup({ owners: ['owner-2'], members: [USER_ID] })
    const wrapper = await mountPage([group], currentUser, new FailingRemoveMemberGroupRepository())

    await wrapper.find('.pi-sign-out').trigger('click')
    const modal = findConfirmationModal(wrapper, 'Leave group')
    modal!.vm.$emit('confirm')
    await flushPromises()

    expect(toastAdd).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'error', detail: 'Failed to leave group' }),
    )
    // The leave action is still offered — nothing actually changed, so a
    // stale/removed button would otherwise strand the user.
    expect(wrapper.find('.pi-sign-out').exists()).toBe(true)
  })
})
