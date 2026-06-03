import { describe, expect, it } from 'vitest'
import { ref, type Ref } from 'vue'
import { usePasswordFilters, type PasswordFiltersDeps } from '@/composables/usePasswordFilters'
import type { Group } from '@/domain/group/Group'
import type { Password } from '@/domain/password/Password'

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

function makePassword(overrides: Partial<Password> = {}): Password {
  return {
    id: 'p1',
    name: 'GitHub',
    folder: 'Work',
    groupId: 'g1',
    createdAt: '2026-01-01T00:00:00Z',
    lastUpdatedAt: '2026-01-01T00:00:00Z',
    canRead: true,
    canWrite: true,
    login: null,
    url: null,
    accessibleGroupIds: [],
    ...overrides,
  }
}

function makeDeps(overrides: Partial<PasswordFiltersDeps> = {}): PasswordFiltersDeps {
  const defaults: PasswordFiltersDeps = {
    passwords: ref<Password[]>([]) as Ref<readonly Password[]>,
    allGroups: ref<Group[]>([]) as Ref<readonly Group[]>,
    userBelongingGroups: ref<Group[]>([]) as Ref<readonly Group[]>,
    currentUserPersonalGroupId: ref<string | null>(null),
    currentUserId: ref<string | null>('u1'),
    isAdmin: ref(false),
    adminPasswordViewEnabled: ref(false),
    routeGroupSlug: ref<string | undefined>(undefined),
    routeFolderFilter: ref<string | undefined>(undefined),
  }
  return { ...defaults, ...overrides }
}

describe('usePasswordFilters', () => {
  it('groups passwords by group then by folder, in sort order', () => {
    const personalGroup = makeGroup({ id: 'personal', name: 'Alice', isPersonal: true })
    const sharedGroup = makeGroup({ id: 'shared', name: 'Team', isPersonal: false })
    const deps = makeDeps({
      allGroups: ref([sharedGroup, personalGroup]),
      userBelongingGroups: ref([sharedGroup, personalGroup]),
      currentUserPersonalGroupId: ref('personal'),
      passwords: ref([
        makePassword({ id: 'p1', folder: 'Work', groupId: 'shared' }),
        makePassword({ id: 'p2', folder: 'Home', groupId: 'personal' }),
        makePassword({ id: 'p3', folder: 'Home', groupId: 'personal' }),
      ]),
    })

    const { groupedByGroupAndFolder } = usePasswordFilters(deps)

    // Personal group is pinned first.
    expect(groupedByGroupAndFolder.value.map((s) => s.id)).toEqual(['personal', 'shared'])
    expect(groupedByGroupAndFolder.value[0].folders[0]).toMatchObject({ name: 'Home', count: 2 })
    expect(groupedByGroupAndFolder.value[1].folders[0]).toMatchObject({ name: 'Work', count: 1 })
  })

  it('filters passwords via searchQuery against name/login/url/folder/group name', () => {
    const group = makeGroup({ id: 'g1', name: 'Engineering' })
    const deps = makeDeps({
      allGroups: ref([group]),
      userBelongingGroups: ref([group]),
      passwords: ref([
        makePassword({ id: 'p1', name: 'GitHub', folder: 'Work' }),
        makePassword({ id: 'p2', name: 'Netflix', folder: 'Entertainment' }),
      ]),
    })

    const { searchQuery, groupedByGroupAndFolder } = usePasswordFilters(deps)

    searchQuery.value = 'netflix'
    expect(groupedByGroupAndFolder.value[0].folders).toEqual([
      { name: 'Entertainment', count: 1, passwords: expect.any(Array) },
    ])

    searchQuery.value = ''
    expect(groupedByGroupAndFolder.value[0].folders).toHaveLength(2)
  })

  it('admin without the "see all" toggle only sees groups they belong to', () => {
    const userGroup = makeGroup({ id: 'own', name: 'Own', owners: ['u1'] })
    const outsideGroup = makeGroup({ id: 'outside', name: 'Outside', owners: ['u2'] })
    const deps = makeDeps({
      allGroups: ref([userGroup, outsideGroup]),
      userBelongingGroups: ref([userGroup]),
      isAdmin: ref(true),
      adminPasswordViewEnabled: ref(false),
      passwords: ref([
        makePassword({ id: 'p1', groupId: 'own' }),
        makePassword({ id: 'p2', groupId: 'outside' }),
      ]),
    })

    const { filterableGroups, groupedByGroupAndFolder } = usePasswordFilters(deps)
    expect(filterableGroups.value.map((g) => g.id)).toEqual(['own'])
    expect(groupedByGroupAndFolder.value.map((s) => s.id)).toEqual(['own'])
  })

  it('admin with the "see all" toggle sees every group', () => {
    const userGroup = makeGroup({ id: 'own', name: 'Own', owners: ['u1'] })
    const outsideGroup = makeGroup({ id: 'outside', name: 'Outside', owners: ['u2'] })
    const deps = makeDeps({
      allGroups: ref([userGroup, outsideGroup]),
      userBelongingGroups: ref([userGroup]),
      isAdmin: ref(true),
      adminPasswordViewEnabled: ref(true),
      passwords: ref([
        makePassword({ id: 'p1', groupId: 'own' }),
        makePassword({ id: 'p2', groupId: 'outside' }),
      ]),
    })

    const { groupedByGroupAndFolder } = usePasswordFilters(deps)
    expect(groupedByGroupAndFolder.value.map((s) => s.id).sort()).toEqual(['outside', 'own'])
  })

  it('route folder filter narrows each section down to a single folder', () => {
    const group = makeGroup({ id: 'g1' })
    const deps = makeDeps({
      allGroups: ref([group]),
      userBelongingGroups: ref([group]),
      passwords: ref([
        makePassword({ id: 'p1', folder: 'Work' }),
        makePassword({ id: 'p2', folder: 'Home' }),
      ]),
      routeFolderFilter: ref('Work'),
    })

    const { groupedByGroupAndFolder } = usePasswordFilters(deps)
    expect(groupedByGroupAndFolder.value[0].folders.map((f) => f.name)).toEqual(['Work'])
  })

  it('selects the route-specified group tab and opens the Default folder', () => {
    const target = makeGroup({ id: 'target', name: 'Target' })
    const deps = makeDeps({
      allGroups: ref([target]),
      userBelongingGroups: ref([target]),
      passwords: ref([
        makePassword({ id: 'p1', folder: 'Default', groupId: 'target' }),
        makePassword({ id: 'p2', folder: 'Other', groupId: 'target' }),
      ]),
      routeGroupSlug: ref('Target'),
    })

    const { selectedGroupTabId, openFolderKey } = usePasswordFilters(deps)
    expect(selectedGroupTabId.value).toBe('target')
    expect(openFolderKey.value).toBe('target-Default')
  })

  it('clears selection state when the visible sections become empty', async () => {
    const group = makeGroup({ id: 'g1' })
    const passwords = ref<Password[]>([makePassword({ id: 'p1', groupId: 'g1' })])
    const deps = makeDeps({
      allGroups: ref([group]),
      userBelongingGroups: ref([group]),
      passwords: passwords as Ref<readonly Password[]>,
    })

    const { selectedGroupTabId, openFolderKey, groupedByGroupAndFolder } = usePasswordFilters(deps)
    // One section was visible, so the tab is set.
    expect(groupedByGroupAndFolder.value).toHaveLength(1)
    expect(selectedGroupTabId.value).toBe('g1')

    // Empty the list → selection should reset.
    passwords.value = []
    await new Promise((r) => setTimeout(r, 0)) // flush watchers
    expect(selectedGroupTabId.value).toBeNull()
    expect(openFolderKey.value).toBeNull()
  })

  it('toggleFolder opens a closed folder and closes an open one', () => {
    const group = makeGroup({ id: 'g1' })
    const deps = makeDeps({
      allGroups: ref([group]),
      userBelongingGroups: ref([group]),
      passwords: ref([makePassword({ id: 'p1', folder: 'Work', groupId: 'g1' })]),
    })

    const { openFolderKey, toggleFolder } = usePasswordFilters(deps)
    openFolderKey.value = null
    toggleFolder('g1-Work')
    expect(openFolderKey.value).toBe('g1-Work')
    toggleFolder('g1-Work')
    expect(openFolderKey.value).toBeNull()
  })
})
