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
    isAdmin: false,
    personalGroupId: 'p-u1',
    ...overrides,
  } as User
}

function makeUseCases(overrides: Partial<GroupMembersUseCases> = {}): GroupMembersUseCases {
  return {
    users: { list: { execute: vi.fn(async () => [] as User[]) } },
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
  it('loadAll fetches users + group details and partitions them by role', async () => {
    const allUsers = [
      makeUser({ id: 'u1', name: 'Owner' }),
      makeUser({ id: 'u2', name: 'Member' }),
      makeUser({ id: 'u3', name: 'Outsider' }),
    ]
    const useCases = makeUseCases({
      users: { list: { execute: vi.fn(async () => allUsers) } },
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
    expect(m.availableUsers.value.map((u) => u.id)).toEqual(['u3'])
    expect(m.isOwner.value).toBe(true)
  })

  it('isOwner is false when the current user is not in owners[]', async () => {
    const useCases = makeUseCases({
      users: { list: { execute: vi.fn(async () => []) } },
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

    const list = vi.fn(async () => [makeUser({ id: 'u3' })])
    const addMemberToGroup = vi.fn(async () => {})

    const useCases = makeUseCases({
      users: { list: { execute: list } },
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
      users: { list: { execute: vi.fn(async () => []) } },
      groups: { get: { execute: vi.fn(async () => makeGroup()) } },
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
})
