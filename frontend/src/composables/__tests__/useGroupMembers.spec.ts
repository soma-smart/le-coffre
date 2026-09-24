import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { useGroupMembers, type GroupMembersUseCases } from '@/composables/useGroupMembers'
import type { Group } from '@/domain/group/Group'
import type { User } from '@/domain/user/User'

function makeGroup(overrides: Partial<Group> = {}): Group {
  return {
    id: 'g1',
    name: 'Team',
    isPersonal: false,
    userId: null,
    owners: ['u1'],
    members: ['u2'],
    ...overrides,
  }
}

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 'u1',
    name: 'Alice',
    email: 'alice@example.com',
    username: 'alice',
    roles: [],
    personalGroupId: null,
    isSso: false,
    ...overrides,
  }
}

/** Resolves a user named after its id, e.g. 'u1' -> 'User u1'. */
function makeGetUser(): GroupMembersUseCases['users']['get'] {
  return {
    execute: vi.fn(async ({ userId }: { userId: string }) =>
      makeUser({ id: userId, name: `User ${userId}` }),
    ),
  }
}

function makeUseCases(overrides: Partial<GroupMembersUseCases> = {}): GroupMembersUseCases {
  return {
    users: {
      get: makeGetUser(),
      search: { execute: vi.fn(async () => [] as User[]) },
    },
    groups: { get: { execute: vi.fn(async () => makeGroup()) } },
    store: {
      addMemberToGroup: vi.fn(async () => {}),
      removeMemberFromGroup: vi.fn(async () => {}),
      promoteToOwner: vi.fn(async () => {}),
    },
    ...overrides,
  }
}

describe('useGroupMembers', () => {
  it('loadAll fetches group details and resolves owner/member ids to users', async () => {
    const useCases = makeUseCases({
      groups: {
        get: { execute: vi.fn(async () => makeGroup({ owners: ['u1'], members: ['u2'] })) },
      },
    })

    const m = useGroupMembers({
      group: ref(makeGroup()),
      currentUserId: ref('u1'),
      useCases,
    })

    await m.loadAll()
    expect(m.fetchStatus.value).toBe('ready')
    expect(m.ownerUsers.value.map((u) => u.id)).toEqual(['u1'])
    expect(m.memberUsers.value.map((u) => u.id)).toEqual(['u2'])
    expect(m.isOwner.value).toBe(true)
  })

  it('isOwner is false before any group has been loaded', () => {
    const m = useGroupMembers({
      group: ref<Group | null>(null),
      currentUserId: ref('u1'),
      useCases: makeUseCases(),
    })
    expect(m.isOwner.value).toBe(false)
  })

  it('keeps fetchStatus ready and drops the failed user when resolving one user fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const useCases = makeUseCases({
      groups: {
        get: { execute: vi.fn(async () => makeGroup({ owners: ['u1'], members: ['u2'] })) },
      },
      users: {
        get: {
          execute: vi.fn(async ({ userId }: { userId: string }) => {
            if (userId === 'u2') throw new Error('user-get-failed')
            return makeUser({ id: userId, name: `User ${userId}` })
          }),
        },
        search: { execute: vi.fn(async () => []) },
      },
    })
    const m = useGroupMembers({
      group: ref(makeGroup()),
      currentUserId: ref('u1'),
      useCases,
    })

    await m.loadAll()

    // The failed member is silently dropped, the rest of the group still loads.
    expect(m.fetchStatus.value).toBe('ready')
    expect(m.fetchError.value).toBeNull()
    expect(m.ownerUsers.value.map((u) => u.id)).toEqual(['u1'])
    expect(m.memberUsers.value).toEqual([])
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Failed to resolve group member u2:',
      expect.any(Error),
    )

    consoleErrorSpy.mockRestore()
  })

  it('isOwner is false when the current user is not in owners[]', async () => {
    const useCases = makeUseCases({
      groups: { get: { execute: vi.fn(async () => makeGroup({ owners: ['u1'] })) } },
    })

    const m = useGroupMembers({
      group: ref(makeGroup()),
      currentUserId: ref('u2'),
      useCases,
    })
    await m.loadAll()
    expect(m.isOwner.value).toBe(false)
  })

  it('addMember runs the store action then reloads, returning true on success', async () => {
    const initial = makeGroup({ members: [] })
    const updated = makeGroup({ members: ['u3'] })
    const get = vi
      .fn<() => Promise<Group>>()
      .mockResolvedValueOnce(initial)
      .mockResolvedValueOnce(updated)

    const addMemberToGroup = vi.fn(async () => {})

    const useCases = makeUseCases({
      groups: { get: { execute: get } },
      store: {
        addMemberToGroup,
        removeMemberFromGroup: vi.fn(async () => {}),
        promoteToOwner: vi.fn(async () => {}),
      },
    })

    const m = useGroupMembers({
      group: ref(makeGroup()),
      currentUserId: ref('u1'),
      useCases,
    })
    await m.loadAll()

    const ok = await m.addMember('u3')
    expect(ok).toBe(true)
    expect(addMemberToGroup).toHaveBeenCalledWith('g1', 'u3')
    expect(m.actionStatus.value).toBe('ready')
    // Second loadAll happened: groups.get called twice.
    expect(get).toHaveBeenCalledTimes(2)
  })

  it('addMember returns false (and surfaces actionError) when the store throws', async () => {
    const useCases = makeUseCases({
      store: {
        addMemberToGroup: vi.fn(async () => {
          throw new Error('boom')
        }),
        removeMemberFromGroup: vi.fn(async () => {}),
        promoteToOwner: vi.fn(async () => {}),
      },
    })

    const m = useGroupMembers({
      group: ref(makeGroup()),
      currentUserId: ref('u1'),
      useCases,
    })

    const ok = await m.addMember('u3')
    expect(ok).toBe(false)
    expect(m.actionStatus.value).toBe('error')
    expect(m.actionError.value).toBeInstanceOf(Error)
  })

  it('returns false from add/remove/promote when no group is provided', async () => {
    const useCases = makeUseCases()
    const m = useGroupMembers({
      group: ref<Group | null>(null),
      currentUserId: ref('u1'),
      useCases,
    })
    expect(await m.addMember('u3')).toBe(false)
    expect(await m.removeMember('u3')).toBe(false)
    expect(await m.promoteToOwner('u3')).toBe(false)
  })

  it('removeMember calls the store action and reloads the group', async () => {
    const removeMemberFromGroup = vi.fn(async () => {})
    const get = vi
      .fn<() => Promise<Group>>()
      .mockResolvedValueOnce(makeGroup({ members: ['u2'] }))
      .mockResolvedValueOnce(makeGroup({ members: [] }))
    const useCases = makeUseCases({
      groups: { get: { execute: get } },
      store: {
        addMemberToGroup: vi.fn(async () => {}),
        removeMemberFromGroup,
        promoteToOwner: vi.fn(async () => {}),
      },
    })

    const m = useGroupMembers({
      group: ref(makeGroup()),
      currentUserId: ref('u1'),
      useCases,
    })
    await m.loadAll()

    const ok = await m.removeMember('u2')
    expect(ok).toBe(true)
    expect(removeMemberFromGroup).toHaveBeenCalledWith('g1', 'u2')
    expect(get).toHaveBeenCalledTimes(2)
  })

  it('promoteToOwner calls the store action and reloads the group', async () => {
    const promoteToOwner = vi.fn(async () => {})
    const get = vi
      .fn<() => Promise<Group>>()
      .mockResolvedValueOnce(makeGroup({ owners: ['u1'], members: ['u2'] }))
      .mockResolvedValueOnce(makeGroup({ owners: ['u1', 'u2'], members: [] }))
    const useCases = makeUseCases({
      groups: { get: { execute: get } },
      store: {
        addMemberToGroup: vi.fn(async () => {}),
        removeMemberFromGroup: vi.fn(async () => {}),
        promoteToOwner,
      },
    })

    const m = useGroupMembers({
      group: ref(makeGroup()),
      currentUserId: ref('u1'),
      useCases,
    })
    await m.loadAll()

    const ok = await m.promoteToOwner('u2')
    expect(ok).toBe(true)
    expect(promoteToOwner).toHaveBeenCalledWith('g1', 'u2')
    expect(get).toHaveBeenCalledTimes(2)
  })

  describe('searchAvailableUsers', () => {
    it('does not call the API and returns [] below the minimum query length', async () => {
      const search = vi.fn(async () => [makeUser()])
      const useCases = makeUseCases({ users: { get: makeGetUser(), search: { execute: search } } })

      const m = useGroupMembers({
        group: ref(makeGroup()),
        currentUserId: ref('u1'),
        useCases,
      })

      expect(await m.searchAvailableUsers('ab')).toEqual([])
      expect(search).not.toHaveBeenCalled()
    })

    it('calls users.search and filters out ids already in the group', async () => {
      const search = vi.fn(async () => [
        makeUser({ id: 'u1', name: 'Already Owner' }),
        makeUser({ id: 'u2', name: 'Already Member' }),
        makeUser({ id: 'u3', name: 'Outsider' }),
      ])
      const useCases = makeUseCases({
        groups: {
          get: { execute: vi.fn(async () => makeGroup({ owners: ['u1'], members: ['u2'] })) },
        },
        users: { get: makeGetUser(), search: { execute: search } },
      })

      const m = useGroupMembers({
        group: ref(makeGroup()),
        currentUserId: ref('u1'),
        useCases,
      })
      await m.loadAll()

      const results = await m.searchAvailableUsers('out')
      expect(search).toHaveBeenCalledWith({ query: 'out' })
      expect(results.map((u) => u.id)).toEqual(['u3'])
    })

    it('surfaces searchError and returns [] when the search call throws', async () => {
      const useCases = makeUseCases({
        users: {
          get: makeGetUser(),
          search: {
            execute: vi.fn(async () => {
              throw new Error('search-failed')
            }),
          },
        },
      })

      const m = useGroupMembers({
        group: ref(makeGroup()),
        currentUserId: ref('u1'),
        useCases,
      })

      const results = await m.searchAvailableUsers('abcdef')
      expect(results).toEqual([])
      expect(m.searchError.value).toBeInstanceOf(Error)
    })
  })
})
