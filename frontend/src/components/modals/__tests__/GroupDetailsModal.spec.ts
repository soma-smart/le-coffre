import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
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

const currentUser: User = {
  id: USER_ID,
  username: 'ada',
  email: 'ada@example.com',
  name: 'Ada',
  roles: [],
  personalGroupId: 'group-personal',
  isSso: false,
}

const groupAlpha: Group = {
  id: 'group-alpha',
  name: 'Alpha',
  isPersonal: false,
  userId: null,
  owners: [USER_ID],
  members: ['member-1'],
}

const groupBeta: Group = {
  id: 'group-beta',
  name: 'Beta',
  isPersonal: false,
  userId: null,
  owners: [USER_ID, 'owner-2'],
  members: [],
}

/** Lets a single test fail `get()` for one chosen group id, once. */
class FlakyGroupRepository extends InMemoryGroupRepository {
  private failOnceFor: string | null = null

  failNextGetFor(groupId: string): this {
    this.failOnceFor = groupId
    return this
  }

  async get(groupId: string): Promise<Group> {
    if (this.failOnceFor === groupId) {
      this.failOnceFor = null
      throw new Error(`network error fetching ${groupId}`)
    }
    return super.get(groupId)
  }
}

// Pass-through so PrimeVue's Dialog teleport does not move content out of the wrapper.
const DialogStub = defineComponent({
  props: ['visible', 'header'],
  setup(props, { slots }) {
    return () =>
      h('div', { 'data-testid': 'dialog' }, [
        props.header,
        slots.default?.(),
        slots.footer?.(),
      ])
  },
})

async function mountModal(groupRepository: InMemoryGroupRepository, group: Group | null) {
  const userRepository = new InMemoryUserRepository()
    .setCurrent(currentUser)
    .seed({ ...currentUser, id: 'member-1', name: 'Member One', email: 'member1@example.com' })
    .seed({ ...currentUser, id: 'owner-2', name: 'Owner Two', email: 'owner2@example.com' })

  const { pinia, container } = createTestContext({ groupRepository, userRepository })
  const wrapper = mount(GroupDetailsModal, {
    props: { visible: true, group },
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
      stubs: { Dialog: DialogStub },
    },
  })
  await flushPromises()
  return wrapper
}

describe('GroupDetailsModal leave action', () => {
  it('is enabled for a plain member and emits leaveGroup with the group', async () => {
    const group: Group = { ...groupAlpha, owners: [], members: [USER_ID] }
    const repo = new InMemoryGroupRepository().seed(group)
    const wrapper = await mountModal(repo, group)

    const button = wrapper.find('.pi-sign-out').element.closest('button')
    expect(button?.disabled).toBe(false)

    await wrapper.find('.pi-sign-out').trigger('click')

    expect(wrapper.emitted('leaveGroup')).toBeTruthy()
    expect(wrapper.emitted('leaveGroup')![0][0]).toMatchObject({ id: group.id })
  })

  it('is disabled for a non-sole owner, with the ownership tooltip described', async () => {
    const repo = new InMemoryGroupRepository().seed(groupBeta)
    const wrapper = await mountModal(repo, groupBeta)

    const button = wrapper.find('.pi-sign-out').element.closest('button')
    expect(button?.disabled).toBe(true)
    expect(button?.getAttribute('aria-describedby')).toBe('leave-blocked-reason-modal')
    expect(wrapper.text()).toContain('Demote yourself to member first')
  })

  it('emits the live group prop, never stale groupDetails from the prior group', async () => {
    // Regression: opening Alpha, closing, then opening Beta while its
    // groups.get() fails (network error) used to leave `groupDetails` holding
    // Alpha's data. The modal would then show Beta's title but act on Alpha
    // when "Leave" was clicked. `props.group` (driven by the page's own
    // `selectedGroup`) must always be the one actually emitted.
    const repo = new FlakyGroupRepository()
    repo.seed(groupAlpha).seed(groupBeta)

    const wrapper = await mountModal(repo, groupAlpha)
    expect(wrapper.text()).toContain('Alpha')

    await wrapper.setProps({ visible: false })
    await flushPromises()

    repo.failNextGetFor(groupBeta.id)
    await wrapper.setProps({ group: groupBeta, visible: true })
    await flushPromises()

    // The fetch for Beta failed, so `groupDetails` is still unset/Alpha's —
    // but the modal must show Beta's own data for the decision and the click.
    expect(wrapper.text()).toContain('Beta')
    expect(wrapper.text()).not.toContain('Alpha')

    await wrapper.find('.pi-sign-out').trigger('click')

    expect(wrapper.emitted('leaveGroup')).toBeTruthy()
    expect(wrapper.emitted('leaveGroup')![0][0]).toMatchObject({ id: groupBeta.id })
  })
})
