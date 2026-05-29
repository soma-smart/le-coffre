import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import SharePasswordModal from '@/components/modals/SharePasswordModal.vue'
import type { Container } from '@/container'
import type { PasswordRepository } from '@/application/ports/PasswordRepository'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import { useGroupsStore } from '@/stores/groups'
import type { Password, PasswordAccess } from '@/domain/password/Password'
import type { User } from '@/domain/user/User'
import { createTestContext } from '@/test/componentTestHelpers'

const DialogStub = defineComponent({
  props: ['visible'],
  setup(_, { slots }) {
    return () => h('div', { class: 'dialog-stub' }, [slots.default?.(), slots.footer?.()])
  },
})

const ownerPassword: Password = {
  id: 'pwd-1',
  name: 'Gmail',
  folder: 'Mail',
  groupId: 'owner-group',
  createdAt: '2024-01-01T00:00:00Z',
  lastUpdatedAt: '2024-01-02T00:00:00Z',
  canRead: true,
  canWrite: true,
  login: null,
  url: null,
  accessibleGroupIds: ['owner-group'],
}

function makeUser(id: string, name: string): User {
  return {
    id,
    username: name.toLowerCase(),
    email: `${name.toLowerCase()}@example.com`,
    name,
    roles: [],
    personalGroupId: `personal-${id}`,
    isSso: false,
  }
}

function seedGroups() {
  const groupsStore = useGroupsStore()
  groupsStore.groups = [
    {
      id: 'owner-group',
      name: 'Owner',
      isPersonal: true,
      userId: 'user-1',
      owners: ['user-1'],
      members: [],
    },
    {
      id: 'team-group',
      name: 'Team',
      isPersonal: false,
      userId: null,
      owners: ['user-1'],
      members: ['user-1', 'user-2'],
    },
  ]
  // The modal's onMounted + watch(visible) call fetchAllGroups(); stub it so
  // the SDK call doesn't fire into the void during the test.
  groupsStore.fetchAllGroups = vi.fn(async () => {})
}

function mountModal(container: Container, pinia: Pinia) {
  return mount(SharePasswordModal, {
    props: { visible: true, password: ownerPassword },
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
      stubs: { Dialog: DialogStub },
    },
  })
}

describe('SharePasswordModal', () => {
  let repo: InMemoryPasswordRepository
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    repo = new InMemoryPasswordRepository().seed(ownerPassword, 'secret')
    ;({ pinia, container } = createTestContext({ passwordRepository: repo }))
    seedGroups()
  })

  it('lists the groups that have access in the group access view', async () => {
    await repo.share('pwd-1', 'team-group')

    const wrapper = mountModal(container, pinia)
    await flushPromises()

    expect(wrapper.text()).toContain('Owner')
    expect(wrapper.text()).toContain('Team')
  })

  it('shows a group member in the user access view, linked via the shared group', async () => {
    // Backend access links: an owner (via the owning group) and a plain member
    // (via the shared group) — the member is the case that used to be missing.
    const access: PasswordAccess = {
      resourceId: 'pwd-1',
      users: [
        {
          userId: 'user-1',
          groupId: 'owner-group',
          roleInGroup: 'owner',
          groupRole: 'owner',
          permissions: ['read'],
        },
        {
          userId: 'user-2',
          groupId: 'team-group',
          roleInGroup: 'member',
          groupRole: 'member',
          permissions: ['read'],
        },
      ],
      groups: [
        { groupId: 'owner-group', role: 'owner', permissions: ['read'] },
        { groupId: 'team-group', role: 'member', permissions: ['read'] },
      ],
    }
    const accessRepo = { listAccess: async () => access } as unknown as PasswordRepository
    const userRepo = new InMemoryUserRepository()
    userRepo.seed(makeUser('user-1', 'Alice'))
    userRepo.seed(makeUser('user-2', 'Bob'))

    const ctx = createTestContext({ passwordRepository: accessRepo, userRepository: userRepo })
    seedGroups()

    const wrapper = mountModal(ctx.container, ctx.pinia)
    await flushPromises()

    const text = wrapper.text()
    // The member now appears (the bug fix) alongside the owner.
    expect(text).toContain('Alice')
    expect(text).toContain('Bob')
    // Bob's access is via the Team group, shown as a shared link.
    expect(text).toContain('Team')
    expect(text).toContain('shared')
    // The owner link is labelled as owning the password.
    expect(text).toContain('owns')
  })
})
