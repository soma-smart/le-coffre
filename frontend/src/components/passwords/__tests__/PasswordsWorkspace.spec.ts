import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import { mount, flushPromises } from '@vue/test-utils'
import HomePage from '@/pages/HomePage.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import { useUserStore } from '@/stores/user'
import type { Group } from '@/domain/group/Group'
import type { Password } from '@/domain/password/Password'
import type { User } from '@/domain/user/User'
import { createTestContext } from '@/test/componentTestHelpers'

const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

const CURRENT_USER: User = {
  id: 'u1',
  username: 'alice',
  email: 'alice@example.com',
  name: 'Alice',
  roles: [],
  personalGroupId: 'g2',
  isSso: false,
}

const ENGINEERING: Group = {
  id: 'g1',
  name: 'Engineering',
  isPersonal: false,
  userId: null,
  owners: ['u1'],
  members: [],
}

const PERSONAL: Group = {
  id: 'g2',
  name: 'Alice',
  isPersonal: true,
  userId: 'u1',
  owners: ['u1'],
  members: [],
}

function makePassword(overrides: Partial<Password> = {}): Password {
  return {
    id: 'p1',
    name: 'Gmail',
    folder: 'default',
    groupId: 'g1',
    createdAt: '2026-01-01T00:00:00Z',
    lastUpdatedAt: '2026-01-01T00:00:00Z',
    canRead: true,
    canWrite: true,
    login: 'alice@example.com',
    url: null,
    // Empty, not ['g1'] — accessibleGroupIdsFor() falls back to the
    // password's own groupId, so overriding groupId without also touching
    // accessibleGroupIds still resolves to the right group.
    accessibleGroupIds: [],
    accessExpiresAt: null,
    ...overrides,
  }
}

async function mountWorkspace(passwords: Password[], initialPath: string) {
  const passwordRepository = new InMemoryPasswordRepository()
  for (const password of passwords) {
    passwordRepository.seed(password, `secret-for-${password.id}`)
  }
  const groupRepository = new InMemoryGroupRepository().seed(ENGINEERING).seed(PERSONAL)
  const userRepository = new InMemoryUserRepository().setCurrent(CURRENT_USER)

  const { pinia, container } = createTestContext({
    passwordRepository,
    groupRepository,
    userRepository,
  })

  // PasswordsWorkspace doesn't fetch the current user itself (MainMenu does,
  // in the real app) — prime it directly so userBelongingGroups is non-empty.
  await useUserStore().fetchCurrentUser()

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'Home', component: HomePage },
      { path: '/passwords/:groupSlug', name: 'HomeGroup', component: HomePage },
    ],
  })
  router.push(initialPath)
  await router.isReady()

  const wrapper = mount(HomePage, {
    global: {
      plugins: [router, pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
    },
  })
  await flushPromises()

  return { wrapper, router }
}

describe('PasswordsWorkspace (via HomePage)', () => {
  beforeEach(() => {
    toastAdd.mockClear()
  })

  it("selects the password named by the route's ?password= query", async () => {
    const passwords = [
      makePassword({ id: 'p1', name: 'Gmail' }),
      makePassword({ id: 'p2', name: 'GitHub' }),
    ]
    const { wrapper } = await mountWorkspace(passwords, '/passwords/Engineering?password=p2')

    expect(wrapper.get('[aria-current="true"]').text()).toContain('GitHub')
    expect(wrapper.text()).toContain('••••••••') // detail pane rendered for GitHub
  })

  it('auto-selects the first password in scope when no ?password= is given', async () => {
    const passwords = [
      makePassword({ id: 'p1', name: 'Gmail' }),
      makePassword({ id: 'p2', name: 'GitHub' }),
    ]
    const { wrapper } = await mountWorkspace(passwords, '/passwords/Engineering')

    expect(wrapper.get('[aria-current="true"]').text()).toContain('Gmail')
  })

  it('drops a stale ?password= (deleted / inaccessible) and falls back to the first row', async () => {
    const passwords = [makePassword({ id: 'p1', name: 'Gmail' })]
    const { wrapper, router } = await mountWorkspace(
      passwords,
      '/passwords/Engineering?password=does-not-exist',
    )
    await flushPromises()

    expect(router.currentRoute.value.query.password).toBeUndefined()
    expect(wrapper.get('[aria-current="true"]').text()).toContain('Gmail')
  })

  it('follows a ?password= that resolves in a different group to where it actually lives', async () => {
    const passwords = [
      makePassword({ id: 'p1', name: 'Gmail', groupId: 'g1' }),
      makePassword({ id: 'p2', name: 'Personal Note', groupId: 'g2', folder: 'default' }),
    ]
    const { wrapper, router } = await mountWorkspace(
      passwords,
      '/passwords/Engineering?password=p2',
    )
    await flushPromises()

    expect(router.currentRoute.value.params.groupSlug).toBe('Alice')
    expect(wrapper.get('[aria-current="true"]').text()).toContain('Personal Note')
  })

  it('widens the middle pane to every visible group when searching', async () => {
    const passwords = [
      makePassword({ id: 'p1', name: 'Gmail', groupId: 'g1' }),
      makePassword({ id: 'p2', name: 'Personal Note', groupId: 'g2', folder: 'default' }),
    ]
    const { wrapper } = await mountWorkspace(passwords, '/passwords/Engineering')

    const search = wrapper.get('input[placeholder="Search all passwords..."]')
    await search.setValue('personal')
    await flushPromises()

    expect(wrapper.text()).toContain('Search results')
    expect(wrapper.text()).toContain('Personal Note')
    expect(wrapper.text()).not.toContain('Gmail')
  })

  it('clicking a search result navigates to its own group and selects it', async () => {
    const passwords = [
      makePassword({ id: 'p1', name: 'Gmail', groupId: 'g1' }),
      makePassword({ id: 'p2', name: 'Personal Note', groupId: 'g2', folder: 'default' }),
    ]
    const { wrapper, router } = await mountWorkspace(passwords, '/passwords/Engineering')

    const search = wrapper.get('input[placeholder="Search all passwords..."]')
    await search.setValue('personal')
    await flushPromises()

    const resultRow = wrapper
      .findAll('.cursor-pointer')
      .find((el) => el.text().includes('Personal Note'))
    expect(resultRow).toBeDefined()
    await resultRow!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.params.groupSlug).toBe('Alice')
    expect(router.currentRoute.value.query.password).toBe('p2')
  })

  it('opens the history modal from the detail pane\'s "View All"', async () => {
    const passwords = [makePassword({ id: 'p1', name: 'Gmail' })]
    const { wrapper } = await mountWorkspace(passwords, '/passwords/Engineering')

    expect(wrapper.findComponent({ name: 'PasswordHistoryModal' }).props('visible')).toBe(false)

    await wrapper.get('button:has(> span.pi-history)').trigger('click')

    expect(wrapper.findComponent({ name: 'PasswordHistoryModal' }).props('visible')).toBe(true)
  })
})
