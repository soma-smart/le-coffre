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

  it('keeps the cached groups across cheap calls and refreshes on force=true', async () => {
    // Behavioural: the underlying repository returns a different group on
    // every call. If the store fetched fresh every time, the second call
    // would see g2; with the cache, it sees g1. force=true bypasses.
    let counter = 0
    const evolvingExecute = async () => [makeGroup({ id: `g${++counter}` })]
    const customContainer: Container = {
      ...container,
      groups: {
        ...container.groups,
        list: { execute: evolvingExecute } as unknown as typeof container.groups.list,
      },
    }

    const { stores } = mountWithContext(customContainer, pinia)
    await stores.groups.fetchAllGroups()
    expect(stores.groups.groups.map((g) => g.id)).toEqual(['g1'])

    await stores.groups.fetchAllGroups()
    expect(stores.groups.groups.map((g) => g.id)).toEqual(['g1']) // still cached

    await stores.groups.fetchAllGroups(true)
    expect(stores.groups.groups.map((g) => g.id)).toEqual(['g2']) // forced refresh
  })

  it('three concurrent fetchAllGroups all settle on the same list', async () => {
    // If the store didn't dedupe, three concurrent fetches would each see a
    // different counter value and the last writer would set groups to ['g3'].
    // With dedupe, all callers share the first response.
    let counter = 0
    const evolvingExecute = async () => [makeGroup({ id: `g${++counter}` })]
    const customContainer: Container = {
      ...container,
      groups: {
        ...container.groups,
        list: { execute: evolvingExecute } as unknown as typeof container.groups.list,
      },
    }

    const { stores } = mountWithContext(customContainer, pinia)
    await Promise.all([
      stores.groups.fetchAllGroups(),
      stores.groups.fetchAllGroups(),
      stores.groups.fetchAllGroups(),
    ])
    expect(stores.groups.groups.map((g) => g.id)).toEqual(['g1'])
  })

  it('createGroup makes the new group visible without an explicit refetch', async () => {
    groupRepo.useIdGenerator(() => 'new-group')
    const { stores } = mountWithContext(container, pinia)
    await stores.groups.fetchAllGroups()
    expect(stores.groups.groups).toEqual([])

    const id = await stores.groups.createGroup('Fresh')
    expect(id).toBe('new-group')
    expect(stores.groups.groups.map((g) => g.id)).toContain('new-group')
  })

  it('updateGroup reflects the renamed group in store state', async () => {
    groupRepo.seed(makeGroup({ id: 'g1', name: 'Old Name' }))
    const { stores } = mountWithContext(container, pinia)
    await stores.groups.fetchAllGroups()

    await stores.groups.updateGroup('g1', 'Renamed')

    expect(stores.groups.groups.find((g) => g.id === 'g1')?.name).toBe('Renamed')
  })

  it('addMemberToGroup adds the user to the in-store group members list', async () => {
    groupRepo.seed(makeGroup({ id: 'g1', owners: ['u1'], members: [] }))
    const { stores } = mountWithContext(container, pinia)
    await stores.groups.fetchAllGroups()

    await stores.groups.addMemberToGroup('g1', 'u3')
    // The store's mutating actions don't auto-refetch (only create/update/
    // delete do); members live on the server until the next fetch. The
    // behavioural assertion: a fresh fetch sees the new member.
    await stores.groups.fetchAllGroups(true)
    expect(stores.groups.groups.find((g) => g.id === 'g1')?.members).toContain('u3')
  })

  it('removeMemberFromGroup drops the member after the next fetch', async () => {
    groupRepo.seed(makeGroup({ id: 'g1', owners: ['u1'], members: ['u3'] }))
    const { stores } = mountWithContext(container, pinia)
    await stores.groups.fetchAllGroups()

    await stores.groups.removeMemberFromGroup('g1', 'u3')
    await stores.groups.fetchAllGroups(true)
    expect(stores.groups.groups.find((g) => g.id === 'g1')?.members).not.toContain('u3')
  })

  it('promoteToOwner adds the user to the owners list', async () => {
    groupRepo.seed(makeGroup({ id: 'g1', owners: ['u1'], members: ['u3'] }))
    const { stores } = mountWithContext(container, pinia)
    await stores.groups.fetchAllGroups()

    await stores.groups.promoteToOwner('g1', 'u3')
    await stores.groups.fetchAllGroups(true)
    const group = stores.groups.groups.find((g) => g.id === 'g1')
    expect(group?.owners).toContain('u3')
  })

  it('deleteGroup removes the group from the in-store list', async () => {
    groupRepo.seed(makeGroup({ id: 'g1', name: 'Doomed' }))
    groupRepo.seed(makeGroup({ id: 'g2', name: 'Survivor' }))
    const { stores } = mountWithContext(container, pinia)
    await stores.groups.fetchAllGroups()
    expect(stores.groups.groups.length).toBe(2)

    await stores.groups.deleteGroup('g1')

    expect(stores.groups.groups.map((g) => g.id)).toEqual(['g2'])
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
