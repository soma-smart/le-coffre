import { computed, ref, watch, type Ref } from 'vue'
import type { Group } from '@/domain/group/Group'
import {
  accessibleGroupIdsFor,
  matchesPasswordQuery,
  type Password,
} from '@/domain/password/Password'
import { sortGroupsByName } from '@/utils/groupSort'
import { findGroupIdBySlug } from '@/utils/groupSlug'

export interface GroupedFolder {
  name: string
  count: number
  passwords: Password[]
}

export interface GroupedSection {
  id: string
  name: string
  isPersonal: boolean
  isOwnedByCurrentUser: boolean
  count: number
  folders: GroupedFolder[]
}

export interface PasswordFiltersDeps {
  /** Every password visible to the current user (store-fed). */
  passwords: Ref<readonly Password[]>
  /** Every group the backend returned (includes groups the user isn't in). */
  allGroups: Ref<readonly Group[]>
  /** Groups the current user belongs to (owner or member). */
  userBelongingGroups: Ref<readonly Group[]>
  /** The personal-group id for the current user, if known. */
  currentUserPersonalGroupId: Ref<string | null>
  /** The current user's id, for is-owner-of-group checks. */
  currentUserId: Ref<string | null>
  /** Whether the current user is an admin (unlocks the "all groups" view). */
  isAdmin: Ref<boolean>
  /** Whether the admin has opted into the "see every group" view. */
  adminPasswordViewEnabled: Ref<boolean>
  /** Route param: the currently-active group slug, or undefined. */
  routeGroupSlug: Ref<string | undefined>
  /** Route query: narrow the view to a single folder, or undefined. */
  routeFolderFilter: Ref<string | undefined>
}

/**
 * Pure reactive logic for the passwords listing page. Takes the minimal set of
 * refs it needs (passwords, groups, user context, route state) and returns:
 *
 * - `searchQuery` — v-model into the search input
 * - `filterableGroups` — scope of the list (admin-view vs user's own)
 * - `selectedGroupIdFromRoute` — the group id the url points at
 * - `groupedByGroupAndFolder` — the fully-shaped list sections
 * - `selectedGroupTabId` / `openFolderKey` — UI selection state
 * - `selectedGroupSection` — the section currently opened
 * - `setDefaultOpenFolderForSelectedGroup` — reset helper the container calls
 *   after a create/edit flow completes
 *
 * Everything router-aware (vault gating, modal state, fetching) stays in the
 * calling component. This composable is fully testable without Vue Router or
 * Pinia — pass plain refs.
 */
export function usePasswordFilters(deps: PasswordFiltersDeps) {
  const searchQuery = ref('')
  const selectedGroupTabId = ref<string | null>(null)
  const openFolderKey = ref<string | null>(null)

  const filterableGroups = computed<Group[]>(() => {
    if (!deps.isAdmin.value) return [...deps.userBelongingGroups.value]
    if (!deps.adminPasswordViewEnabled.value) return [...deps.userBelongingGroups.value]
    return [...deps.allGroups.value]
  })

  const selectedGroupIdFromRoute = computed<string | null>(() =>
    findGroupIdBySlug(filterableGroups.value, deps.routeGroupSlug.value),
  )

  const groupedByGroupAndFolder = computed<GroupedSection[]>(() => {
    const sortedVisibleGroups = sortGroupsByName(
      filterableGroups.value,
      deps.currentUserPersonalGroupId.value,
    )
    const groupsById = new Map<string, Group>(sortedVisibleGroups.map((g) => [g.id, g]))
    const currentUserId = deps.currentUserId.value
    const visibleGroupIds = new Set(sortedVisibleGroups.map((g) => g.id))
    const groupPasswordMap = new Map<string, Password[]>()

    for (const password of deps.passwords.value) {
      for (const groupId of accessibleGroupIdsFor(password)) {
        if (!visibleGroupIds.has(groupId)) continue
        const groupName = groupsById.get(groupId)?.name
        if (!matchesPasswordQuery(password, searchQuery.value, groupName)) continue
        if (!groupPasswordMap.has(groupId)) groupPasswordMap.set(groupId, [])
        groupPasswordMap.get(groupId)!.push(password)
      }
    }

    const sections: GroupedSection[] = []
    for (const groupId of sortedVisibleGroups.map((g) => g.id)) {
      const groupPasswords = groupPasswordMap.get(groupId)
      if (!groupPasswords || groupPasswords.length === 0) continue

      const folderMap = new Map<string, Password[]>()
      for (const password of groupPasswords) {
        const existing = folderMap.get(password.folder) ?? []
        existing.push(password)
        folderMap.set(password.folder, existing)
      }

      const folders = Array.from(folderMap.entries())
        .filter(
          ([folderName]) =>
            !deps.routeFolderFilter.value || folderName === deps.routeFolderFilter.value,
        )
        .map(([name, items]) => ({ name, count: items.length, passwords: items }))

      if (folders.length === 0) continue

      const group = groupsById.get(groupId)
      const isOwnedByCurrentUser = !!(
        group &&
        currentUserId &&
        group.owners?.includes(currentUserId)
      )

      sections.push({
        id: groupId,
        name: group?.name ?? groupId,
        isPersonal: group?.isPersonal ?? false,
        isOwnedByCurrentUser,
        count: groupPasswords.length,
        folders,
      })
    }
    return sections
  })

  const selectedGroupSection = computed<GroupedSection | null>(() => {
    if (!selectedGroupTabId.value) return null
    const existing = groupedByGroupAndFolder.value.find((s) => s.id === selectedGroupTabId.value)
    if (existing) return existing

    const selectedGroup = filterableGroups.value.find((g) => g.id === selectedGroupTabId.value)
    if (!selectedGroup) return null

    const currentUserId = deps.currentUserId.value
    return {
      id: selectedGroup.id,
      name: selectedGroup.name,
      isPersonal: selectedGroup.isPersonal,
      isOwnedByCurrentUser: !!(currentUserId && selectedGroup.owners?.includes(currentUserId)),
      count: 0,
      folders: [],
    }
  })

  function setDefaultOpenFolderForSelectedGroup() {
    const section = selectedGroupSection.value
    if (!section || section.folders.length === 0) {
      openFolderKey.value = null
      return
    }
    const defaultFolder = section.folders.find(
      (folder) => folder.name.trim().toLowerCase() === 'default',
    )
    const folderToOpen = defaultFolder ?? section.folders[0]
    openFolderKey.value = `${section.id}-${folderToOpen.name}`
  }

  watch(
    selectedGroupIdFromRoute,
    (groupId) => {
      if (!groupId) return
      if (selectedGroupTabId.value !== groupId) {
        selectedGroupTabId.value = groupId
        setDefaultOpenFolderForSelectedGroup()
      }
    },
    { immediate: true },
  )

  // When the list of sections changes, keep the tab selection coherent.
  // `immediate: true` makes the initial selection happen on first run instead
  // of waiting for the first data change — matches the behaviour the old
  // component relied on once stores populated and is easier to unit-test.
  watch(
    groupedByGroupAndFolder,
    (sections) => {
      if (sections.length === 0) {
        selectedGroupTabId.value = null
        openFolderKey.value = null
        return
      }

      if (selectedGroupIdFromRoute.value) {
        if (selectedGroupTabId.value !== selectedGroupIdFromRoute.value) {
          selectedGroupTabId.value = selectedGroupIdFromRoute.value
        }
        if (openFolderKey.value === null) setDefaultOpenFolderForSelectedGroup()
        return
      }

      if (
        !selectedGroupTabId.value ||
        !sections.some((section) => section.id === selectedGroupTabId.value)
      ) {
        const personal = sections.find((s) => s.id === deps.currentUserPersonalGroupId.value)
        selectedGroupTabId.value = personal?.id ?? sections[0].id
        setDefaultOpenFolderForSelectedGroup()
      }
    },
    { immediate: true },
  )

  function toggleFolder(folderKey: string) {
    openFolderKey.value = openFolderKey.value === folderKey ? null : folderKey
  }

  return {
    searchQuery,
    filterableGroups,
    selectedGroupIdFromRoute,
    groupedByGroupAndFolder,
    selectedGroupSection,
    selectedGroupTabId,
    openFolderKey,
    setDefaultOpenFolderForSelectedGroup,
    toggleFolder,
  }
}
