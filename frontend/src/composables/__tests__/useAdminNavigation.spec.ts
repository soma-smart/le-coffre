import { describe, expect, it } from 'vitest'
import { ref, type Ref } from 'vue'
import { useAdminNavigation, type AdminNavigationDeps } from '@/composables/useAdminNavigation'
import type { Group } from '@/domain/group/Group'

function makeGroup(overrides: Partial<Group> = {}): Group {
  return {
    id: 'g1',
    name: 'Engineering',
    isPersonal: false,
    userId: null,
    owners: ['u1'],
    members: [],
    ...overrides,
  }
}

function makeDeps(overrides: Partial<AdminNavigationDeps> = {}): AdminNavigationDeps {
  const defaults: AdminNavigationDeps = {
    allGroups: ref<Group[]>([]) as Ref<readonly Group[]>,
    userBelongingGroups: ref<Group[]>([]) as Ref<readonly Group[]>,
    currentUserPersonalGroupId: ref<string | null>(null),
    isAdmin: ref(false),
    adminPasswordViewEnabled: ref(false),
    passwordCountByGroupId: ref<Record<string, number>>({}),
  }
  return { ...defaults, ...overrides }
}

describe('useAdminNavigation', () => {
  it('myPasswordGroups returns the user belonging list, personal pinned first', () => {
    const personal = makeGroup({ id: 'p1', name: 'Personal', isPersonal: true })
    const team = makeGroup({ id: 't1', name: 'Team', isPersonal: false })
    const deps = makeDeps({
      userBelongingGroups: ref([team, personal]),
      currentUserPersonalGroupId: ref('p1'),
    })

    const { myPasswordGroups } = useAdminNavigation(deps, ref('u1'))
    expect(myPasswordGroups.value.map((g) => g.id)).toEqual(['p1', 't1'])
  })

  it('non-admins see no admin-extra groups regardless of password counts', () => {
    const own = makeGroup({ id: 'own' })
    const outside = makeGroup({ id: 'outside' })
    const deps = makeDeps({
      allGroups: ref([own, outside]),
      userBelongingGroups: ref([own]),
      passwordCountByGroupId: ref({ outside: 7 }),
      isAdmin: ref(false),
    })

    const { adminExtraPasswordGroups } = useAdminNavigation(deps, ref('u1'))
    expect(adminExtraPasswordGroups.value).toEqual([])
  })

  it('admin sees outside groups that have at least one password', () => {
    const own = makeGroup({ id: 'own' })
    const populated = makeGroup({ id: 'populated' })
    const empty = makeGroup({ id: 'empty' })
    const deps = makeDeps({
      allGroups: ref([own, populated, empty]),
      userBelongingGroups: ref([own]),
      isAdmin: ref(true),
      passwordCountByGroupId: ref({ populated: 3, empty: 0 }),
    })

    const { adminExtraPasswordGroups } = useAdminNavigation(deps, ref('u1'))
    expect(adminExtraPasswordGroups.value.map((g) => g.id)).toEqual(['populated'])
  })

  it('visiblePasswordGroups honours the admin "see all" toggle', () => {
    const own = makeGroup({ id: 'own' })
    const extra = makeGroup({ id: 'extra' })
    const deps = makeDeps({
      allGroups: ref([own, extra]),
      userBelongingGroups: ref([own]),
      isAdmin: ref(true),
      adminPasswordViewEnabled: ref(false),
      passwordCountByGroupId: ref({ extra: 1 }),
    })

    const { visiblePasswordGroups } = useAdminNavigation(deps, ref('u1'))
    expect(visiblePasswordGroups.value.map((g) => g.id)).toEqual(['own'])

    deps.adminPasswordViewEnabled.value = true
    expect(visiblePasswordGroups.value.map((g) => g.id)).toEqual(['own', 'extra'])
  })

  it('isOwnerOfGroup is false without a current user, true when in owners[]', () => {
    const deps = makeDeps()
    const { isOwnerOfGroup } = useAdminNavigation(deps, ref<string | null>(null))
    expect(isOwnerOfGroup({ owners: ['u1'] })).toBe(false)

    const withUser = useAdminNavigation(deps, ref('u1'))
    expect(withUser.isOwnerOfGroup({ owners: ['u1'] })).toBe(true)
    expect(withUser.isOwnerOfGroup({ owners: ['u2'] })).toBe(false)
  })

  it('getDefaultGroupId prefers the personal group when present', () => {
    const personal = makeGroup({ id: 'p1', isPersonal: true })
    const team = makeGroup({ id: 't1', name: 'Alpha' })
    const deps = makeDeps({
      currentUserPersonalGroupId: ref('p1'),
      userBelongingGroups: ref([personal, team]),
    })
    const { getDefaultGroupId, myPasswordGroups } = useAdminNavigation(deps, ref('u1'))
    expect(getDefaultGroupId(myPasswordGroups.value)).toBe('p1')
  })
})
