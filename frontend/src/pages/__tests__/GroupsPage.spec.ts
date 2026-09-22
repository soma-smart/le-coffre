import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import GroupsPage from '@/pages/GroupsPage.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import type { Group } from '@/domain/group/Group'
import type { User } from '@/domain/user/User'

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

async function mountPage(groups: Group[], user: User = currentUser) {
  const groupRepository = new InMemoryGroupRepository()
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

  it('appears on every group for an administrator', async () => {
    const wrapper = await mountPage(
      [sharedGroup({ id: 'g1', name: 'Platform', owners: ['someone-else'] })],
      { ...currentUser, roles: ['admin'] },
    )

    expect(wrapper.find('[data-testid="service-accounts-button"]').exists()).toBe(true)
  })
})
