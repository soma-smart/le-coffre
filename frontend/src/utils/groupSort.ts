import type { GroupItem } from '@/client/types.gen'

export type GroupSortMode = 'name' | 'count'

/**
 * Sort groups alphabetically.
 * If myPersonalGroupId is provided, that group is always pinned first.
 * Otherwise, any group flagged is_personal comes first.
 */
export function sortGroupsByName(
  groups: GroupItem[],
  myPersonalGroupId?: string | null,
): GroupItem[] {
  return [...groups].sort((a, b) => {
    if (myPersonalGroupId) {
      if (a.id === myPersonalGroupId) return -1
      if (b.id === myPersonalGroupId) return 1
    } else {
      if (a.is_personal && !b.is_personal) return -1
      if (!a.is_personal && b.is_personal) return 1
    }
    return a.name.localeCompare(b.name)
  })
}

/**
 * Sort groups by password count descending.
 * If myPersonalGroupId is provided, that group is always pinned first.
 * Otherwise, any group flagged is_personal comes first.
 * Ties between non-pinned groups broken alphabetically.
 */
export function sortGroupsByCount(
  groups: GroupItem[],
  passwordCounts: Record<string, number>,
  myPersonalGroupId?: string | null,
): GroupItem[] {
  return [...groups].sort((a, b) => {
    if (myPersonalGroupId) {
      if (a.id === myPersonalGroupId) return -1
      if (b.id === myPersonalGroupId) return 1
    } else {
      if (a.is_personal && !b.is_personal) return -1
      if (!a.is_personal && b.is_personal) return 1
    }
    const countA = passwordCounts[a.id] ?? 0
    const countB = passwordCounts[b.id] ?? 0
    if (countB !== countA) return countB - countA
    return a.name.localeCompare(b.name)
  })
}

/**
 * Sort groups according to the given mode.
 * The current user's personal group (myPersonalGroupId) is always pinned first.
 * Falls back to name sort if mode is 'count' but no counts are provided.
 */
export function sortGroups(
  groups: GroupItem[],
  mode: GroupSortMode,
  passwordCounts?: Record<string, number>,
  myPersonalGroupId?: string | null,
): GroupItem[] {
  if (mode === 'count' && passwordCounts) {
    return sortGroupsByCount(groups, passwordCounts, myPersonalGroupId)
  }
  return sortGroupsByName(groups, myPersonalGroupId)
}
