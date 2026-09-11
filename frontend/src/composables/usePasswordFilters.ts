import { computed, ref, watch, type Ref } from 'vue'
import type { Group } from '@/domain/group/Group'
import {
  accessibleGroupIdsFor,
  folderLabelOf,
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
 * - `selectedGroupTabId` — which group is currently selected
 * - `selectedGroupSection` — the section currently opened
 * - `selectedFolderName` / `visiblePasswords` / `paneTitle` / `paneCount` — the
 *   middle pane's contents, narrowed to the route's `?folder=` when set
 * - `searchResults` — every password matching `searchQuery`, across every
 *   group `filterableGroups` allows (not just the selected one)
 *
 * Everything router-aware (vault gating, modal state, fetching) stays in the
 * calling component. This composable is fully testable without Vue Router or
 * Pinia — pass plain refs.
 */
export function usePasswordFilters(deps: PasswordFiltersDeps) {
  const searchQuery = ref('')
  const selectedGroupTabId = ref<string | null>(null)

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

  /**
   * The folder narrowing the middle pane, straight from the route — `null`
   * means "whole group".
   */
  const selectedFolderName = computed<string | null>(() => deps.routeFolderFilter.value ?? null)

  /**
   * The passwords the middle pane should list: the selected group, narrowed
   * to `selectedFolderName` when set. Reuses `selectedGroupSection.folders`,
   * which the route-folder-filter loop above already prunes to that single
   * folder — so this is a flatten, not a second filtering pass.
   */
  const visiblePasswords = computed<Password[]>(() => {
    const section = selectedGroupSection.value
    if (!section) return []
    return section.folders.flatMap((folder) => folder.passwords)
  })

  /** Middle pane header: the folder name when narrowed, else the group name. */
  const paneTitle = computed<string>(() => {
    if (selectedFolderName.value) return folderLabelOf(selectedFolderName.value)
    return selectedGroupSection.value?.name ?? ''
  })

  const paneCount = computed<number>(() => visiblePasswords.value.length)

  /**
   * Global search results: every password matching `searchQuery`, across
   * every group `filterableGroups` allows (not just the selected one) — a
   * password manager's search has to find what you can't currently see.
   * Empty when the query is empty, so callers can use it to detect "search
   * mode" without re-deriving the same trim/empty check.
   */
  const searchResults = computed<Password[]>(() => {
    const query = searchQuery.value.trim()
    if (!query) return []

    const visibleGroupIds = new Set(filterableGroups.value.map((group) => group.id))
    const groupsById = new Map(filterableGroups.value.map((group) => [group.id, group]))
    const seen = new Set<string>()
    const results: Password[] = []

    for (const password of deps.passwords.value) {
      if (seen.has(password.id)) continue
      const isAccessible = accessibleGroupIdsFor(password).some((id) => visibleGroupIds.has(id))
      if (!isAccessible) continue

      const groupName = groupsById.get(password.groupId)?.name
      if (!matchesPasswordQuery(password, query, groupName)) continue

      seen.add(password.id)
      results.push(password)
    }

    return results.sort((a, b) => a.name.localeCompare(b.name))
  })

  watch(
    selectedGroupIdFromRoute,
    (groupId) => {
      if (!groupId) return
      selectedGroupTabId.value = groupId
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
        return
      }

      if (selectedGroupIdFromRoute.value) {
        if (selectedGroupTabId.value !== selectedGroupIdFromRoute.value) {
          selectedGroupTabId.value = selectedGroupIdFromRoute.value
        }
        return
      }

      if (
        !selectedGroupTabId.value ||
        !sections.some((section) => section.id === selectedGroupTabId.value)
      ) {
        const personal = sections.find((s) => s.id === deps.currentUserPersonalGroupId.value)
        selectedGroupTabId.value = personal?.id ?? sections[0].id
      }
    },
    { immediate: true },
  )

  return {
    searchQuery,
    filterableGroups,
    selectedGroupIdFromRoute,
    groupedByGroupAndFolder,
    selectedGroupSection,
    selectedGroupTabId,
    selectedFolderName,
    visiblePasswords,
    paneTitle,
    paneCount,
    searchResults,
  }
}
