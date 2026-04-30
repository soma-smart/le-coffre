import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount, type VueWrapper } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import type { Group } from '@/domain/group/Group'
import type { User } from '@/domain/user/User'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import { useGroupsStore } from '@/stores/groups'
import { useUserStore } from '@/stores/user'
import { createTestContext } from '@/test/componentTestHelpers'

interface ProbedStores {
  groups: ReturnType<typeof useGroupsStore>
  user: ReturnType<typeof useUserStore>
}

function mountWithContext(
  container: Container,
  pinia: Pinia,
): { wrapper: VueWrapper<unknown>; stores: ProbedStores } {
  const Probe = defineComponent({
    setup() {
      return { groups: useGroupsStore(), user: useUserStore() }
    },
    render() {
      return h('div')
    },
  })
  const wrapper = mount(Probe, {
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
    },
  })
  return { wrapper, stores: wrapper.vm as unknown as ProbedStores }
}

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 'u1',
    username: 'alice',
    email: 'alice@example.com',
    name: 'Alice',
    roles: [],
    personalGroupId: 'personal-1',
    isSso: false,
    ...overrides,
  }
}

function makeGroup(overrides: Partial<Group> = {}): Group {
  return {
    id: 'g1',
    name: 'Team',
    isPersonal: false,
    userId: null,
    owners: [],
    members: [],
    ...overrides,
  }
}

describe('useGroupsStore', () => {
  let groupRepo: InMemoryGroupRepository
  let userRepo: InMemoryUserRepository
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    groupRepo = new InMemoryGroupRepository()
    userRepo = new InMemoryUserRepository()
    userRepo.setCurrent(makeUser())
    ;({ pinia, container } = createTestContext({
      groupRepository: groupRepo,
      userRepository: userRepo,
    }))
  })

  it('partitions fetched groups into personal vs shared and identifies the user personal group', async () => {
    groupRepo.seed(
      makeGroup({ id: 'personal-1', name: 'My Stuff', isPersonal: true, userId: 'u1' }),
    )
    groupRepo.seed(makeGroup({ id: 'shared-1', name: 'Engineering' }))
    groupRepo.seed(makeGroup({ id: 'shared-2', name: 'Ops' }))

    const { stores } = mountWithContext(container, pinia)
    await stores.groups.fetchAllGroups()

    expect(stores.groups.groups.map((g) => g.id).sort()).toEqual([
      'personal-1',
      'shared-1',
      'shared-2',
    ])
    expect(stores.groups.sharedGroups.map((g) => g.id).sort()).toEqual(['shared-1', 'shared-2'])
    expect(stores.groups.personalGroups.map((g) => g.id)).toEqual(['personal-1'])
    expect(stores.groups.userPersonalGroup?.id).toBe('personal-1')
  })

  it('ownedSharedGroups + userBelongingGroups + groupsForPasswordCreation derive from membership', async () => {
    // Personal groups still need u1 in owners[] for membership predicates;
    // userId is a domain field that flags personal vs shared but doesn't
    // imply membership on its own.
    groupRepo.seed(makeGroup({ id: 'personal-1', isPersonal: true, userId: 'u1', owners: ['u1'] }))
    groupRepo.seed(makeGroup({ id: 'owned', name: 'Owned', owners: ['u1'] }))
    groupRepo.seed(makeGroup({ id: 'member', name: 'Member', members: ['u1'] }))
    groupRepo.seed(makeGroup({ id: 'outside', name: 'Outside', owners: ['u2'] }))

    const { stores } = mountWithContext(container, pinia)
    await stores.groups.fetchAllGroups()

    expect(stores.groups.ownedSharedGroups.map((g) => g.id)).toEqual(['owned'])
    expect(stores.groups.userBelongingGroups.map((g) => g.id).sort()).toEqual([
      'member',
      'owned',
      'personal-1',
    ])
    expect(stores.groups.groupsForPasswordCreation.map((g) => g.id)).toEqual([
      'personal-1',
      'owned',
    ])
  })

  it('caches groups for 30 seconds and refetches when force=true', async () => {
    const listSpy = vi.fn(async () => [makeGroup({ id: 'g1' })])
    const customContainer: Container = {
      ...container,
      groups: {
        ...container.groups,
        list: { execute: listSpy } as unknown as typeof container.groups.list,
      },
    }

    const { stores } = mountWithContext(customContainer, pinia)
    await stores.groups.fetchAllGroups()
    await stores.groups.fetchAllGroups()
    expect(listSpy).toHaveBeenCalledTimes(1)

    await stores.groups.fetchAllGroups(true)
    expect(listSpy).toHaveBeenCalledTimes(2)
  })

  it('dedupes concurrent fetchAllGroups into a single request', async () => {
    const listSpy = vi.fn(async () => [makeGroup({ id: 'g1' })])
    const customContainer: Container = {
      ...container,
      groups: {
        ...container.groups,
        list: { execute: listSpy } as unknown as typeof container.groups.list,
      },
    }

    const { stores } = mountWithContext(customContainer, pinia)
    await Promise.all([
      stores.groups.fetchAllGroups(),
      stores.groups.fetchAllGroups(),
      stores.groups.fetchAllGroups(),
    ])
    expect(listSpy).toHaveBeenCalledTimes(1)
  })

  it('createGroup invalidates cache and refetches with the new id present', async () => {
    groupRepo.useIdGenerator(() => 'new-group')
    const { stores } = mountWithContext(container, pinia)
    await stores.groups.fetchAllGroups()
    expect(stores.groups.groups).toEqual([])

    const id = await stores.groups.createGroup('Fresh')
    expect(id).toBe('new-group')
    expect(stores.groups.groups.map((g) => g.id)).toContain('new-group')
  })

  it('clear() wipes every state ref and the cache', async () => {
    groupRepo.seed(makeGroup({ id: 'personal-1', isPersonal: true, userId: 'u1' }))
    groupRepo.seed(makeGroup({ id: 'shared-1' }))
    const { stores } = mountWithContext(container, pinia)
    await stores.groups.fetchAllGroups()
    expect(stores.groups.groups.length).toBe(2)

    stores.groups.clear()

    expect(stores.groups.groups).toEqual([])
    expect(stores.groups.sharedGroups).toEqual([])
    expect(stores.groups.personalGroups).toEqual([])
    expect(stores.groups.userPersonalGroup).toBeNull()
    expect(stores.groups.error).toBeNull()
  })

  it('records error and leaves groups untouched when the use case fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      const failingExecute = vi.fn(async () => {
        throw new Error('list-failed')
      })
      const customContainer: Container = {
        ...container,
        groups: {
          ...container.groups,
          list: { execute: failingExecute } as unknown as typeof container.groups.list,
        },
      }
      const { stores } = mountWithContext(customContainer, pinia)
      await stores.groups.fetchAllGroups()

      expect(stores.groups.groups).toEqual([])
      expect(stores.groups.error).toBe('list-failed')
    } finally {
      consoleErrorSpy.mockRestore()
    }
  })
})
