import { describe, expect, it, vi } from 'vitest'
import { ref, type Ref } from 'vue'
import { usePasswordSharedAccess } from '@/composables/usePasswordSharedAccess'
import type { Group } from '@/domain/group/Group'
import type { Password, PasswordEvent } from '@/domain/password/Password'

function makePassword(overrides: Partial<Password> = {}): Password {
  return {
    id: 'p1',
    name: 'GitHub',
    folder: 'Work',
    groupId: 'g-owner',
    createdAt: '',
    lastUpdatedAt: '',
    canRead: true,
    canWrite: false,
    login: null,
    url: null,
    accessibleGroupIds: [],
    ...overrides,
  }
}

function makeGroup(overrides: Partial<Group> = {}): Group {
  return {
    id: 'g1',
    name: 'Group',
    isPersonal: false,
    userId: null,
    owners: [],
    members: ['u1'],
    ...overrides,
  }
}

function makeShareEvent(overrides: Partial<PasswordEvent> = {}): PasswordEvent {
  return {
    eventId: 'e1',
    eventType: 'PasswordSharedEvent',
    occurredOn: '2026-04-01T10:00:00Z',
    actorUserId: 'admin',
    actorEmail: 'admin@example.com',
    eventData: { shared_with_group_id: 'g1' },
    ...overrides,
  }
}

function flushMicrotasks() {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

describe('usePasswordSharedAccess', () => {
  it('does not call listEvents when the user can write in context', async () => {
    const listEvents = vi.fn()
    usePasswordSharedAccess({
      password: ref(makePassword()),
      contextGroupId: ref(undefined),
      canWriteInContext: ref(true),
      userBelongingGroups: ref([makeGroup({ id: 'g1' })]) as Ref<readonly Group[]>,
      passwords: { listEvents: { execute: listEvents } },
      users: { get: { execute: vi.fn() } },
    })
    await flushMicrotasks()
    expect(listEvents).not.toHaveBeenCalled()
  })

  it('does not load when context group is the password owner group', async () => {
    const listEvents = vi.fn()
    usePasswordSharedAccess({
      password: ref(makePassword({ groupId: 'g-owner' })),
      contextGroupId: ref('g-owner'),
      canWriteInContext: ref(false),
      userBelongingGroups: ref([makeGroup({ id: 'g-owner' })]) as Ref<readonly Group[]>,
      passwords: { listEvents: { execute: listEvents } },
      users: { get: { execute: vi.fn() } },
    })
    await flushMicrotasks()
    expect(listEvents).not.toHaveBeenCalled()
  })

  it('selects the most recent share event matching the context group', async () => {
    const events: PasswordEvent[] = [
      makeShareEvent({
        eventId: 'old',
        occurredOn: '2026-03-01T00:00:00Z',
        eventData: { shared_with_group_id: 'g1' },
      }),
      makeShareEvent({
        eventId: 'newer',
        occurredOn: '2026-04-01T00:00:00Z',
        eventData: { shared_with_group_id: 'g1' },
      }),
      makeShareEvent({
        eventId: 'other-group',
        occurredOn: '2026-04-15T00:00:00Z',
        eventData: { shared_with_group_id: 'g-other' },
      }),
    ]

    const { sharedAccessInfo } = usePasswordSharedAccess({
      password: ref(makePassword()),
      contextGroupId: ref('g1'),
      canWriteInContext: ref(false),
      userBelongingGroups: ref([makeGroup({ id: 'g1' })]) as Ref<readonly Group[]>,
      passwords: { listEvents: { execute: vi.fn(async () => events) } },
      users: { get: { execute: vi.fn(async () => ({ username: 'admin' })) } },
    })

    await flushMicrotasks()
    expect(sharedAccessInfo.value).toEqual({
      occurredOn: '2026-04-01T00:00:00Z',
      actorUsername: 'admin',
    })
  })

  it('falls back to actorEmail when the user lookup fails', async () => {
    const events = [makeShareEvent({ actorUserId: 'absent', actorEmail: 'fallback@example.com' })]
    const { sharedAccessInfo } = usePasswordSharedAccess({
      password: ref(makePassword()),
      contextGroupId: ref('g1'),
      canWriteInContext: ref(false),
      userBelongingGroups: ref([makeGroup({ id: 'g1' })]) as Ref<readonly Group[]>,
      passwords: { listEvents: { execute: vi.fn(async () => events) } },
      users: {
        get: {
          execute: vi.fn(async () => {
            throw new Error('not found')
          }),
        },
      },
    })

    await flushMicrotasks()
    expect(sharedAccessInfo.value?.actorUsername).toBe('fallback@example.com')
  })

  it('without a context group, only matches shares with one of the user belonging groups', async () => {
    const events = [
      makeShareEvent({ eventData: { shared_with_group_id: 'visible' } }),
      makeShareEvent({ eventId: 'invisible', eventData: { shared_with_group_id: 'hidden' } }),
    ]
    const { sharedAccessInfo } = usePasswordSharedAccess({
      password: ref(makePassword()),
      contextGroupId: ref(undefined),
      canWriteInContext: ref(false),
      userBelongingGroups: ref([makeGroup({ id: 'visible' })]) as Ref<readonly Group[]>,
      passwords: { listEvents: { execute: vi.fn(async () => events) } },
      users: { get: { execute: vi.fn(async () => ({ username: 'admin' })) } },
    })

    await flushMicrotasks()
    expect(sharedAccessInfo.value?.occurredOn).toBe('2026-04-01T10:00:00Z')
  })
})
